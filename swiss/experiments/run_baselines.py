"""Task A8: baseline controllers on the Swiss district (2023, hourly, one deterministic episode).

Controllers (all stock CityLearn 3.3.0 classes, no learning):
  ALG-001 ZeroActionBaselineAgent        storage never used (uncontrolled reference)
  ALG-002 BusinessAsUsualAgent           stock BAU (EV/appliance/battery oriented; expected identical to ALG-001 here)
  ALG-003 BasicRBC                       stock: charge thermal storage 22:00-08:00, discharge otherwise
  ALG-004 HourRBC tariff-aware (rate r)  HourRBC with action_map: charge at local hours when EKZ tariff is low, discharge when high
Metrics: raw district series (kWh, kW, CHF), CityLearn KPIs from env.evaluate(), reward R-001 totals.
Run: PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py
"""
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn import __version__ as CL_VERSION  # noqa: E402
from citylearn.agents.baseline import BusinessAsUsualAgent, ZeroActionBaselineAgent  # noqa: E402
from citylearn.agents.rbc import BasicRBC, HourRBC  # noqa: E402
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.experiments.rewards import SCALES, SwissDistrictReward, TERMS  # noqa: E402

SCHEMA = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'schema.json')
RES = os.path.join(ROOT, 'swiss', 'experiments', 'results')
PRICE = pd.read_csv(os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'pricing.csv')).electricity_pricing.to_numpy()


def tariff_map(rate):
    """CityLearn hour 1..24 = local hour + 1. EKZ high tariff = weekdays 07:00-20:00 local = hours 8..20.
    HourRBC maps by hour only (no weekday) so weekends are treated like weekdays (documented approximation)."""
    m = {}
    for h in range(1, 25):
        m[h] = rate if (h <= 7 or h >= 21) else (-rate if 9 <= h <= 20 else 0.0)
    return {'heating_storage': dict(m), 'dhw_storage': dict(m)}


CONTROLLERS = {
    'ALG-001_zero_action': lambda env: ZeroActionBaselineAgent(env),
    'ALG-002_business_as_usual': lambda env: BusinessAsUsualAgent(env),
    'ALG-003_basic_rbc': lambda env: BasicRBC(env),
    'ALG-004_hour_rbc_tariff_r0.05': lambda env: HourRBC(env, action_map=tariff_map(0.05)),
    'ALG-004_hour_rbc_tariff_r0.10': lambda env: HourRBC(env, action_map=tariff_map(0.10)),
    'ALG-004_hour_rbc_tariff_r0.20': lambda env: HourRBC(env, action_map=tariff_map(0.20)),
}


def rollout(name, make_agent, scales=None):
    env = CityLearnEnv(SCHEMA, central_agent=True, reward_function=SwissDistrictReward)
    if scales is not None:
        env.unwrapped.reward_function.scales = scales if hasattr(env, 'unwrapped') else None
    agent = make_agent(env)
    obs, _ = env.reset()
    tot = {k: 0.0 for k in TERMS}; ret = 0.0
    rf = env.unwrapped.reward_function if hasattr(env, 'unwrapped') else env.reward_function
    if scales is not None:
        rf.scales = dict(scales)
    while not env.terminated:
        actions = agent.predict(obs)
        obs, reward, terminated, truncated, _ = env.step(actions)
        ret += float(np.sum(reward))
        for k in TERMS:
            tot[k] += rf.last_terms[k] if rf.last_terms else 0.0
        if terminated or truncated:
            break
    net = np.sum([np.asarray(b.net_electricity_consumption, dtype=float) for b in env.buildings], axis=0)
    imp = np.sum([np.maximum(np.asarray(b.net_electricity_consumption, dtype=float), 0) for b in env.buildings], axis=0)
    n = len(net)
    kpi = env.evaluate()
    d = kpi[kpi['level'] == 'district'].set_index('cost_function')['value'] if 'level' in kpi else pd.Series(dtype=float)
    out = {'controller': name, 'steps': int(n), 'reward_return': ret,
           'district_import_kwh': float(imp.sum()), 'district_peak_kw': float(net.max()),
           'cost_chf_excl_vat': float((imp * PRICE[:n]).sum()),
           'mean_daily_peak_kw': float(pd.Series(net).groupby(np.arange(n) // 24).max().mean()),
           'ramping_sum_kw': float(np.abs(np.diff(net)).sum()),
           'high_tariff_import_share': float(imp[PRICE[:n] > PRICE.min() + 1e-9].sum() / imp.sum())}
    for k in TERMS:
        out[f'term_{k}_sum'] = tot[k]
    for k, v in d.items():
        out[f'kpi_{k}'] = float(v) if pd.notna(v) else np.nan
    return out, tot


if __name__ == '__main__':
    os.makedirs(RES, exist_ok=True)
    # reference scales = mean per-step term under the zero-action rollout
    _, tot0 = rollout('scale_reference', CONTROLLERS['ALG-001_zero_action'])
    steps = 8759
    scales = {k: (tot0[k] / steps if tot0[k] > 0 else 1.0) for k in TERMS}
    json.dump(scales, open(SCALES, 'w'), indent=1)
    rows = []
    for name, mk in CONTROLLERS.items():
        r, _ = rollout(name, mk, scales)
        rows.append(r)
        print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in ('district_import_kwh', 'district_peak_kw', 'cost_chf_excl_vat', 'mean_daily_peak_kw', 'reward_return', 'high_tariff_import_share')}, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES, 'baselines_2023.csv'), index=False)
    meta = {'citylearn': CL_VERSION, 'python': sys.version.split()[0], 'numpy': np.__version__, 'pandas': pd.__version__,
            'git_head': subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip(),
            'scales': scales, 'schema': os.path.relpath(SCHEMA, ROOT), 'seed': 0}
    json.dump(meta, open(os.path.join(RES, 'baselines_2023_meta.json'), 'w'), indent=1)
