"""Origin-aware load forecaster for the MPC (research note section 9).

One gradient-boosting model per building maps (target-step calendar and weather features, lead time, load observed just before the origin, mean load of the last 24 h,
same hour one week and one day before the TARGET step when already observed) to the load at lead 1..H. Trained on (origin, lead) pairs whose target lies outside the test
weeks +- 1 week; the history inputs of an origin may lie anywhere in the past (that is observed information). Weather over the horizon is taken as KNOWN (A-M3).
`python swiss/experiments/mpc_forecast.py` prints the test-week nRMSE (RMSE / series standard deviation, mean over buildings) against the plain weather model."""
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402

from swiss.experiments import oracle_pvbat as o, rl  # noqa: E402

H = 48


def weather_features(inp):
    w = inp.env0.buildings[0].weather
    n = inp.N
    T = np.asarray(w.outdoor_dry_bulb_temperature, dtype=float)[:n]
    dif = np.asarray(w.diffuse_solar_irradiance, dtype=float)[:n]
    dire = np.asarray(w.direct_solar_irradiance, dtype=float)[:n]
    t = np.arange(n)
    t24 = np.convolve(T, np.ones(24) / 24, mode='full')[:n]
    return np.column_stack([t % 24, (t // 24) % 7, T, dif, dire, t24])


def rows(y, Xw, origins, lead_max=H):
    """Feature rows for every (origin g, lead k=1..lead_max): target step t = g + k - 1."""
    n = len(y)
    cs = np.concatenate([[0.0], np.cumsum(y)])
    g = np.repeat(origins, lead_max)
    k = np.tile(np.arange(1, lead_max + 1), len(origins))
    t = g + k - 1
    keep = t < n
    g, k, t = g[keep], k[keep], t[keep]
    last = y[g - 1]
    m24 = (cs[g] - cs[g - 24]) / 24.0
    wk = np.where(t - 168 < g, y[np.clip(t - 168, 0, None)], np.nan)             # same hour a week earlier: observed if before the origin
    dy = np.where(t - 24 < g, y[np.clip(t - 24, 0, None)], np.nan)
    wk2 = np.where(t - 336 < g, y[np.clip(t - 336, 0, None)], np.nan)
    X = np.column_stack([Xw[t], k, last, m24, wk, dy, wk2])
    return X, t, g


def train_mask_targets(n):
    ok = np.ones(n, dtype=bool)
    for kk in rl.TEST_WEEKS:
        ok[max(0, (kk - 1) * rl.WEEK):(kk + 2) * rl.WEEK] = False
    return ok


def fit(y, Xw, step=3):
    origins = np.arange(340, len(y) - H, step)
    X, t, g = rows(y, Xw, origins)
    ok = train_mask_targets(len(y))[t]
    m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, max_leaf_nodes=20, random_state=0)
    return m.fit(X[ok], y[t][ok])


def predict(model, y, Xw, g, h):
    X, t, _ = rows(y, Xw, np.array([g]), lead_max=h)
    return np.clip(model.predict(X), 0.0, None)


def main():
    inp = o.Inputs()
    Xw = weather_features(inp)
    origins_test = np.concatenate([np.arange(k * rl.WEEK, k * rl.WEEK + rl.WEEK, 6) for k in rl.TEST_WEEKS])
    errs, base_errs, by_lead = [], [], np.zeros(H)
    for bi in range(6):
        y = inp.net_s0[bi]
        mdl = fit(y, Xw)
        X, t, g = rows(y, Xw, origins_test)
        p = np.clip(mdl.predict(X), 0, None)
        errs.append(np.sqrt(((p - y[t]) ** 2).mean()) / y.std())
        by_lead += np.array([np.sqrt(((p[X[:, 6] == k] - y[t][X[:, 6] == k]) ** 2).mean()) / y.std() for k in range(1, H + 1)]) / 6
        print(f'building {bi}: nRMSE {errs[-1]:.2f}', flush=True)
    print('origin-aware load forecaster, test weeks, mean nRMSE', round(float(np.mean(errs)), 3), '(plain weather model: 0.68)')
    print('by lead (1,6,12,24,36,48 h):', [round(float(by_lead[k - 1]), 2) for k in (1, 6, 12, 24, 36, 48)])


if __name__ == '__main__':
    main()
