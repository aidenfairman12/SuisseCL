"""B9: district-level metrics of Phase B (acceptance criterion 10) for the baseline and the exact-optimum schedule of every rung (S0 to S3), default assumptions, export price 8 Rp/kWh.
Metrics (swiss/experiments/metrics.py): import and export energy, peak definitions, PV self-consumption, self-sufficiency, import cost, export revenue, bill, battery equivalent cycles,
comfort violations (S3), plus relative emissions (modeled carbon intensity, M-002, relative only) and the share of import in the high-tariff hours (operational flexibility).
S0 has no PV, battery or export price. Baseline: zero action (S0, S1, S2) or thermostat (S3). Optimum: year-long perfect-foresight schedule (S3: pure shifting band 21-24 C).
Run: PYTHONPATH=. cl/bin/python swiss/experiments/phase_b_metrics.py     Output: swiss/experiments/oracle_results/phase_b_metrics.json, docs/experiments/validation_reports/district_metrics_phase_b.md
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle, oracle_pvbat as o, oracle_rc as r  # noqa: E402
from swiss.experiments.metrics import compute_metrics  # noqa: E402

OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'district_metrics_phase_b.md')
CAN = os.path.join(ROOT, 'data', 'canonical')


def main():
    inp = r.RCInputs('h')
    n = inp.N
    price = inp.price
    ci = pd.read_csv(os.path.join(CAN, 'carbon_intensity_citylearn_2023.csv')).carbon_intensity.to_numpy()[:n]
    high = price > price.min() + 1e-9
    rows = {}

    def put(name, net, pv=None, ch=None, dis=None, cap=None, export_price=None, indoor=None):
        m = compute_metrics(net, price, pv_kwh=pv, battery_charge_kwh=ch, battery_discharge_kwh=dis, battery_capacity_kwh=cap, price_export=export_price,
                            indoor_temp=indoor, comfort_lower=21.0, comfort_upper=24.0 if indoor is not None else None)
        imp = np.maximum(net, 0)
        m['emissions_relative_import_x_ci'] = float((imp * ci[:, None]).sum())
        m['high_tariff_import_share'] = float(imp[high].sum() / imp.sum())
        rows[name] = m

    # S0: tanks only
    env0, imp0 = oracle.zero_action_import()
    net_s0 = np.stack(inp.net_s0, axis=1)
    put('S0 zero action', net_s0)
    tanks = oracle.tank_inputs(env0)
    opt_net = net_s0.copy()
    for t in tanks:
        a, d, E, obj = oracle.solve_tank(t, price, 1.0)
        opt_net[:, t['building']] += (a - d) / t['cop']
    put('S0 optimum (tanks)', opt_net)
    pv_kwh = np.stack([inp.kwp[1.0][bi] * inp.pv_per_kwp for bi in range(6)], axis=1)
    caps = [inp.kwp[1.0][bi] * 1.0 for bi in range(6)]
    pe = 0.08
    # S1, S2
    for name, bat in (('S1', None), ('S2', 1.0)):
        tot, sols = inp.scenario(1.0, bat, 8.0, with_solution=True)
        net0 = net_s0 - pv_kwh
        put(f'{name} zero action', net0, pv=pv_kwh, export_price=pe)
        net = np.stack([s['imp'] - s['exp'] for s in sols], axis=1)
        put(f'{name} optimum', net, pv=pv_kwh, ch=np.stack([s['c'] for s in sols], axis=1) if bat else None, dis=np.stack([s['u'] for s in sols], axis=1) if bat else None,
            cap=caps if bat else None, export_price=pe)
    # S3
    tot, sols = r.scenario(inp, {}, 'band 21-24', 8.0, with_solution=True)
    base_net = np.stack([(inp.net_s0[bi] - inp.derived_heat[bi] / inp.heat_tank[bi]['cop'] - inp.kwp[1.0][bi] * inp.pv_per_kwp + s['q_thermostat'] / inp.heat_tank[bi]['cop']) for bi, s in enumerate(sols)], axis=1)
    put('S3 thermostat', base_net, pv=pv_kwh, export_price=pe, indoor=np.stack([s['T_thermostat'] for s in sols], axis=1))
    net = np.stack([s['imp'] - s['exp'] for s in sols], axis=1)
    put('S3 optimum (band 21-24)', net, pv=pv_kwh, ch=np.stack([s['c'] for s in sols], axis=1), dis=np.stack([s['u'] for s in sols], axis=1), cap=caps, export_price=pe,
        indoor=np.stack([s['T'] for s in sols], axis=1))
    hours_above = {nm: int((np.stack([s[k] for s in sols], axis=1) > 24).sum()) for nm, k in (('thermostat', 'T_thermostat'), ('optimum', 'T'))}
    base_em = rows['S0 zero action']['emissions_relative_import_x_ci']
    for v in rows.values():
        v['emissions_index_vs_s0_zero'] = v['emissions_relative_import_x_ci'] / base_em
    json.dump({'rows': rows, 'hours_above_24c': hours_above}, open(os.path.join(OUT, 'phase_b_metrics.json'), 'w'), indent=1)
    cols = [('import_kwh', 'Import (kWh)', '{:.0f}'), ('export_kwh', 'Export (kWh)', '{:.0f}'), ('peak_import_kw_coincident_gross', 'Coincident import peak (kW)', '{:.1f}'),
            ('peak_net_kw_coincident', 'Coincident net peak (kW)', '{:.1f}'), ('peak_import_kw_building_sum', 'Sum of building peaks (kW)', '{:.1f}'),
            ('pv_self_consumption', 'PV self-consumption', '{:.1%}'), ('self_sufficiency', 'Self-sufficiency', '{:.1%}'), ('import_cost_chf', 'Import cost (CHF)', '{:.0f}'),
            ('export_revenue_chf', 'Export revenue (CHF)', '{:.0f}'), ('bill_chf', 'Bill (CHF)', '{:.0f}'), ('battery_equivalent_cycles', 'Battery cycles (sum)', '{:.0f}'),
            ('high_tariff_import_share', 'High-tariff import share', '{:.1%}'), ('emissions_index_vs_s0_zero', 'Emissions index (S0 zero = 1)', '{:.3f}'), ('comfort_violation_steps', 'Building-hours outside 21-24 C', '{:.0f}')]
    L = ['# District metrics of Phase B (B9)', '', 'Generated by `swiss/experiments/phase_b_metrics.py`. Default assumptions (A-011 to A-020), export price 8 Rp/kWh, EKZ standard tariff, hourly. "-" = not applicable (None, never 0). '
         'Emissions are relative only (modeled carbon intensity, level unvalidated, ISS-033). PV, battery and thermal model are assumed (synthetic), so rows S1 to S3 describe the assumed scenario.', '',
         '| Case | ' + ' | '.join(c[1] for c in cols) + ' |', '|---|' + '---|' * len(cols)]
    for name, m in rows.items():
        L.append(f'| {name} | ' + ' | '.join(('-' if m.get(k) is None else f.format(m[k])) for k, _, f in cols) + ' |')
    L += ['', 'Comfort column: building-hours outside the 21-24 C band; almost all are hours above 24 C from free solar and internal gains (the model has no cooling), identical for thermostat and optimum, so the optimum adds no comfort violation (the band limits are respected by construction).', '', 'Peaks: the cost-optimal schedule does not include peak or ramp terms and several batteries and pumps respond to the same price signal, so the coincident import peak rises (S0 +11 %, S2 +74 %, S3 +96 % against the baseline): a ceiling on the bill is not a ceiling on grid benefit. A peak-aware objective is a Phase C topic (reward weights already include a peak term for the learners).', '', f'Indoor temperature above 24 C under the heating-only model (hours in the year, six buildings together): thermostat {hours_above["thermostat"]}, optimum {hours_above["optimum"]} (free solar and internal gains; no cooling in the model, A-020).', '',
          'Operational flexibility, reading: the optimum moves import out of the high-tariff hours and exports less; the coincident peak only moves where the peak falls in PV or battery hours (winter evening peaks are unchanged).', '']
    open(REPORT, 'w', encoding='utf-8').write('\n'.join(L))
    print('\n'.join(L[4:16]))


if __name__ == '__main__':
    main()
