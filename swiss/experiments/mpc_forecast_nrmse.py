"""Forecast error (nRMSE = RMSE / standard deviation of the actual series, mean over the six buildings) of the forecasters used in the MPC studies, measured on the eight
held-out weeks (S2 inputs), so the Controllers page can place the weather-conditioned forecaster on the same axis as the synthetic error sweep.
Weather-conditioned models (mpc.Forecaster modes weather and weather_lag) are out of sample on the test weeks (trained outside the test weeks +- 1 week); weather is taken as known (A-028).
History-only forecasts use the lag rules of mpc_forecast_error.py (load and tank demand: same hour last week; PV: same hour yesterday) at origins every 6 h inside the test weeks,
leads 1 to 48 h. Run: PYTHONPATH=. cl/bin/python swiss/experiments/mpc_forecast_nrmse.py   Output: swiss/experiments/mpc_results/forecast_nrmse_testweeks.json"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle_pvbat as o, rl  # noqa: E402
from swiss.experiments.mpc import Forecaster  # noqa: E402

OUT = os.path.join(ROOT, 'swiss', 'experiments', 'mpc_results', 'forecast_nrmse_testweeks.json')
H = 48


def lagmean(x, g, h, period, K):
    """Mean of the K most recent same-hour values (period steps apart) that are already observed at origin g (same rule as mpc_forecast_error.py)."""
    idx = np.arange(g, g + h)
    base = np.ceil((idx - g + 1) / period).astype(int)
    return sum(x[np.clip(idx - period * (base + j), 0, None)] for j in range(K)) / K


def main():
    inp = o.Inputs()
    te = np.concatenate([np.arange(k * rl.WEEK, k * rl.WEEK + rl.WEEK) for k in rl.TEST_WEEKS])
    origins = np.concatenate([np.arange(k * rl.WEEK, k * rl.WEEK + rl.WEEK, 6) for k in rl.TEST_WEEKS])
    series = {'load': lambda bi: inp.net_s0[bi], 'pv': lambda bi: inp.kwp[1.0][bi] * inp.pv_per_kwp, 'dem': lambda bi: sum(t['demand'] for t in inp.tanks[bi])}
    res = {'unit': 'RMSE divided by the standard deviation of the actual series (whole year), mean over six buildings, eight test weeks', 'weather_known': True}
    for mode in ('weather', 'weather_lag'):
        fc = Forecaster(inp, mode)
        r = {}
        for comp, idx in (('load', 0), ('pv', -1)):
            r[comp] = float(np.mean([np.sqrt(((fc.pred[bi][idx][te] - series[comp](bi)[te]) ** 2).mean()) / series[comp](bi).std() for bi in range(6)]))
        r['dem'] = float(np.mean([np.sqrt(((sum(fc.pred[bi][1 + k][te] for k in range(len(inp.tanks[bi]))) - series['dem'](bi)[te]) ** 2).mean()) / series['dem'](bi).std() for bi in range(6)]))
        res[mode] = r
    hist = {}
    for comp, period in (('load', 168), ('pv', 24), ('dem', 168)):
        e = []
        for bi in range(6):
            x = series[comp](bi)
            se, n = 0.0, 0
            for g in origins:
                d = lagmean(x, int(g), H, period, 1) - x[g:g + H]
                se += (d ** 2).sum(); n += H
            e.append(np.sqrt(se / n) / x.std())
        hist[comp] = float(np.mean(e))
    res['history_only'] = hist
    json.dump(res, open(OUT, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
