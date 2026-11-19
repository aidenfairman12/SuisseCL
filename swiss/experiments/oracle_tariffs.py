"""Exact ceilings under the LABELLED scenario tariffs (B5, step 9): what would a richer price signal be worth? (never a claim about current Swiss prices)

For every tariff of data/canonical/tariff_scenarios_2023_hourly.csv (standard S0, EKZ time-of-use grid fee Q4 2023, EKZ time-of-use 2024 structure,
EKZ dynamic grid fee 2024 on the same dates, stylised spread x2 and x5) the exact perfect-foresight optimum is computed on
  S0  tanks only (Phase A district, no PV)           bill = import cost
  S1  + assumed PV and export price 8 Rp/kWh          (oracle_pvbat)
  S2  + assumed battery                               (oracle_pvbat)
  S3  + RC thermal model, pure shifting band 21-24    (oracle_rc)
The gate (>= 3 % of the bill) is applied per rung and tariff. The dynamics and the programs are those validated by replay in steps 6 and 8; only the price vector
changes, and the realised bill is the net series times that price (the environment does not price anything but imports and the price is not an input of the physics).
Run: PYTHONPATH=. cl/bin/python swiss/experiments/oracle_tariffs.py
Output: swiss/experiments/oracle_results/oracle_tariffs.json and docs/experiments/validation_reports/oracle_cost_bound_tariffs.md
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle, oracle_rc  # noqa: E402

OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'oracle_cost_bound_tariffs.md')
TARIFFS = pd.read_csv(os.path.join(ROOT, 'data', 'canonical', 'tariff_scenarios_2023_hourly.csv'))
LABEL = {'standard_s0': 'S0 standard two-tier (realistic baseline)', 'tou_q4_2023': 'EKZ ToU grid fee, Q4 2023 structure, all year',
         'tou_2024': 'EKZ ToU grid fee, 2024 seasonal structure on 2023', 'dyn_2024': 'EKZ dynamic grid fee 2024, same dates in 2023',
         'spread2': 'stylised: S0 spread x2', 'spread5': 'stylised: S0 spread x5'}
EXPORT_RP = 8.0
DAYAHEAD = os.path.join(ROOT, 'data', 'canonical', 'dayahead_ch_2023_hourly.csv')
LABEL['dayahead_2023'] = 'Swiss day-ahead pass-through 2023 (import: grid + spot + adder, export: spot; revenue neutral to S0)'


def s0_tanks(inp_s0, price):
    """Tanks-only optimum (Phase A program) under a price vector; returns (zero-action bill, optimum saving)."""
    env0, imp0 = inp_s0
    tanks = oracle.tank_inputs(env0)
    n = oracle.N
    saving = sum(-oracle.solve_tank(t, price[:n], 1.0)[3] for t in tanks)
    cost0 = float((imp0[:n] * price[:n]).sum())
    return cost0, saving


def run():
    inp = oracle_rc.RCInputs()
    base_price = inp.price.copy()
    s0 = oracle.zero_action_import()
    res = {'export_price_rp': EXPORT_RP, 'gate_pct': 3.0, 'tariffs': {}}
    t0 = time.time()
    for key in TARIFFS.columns[1:]:
        price = TARIFFS[key].to_numpy()[:oracle.N]
        assert price.min() * 100 >= EXPORT_RP - 1e-9, 'export price must not exceed an import price'
        inp.price = price
        r = {'label': LABEL[key], 'spread_rp': float((price.max() - price.min()) * 100), 'mean_rp': float(price.mean() * 100)}
        cost0, sav = s0_tanks(s0, price)
        r['S0'] = {'zero_bill': cost0, 'saving_chf': sav, 'saving_pct': 100 * sav / cost0}
        for name, pvr, bat in (('S1', 1.0, None), ('S2', 1.0, 1.0)):
            x = inp.scenario(pvr, bat, EXPORT_RP)
            r[name] = {'zero_bill': x['zero_bill'], 'saving_chf': x['saving_chf'], 'saving_pct': x['saving_pct']}
        x = oracle_rc.scenario(inp, {}, 'band 21-24', EXPORT_RP)
        r['S3'] = {'zero_bill': x['zero_bill'], 'saving_chf': x['saving_chf'], 'saving_pct': x['saving_pct']}
        res['tariffs'][key] = r
        print(f'{key:12s} spread {r["spread_rp"]:5.2f} Rp | ' + ' | '.join(f'{k} {r[k]["saving_pct"]:5.2f} %' for k in ('S0', 'S1', 'S2', 'S3')) + f'  [{time.time() - t0:.0f}s]', flush=True)
    # day-ahead pass-through: its own export price series (spot, floored at zero) instead of the fixed 8 Rp/kWh
    da = pd.read_csv(DAYAHEAD)
    price = da.import_chf_kwh.to_numpy()[:oracle.N]
    pexp = da.export_chf_kwh.to_numpy()[:oracle.N] * 100.0
    inp.price = price
    r = {'label': LABEL['dayahead_2023'], 'spread_rp': float((price.max() - price.min()) * 100), 'mean_rp': float(price.mean() * 100), 'export_mean_rp': float(pexp.mean())}
    cost0, sav = s0_tanks(s0, price)
    r['S0'] = {'zero_bill': cost0, 'saving_chf': sav, 'saving_pct': 100 * sav / cost0}
    for name, pvr, bat in (('S1', 1.0, None), ('S2', 1.0, 1.0)):
        x = inp.scenario(pvr, bat, pexp)
        r[name] = {'zero_bill': x['zero_bill'], 'saving_chf': x['saving_chf'], 'saving_pct': x['saving_pct']}
    x = oracle_rc.scenario(inp, {}, 'band 21-24', pexp)
    r['S3'] = {'zero_bill': x['zero_bill'], 'saving_chf': x['saving_chf'], 'saving_pct': x['saving_pct']}
    res['tariffs']['dayahead_2023'] = r
    print('dayahead_2023 spread %.1f | ' % r['spread_rp'] + ' | '.join(f'{k} {r[k]["saving_pct"]:5.2f} %' for k in ('S0', 'S1', 'S2', 'S3')), flush=True)
    inp.price = base_price
    return res


def write_report(res, path=REPORT):
    L = ['# Exact ceilings under richer tariff scenarios (what would a more dynamic price signal be worth?)', '',
         'Generated by `swiss/experiments/oracle_tariffs.py` from `swiss/experiments/oracle_results/oracle_tariffs.json`. Nothing here is typed by hand.', '',
         '**These are labelled scenarios ("what if prices varied more"), not statements about current Swiss prices.** The realistic baseline is S0 (EKZ standard two-tier tariff 2023). '
         'Time-variable products exist in Switzerland only as pilots or opt-in offers (phase_b_plan.md section 3). The EKZ pilot tariffs (time-of-use grid fee, dynamic grid fee) started on 1 October 2023, '
         'so only the structure is carried over to the other months of 2023; the 2024 dynamic fee follows 2024 grid conditions, not the 2023 weather. The last row uses the Swiss day-ahead market price of 2023 '
         '(Energy-Charts, CC BY 4.0 from Bundesnetzagentur | SMARD.de) as a retail pass-through with an assumed exchange rate (0.97 CHF/EUR) and its own export price (the spot price); it is revenue neutral to S0 so only its shape differs. '
         'Other rows: energy component is the 2023 two-tier energy tariff; export price 8 Rp/kWh (assumed, A-015).', '',
         'Share of the bill that the exact optimum (perfect foresight) can save, per scenario rung (S0 tanks only; S1 + assumed PV; S2 + assumed battery; S3 + RC thermal model, pure shifting). '
         f'Gate (D-032): at least {res["gate_pct"]:g} %.', '',
         '| Tariff | Price range (Rp/kWh) | S0 | S1 | S2 | S3 |', '|---|---|---|---|---|---|']
    for k, r in res['tariffs'].items():
        cells = []
        for rung in ('S0', 'S1', 'S2', 'S3'):
            v = r[rung]['saving_pct']
            cells.append(f'{v:.2f} % {"(pass)" if v >= res["gate_pct"] else "(below gate)"}')
        L.append(f'| {r["label"]} | spread {r["spread_rp"]:.1f}, mean {r["mean_rp"]:.1f} | ' + ' | '.join(cells) + ' |')
    L += ['', 'Absolute savings (CHF per year, district):', '', '| Tariff | S0 | S1 | S2 | S3 |', '|---|---|---|---|---|']
    for k, r in res['tariffs'].items():
        L.append(f'| {r["label"]} | ' + ' | '.join(f'{r[x]["saving_chf"]:.0f}' for x in ('S0', 'S1', 'S2', 'S3')) + ' |')
    L += ['', '## How to read it', '- S1 to S3 contain assumed PV, battery and thermal model (A-011 to A-020), so their numbers describe the assumed scenario.',
          '- The bill is net of export revenue and differs between rungs and tariffs, so shares and francs are not comparable across rows without care.',
          '- Perfect foresight: a ceiling, not a forecast. S0 under the standard tariff is the 0.84 % of Phase A.', '']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    res = run()
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, 'oracle_tariffs.json'), 'w'), indent=1)
    if a.out == OUT:
        write_report(res)
    return res


if __name__ == '__main__':
    main()
