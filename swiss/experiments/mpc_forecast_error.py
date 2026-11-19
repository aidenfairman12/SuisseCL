"""Error of simple history-only forecasters on the S2 inputs (nRMSE = RMSE / standard deviation of the series, averaged over the six buildings), leads 1..48 h,
origins every 6 h over the year. Components: net load without PV (load), PV, tank heat demand (dem)."""
import os, sys, json
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle_pvbat as o  # noqa: E402


def lagmean(x, g, h, period, K):
    idx = np.arange(g, g + h)
    base = np.ceil((idx - g + 1) / period).astype(int)
    out = np.zeros(h)
    for j in range(K):
        out += x[np.clip(idx - period * (base + j), 0, None)]
    return out / K


FC = {'day1': lambda x, g, h: lagmean(x, g, h, 24, 1), 'day3': lambda x, g, h: lagmean(x, g, h, 24, 3), 'day7': lambda x, g, h: lagmean(x, g, h, 24, 7),
      'week1': lambda x, g, h: lagmean(x, g, h, 168, 1), 'week2': lambda x, g, h: lagmean(x, g, h, 168, 2), 'week4': lambda x, g, h: lagmean(x, g, h, 168, 4)}


def main():
    inp = o.Inputs()
    res = {}
    for comp in ('load', 'pv', 'dem'):
        res[comp] = {}
        for name, f in FC.items():
            errs = []
            for bi in range(6):
                if comp == 'load': x = inp.net_s0[bi]
                elif comp == 'pv': x = inp.kwp[1.0][bi] * inp.pv_per_kwp
                else: x = sum(t['demand'] for t in inp.tanks[bi])
                se, n = 0.0, 0
                for g in range(24 * 14, inp.N - 48, 6):
                    d = f(x, g, 48) - x[g:g + 48]
                    se += (d ** 2).sum(); n += 48
                errs.append(np.sqrt(se / n) / x.std())
            res[comp][name] = float(np.mean(errs))
        print(comp, {k: round(v, 2) for k, v in res[comp].items()}, flush=True)
    json.dump(res, open(os.path.join(ROOT, 'swiss', 'experiments', 'mpc_results', 'forecast_error.json'), 'w'), indent=1)


main()
