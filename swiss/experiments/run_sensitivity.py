"""Task A9 sensitivity: how robust is the A8 conclusion to the synthetic assumptions?
Variants (datasets built by swiss/citylearn_build/build_dataset.py): reference; tanks x0.5; tanks x2; tank efficiency 0.99
(instead of 0.95); flat-COP (effective supply temperature 80 C, a deliberately flatter COP-vs-temperature curve; eta then
0.65-0.80, NOT a physical Carnot fraction - sensitivity only).
Controllers: zero action, BasicRBC, HourRBC tariff-aware r=0.10. Output: swiss/experiments/results/sensitivity_2023.csv
Run: PYTHONPATH=. cl/bin/python -I swiss/experiments/run_sensitivity.py
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.agents.baseline import ZeroActionBaselineAgent  # noqa: E402
from citylearn.agents.rbc import BasicRBC, HourRBC  # noqa: E402
from citylearn.citylearn import CityLearnEnv  # noqa: E402
from swiss.experiments.run_baselines import PRICE, tariff_map  # noqa: E402

VARIANTS = {'reference': 'swiss_district_2023', 'tanks_x0.5': 'swiss_sens_tank0.5', 'tanks_x2': 'swiss_sens_tank2',
            'tank_eff_0.99': 'swiss_sens_eff0.99', 'flat_cop_T80': 'swiss_sens_flatcop'}
CTRL = {'zero_action': lambda e: ZeroActionBaselineAgent(e), 'basic_rbc': lambda e: BasicRBC(e),
        'tariff_rbc_r0.10': lambda e: HourRBC(e, action_map=tariff_map(0.10))}


def metrics(env):
    imp = np.sum([np.maximum(np.asarray(b.net_electricity_consumption, dtype=float), 0) for b in env.buildings], axis=0)
    net = np.sum([np.asarray(b.net_electricity_consumption, dtype=float) for b in env.buildings], axis=0)
    n = len(net)
    return {'import_kwh': imp.sum(), 'peak_kw': net.max(), 'cost_chf': (imp * PRICE[:n]).sum(),
            'high_tariff_share': imp[PRICE[:n] > PRICE.min() + 1e-9].sum() / imp.sum()}


if __name__ == '__main__':
    rows = []
    for v, d in VARIANTS.items():
        schema = os.path.join(ROOT, 'swiss', 'datasets', d, 'schema.json')
        res = {}
        for c, mk in CTRL.items():
            env = CityLearnEnv(schema, central_agent=True)
            ag = mk(env); obs, _ = env.reset()
            while not env.terminated:
                obs, *_ = env.step(ag.predict(obs))
            res[c] = metrics(env)
        z = res['zero_action']
        for c, m in res.items():
            rows.append({'variant': v, 'controller': c, **{k: float(x) for k, x in m.items()},
                         'cost_vs_zero_pct': 100 * (m['cost_chf'] / z['cost_chf'] - 1),
                         'import_vs_zero_pct': 100 * (m['import_kwh'] / z['import_kwh'] - 1),
                         'peak_vs_zero_pct': 100 * (m['peak_kw'] / z['peak_kw'] - 1),
                         'high_tariff_share_pts_vs_zero': 100 * (m['high_tariff_share'] - z['high_tariff_share'])})
        print(v, 'done', flush=True)
        pd.DataFrame(rows).to_csv(os.path.join(ROOT, 'swiss', 'experiments', 'results', 'sensitivity_2023.csv'), index=False)
    print(pd.DataFrame(rows)[['variant', 'controller', 'cost_chf', 'cost_vs_zero_pct', 'import_vs_zero_pct', 'peak_vs_zero_pct', 'high_tariff_share_pts_vs_zero']].round(2).to_string())
