"""Exact perfect-foresight optimum of the BILL for scenario S3 (assumed PV + export price + battery + single-node RC thermal model with comfort band).

Per building one linear program over the year. Differences to oracle_pvbat.py (S1/S2): space heat Q_t is a decision (it was a fixed demand), the indoor
temperature T_t follows the RC model exactly (linear in Q), and a comfort band limits T_t. CityLearn semantics mirrored (checked by replay):
  Q_t  heat delivered to the room (heating_demand);  d_t  heating tank discharge serves part of Q;  a_t  tank charging heat
  heat pump output (Q - d + a) <= nominal power x COP;   heat pump electricity (Q - d + a) / COP
  T_t = e T_{t-1} + (1 - e) [T_amb + (g A I + L A + 1000 Q_t) / H],  e = exp(-3600 H / C)         (M-005, exact step)
  net_t = base_t - pv_t + (Q - d + a) / COP_h + (a2 - d2) / COP_dhw + c - u,   base_t = S0 net - derived space heat / COP_h (no PV, no battery)
Comfort band: T_t >= lower always; T_t <= upper_t = max(upper, thermostat temperature of the baseline) because the model has no cooling and the baseline itself
leaves the band when free gains are large (A-020); T_N >= setpoint (no end-of-year cool-down gain). Two band variants are reported:
  'band 20-24'  lower 20 C: the optimum may also lower the average temperature (saves energy, not only shifts it)
  'band 21-24'  lower 21 C: preheating above the setpoint only (a pure shifting ceiling, no energy saved by a colder house); the GATE uses this one
Baseline = thermostat at 21 C with the heat pump limited by its nominal output, tanks and battery idle.

Run: PYTHONPATH=. cl/bin/python swiss/experiments/oracle_rc.py
Output: swiss/experiments/oracle_results/oracle_rc.json and docs/experiments/validation_reports/oracle_cost_bound_s3.md
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.experiments import oracle, rl  # noqa: E402
from swiss.experiments.oracle_pvbat import CAN, DS, GATE_EXPORT_RP, GATE_PCT, ROLES, Inputs, battery_spec  # noqa: E402
from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402
from swiss.models.rc_building import PRIORS, calibrate_area, simulate_ideal  # noqa: E402

OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'oracle_cost_bound_s3.md')
UPPER = 24.0
BANDS = {'band 20-24': 20.0, 'band 21-24': 21.0, 'no thermal flexibility': 21.0}
UPPER_BY = {'band 20-24': 24.0, 'band 21-24': 24.0, 'no thermal flexibility': 21.0}   # last: the house may not go above the thermostat path, so only tanks and battery act


class RCInputs(Inputs):
    def __init__(self):
        super().__init__()
        import pandas as pd
        w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'))
        self.ta = w.temp_c.to_numpy()[:self.N]
        self.ghi = (w.beam_horizontal_wm2.fillna(0).clip(lower=0) + w.diffuse_wm2.fillna(0).clip(lower=0)).to_numpy()[:self.N]
        self.derived_heat = []
        for bi, b in enumerate(self.env0.buildings):
            self.derived_heat.append(np.asarray(b.heating_demand, dtype=float)[:self.N])
        self.heat_tank = [next(t for t in ts if t['kind'] == 'heating') for ts in self.tanks]
        self.dhw_tank = [next((t for t in ts if t['kind'] == 'dhw'), None) for ts in self.tanks]
        self.priors_default = dict(PRIORS)

    def area(self, bi, p):
        return calibrate_area(float(self.derived_heat[bi].sum()), self.ta, self.ghi, p)


def thermostat(inp, bi, area, p, n):
    ht = inp.heat_tank[bi]
    q, T = simulate_ideal(area, inp.ta[:n], inp.ghi[:n], p, q_max=ht['maxout'][:n])
    return q, T


def solve_rc_building(inp, bi, p, p_exp, lower, kwp, bat_kwh_per_kwp, n, band_name='band 21-24'):
    A = inp.area(bi, p)
    price = inp.price[:n]
    ta, ghi = inp.ta[:n], inp.ghi[:n]
    ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
    cop = ht['cop'][:n]
    q_th, T_th = thermostat(inp, bi, A, p, n)
    base = inp.net_s0[bi][:n] - inp.derived_heat[bi][:n] / cop - kwp * inp.pv_per_kwp[:n]
    bat = None if bat_kwh_per_kwp is None else battery_spec(kwp * bat_kwh_per_kwp)
    blocks, idx = [], {}

    def add(name, lo, hi, cost):
        idx[name] = sum(b[1] for b in blocks)
        blocks.append((name, n, np.broadcast_to(lo, (n,)), np.broadcast_to(hi, (n,)), np.broadcast_to(cost, (n,))))

    caph = ht['cap']
    add('a', 0.0, np.minimum(caph, ht['maxout'][:n]), 0.0); add('d', 0.0, caph, 0.0); add('E', 0.0, caph, 0.0)
    add('Q', 0.0, ht['maxout'][:n], 0.0)
    upper_t = np.maximum(UPPER_BY[band_name], T_th)
    add('T', np.minimum(lower, T_th), upper_t, 0.0)      # the baseline path is always feasible (the heat pump cannot always reach 21 C in extreme cold)
    if wt is not None:
        add('a2', 0.0, np.minimum(wt['cap'], wt['maxout'][:n]), 0.0); add('d2', 0.0, np.minimum(wt['cap'], wt['demand'][:n]), 0.0); add('E2', 0.0, wt['cap'], 0.0)
    if bat is not None:
        add('c', 0.0, bat['power'], 0.0); add('u', 0.0, bat['power'], 0.0); add('Eb', bat['emin'], bat['cap'], 0.0)
    add('i', 0.0, np.inf, price); add('x', 0.0, np.inf, -p_exp)
    names = [b[0] for b in blocks]
    cvec = np.concatenate([b[4] for b in blocks]); lo = np.concatenate([b[2] for b in blocks]); hi = np.concatenate([b[3] for b in blocks]).astype(float)
    # terminal temperature: no end-of-year cool-down gain
    last = idx['T'] + n - 1
    lo = lo.copy(); lo[last] = max(lo[last], min(p['setpoint_c'], T_th[-1]))
    I = sp.identity(n, format='csr'); Z = sp.csr_matrix((n, n))

    def sub(lam):
        return sp.diags([np.full(n - 1, -(1.0 - lam))], [-1], shape=(n, n), format='csr')

    def row(entries):
        m = [Z] * len(blocks)
        for name, mat in entries:
            m[names.index(name)] = mat
        return sp.hstack(m, format='csr')

    eq, beq, ub, bub = [], [], [], []
    for tag, t, qa, qd, qe in (('h', ht, 'a', 'd', 'E'), ('w', wt, 'a2', 'd2', 'E2')):
        if t is None:
            continue
        rho, lam = t['rho'], t['loss']
        eq.append(row([(qa, -rho * I), (qd, I / rho), (qe, I + sub(lam))]))
        b = np.zeros(n); b[0] = (1.0 - lam) * t['e0']; beq.append(b)
    ub.append(row([('Q', I), ('d', -I), ('a', I)])); bub.append(ht['maxout'][:n])        # heat pump output: Q - d + a <= maxout
    ub.append(row([('d', I), ('Q', -I)])); bub.append(np.zeros(n))                       # tank can only serve what the room takes: d <= Q
    if wt is not None:
        ub.append(row([('a2', I), ('d2', -I)])); bub.append(wt['maxout'][:n] - wt['demand'][:n])
    # RC: T_t - e T_{t-1} - (1-e) 1000 Q_t / H = (1-e) (T_amb + (g A I + L A) / H);  T_{-1} = setpoint
    Hh = p['H_w_per_k_m2'] * A
    e = float(np.exp(-3600.0 * p['H_w_per_k_m2'] / p['C_j_per_k_m2']))
    rhs = (1 - e) * (ta + (p['g'] * A * ghi + p['L_internal_w_m2'] * A) / Hh)
    rhs = rhs.copy(); rhs[0] += e * p['setpoint_c']
    eq.append(row([('T', I + sp.diags([np.full(n - 1, -e)], [-1], shape=(n, n), format='csr')), ('Q', -(1 - e) * 1000.0 / Hh * I)])); beq.append(rhs)
    if bat is not None:
        eq.append(row([('c', -bat['eta1'] * I), ('u', I / bat['eta1']), ('Eb', I + sub(0.0))]))
        b = np.zeros(n); b[0] = bat['e0']; beq.append(b)
    ent = [('i', I), ('x', -I), ('Q', -sp.diags(1.0 / cop)), ('a', -sp.diags(1.0 / cop)), ('d', sp.diags(1.0 / cop))]
    if wt is not None:
        ent += [('a2', -sp.diags(1.0 / wt['cop'][:n])), ('d2', sp.diags(1.0 / wt['cop'][:n]))]
    if bat is not None:
        ent += [('c', -I), ('u', I)]
    eq.append(row(ent)); beq.append(base)
    r = linprog(cvec, A_ub=sp.vstack(ub, format='csr'), b_ub=np.concatenate(bub), A_eq=sp.vstack(eq, format='csr'), b_eq=np.concatenate(beq),
                bounds=np.column_stack([lo, hi]), method='highs')
    if r.status != 0:
        raise RuntimeError(f'LP failed: {r.message}')
    x = r.x
    get = lambda nm: x[idx[nm]: idx[nm] + n]   # noqa: E731
    imp, exp = get('i'), get('x')
    # thermostat baseline bill (tanks and battery idle)
    net_base = base + q_th / cop
    zero = float((price * np.maximum(net_base, 0)).sum() - p_exp * np.maximum(-net_base, 0).sum())
    sol = {'bill': float(r.fun), 'zero_bill': zero, 'imp': imp, 'exp': exp, 'Q': get('Q'), 'a': get('a'), 'd': get('d'), 'T': get('T'), 'area': A,
           'a2': get('a2') if wt is not None else None, 'd2': get('d2') if wt is not None else None,
           'c': get('c') if bat is not None else None, 'u': get('u') if bat is not None else None, 'T_thermostat': T_th, 'q_thermostat': q_th,
           'import_kwh': float(imp.sum()), 'export_kwh': float(exp.sum()), 'T_mean': float(get('T').mean()), 'T_th_mean': float(T_th.mean())}
    return sol


def scenario(inp, p_over, band_name, p_exp_rp, pv_ratio=1.0, bat=1.0, n=None, with_solution=False):
    n = n or inp.N
    p = {**PRIORS, **p_over}
    lower = BANDS[band_name]
    tot = {'zero_bill': 0.0, 'opt_bill': 0.0, 'opt_import_kwh': 0.0, 'opt_export_kwh': 0.0}
    sols = []
    for bi in range(len(inp.net_s0)):
        s = solve_rc_building(inp, bi, p, p_exp_rp / 100.0, lower, inp.kwp[pv_ratio][bi], bat, n, band_name)
        tot['zero_bill'] += s['zero_bill']; tot['opt_bill'] += s['bill']
        tot['opt_import_kwh'] += s['import_kwh']; tot['opt_export_kwh'] += s['export_kwh']
        sols.append(s)
    tot['saving_chf'] = tot['zero_bill'] - tot['opt_bill']
    tot['saving_pct'] = 100.0 * tot['saving_chf'] / tot['zero_bill']
    tot['export_price_rp'] = p_exp_rp; tot['band'] = band_name
    return (tot, sols) if with_solution else tot


def schedule(env, inp, sols, n_total, kwp, bat_kwh_per_kwp):
    from swiss.citylearn_build.build_dataset import BATTERY
    cols = [(bi, nm) for bi, b in enumerate(env.buildings) for nm in b.active_actions]
    act = np.zeros((n_total, len(cols)))
    for j, (bi, nm) in enumerate(cols):
        s = sols[bi]; m = len(s['imp']); ht = inp.heat_tank[bi]
        if nm == 'heating_storage':
            act[:m, j] = np.clip((s['a'] - s['d']) / ht['cap'], -1, 1)
        elif nm == 'dhw_storage' and s['a2'] is not None:
            wt = inp.dhw_tank[bi]; act[:m, j] = np.clip((s['a2'] - s['d2']) / wt['cap'], -1, 1)
        elif nm == 'heating_device':
            act[:m, j] = np.clip(s['Q'] / ht['maxout'][:m], 0, 1)
        elif nm == 'electrical_storage' and s['c'] is not None:
            act[:m, j] = np.clip((s['c'] - s['u']) / (BATTERY['c_rate'] * kwp[bi] * bat_kwh_per_kwp), -1, 1)
    return act


def replay(inp, p_over, band_name, p_exp_rp, n=None):
    n = n or inp.N
    tot, sols = scenario(inp, p_over, band_name, p_exp_rp, n=n, with_solution=True)
    kwp = inp.kwp[1.0]
    env = CityLearnEnv(os.path.join(DS, 'swiss_rc_2023', 'schema.json'), central_agent=True, reward_function=SwissDistrictReward)
    ag = oracle.Replay(schedule(env, inp, sols, inp.N, kwp, 1.0))
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    net = np.stack([np.asarray(b.net_electricity_consumption, dtype=float)[:n] for b in env.buildings], axis=1)
    price = inp.price[:n]
    imp, exp = np.maximum(net, 0), np.maximum(-net, 0)
    realised = float((imp * price[:, None]).sum() - p_exp_rp / 100.0 * exp.sum())
    temps = np.stack([np.asarray(b.energy_simulation.indoor_dry_bulb_temperature, dtype=float)[:n] for b in env.buildings], axis=1)
    pred_T = np.stack([s['T'] for s in sols], axis=1)
    return {'predicted_bill_chf': tot['opt_bill'], 'realised_bill_chf': realised, 'zero_bill_chf': tot['zero_bill'],
            'rel_diff_saving_pct': 100.0 * abs((tot['zero_bill'] - realised) - tot['saving_chf']) / max(abs(tot['saving_chf']), 1e-9),
            'max_temperature_difference_k': float(np.abs(temps - pred_T).max()), 'steps': int(n)}


SWEEP_H = (1.0, 1.03, 1.5, 2.1)
SWEEP_C = (80e3, 110e3, 165e3)


def run(validate=True):
    inp = RCInputs()
    res = {'gate_pct': GATE_PCT, 'gate_export_rp': GATE_EXPORT_RP, 'bands': {}, 'sweep': [], 'replay': {}, 'export': {}}
    t0 = time.time()
    for bn in BANDS:
        r = scenario(inp, {}, bn, GATE_EXPORT_RP)
        res['bands'][bn] = r
        print(f'S3 {bn} export {GATE_EXPORT_RP:g}: thermostat bill {r["zero_bill"]:.0f} optimum {r["opt_bill"]:.0f} saving {r["saving_chf"]:.0f} = {r["saving_pct"]:.2f} % [{time.time() - t0:.0f}s]', flush=True)
    for rp in (0.0, 4.0, 12.0):
        res['export'][str(rp)] = scenario(inp, {}, 'band 21-24', rp)
        print(f'S3 band 21-24 export {rp:g}: {res["export"][str(rp)]["saving_pct"]:.2f} %', flush=True)
    for h in SWEEP_H:
        for c in SWEEP_C:
            r = scenario(inp, {'H_w_per_k_m2': h, 'C_j_per_k_m2': c}, 'band 21-24', GATE_EXPORT_RP)
            r.update({'H': h, 'C_kj': c / 1e3, 'tau_h': round(c / h / 3600.0, 1)})
            res['sweep'].append(r)
            print(f'  sweep H {h:4.2f} C {c / 1e3:4.0f} tau {c / h / 3600:5.1f} h: saving {r["saving_pct"]:.2f} % ({r["saving_chf"]:.0f} CHF) [{time.time() - t0:.0f}s]', flush=True)
    if validate:
        for bn in ('band 20-24', 'band 21-24'):
            res['replay'][bn] = replay(inp, {}, bn, GATE_EXPORT_RP, n=1500)
            r = res['replay'][bn]
            print(f'replay {bn} (1500 steps): predicted bill {r["predicted_bill_chf"]:.2f} realised {r["realised_bill_chf"]:.2f} (saving diff {r["rel_diff_saving_pct"]:.3f} %, max T diff {r["max_temperature_difference_k"]:.3f} K)', flush=True)
    g = res['bands']['band 21-24']['saving_pct']
    sw = [s['saving_pct'] for s in res['sweep']]
    res['gate'] = {'saving_pct_pure_shifting_default': g, 'passed': bool(g >= GATE_PCT), 'sweep_min_pct': min(sw), 'sweep_max_pct': max(sw),
                   'passed_all_sweep': bool(min(sw) >= GATE_PCT)}
    return res


def write_report(res, path=REPORT):
    L = ['# Exact bill optimum for scenario S3 (assumed PV, export price, battery and a single-node RC building model)', '',
         'Generated by `swiss/experiments/oracle_rc.py` from `swiss/experiments/oracle_results/oracle_rc.json`. Nothing here is typed by hand.', '',
         'S3 = S2 + the RC thermal model of M-005 (equation (1) of Melillo et al. 2021, pooled per-m2 priors, effective area calibrated to the derived annual heat; **synthetic**, no indoor-temperature data exist, ISS-004). '
         'The baseline is a thermostat at 21 C (heat pump limited by its nominal output; tanks and battery idle). Perfect foresight; comfort band as in A-020 (upper limit never below what the thermostat itself reaches, because the model has no cooling). '
         'The thermostat baseline bill differs from the S2 zero-action bill because the RC model generates the space heat instead of the derived hourly series.', '',
         f'**Gate (D-032):** at least {res["gate_pct"]:g} % of the bill at {res["gate_export_rp"]:g} Rp/kWh. The gate uses the *pure shifting* variant (lower limit 21 C: preheating only, no energy saved by a colder house).', '',
         '| Comfort band | Thermostat bill (CHF) | Optimum bill (CHF) | Best saving (CHF) | Share of the bill |', '|---|---|---|---|---|']
    for bn, v in res['bands'].items():
        L.append(f'| {bn} | {v["zero_bill"]:.0f} | {v["opt_bill"]:.0f} | {v["saving_chf"]:.0f} | {v["saving_pct"]:.2f} % |')
    g = res['gate']
    L += ['', f'**Gate result:** {g["saving_pct_pure_shifting_default"]:.2f} % with default priors, so the gate is **{"PASSED" if g["passed"] else "NOT passed (negative result)"}**. '
          f'Across the sweep below the share ranges from {g["sweep_min_pct"]:.2f} % to {g["sweep_max_pct"]:.2f} %; the gate is {"passed" if g["passed_all_sweep"] else "NOT passed"} at every swept parameter set.', '',
          '## Sensitivity to the export price (band 21-24)', '', '| Export price (Rp/kWh) | Thermostat bill | Optimum bill | Saving | Share |', '|---|---|---|---|---|']
    for rp, v in sorted(res['export'].items(), key=lambda kv: float(kv[0])):
        L.append(f'| {float(rp):g} | {v["zero_bill"]:.0f} | {v["opt_bill"]:.0f} | {v["saving_chf"]:.0f} | {v["saving_pct"]:.2f} % |')
    L += ['', f'## Sweep of the thermal priors (band 21-24, export price {res["gate_export_rp"]:g} Rp/kWh; effective areas recalibrated for every H)', '',
          '| H (W/Km2) | C (kJ/Km2) | Time constant (h) | Saving (CHF) | Share of the bill |', '|---|---|---|---|---|']
    for s in res['sweep']:
        L.append(f'| {s["H"]:g} | {s["C_kj"]:g} | {s["tau_h"]:g} | {s["saving_chf"]:.0f} | {s["saving_pct"]:.2f} % |')
    L += ['', '## Replay in CityLearn (first 1,500 steps, default priors)', '', '| Band | Predicted bill | Realised bill | Difference (share of saving) | Max temperature difference (K) |', '|---|---|---|---|---|']
    for bn, r in res['replay'].items():
        L.append(f'| {bn} | {r["predicted_bill_chf"]:.2f} | {r["realised_bill_chf"]:.2f} | {r["rel_diff_saving_pct"]:.3f} % | {r["max_temperature_difference_k"]:.3f} |')
    L += ['', '## How to read it', '- The thermal flexibility here belongs to an assumed building: C is an unverified class value, between-building differences are not modelled (pooled priors), and the heat level is anchored to a derived (not measured) series.',
          '- "no thermal flexibility" keeps the house on the thermostat path (tanks and battery act only): the difference to "band 21-24" is what building thermal mass adds. A saving that exceeds the "band 21-24" figure in the "band 20-24" row comes from letting the house run colder on average (energy saved), not from shifting.',
          '- Perfect foresight: this is a ceiling, not a forecast of what a learned controller reaches.', '']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    res = run()
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, 'oracle_rc.json'), 'w'), indent=1)
    if a.out == OUT:
        write_report(res)
    return res


if __name__ == '__main__':
    main()
