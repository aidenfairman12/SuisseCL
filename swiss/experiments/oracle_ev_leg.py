"""B8 EV charging and B6 local electricity community (LEG): labelled scenarios on S2 (assumed PV and battery), exact optima by linear program.
These are LP-level scenarios: the CityLearn environment has no EV or LEG in this dataset, so there is no replay for them (decision D-045); the physical balance of every building is
the validated S2 balance plus the EV load, and the bill identities are tested in swiss/tests/test_ev_leg.py.

EV (B8). Measured data: the EKZ EV charging station meter 198511 (an apartment building with 5 housing units, 6,428 kWh in 2023, hourly profile from the 15-minute file; 1.7 % of quarters
missing are filled with the mean of the same hour and day type). The meter aggregates several vehicles, so one EV per housing unit is ASSUMED (profile / 5, about 1,285 kWh per year per EV).
EVs are assigned to SFH-mid and SFH-high only: SFH-low's measured household electricity already contains EV charging (ISS-026), adding one would double count. Keep separate from
measured loads: the EV load is added on top of the S2 net consumption and reported separately.
Flexibility (assumed): the vehicle is plugged in every day from 17:00 to 08:00 local time; the energy the measured profile delivers inside that window must still be delivered inside
it (arrival-to-departure window, no V2G), at most 7.4 kW; charging outside the window stays as measured and fixed.
Variants per rung: no EV; EV uncontrolled (measured shape) with everything else optimised; EV flexible.

LEG (B6). Framework facts (reported from EKZ document "Voraussetzungen fuer die Bildung und die Teilnahme an einer LEG", read 2026-11-18, and DSO notices; the statutory text itself was not
read): since 1 January 2026 (StromVG art. 17d ff., StromVV art. 19e ff.), participants in one municipality, on the same grid level and supplied by the same substation, with communicating smart
meters and generation of at least 5 % of the connection power, may trade self-generated electricity freely among themselves; the grid-use tariff is discounted by 40 % on the internally
exchanged energy (20 % if a voltage transformation is needed); residual supply stays with the supplier. Physical flows are unchanged; only the financial allocation changes.
Model (assumptions, labelled): the six buildings form one LEG (they are a composite, not real neighbours); the discount delta = 0.4; in every step internal exchange s = min(sum exports,
sum imports) is allocated pro rata; buyers pay the internal price p_leg plus (1 - delta) x grid fee on the internal share instead of energy plus grid fee; sellers receive p_leg instead of the export
price; p_leg = 9 Rp/kWh (between the 8 Rp/kWh export price and the 10.35 Rp/kWh energy price, assumed). For the district total p_leg cancels: gain per internal kWh = energy price + delta x grid fee
- export price. Levies other than the grid fee and administration fees are not modelled. The joint optimum uses one program for all buildings.
Run: PYTHONPATH=. cl/bin/python swiss/experiments/oracle_ev_leg.py   Output: swiss/experiments/oracle_results/ev_leg.json and docs/experiments/validation_reports/ev_leg_scenarios.md
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.optimize import linprog

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle_pvbat as o  # noqa: E402

OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'ev_leg_scenarios.md')
EV_METER = 198511
EV_UNITS = 5
EV_BUILDINGS = {1: 'SFH-mid', 2: 'SFH-high'}
PLUG_FROM, PLUG_TO = 17, 8        # local hours: plugged in from 17:00 to 08:00 next day (assumed)
P_EV_KW = 7.4                     # assumed maximum charging power
DELTA = 0.4
P_LEG = 0.09
EXPORT_RP = 8.0


def ev_profile(n, dt_h=1.0):
    d = pd.read_csv(os.path.join(ROOT, 'data', 'raw', 'ekz', 'extracted', 'smart_meter_data', f'{EV_METER}.csv'), sep=';', parse_dates=['timestamp_utc']).set_index('timestamp_utc')
    q = d['kWh_to_installation']['2022-12-31 23:00':'2023-12-31 22:45']
    h = q.groupby(q.index.floor('1h')).sum(min_count=4)
    loc = h.index.tz_convert('Europe/Zurich')
    dt = np.where(loc.dayofweek < 5, 'wd', 'we')
    key = pd.Series(list(zip(loc.hour, dt)), index=h.index)
    fill = h.groupby(key).transform('mean')
    filled = h.fillna(fill)
    return (filled / EV_UNITS).to_numpy()[:n], int(h.isna().sum())


def windows_for(n, loc_hour, loc_date):
    """Plug-in windows (start, end exclusive) covering hours >= 17 of day d and < 08 of day d+1, fully inside [0, n)."""
    out, cur = [], None
    in_win = (loc_hour >= PLUG_FROM) | (loc_hour < PLUG_TO)
    k = 0
    while k < n:
        if in_win[k]:
            j = k
            while j < n and in_win[j]:
                j += 1
            out.append((k, j))
            k = j
        else:
            k += 1
    full = [(a, b) for (a, b) in out if (b - a) >= 10]       # drop truncated windows at the ends of the year
    return full


def build_ev(inp, n=None):
    n = n or inp.N
    base, n_missing = ev_profile(n)
    import pandas as pd2
    w = pd2.read_csv(os.path.join(ROOT, 'data', 'canonical', 'tariff_ekz_standard_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    loc = pd2.DatetimeIndex(w.timestamp_utc).tz_convert('Europe/Zurich')[:n]
    wins = windows_for(n, loc.hour.to_numpy(), loc.date)
    cap = np.zeros(n); fixed = base.copy(); windows = []
    for a, b in wins:
        e = float(base[a:b].sum())
        assert e <= P_EV_KW * (b - a) + 1e-9
        cap[a:b] = P_EV_KW * inp.dt_h
        fixed[a:b] = 0.0
        windows.append((a, b, e))
    return {bi: {'base': base, 'fixed': fixed, 'cap': cap, 'windows': windows} for bi in EV_BUILDINGS}, {'annual_kwh_per_ev': float(base.sum()), 'missing_hours_filled': n_missing,
            'windows': len(windows), 'shiftable_share': float(sum(w[2] for w in windows) / base.sum())}


def leg_district(inp, ev, flexible_ev, delta, p_exp_rp=EXPORT_RP, n=None):
    """Joint optimum of all buildings with a LEG (delta=0 gives the plain joint optimum, same value as the sum of separate optima)."""
    n = n or inp.N
    p_exp = p_exp_rp / 100.0
    price = inp.price[:n]
    tar = pd.read_csv(os.path.join(ROOT, 'data', 'canonical', 'tariff_ekz_standard_2023_hourly.csv'))
    e_t = tar.energy_rp_kwh.to_numpy()[:n] / 100.0
    g_t = tar.grid_rp_kwh.to_numpy()[:n] / 100.0
    gain = np.maximum(e_t + delta * g_t - p_exp, 0.0)                        # CHF per internally exchanged kWh (district level; p_leg cancels)
    lps, zero_nets = [], []
    for bi in range(len(inp.net_s0)):
        kwp = inp.kwp[1.0][bi]
        net0 = inp.net_s0[bi][:n] - kwp * inp.pv_per_kwp[:n]
        bat = o.battery_spec(kwp * 1.0, inp.dt_h)
        tanks = [{**t, **{k: t[k][:n] for k in ('cop', 'maxout', 'demand')}} for t in inp.tanks[bi]]
        evb = ev.get(bi) if ev else None
        zero_nets.append(net0 + (evb['base'][:n] if evb else 0.0))
        if evb is not None and flexible_ev:
            lps.append(o.solve_building(net0 + evb['fixed'][:n], price, p_exp, tanks, bat, ev={'cap': evb['cap'][:n], 'windows': evb['windows']}, build_only=True))
        else:
            lps.append(o.solve_building(zero_nets[-1], price, p_exp, tanks, bat, build_only=True))
    offs = np.cumsum([0] + [lp['nv'] for lp in lps])
    nvb = int(offs[-1])
    c = np.concatenate([lp['c'] for lp in lps] + [-gain])
    lo = np.concatenate([lp['lo'] for lp in lps] + [np.zeros(n)]); hi = np.concatenate([lp['hi'] for lp in lps] + [np.full(n, np.inf)])
    A_eq = sp.block_diag([lp['A_eq'] for lp in lps] + [sp.csr_matrix((0, n))], format='csr'); b_eq = np.concatenate([lp['b_eq'] for lp in lps])
    A_ub0 = sp.block_diag([lp['A_ub'] for lp in lps] + [sp.csr_matrix((0, n))], format='csr'); b_ub0 = np.concatenate([lp['b_ub'] for lp in lps])
    I = sp.identity(n, format='csr')
    cols_x = [offs[k] + lps[k]['idx']['x'] for k in range(len(lps))]; cols_i = [offs[k] + lps[k]['idx']['i'] for k in range(len(lps))]
    def stack(cols):
        m = sp.csr_matrix((n, nvb + n))
        for cc in cols:
            m = m + sp.hstack([sp.csr_matrix((n, cc)), I, sp.csr_matrix((n, nvb + n - cc - n))], format='csr')
        return m
    S = sp.hstack([sp.csr_matrix((n, nvb)), I], format='csr')
    A_ub = sp.vstack([A_ub0, S - stack(cols_x), S - stack(cols_i)], format='csr'); b_ub = np.concatenate([b_ub0, np.zeros(2 * n)])
    r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=np.column_stack([lo, hi]), method='highs')
    if r.status != 0:
        raise RuntimeError(r.message)
    x = r.x
    sols = [o.unpack(lps[k], x[offs[k]:offs[k + 1]]) for k in range(len(lps))]
    s_t = x[nvb:]
    imp = sum(s['imp'] for s in sols); exp = sum(s['exp'] for s in sols)
    bill_no_leg = sum(s['bill'] for s in sols)
    # zero-action district bill with and without the LEG
    z_imp = sum(np.maximum(z, 0) for z in zero_nets); z_exp = sum(np.maximum(-z, 0) for z in zero_nets)
    z_bill = sum(o.zero_bill(z, price, p_exp) for z in zero_nets)
    z_s = np.minimum(z_imp, z_exp)
    return {'bill_with_leg': float(r.fun), 'bill_before_leg_credit': float(bill_no_leg), 'internal_kwh': float(s_t.sum()), 'import_kwh': float(imp.sum()), 'export_kwh': float(exp.sum()),
            'sharing_share_of_import': float(s_t.sum() / imp.sum()), 'zero_bill': float(z_bill), 'zero_bill_with_leg': float(z_bill - (gain * z_s).sum()), 'zero_internal_kwh': float(z_s.sum()),
            'zero_import_kwh': float(z_imp.sum()), 'gain_chf_per_kwh_mean': float(gain.mean())}


def main():
    t0 = time.time()
    inp = o.Inputs()
    ev, evinfo = build_ev(inp)
    res = {'ev_info': evinfo, 'export_price_rp': EXPORT_RP, 'delta': DELTA, 'p_leg_chf_kwh': P_LEG, 'ev': {}, 'leg': {}}
    # --- EV on S2
    base = inp.scenario(1.0, 1.0, EXPORT_RP)
    unc = inp.scenario(1.0, 1.0, EXPORT_RP, ev={bi: {**v, 'flexible': False} for bi, v in ev.items()})
    flex = inp.scenario(1.0, 1.0, EXPORT_RP, ev=ev)
    res['ev'] = {'S2_no_ev': {k: base[k] for k in ('zero_bill', 'opt_bill', 'saving_pct')},
                 'S2_ev_uncontrolled_others_optimised': {k: unc[k] for k in ('zero_bill', 'opt_bill', 'saving_pct')},
                 'S2_ev_flexible': {k: flex[k] for k in ('zero_bill', 'opt_bill', 'saving_pct')},
                 'ev_flexibility_value_chf': float(unc['opt_bill'] - flex['opt_bill']), 'ev_flexibility_value_pct_of_zero_bill': float(100 * (unc['opt_bill'] - flex['opt_bill']) / flex['zero_bill'])}
    print('EV', json.dumps(res['ev'])[:600], round(time.time() - t0), flush=True)
    # --- LEG on S2 (no EV) and on S2 with flexible EVs; delta sweep
    for label, evx, flexible in (('S2', None, False), ('S2_with_flexible_ev', ev, True)):
        res['leg'][label] = {}
        for d in (0.0, 0.2, 0.4):
            r = leg_district(inp, evx, flexible, d)
            res['leg'][label][str(d)] = r
            print('LEG', label, d, {k: round(v, 1) for k, v in r.items() if k in ('bill_with_leg', 'zero_bill_with_leg', 'internal_kwh')}, round(time.time() - t0), flush=True)
    json.dump(res, open(os.path.join(OUT, 'ev_leg.json'), 'w'), indent=1)
    write_report(res)


def write_report(res):
    e = res['ev']; i = res['ev_info']
    L = ['# EV charging (B8) and local electricity community (B6): labelled scenarios on S2', '',
         'Generated by `swiss/experiments/oracle_ev_leg.py` from `swiss/experiments/oracle_results/ev_leg.json`. Nothing here is typed by hand. **Both are LP-level scenarios without CityLearn replay (D-045): the environment has no EV or LEG components in this dataset.** Assumptions are listed in the script header and in A-026 to A-029.', '',
         '## EV charging', '',
         f'Measured shape: EKZ EV charging station meter 198511 (5 housing units), one EV per unit assumed, {i["annual_kwh_per_ev"]:.0f} kWh per EV and year, {i["missing_hours_filled"]} hours filled; vehicles in SFH-mid and SFH-high only (SFH-low already contains EV charging in its measured load, ISS-026). Plug-in window 17:00 to 08:00 every day, at most 7.4 kW, no V2G (all assumed); {100 * i["shiftable_share"]:.0f} % of the energy is charged inside the window and can be shifted.', '',
         '| Case (S2, export 8 Rp/kWh) | Zero-action bill (CHF) | Optimum bill (CHF) | Saving vs zero action |', '|---|---|---|---|']
    for k, lab in (('S2_no_ev', 'no EV (as step 6)'), ('S2_ev_uncontrolled_others_optimised', 'EV charges as measured, tanks and battery optimised'), ('S2_ev_flexible', 'EV charging also optimised')):
        v = e[k]
        L.append(f'| {lab} | {v["zero_bill"]:.0f} | {v["opt_bill"]:.0f} | {v["saving_pct"]:.2f} % |')
    L += ['', f'Value of EV flexibility on top of the other optimised devices: **{e["ev_flexibility_value_chf"]:.0f} CHF per year** ({e["ev_flexibility_value_pct_of_zero_bill"]:.2f} % of the zero-action bill).', '',
          '## Local electricity community (LEG)', '',
          'All six buildings form one LEG (hypothetical: they are a composite, not neighbours; the real conditions are same municipality, grid level and substation). Physical flows at every meter are unchanged; the financial allocation changes: internally exchanged energy is paid at the internal price and the grid-use tariff on it is discounted (EKZ: 40 %, 20 % if a transformation is needed). District total gain per internal kWh = energy price + discount x grid fee - export price (the internal price cancels between buyers and sellers).', '',
          '| Case | Discount | Zero-action bill, no LEG | Zero-action bill with LEG | Optimum with LEG | Internal exchange (kWh) | Share of imports bought internally |', '|---|---|---|---|---|---|---|']
    for label, d in res['leg'].items():
        for dl, r in d.items():
            L.append(f'| {label} | {float(dl) * 100:.0f} % | {r["zero_bill"]:.0f} | {r["zero_bill_with_leg"]:.0f} | {r["bill_with_leg"]:.0f} | {r["internal_kwh"]:.0f} | {100 * r["sharing_share_of_import"]:.1f} % |')
    L += ['', 'A discount of 0 % still lets buyers replace the energy price by the internal price and sellers earn more than the export price, but the district total only shows the energy-price-minus-export-price margin. '
          'The LEG changes who pays, not what flows: a controller can profit from it by keeping exports and imports in the same steps (more internal exchange), which the joint optimum does.', '',
          '## Limits', '- LEG: framework facts come from the EKZ conditions document and DSO notices, not from the statute; administration fees, other levies and the real community structure are not modelled; the buildings are a composite.',
          '- EV: one aggregate charging-station profile divided by an assumed number of vehicles; plug-in times and vehicle batteries are assumptions; no replay in CityLearn.', '']
    open(REPORT, 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    main()
