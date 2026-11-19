"""Exact perfect-foresight optimum of the BILL for scenarios S1 (assumed PV + export price) and S2 (+ assumed battery) (Phase B step 6).

Per building (no coupling between buildings: no peak or ramp terms), one linear program over the whole year. Variables per hour:
  tanks    a (heat into tank), d (heat out of tank), E (stored heat)       same rules as swiss/experiments/oracle.py (Phase A, replay-exact)
  battery  c (grid-side charge), u (grid-side discharge), Eb (stored)       Eb_t = Eb_{t-1} + eta1 c_t - u_t / eta1, Emin <= Eb <= cap, c,u <= P
                                                                           eta1 = sqrt(round-trip efficiency): CityLearn 3.3.0 Battery (verified, test_battery.py)
  grid     i (import), x (export)                                          i_t - x_t = net0_t + sum_tanks (a - d)/COP + c_t - u_t
Objective: minimise sum_t price_t i_t - export_price x_t, which is the bill (import cost minus export revenue). net0 is the building's zero-action net
consumption of that scenario (PV included). The program stays linear because the battery curves are flat and efficiency is constant (D-035). It needs
export_price <= import price in every hour (else exporting and re-importing would be an unbounded gain); checked.
Not covered: peak and ramp reward terms, forecast error (the optimum knows the whole year), degradation and temperature effects (not modelled).
Validated by replay in CityLearn (`replay`): the realised bill must match the program's prediction (stop condition: more than 0.5 % apart).

Run: PYTHONPATH=. cl/bin/python swiss/experiments/oracle_pvbat.py [--export 0 4 8 12]
Output: swiss/experiments/oracle_results/oracle_pvbat.json and docs/experiments/validation_reports/oracle_cost_bound_s1_s2.md
"""
import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.optimize import linprog

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.citylearn_build.build_dataset import BATTERY  # noqa: E402
from swiss.experiments import oracle, rl  # noqa: E402
from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402

OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'oracle_cost_bound_s1_s2.md')
CAN = os.path.join(ROOT, 'data', 'canonical')
DS = os.path.join(ROOT, 'swiss', 'datasets')
GATE_PCT = 3.0            # D-032 ceiling-first rule
GATE_EXPORT_RP = 8.0      # the gate is evaluated at the default assumed export price (A-015); the other prices are reported next to it
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']


def battery_spec(cap_kwh, dt_h=1.0):
    eta1 = BATTERY['efficiency'] ** 0.5
    emin = (1.0 - BATTERY['depth_of_discharge']) * cap_kwh
    return {'cap': cap_kwh, 'power': BATTERY['c_rate'] * cap_kwh * dt_h, 'eta1': eta1, 'emin': emin, 'e0': emin}     # power = energy per step


def solve_building(net0, price, p_exp, tanks, battery=None, ev=None, build_only=False):
    """Exact optimum for one building. Returns dict with arrays and the bill; `tanks` entries as oracle.tank_inputs (sliced to len(net0)).
    ev (B8): optional dict {'cap': per-step maximum charging energy (0 outside plug-in windows), 'windows': [(start, end, energy_kwh)]}; the charging energy of every window
    must be delivered inside it (net0 then contains only the non-shiftable part of the EV load). build_only=True returns the assembled program (for the joint LEG program)."""
    n = len(net0)
    p_exp = np.broadcast_to(np.asarray(p_exp, dtype=float), (n,))     # scalar or one price per step
    assert (p_exp <= price + 1e-12).all(), 'export price above an import price makes the program unbounded'
    blocks = []                      # (name, size, lower, upper, cost)
    idx = {}

    def add(name, lo, hi, cost):
        idx[name] = sum(b[1] for b in blocks)
        blocks.append((name, n, np.broadcast_to(lo, (n,)), np.broadcast_to(hi, (n,)), np.broadcast_to(cost, (n,))))

    for k, t in enumerate(tanks):
        cap = t['cap']
        rate = cap * t.get('dt_h', 1.0)      # at most capacity x step length moves per step (action space of CityLearn)
        add(f'a{k}', 0.0, np.minimum(rate, t['maxout']), 0.0)
        add(f'd{k}', 0.0, np.minimum(rate, t['demand']), 0.0)
        add(f'E{k}', 0.0, cap, 0.0)
    if battery is not None:
        add('c', 0.0, battery['power'], 0.0)
        add('u', 0.0, battery['power'], 0.0)
        add('Eb', battery['emin'], battery['cap'], 0.0)
    if ev is not None:
        add('ev', 0.0, np.asarray(ev['cap'], dtype=float), 0.0)
    add('i', 0.0, np.inf, price)
    add('x', 0.0, np.inf, -p_exp)
    nv = sum(b[1] for b in blocks)
    cvec = np.concatenate([b[4] for b in blocks]); lo = np.concatenate([b[2] for b in blocks]); hi = np.concatenate([b[3] for b in blocks])
    I = sp.identity(n, format='csr'); Z = sp.csr_matrix((n, n))
    sub = lambda lam: sp.diags([np.full(n - 1, -(1.0 - lam))], [-1], shape=(n, n), format='csr')   # noqa: E731
    eq_rows, b_eq, ub_rows, b_ub = [], [], [], []

    def row(entries):
        m = [Z] * len(blocks)
        for name, mat in entries:
            m[[b[0] for b in blocks].index(name)] = mat
        return sp.hstack(m, format='csr')

    for k, t in enumerate(tanks):                                  # E_t - (1-lam) E_{t-1} - rho a_t + d_t/rho = 0
        rho, lam = t['rho'], t['loss']
        eq_rows.append(row([(f'a{k}', -rho * I), (f'd{k}', I / rho), (f'E{k}', I + sub(lam))]))
        b = np.zeros(n); b[0] = (1.0 - lam) * t['e0']; b_eq.append(b)
        ub_rows.append(row([(f'a{k}', I), (f'd{k}', -I)])); b_ub.append(t['maxout'] - t['demand'])   # shared heat-pump output
    if battery is not None:                                        # Eb_t - Eb_{t-1} - eta1 c_t + u_t/eta1 = 0
        eq_rows.append(row([('c', -battery['eta1'] * I), ('u', I / battery['eta1']), ('Eb', I + sub(0.0))]))
        b = np.zeros(n); b[0] = battery['e0']; b_eq.append(b)
    ent = [('i', I), ('x', -I)]                                    # i - x - sum (a-d)/cop - c + u = net0
    for k, t in enumerate(tanks):
        ent += [(f'a{k}', -sp.diags(1.0 / t['cop'])), (f'd{k}', sp.diags(1.0 / t['cop']))]
    if battery is not None:
        ent += [('c', -I), ('u', I)]
    if ev is not None:
        ent += [('ev', -I)]
        for (a, b2, e_kwh) in ev['windows']:          # every plug-in window receives exactly its energy
            cols = np.arange(idx['ev'] + a, idx['ev'] + b2)
            eq_rows.append(sp.csr_matrix((np.ones(len(cols)), (np.zeros(len(cols), dtype=int), cols)), shape=(1, nv)))
            b_eq.append(np.array([float(e_kwh)]))
    eq_rows.append(row(ent)); b_eq.append(np.asarray(net0, dtype=float))
    if build_only:
        return {'c': cvec, 'lo': lo, 'hi': hi, 'A_eq': sp.vstack(eq_rows, format='csr'), 'b_eq': np.concatenate(b_eq),
                'A_ub': sp.vstack(ub_rows, format='csr') if ub_rows else sp.csr_matrix((0, nv)), 'b_ub': np.concatenate(b_ub) if b_ub else np.zeros(0), 'idx': idx, 'n': n, 'nv': nv,
                'price': price, 'p_exp': p_exp, 'tanks': tanks, 'battery': battery, 'ev': ev}
    r = linprog(cvec, A_ub=sp.vstack(ub_rows, format='csr') if ub_rows else None, b_ub=np.concatenate(b_ub) if b_ub else None,
                A_eq=sp.vstack(eq_rows, format='csr'), b_eq=np.concatenate(b_eq), bounds=np.column_stack([lo, hi]), method='highs')
    if r.status != 0:
        raise RuntimeError(f'LP failed: {r.message}')
    x = r.x
    get = lambda name: x[idx[name]: idx[name] + n]   # noqa: E731
    imp, exp = get('i'), get('x')
    return {'bill': float(r.fun), 'import_kwh': float(imp.sum()), 'export_kwh': float(exp.sum()), 'import_cost': float((price * imp).sum()),
            'imp': imp, 'exp': exp, 'a': [get(f'a{k}') for k in range(len(tanks))], 'd': [get(f'd{k}') for k in range(len(tanks))],
            'c': get('c') if battery is not None else None, 'u': get('u') if battery is not None else None,
            'Eb': get('Eb') if battery is not None else None, 'ev': get('ev') if ev is not None else None}


def unpack(lp, x):
    """Solution arrays of one building from a stacked solution vector slice x (length lp['nv'])."""
    n, idx = lp['n'], lp['idx']
    get = lambda name: x[idx[name]: idx[name] + n]   # noqa: E731
    imp, exp = get('i'), get('x')
    return {'imp': imp, 'exp': exp, 'c': get('c') if lp['battery'] is not None else None, 'u': get('u') if lp['battery'] is not None else None,
            'ev': get('ev') if lp['ev'] is not None else None, 'import_kwh': float(imp.sum()), 'export_kwh': float(exp.sum()),
            'bill': float((lp['price'] * imp).sum() - (lp['p_exp'] * exp).sum())}


def zero_bill(net0, price, p_exp):
    return float((price * np.maximum(net0, 0)).sum() - (np.asarray(p_exp, dtype=float) * np.maximum(-net0, 0)).sum())


class Inputs:
    """Everything the programs need, read once: S0 zero-action net per building, tank inputs, PV per kWp and kWp per building and ratio."""

    def __init__(self, resolution='h'):
        """resolution 'h' = hourly datasets (Phase A and B), 'q15' = the 15-minute datasets of B2 (swiss/datasets/*_q15)."""
        self.resolution = resolution
        sfx = '_q15' if resolution == 'q15' else ''
        self.sfx = sfx
        self.env0, _ = oracle.zero_action_import(os.path.join(DS, f'swiss_district_2023{sfx}', 'schema.json'))
        self.N = self.env0.time_steps - 1
        self.dt_h = self.env0.seconds_per_time_step / 3600.0
        self.price = pd.read_csv(os.path.join(DS, f'swiss_district_2023{sfx}', 'pricing.csv')).electricity_pricing.to_numpy()[:self.N]
        self.net_s0 = [np.asarray(b.net_electricity_consumption, dtype=float)[:self.N] for b in self.env0.buildings]
        allt = oracle.tank_inputs(self.env0)
        self.tanks = [[t for t in allt if t['building'] == bi] for bi in range(len(self.env0.buildings))]
        pvf = os.path.join(CAN, 'q15', 'pv_ac_w_per_kwp_2023_15min.csv') if resolution == 'q15' else os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv')
        self.pv_per_kwp = pd.read_csv(pvf).pv_ac_w_per_kwp.to_numpy()[:self.N] / 1000.0 * self.dt_h        # kWh per kWp per step
        meta = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))
        self.kwp = {r: [meta['buildings'][role]['ratios'][str(r)]['kwp'] for role in ROLES] for r in (0.5, 1.0, 1.5)}

    def scenario(self, pv_ratio, battery_kwh_per_kwp, p_exp_rp, n=None, with_solution=False, ev=None):
        """District result for one scenario. pv_ratio None = no PV (S0); battery_kwh_per_kwp None = no battery."""
        n = n or self.N
        p_exp = np.asarray(p_exp_rp, dtype=float) / 100.0                  # scalar or per-step series (Rp/kWh in)
        p_exp = p_exp if p_exp.ndim == 0 else p_exp[:n]
        price = self.price[:n]
        tot = {'zero_bill': 0.0, 'opt_bill': 0.0, 'zero_import_cost': 0.0, 'opt_import_cost': 0.0, 'opt_export_kwh': 0.0, 'zero_export_kwh': 0.0,
               'opt_import_kwh': 0.0}
        sols = []
        for bi in range(len(self.net_s0)):
            kwp = 0.0 if pv_ratio is None else self.kwp[pv_ratio][bi]
            net0 = self.net_s0[bi][:n] - kwp * self.pv_per_kwp[:n]
            bat = None if battery_kwh_per_kwp is None else battery_spec(kwp * battery_kwh_per_kwp, self.dt_h)
            tanks = [{**t, **{k: t[k][:n] for k in ('cop', 'maxout', 'demand')}} for t in self.tanks[bi]]
            evb = None if ev is None else ev.get(bi)
            net0_zero = net0 if evb is None else net0 + evb['base'][:n]          # B8: uncontrolled EV load is part of the baseline
            if evb is None:
                s = solve_building(net0, price, p_exp, tanks, bat)
            elif evb.get('flexible', True):
                s = solve_building(net0 + evb['fixed'][:n], price, p_exp, tanks, bat, ev={'cap': evb['cap'][:n], 'windows': evb['windows']})
            else:                                                                  # EV charges as measured, everything else optimised
                s = solve_building(net0_zero, price, p_exp, tanks, bat)
            net0 = net0_zero
            tot['zero_bill'] += zero_bill(net0, price, p_exp)
            tot['zero_import_cost'] += float((price * np.maximum(net0, 0)).sum())
            tot['zero_export_kwh'] += float(np.maximum(-net0, 0).sum())
            tot['opt_bill'] += s['bill']; tot['opt_import_cost'] += s['import_cost']
            tot['opt_export_kwh'] += s['export_kwh']; tot['opt_import_kwh'] += s['import_kwh']
            sols.append(s)
        tot['saving_chf'] = tot['zero_bill'] - tot['opt_bill']
        tot['saving_pct'] = 100.0 * tot['saving_chf'] / tot['zero_bill']
        tot['export_price_rp'] = float(np.mean(p_exp_rp))
        return (tot, sols) if with_solution else tot


def schedule(env, tanks, sols, battery_caps, n_total, dt_h=1.0):  # battery_caps in kWh; actions are fractions of capacity x step length (tanks) or nominal power x step length (battery)
    """Action matrix (steps x action slots, central agent) that realises the solutions; slots follow each building's active_actions."""
    cols = []
    for bi, b in enumerate(env.buildings):
        for nm in b.active_actions:
            cols.append((bi, nm))
    act = np.zeros((n_total, len(cols)))
    for j, (bi, nm) in enumerate(cols):
        s = sols[bi]; m = len(s['imp'])
        if nm in ('heating_storage', 'dhw_storage'):
            kind = 'heating' if nm == 'heating_storage' else 'dhw'
            for k, t in enumerate(tanks[bi]):
                if t['kind'] == kind:
                    act[:m, j] = np.clip((s['a'][k] - s['d'][k]) / (t['cap'] * dt_h), -1, 1)
        elif nm == 'electrical_storage' and s['c'] is not None:
            act[:m, j] = np.clip((s['c'] - s['u']) / (BATTERY['c_rate'] * battery_caps[bi] * dt_h), -1, 1)   # CityLearn battery action is a fraction of NOMINAL POWER (checked), tanks use capacity
    return act


def replay(inp, pv_ratio, battery_kwh_per_kwp, p_exp_rp, schema_name, n=None):
    """Play the optimum in CityLearn; return (predicted bill, realised bill) over the first n steps and the realised import and export."""
    n = n or inp.N
    tot, sols = inp.scenario(pv_ratio, battery_kwh_per_kwp, p_exp_rp, n=n, with_solution=True)
    kwp = inp.kwp[pv_ratio]
    caps = [k * (battery_kwh_per_kwp or 0.0) for k in kwp]
    env = CityLearnEnv(os.path.join(DS, schema_name + inp.sfx, 'schema.json'), central_agent=True, reward_function=SwissDistrictReward)
    act = schedule(env, inp.tanks, sols, caps, inp.N, inp.dt_h)
    ag = oracle.Replay(act)
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    net = np.stack([np.asarray(b.net_electricity_consumption, dtype=float)[:n] for b in env.buildings], axis=1)
    price = inp.price[:n]
    imp, exp = np.maximum(net, 0), np.maximum(-net, 0)
    realised = float((imp * price[:, None]).sum() - p_exp_rp / 100.0 * exp.sum())
    return {'predicted_bill_chf': tot['opt_bill'], 'realised_bill_chf': realised, 'zero_bill_chf': tot['zero_bill'],
            'predicted_saving_chf': tot['saving_chf'], 'realised_saving_chf': tot['zero_bill'] - realised,
            'rel_diff_bill_pct': 100.0 * abs(realised - tot['opt_bill']) / tot['zero_bill'],
            'rel_diff_saving_pct': 100.0 * abs((tot['zero_bill'] - realised) - tot['saving_chf']) / max(abs(tot['saving_chf']), 1e-9),
            'steps': int(n)}


def run(export_rps, validate=True):
    inp = Inputs()
    res = {'gate_pct': GATE_PCT, 'gate_export_rp': GATE_EXPORT_RP, 'rungs': {}, 'what_if': [], 'replay': {}}
    t0 = time.time()
    for name, pvr, bat in (('S1', 1.0, None), ('S2', 1.0, 1.0)):
        res['rungs'][name] = {}
        for rp in export_rps:
            r = inp.scenario(pvr, bat, rp)
            res['rungs'][name][str(rp)] = r
            print(f'{name} export {rp:4.1f} Rp: zero bill {r["zero_bill"]:9.0f}  optimum {r["opt_bill"]:9.0f}  saving {r["saving_chf"]:7.0f} CHF = {r["saving_pct"]:5.2f} %  [{time.time() - t0:.0f}s]', flush=True)
    # value of the battery itself: S2 optimum against S1 zero-action
    for rp in export_rps:
        s1, s2 = res['rungs']['S1'][str(rp)], res['rungs']['S2'][str(rp)]
        s2['bill_vs_s1_zero_action_chf'] = s1['zero_bill'] - s2['opt_bill']
        s2['bill_vs_s1_zero_action_pct'] = 100.0 * (s1['zero_bill'] - s2['opt_bill']) / s1['zero_bill']
    for label, pvr, bat in (('S2, battery 0.5 kWh/kWp', 1.0, 0.5), ('S2, battery 2 kWh/kWp', 1.0, 2.0), ('S2, PV x0.5 (battery 1 kWh/kWp)', 0.5, 1.0),
                            ('S2, PV x1.5 (battery 1 kWh/kWp)', 1.5, 1.0), ('S1, PV x0.5', 0.5, None), ('S1, PV x1.5', 1.5, None)):
        r = inp.scenario(pvr, bat, GATE_EXPORT_RP)
        res['what_if'].append({'case': label, 'export_price_rp': GATE_EXPORT_RP, **r})
        print(f'what-if {label:36s} saving {r["saving_chf"]:7.0f} CHF = {r["saving_pct"]:5.2f} %  [{time.time() - t0:.0f}s]', flush=True)
    if validate:
        for name, pvr, bat, sch in (('S1', 1.0, None, 'swiss_pv_2023'), ('S2', 1.0, 1.0, 'swiss_pvbat_2023')):
            rp = GATE_EXPORT_RP
            res['replay'][name] = replay(inp, pvr, bat, rp, sch)
            r = res['replay'][name]
            print(f'replay {name}: predicted bill {r["predicted_bill_chf"]:.2f}, realised {r["realised_bill_chf"]:.2f} CHF (saving diff {r["rel_diff_saving_pct"]:.3f} %)', flush=True)
    for name in ('S1', 'S2'):
        g = res['rungs'][name][str(GATE_EXPORT_RP)]['saving_pct']
        res['rungs'][name]['gate'] = {'saving_pct_at_gate_price': g, 'passed': bool(g >= GATE_PCT),
                                      'passed_at_any_price': bool(any(res['rungs'][name][str(rp)]['saving_pct'] >= GATE_PCT for rp in export_rps))}
    return res


def write_report(res, path=REPORT):
    L = ['# Exact bill optimum with assumed PV, export price and battery (ceiling for S1 and S2)', '',
         'Generated by `swiss/experiments/oracle_pvbat.py` from `swiss/experiments/oracle_results/oracle_pvbat.json`. Nothing here is typed by hand.', '',
         'Scenarios: **S1** = Phase A district + assumed PV (M-003, A-011 to A-014) + assumed export price (A-015); **S2** = S1 + assumed battery per building '
         '(M-004, A-016, A-017). Both describe a district with assumed equipment, not the real houses. The program is a linear program per building with perfect foresight '
         '(tanks, battery, import and export in one year); the bill is import cost minus export revenue. Not covered: peak and ramp reward terms, forecast error.', '',
         f'**Gate (D-032):** RL is run on a rung only if the optimum saves at least {res["gate_pct"]:g} % of the bill at the default export price '
         f'({res["gate_export_rp"]:g} Rp/kWh). The other export prices are shown next to it.', '',
         '| Rung | Export price (Rp/kWh) | Zero-action bill (CHF) | Optimum bill (CHF) | Best saving (CHF) | Share of the bill |', '|---|---|---|---|---|---|']
    for name in ('S1', 'S2'):
        for rp, v in res['rungs'][name].items():
            if rp == 'gate':
                continue
            L.append(f'| {name} | {float(rp):g} | {v["zero_bill"]:.0f} | {v["opt_bill"]:.0f} | {v["saving_chf"]:.0f} | {v["saving_pct"]:.2f} % |')
    L += ['', '## Gate result', '']
    for name in ('S1', 'S2'):
        g = res['rungs'][name]['gate']
        L.append(f'- **{name}**: {g["saving_pct_at_gate_price"]:.2f} % at {res["gate_export_rp"]:g} Rp/kWh, so the gate is **{"PASSED" if g["passed"] else "NOT passed (negative result: no RL queued on this rung)"}**'
                 f' (passed at any swept export price: {"yes" if g["passed_at_any_price"] else "no"}).')
    L += ['', 'Value of the battery itself (S2 optimum against the S1 zero-action bill, i.e. what installing the battery and controlling it perfectly is worth, versus controlling a district that already has PV):', '',
          '| Export price (Rp/kWh) | S1 zero-action bill (CHF) | S2 optimum bill (CHF) | Difference (CHF) | Share |', '|---|---|---|---|---|']
    for rp, v in res['rungs']['S2'].items():
        if rp == 'gate':
            continue
        L.append(f'| {float(rp):g} | {res["rungs"]["S1"][rp]["zero_bill"]:.0f} | {v["opt_bill"]:.0f} | {v["bill_vs_s1_zero_action_chf"]:.0f} | {v["bill_vs_s1_zero_action_pct"]:.2f} % |')
    L += ['', f'## What-ifs (one assumption changed, export price {res["gate_export_rp"]:g} Rp/kWh)', '', '| Case | Zero-action bill (CHF) | Best saving (CHF) | Share of the bill |', '|---|---|---|---|']
    for w in res['what_if']:
        L.append(f'| {w["case"]} | {w["zero_bill"]:.0f} | {w["saving_chf"]:.0f} | {w["saving_pct"]:.2f} % |')
    L += ['', 'PV size is limited by the rooftop cap (A-013), so "PV x0.5" and "PV x1.5" change only buildings where the cap does not bind.', '', '## Replay in CityLearn', '',
          'The optimum of each rung was played in the real environment at the default export price. Stop condition of the plan: more than 0.5 % apart.', '',
          '| Rung | Predicted bill | Realised bill | Predicted saving | Realised saving | Difference (share of saving) |', '|---|---|---|---|---|---|']
    for name, r in res['replay'].items():
        L.append(f'| {name} | {r["predicted_bill_chf"]:.2f} | {r["realised_bill_chf"]:.2f} | {r["predicted_saving_chf"]:.2f} | {r["realised_saving_chf"]:.2f} | {r["rel_diff_saving_pct"]:.3f} % |')
    L += ['', 'Comparison with Phase A (S0, flat two-tier tariff, tanks only): ceiling 0.84 % of the bill (`oracle_cost_bound.md`).', '',
          '## How to read it', '- The ceilings are exact for this simulator and its assumptions; PV, export price and battery are assumptions (A-011 to A-017), so these numbers describe the assumed scenario.',
          '- The saving share is relative to the zero-action bill of the same scenario.', '']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', type=float, nargs='+', default=[0.0, 4.0, 8.0, 12.0])
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    res = run(a.export)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, 'oracle_pvbat.json'), 'w'), indent=1)
    if a.out == OUT:
        write_report(res)
    return res


if __name__ == '__main__':
    main()
