"""Receding-horizon MPC on the held-out weeks (research note docs/phases/control_methods_shortlist.md, method 1).

Every step the exact bill LP of `oracle_pvbat.solve_building` is re-solved per building over the next H hours from the state CityLearn reports now (tank and battery
energy), with FORECASTS in place of the future; only the first step's action is sent to CityLearn (a subclass-free agent; CityLearn is not edited). The plant is the real
CityLearn environment, so model mismatch (forecast error, clipping) shows up in the realised bill. Scored with `rl.window_metrics` on `rl.TEST_WEEKS`, same warm-up as the RL
protocol, so results compare directly with `rl.py`, the PV rule and the exact optimum on the same weeks.

Forecast modes (ASSUMPTIONS, labelled):
  perfect   the true future (isolates the loss of the finite horizon and the receding structure)
  naive     only data up to the previous step: net load without PV and tank demand = same hour one week earlier; PV = same hour one day earlier.
            Weather-driven heat-pump COP and maximum output are taken as known (a weather forecast with no error: ASSUMPTION A-M1).
  noisy     perfect + synthetic Gaussian error of `level` x the year's standard deviation, fixed per target step (synthetic, labelled), on net load, PV and tank demand.
Terminal value: stored energy at the end of the horizon is credited at the lowest tariff price (battery: x eta1; tank heat: / COP x rho), so the plan does not dump storage at
the horizon end (ASSUMPTION A-M2; `tv` scales it, 0 disables).

Run: PYTHONPATH=. cl/bin/python swiss/experiments/mpc.py --scenario s2 --mode naive --horizon 48 [--level 0.3] [--weeks 3 10 ...] --out swiss/experiments/mpc_results
"""
import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
from scipy.optimize import linprog

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle_pvbat as o, rl  # noqa: E402

EXPORT = 0.08
OUT = os.path.join(ROOT, 'swiss', 'experiments', 'mpc_results')


class Forecaster:
    """Returns, for building bi and global steps [g, g+h), the forecast of (net0 incl. PV, tank demand list)."""

    def __init__(self, inp, mode, level=0.0, seed=0, perfect_parts=(), rc=False, stoch=False, err_scale=1.0):
        self.inp, self.mode, self.level, self.stoch, self.err_scale = inp, mode, level, stoch, err_scale
        self.tk = (lambda bi: [t for t in inp.tanks[bi] if t['kind'] == 'dhw']) if rc else (lambda bi: inp.tanks[bi])      # rc: space heat is a decision, only DHW demand is forecast
        self.pv = {bi: inp.kwp[1.0][bi] * inp.pv_per_kwp for bi in range(len(inp.net_s0))}
        self.load = {bi: inp.net_s0[bi] - (inp.derived_heat[bi] / inp.heat_tank[bi]['cop'] if rc else 0.0) for bi in range(len(inp.net_s0))}   # zero-action net WITHOUT PV (rc: and without space heat)
        self.perfect_parts = tuple(perfect_parts)
        self.pred = self._fit_weather(lag=(mode == 'weather_lag')) if mode in ('weather', 'weather_lag') else None
        rng = np.random.default_rng(seed)
        self.eps = {bi: rng.standard_normal((1 + len(self.tk(bi)) + 1, inp.N)) for bi in range(len(inp.net_s0))}   # rows: load, tanks..., pv
        self.std = {bi: ([self.load[bi].std()] + [t['demand'].std() for t in self.tk(bi)] + [self.pv[bi].std()]) for bi in range(len(inp.net_s0))}

    def _fit_weather(self, lag=False):
        """Weather-conditioned forecasters (gradient boosting per building and component), trained on every step outside the test weeks +- 1 week (out-of-sample on the tests).
        The weather itself (temperature, direct and diffuse irradiance) is taken as KNOWN over the horizon: a day-ahead weather forecast with no error (ASSUMPTION A-M3)."""
        from sklearn.ensemble import HistGradientBoostingRegressor
        w = self.inp.env0.buildings[0].weather
        T = np.asarray(w.outdoor_dry_bulb_temperature, dtype=float)[:self.inp.N]
        dif = np.asarray(w.diffuse_solar_irradiance, dtype=float)[:self.inp.N]
        dire = np.asarray(w.direct_solar_irradiance, dtype=float)[:self.inp.N]
        n = self.inp.N
        t = np.arange(n)
        t24 = np.convolve(T, np.ones(24) / 24, mode='full')[:n]
        X = np.column_stack([t % 24, (t // 24) % 7, T, dif, dire, t24])
        train = np.ones(n, dtype=bool)
        for k in rl.TEST_WEEKS:
            train[max(0, (k - 1) * rl.WEEK):(k + 2) * rl.WEEK] = False
        out = {}
        for bi in range(len(self.inp.net_s0)):
            comps = [self.load[bi]] + [t_['demand'] for t_ in self.tk(bi)] + [self.pv[bi]]
            out[bi] = []
            for ci, y in enumerate(comps):
                Xc = X
                if lag and ci < len(comps) - 1:                      # history features of the target itself: same hour 1 and 2 weeks earlier (observed before any lead <= 168 h)
                    l1 = np.concatenate([np.full(168, y[:168].mean()), y[:-168]]); l2 = np.concatenate([np.full(336, y[:336].mean()), y[:-336]])
                    Xc = np.column_stack([X, l1, l2, (l1 + l2) / 2])
                m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, max_leaf_nodes=15, random_state=0).fit(Xc[train], y[train])
                out[bi].append(np.clip(m.predict(Xc), 0.0, None) if y.min() >= 0 else m.predict(Xc))
        if self.stoch:                                                    # out-of-sample residuals of the training weeks (4 blocked folds by week): error samples for scenarios
            wk = t // rl.WEEK
            elig = np.unique(wk[train])
            fold = {w: i % 4 for i, w in enumerate(elig)}
            fid = np.array([fold.get(w, -1) for w in wk])
            self.resid, self.valid = {}, train.copy()
            for bi in range(len(self.inp.net_s0)):
                comps = [self.load[bi]] + [t_['demand'] for t_ in self.tk(bi)] + [self.pv[bi]]
                self.resid[bi] = []
                for y in comps:
                    r = np.full(n, np.nan)
                    for f in range(4):
                        tr = train & (fid != f)
                        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, max_leaf_nodes=15, random_state=0).fit(X[tr], y[tr])
                        te = fid == f
                        r[te] = y[te] - np.clip(m.predict(X[te]), 0.0, None)
                    self.resid[bi].append(r)
        return out

    def sample_starts(self, g, h, K):
        """K start steps of error blocks of length h from the training weeks, aligned on the hour of day of g (common to all buildings: errors are correlated across them)."""
        n = self.inp.N
        ok = np.isnan(self.resid[0][0]) == False  # noqa: E712
        cs = np.concatenate([[0], np.cumsum(~ok)])
        cand = np.array([s0 for s0 in range(g % 24, n - h, 24) if cs[s0 + h] - cs[s0] == 0])
        rng = np.random.default_rng(g)
        return rng.choice(cand, size=K, replace=len(cand) < K)

    def scenarios(self, bi, g, h, starts):
        """Forecast + sampled error blocks: list of (net0, demand list) for the given starts."""
        p = self.pred[bi]
        out = []
        for s0 in starts:
            load = p[0][g:g + h] + self.err_scale * self.resid[bi][0][s0:s0 + h]
            pv = np.clip(p[-1][g:g + h] + self.err_scale * self.resid[bi][-1][s0:s0 + h], 0.0, None)
            dem = [np.clip(p[1 + k][g:g + h] + self.err_scale * self.resid[bi][1 + k][s0:s0 + h], 0.0, None) for k in range(len(self.tk(bi)))]
            out.append((load - pv, dem))
        return out

    def get(self, bi, g, h):
        sl = slice(g, g + h)
        tanks = self.tk(bi)
        if self.mode in ('weather', 'weather_lag'):
            p = self.pred[bi]
            load = self.load[bi][sl] if 'load' in self.perfect_parts else p[0][sl]
            pv = self.pv[bi][sl] if 'pv' in self.perfect_parts else p[-1][sl]
            dem = [t['demand'][sl] if 'dem' in self.perfect_parts else p[1 + k][sl] for k, t in enumerate(tanks)]
            return load - pv, dem
        if self.mode == 'perfect':
            return self.load[bi][sl] - self.pv[bi][sl], [t['demand'][sl] for t in tanks]
        if self.mode == 'noisy':
            e, s, L = self.eps[bi], self.std[bi], self.level
            load = self.load[bi][sl] + L * s[0] * e[0, sl]
            pv = np.clip(self.pv[bi][sl] + L * s[-1] * e[-1, sl], 0.0, None)
            dem = [np.clip(t['demand'][sl] + L * s[1 + k] * e[1 + k, sl], 0.0, None) for k, t in enumerate(tanks)]
            return load - pv, dem
        if self.mode == 'naive':
            idx = np.arange(g, g + h)
            pv_idx = np.clip(idx - 24 * np.ceil((idx - g + 1) / 24.0).astype(int), 0, None)   # latest same-hour value that is already observed (g-1 and earlier)
            wk = np.minimum(idx - 168 * np.ceil((idx - g + 1) / 168.0).astype(int), g - 1).clip(0, None)
            return self.load[bi][wk] - self.pv[bi][pv_idx], [t['demand'][wk] for t in tanks]
        raise ValueError(self.mode)


class MPCAgent:
    def __init__(self, env, s0, inp, fc, horizon=48, tv=1.0, peak_w=0.0, K=1, share=1):
        self.share = share
        self.env, self.s0, self.inp, self.fc, self.H, self.tv, self.peak_w, self.K = env, s0, inp, fc, horizon, tv, peak_w, K
        self.p_low = float(inp.price.min())
        self.n_act = [list(b.active_actions) for b in env.buildings]
        self.solve_s = 0.0

    def _state(self, b, t):
        """Energy in kWh before step t: tanks (heating, dhw) and battery."""
        out = {}
        for kind in ('heating', 'dhw'):
            tank = getattr(b, f'{kind}_storage')
            cap = float(tank.capacity)
            if cap > 0:
                out[kind] = (float(tank.soc[t - 1]) if t > 0 else float(tank.initial_soc)) * cap
        bat = b.electrical_storage
        cap = float(bat.capacity)
        out['bat'] = ((float(bat.soc[t - 1]) if t > 0 else float(bat.initial_soc)) * cap) if cap > 0 else None
        return out

    def _lp(self, bi, b, t, g, fcst=None):
        """Assemble the horizon LP of one building (forecasts in, CityLearn state in); the terminal credit is already in the cost vector."""
        inp = self.inp
        h = min(self.H, inp.N - g)
        st = self._state(b, t)
        net0, dem = fcst if fcst is not None else self.fc.get(bi, g, h)
        tanks = []
        for k, tk in enumerate(inp.tanks[bi]):
            tanks.append({**tk, 'cop': tk['cop'][g:g + h], 'maxout': tk['maxout'][g:g + h], 'demand': dem[k], 'e0': st[tk['kind']]})
        bat = None
        if st['bat'] is not None:
            bat = o.battery_spec(inp.kwp[1.0][bi] * 1.0, inp.dt_h)
            bat['e0'] = min(max(st['bat'], bat['emin']), bat['cap'])
        price = inp.price[g:g + h]
        lp = o.solve_building(net0, price, EXPORT, tanks, bat, build_only=True)
        c, idx = lp['c'].copy(), lp['idx']
        if self.tv > 0:                                                    # credit the stored energy at the horizon end
            for k, tk in enumerate(tanks):
                c[idx[f'E{k}'] + h - 1] -= self.tv * self.p_low * tk['rho'] / float(tk['cop'][-1])
            if bat is not None:
                c[idx['Eb'] + h - 1] -= self.tv * self.p_low * bat['eta1']
        lp['c'] = c
        return lp, tanks, bat

    def _first_actions(self, b, x, lp, tanks, bat):
        idx, inp = lp['idx'], self.inp
        first = lambda name: float(x[idx[name]])   # noqa: E731
        return {'tanks': {tk['kind']: (first(f'a{k}') - first(f'd{k}')) / (tk['cap'] * inp.dt_h) for k, tk in enumerate(tanks)},
                'bat': ((first('c') - first('u')) / (float(b.electrical_storage.nominal_power) * inp.dt_h)) if bat is not None else 0.0}

    def plan_building(self, bi, b, t, g):
        lp, tanks, bat = self._lp(bi, b, t, g)
        r = linprog(lp['c'], A_ub=lp['A_ub'] if lp['A_ub'].shape[0] else None, b_ub=lp['b_ub'] if lp['b_ub'].shape[0] else None, A_eq=lp['A_eq'], b_eq=lp['b_eq'],
                    bounds=np.column_stack([lp['lo'], lp['hi']]), method='highs')
        return None if r.status != 0 else self._first_actions(b, r.x, lp, tanks, bat)

    def plan_building_stochastic(self, bi, b, t, g, starts):
        """Scenario LP: K error scenarios, expected bill (cost / K), NET first-step actions of every tank and the battery shared by all scenarios (non-anticipativity),
        everything later per scenario (recourse). Same state, bounds and terminal credit as the deterministic LP."""
        import scipy.sparse as sp
        h = min(self.H, self.inp.N - g)
        K = len(starts)
        parts = [self._lp(bi, b, t, g, fcst=f) for f in self.fc.scenarios(bi, g, h, starts)]
        nv = parts[0][0]['nv']
        A_eq = sp.block_diag([p[0]['A_eq'] for p in parts], format='csr')
        A_ub = sp.block_diag([p[0]['A_ub'] for p in parts], format='csr') if parts[0][0]['A_ub'].shape[0] else None
        c = np.concatenate([p[0]['c'] / K for p in parts]); lo = np.concatenate([p[0]['lo'] for p in parts]); hi = np.concatenate([p[0]['hi'] for p in parts])
        idx, tanks, bat = parts[0][0]['idx'], parts[0][1], parts[0][2]
        pairs = [(f'a{k}', f'd{k}') for k in range(len(tanks))] + ([('c', 'u')] if bat is not None else [])
        rows, cols, vals, r = [], [], [], 0
        for k in range(1, K):
            for step in range(min(self.share, h)):                        # the first `share` steps are decided before the noise is seen (shared); later steps adapt per scenario
                for pos, neg in pairs:
                    for kk, sgn in ((0, -1.0), (k, 1.0)):
                        rows += [r, r]; cols += [kk * nv + idx[pos] + step, kk * nv + idx[neg] + step]; vals += [sgn, -sgn]
                    r += 1
        link = sp.csr_matrix((vals, (rows, cols)), shape=(r, K * nv))
        A_eq = sp.vstack([A_eq, link], format='csr'); b_eq = np.concatenate([p[0]['b_eq'] for p in parts] + [np.zeros(r)])
        res = linprog(c, A_ub=A_ub, b_ub=np.concatenate([p[0]['b_ub'] for p in parts]) if A_ub is not None else None, A_eq=A_eq, b_eq=b_eq,
                      bounds=np.column_stack([lo, hi]), method='highs')
        if res.status != 0:
            return None
        return self._first_actions(b, res.x[:nv], parts[0][0], tanks, bat)

    def plan_district(self, t, g):
        """One joint LP over all buildings with a district peak variable P >= sum_b (import_b - export_b) at every step of the horizon, cost peak_w CHF per kW of P.
        Plans are per building as before; the peak couples them (coincident peak). Returns one plan per building, or None if the LP fails."""
        import scipy.sparse as sp
        parts = [self._lp(bi, b, t, g) for bi, b in enumerate(self.env.buildings)]
        h = parts[0][0]['n']
        offs = np.cumsum([0] + [p[0]['nv'] for p in parts])
        nv = int(offs[-1]) + 1                                                    # last variable = P
        pad = lambda m, k: sp.hstack([m, sp.csr_matrix((m.shape[0], nv - offs[k] - m.shape[1]))], format='csr') if offs[k] == 0 else sp.hstack(   # noqa: E731
            [sp.csr_matrix((m.shape[0], int(offs[k]))), m, sp.csr_matrix((m.shape[0], nv - int(offs[k]) - m.shape[1]))], format='csr')
        A_eq = sp.vstack([pad(p[0]['A_eq'], k) for k, p in enumerate(parts)], format='csr')
        b_eq = np.concatenate([p[0]['b_eq'] for p in parts])
        ub_rows = [pad(p[0]['A_ub'], k) for k, p in enumerate(parts) if p[0]['A_ub'].shape[0]]
        b_ub = [p[0]['b_ub'] for p in parts if p[0]['A_ub'].shape[0]]
        rows, cols, vals = [], [], []
        for k, p in enumerate(parts):
            idx = p[0]['idx']
            for tt in range(h):
                rows += [tt, tt]; cols += [int(offs[k]) + idx['i'] + tt, int(offs[k]) + idx['x'] + tt]; vals += [1.0, -1.0]
        rows += list(range(h)); cols += [nv - 1] * h; vals += [-1.0] * h
        ub_rows.append(sp.csr_matrix((vals, (rows, cols)), shape=(h, nv))); b_ub.append(np.zeros(h))
        c = np.concatenate([p[0]['c'] for p in parts] + [[self.peak_w]])
        lo = np.concatenate([p[0]['lo'] for p in parts] + [[0.0]]); hi = np.concatenate([p[0]['hi'] for p in parts] + [[np.inf]])
        r = linprog(c, A_ub=sp.vstack(ub_rows, format='csr'), b_ub=np.concatenate(b_ub), A_eq=A_eq, b_eq=b_eq, bounds=np.column_stack([lo, hi]), method='highs')
        if r.status != 0:
            return None
        return [self._first_actions(b, r.x[int(offs[k]):int(offs[k + 1])], parts[k][0], parts[k][1], parts[k][2]) for k, b in enumerate(self.env.buildings)]

    def predict(self, observations):
        t = self.env.time_step
        g = self.s0 + t
        t0 = time.time()
        acts = []
        plans = self.plan_district(t, g) if (self.peak_w > 0 and g < self.inp.N) else None
        for bi, b in enumerate(self.env.buildings):
            if self.peak_w > 0:
                plan = plans[bi] if plans else None
            elif g >= self.inp.N:
                plan = None
            elif self.K > 1:
                if bi == 0:
                    starts = self.fc.sample_starts(g, min(self.H, self.inp.N - g), self.K)
                plan = self.plan_building_stochastic(bi, b, t, g, starts)
            else:
                plan = self.plan_building(bi, b, t, g)
            for nm in self.n_act[bi]:
                if plan is None:
                    acts.append(0.0)
                elif nm == 'heating_storage':
                    acts.append(float(np.clip(plan['tanks'].get('heating', 0.0), -1, 1)))
                elif nm == 'dhw_storage':
                    acts.append(float(np.clip(plan['tanks'].get('dhw', 0.0), -1, 1)))
                elif nm == 'electrical_storage':
                    acts.append(float(np.clip(plan['bat'], -1, 1)))
                elif nm == 'heating_device':
                    acts.append(float(np.clip(plan.get('heating_device', 0.0), 0.0, 1.0)))
                else:
                    acts.append(0.0)
        self.solve_s += time.time() - t0
        return [acts]


class MPCAgentRC(MPCAgent):
    """S3: the same receding-horizon LP, with the single-node RC room model of `oracle_rc.solve_rc_building` inside (heat Q is a decision, indoor temperature T follows
    the RC step from the room temperature CityLearn reports now). Comfort band 21 to 24 C as soft constraints (slack penalties: cold 5 CHF per K h, hot 0.05); the band
    upper limit is the thermostat path if that is higher (the model cannot cool, A-020). Weather (ambient, irradiance) is taken as KNOWN (A-M3). The plant is the CityLearn
    RC building with the same parameters, so model mismatch is ZERO by default (ASSUMPTION A-M4; `--rc-perturb` changes the plant's H and C by a factor in the planner only)."""
    LOWER, UPPER, W_COLD, W_HOT = 21.0, 24.0, 5.0, 0.05

    def __init__(self, env, s0, inp, fc, horizon=48, tv=1.0, peak_w=0.0, perturb=1.0, margin=0.0, correct=False):
        super().__init__(env, s0, inp, fc, horizon, tv, peak_w)
        self.LOWER = 21.0 + margin                                     # comfort margin: plan to LOWER, scored against 21 C
        self.correct, self.pred_T, self.bias = correct, {}, {}
        from swiss.experiments import oracle_rc as orc
        from swiss.models.rc_building import PRIORS
        self.p = dict(PRIORS)
        self.perturb = perturb
        self.Tth = {bi: orc.thermostat(inp, bi, b.dynamics.area_eff, self.p, inp.N)[1] for bi, b in enumerate(env.buildings)}

    def _lp(self, bi, b, t, g):
        import scipy.sparse as sp
        inp = self.inp
        h = min(self.H, inp.N - g)
        sl = slice(g, g + h)
        ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
        dyn = b.dynamics
        A, p = dyn.area_eff, dict(dyn.params)
        pp = dict(p)
        pp['H_w_per_k_m2'] = p['H_w_per_k_m2'] * self.perturb            # planner's model; the plant keeps p
        pp['C_j_per_k_m2'] = p['C_j_per_k_m2'] * self.perturb
        st = self._state(b, t)
        base, dem = self.fc.get(bi, g, h)
        cop, maxout = ht['cop'][sl], ht['maxout'][sl]
        price = inp.price[sl]
        dt_h = inp.dt_h
        bat = None
        if st['bat'] is not None:
            bat = o.battery_spec(inp.kwp[1.0][bi] * 1.0, dt_h)
            bat['e0'] = min(max(st['bat'], bat['emin']), bat['cap'])
        Tth = self.Tth[bi][sl]
        blocks, idx = [], {}

        def add(name, lo, hi, cost):
            idx[name] = sum(q[1] for q in blocks)
            blocks.append((name, h, np.broadcast_to(lo, (h,)), np.broadcast_to(hi, (h,)), np.broadcast_to(cost, (h,))))

        rate_h = ht['cap'] * dt_h
        add('a', 0.0, np.minimum(rate_h, maxout), 0.0); add('d', 0.0, rate_h, 0.0); add('E', 0.0, ht['cap'], 0.0); add('Q', 0.0, maxout, 0.0)
        add('T', -50.0, 80.0, 0.0); add('sl', 0.0, np.inf, self.W_COLD); add('su', 0.0, np.inf, self.W_HOT)
        if wt is not None:
            rate_w = wt['cap'] * dt_h
            wdem = dem[0]
            add('a2', 0.0, np.minimum(rate_w, wt['maxout'][sl]), 0.0); add('d2', 0.0, np.minimum(rate_w, wdem), 0.0); add('E2', 0.0, wt['cap'], 0.0)
        if bat is not None:
            add('c', 0.0, bat['power'], 0.0); add('u', 0.0, bat['power'], 0.0); add('Eb', bat['emin'], bat['cap'], 0.0)
        add('i', 0.0, np.inf, price); add('x', 0.0, np.inf, -EXPORT)
        names = [q[0] for q in blocks]
        cvec = np.concatenate([q[4] for q in blocks]).astype(float)
        lo = np.concatenate([q[2] for q in blocks]).astype(float); hi = np.concatenate([q[3] for q in blocks]).astype(float)
        nv = len(cvec)
        I = sp.identity(h, format='csr'); Z = sp.csr_matrix((h, h))
        sub = lambda lam: sp.diags([np.full(h - 1, -(1.0 - lam))], [-1], shape=(h, h), format='csr')   # noqa: E731

        def row(entries):
            m = [Z] * len(blocks)
            for nm, mat in entries:
                m[names.index(nm)] = mat
            return sp.hstack(m, format='csr')

        eq, beq, ub, bub = [], [], [], []
        for t_, qa, qd, qe, e0 in ((ht, 'a', 'd', 'E', st['heating']), (wt, 'a2', 'd2', 'E2', st.get('dhw'))):
            if t_ is None:
                continue
            rho, lam = t_['rho'], t_['loss']
            eq.append(row([(qa, -rho * I), (qd, I / rho), (qe, I + sub(lam))]))
            b0 = np.zeros(h); b0[0] = (1.0 - lam) * e0; beq.append(b0)
        ub.append(row([('Q', I), ('d', -I), ('a', I)])); bub.append(maxout)
        ub.append(row([('d', I), ('Q', -I)])); bub.append(np.zeros(h))
        if wt is not None:
            ub.append(row([('a2', I), ('d2', -I)])); bub.append(wt['maxout'][sl] - dem[0])
        w = b.weather
        ta = np.asarray(w.outdoor_dry_bulb_temperature, dtype=float)       # episode-relative arrays: use global inputs instead
        ta, ghi = inp.ta[sl], inp.ghi[sl]
        Hh = pp['H_w_per_k_m2'] * A
        e = float(np.exp(-3600.0 * dt_h * pp['H_w_per_k_m2'] / pp['C_j_per_k_m2']))
        rhs = (1 - e) * (ta + (pp['g'] * A * ghi + pp['L_internal_w_m2'] * A) / Hh)
        if self.correct and bi in self.pred_T:                         # online correction: smoothed residual between the room temperature predicted for the last step and the one observed
            r = float(np.clip(float(dyn.temperature) - self.pred_T[bi], -2.0, 2.0))
            self.bias[bi] = 0.7 * self.bias.get(bi, 0.0) + 0.3 * r
            rhs = rhs + self.bias[bi]
        rhs = rhs.copy(); rhs[0] += e * float(dyn.temperature)
        eq.append(row([('T', I + sp.diags([np.full(h - 1, -e)], [-1], shape=(h, h), format='csr')), ('Q', -(1 - e) * 1000.0 / (Hh * dt_h) * I)])); beq.append(rhs)
        lower, upper = np.where(Tth < 20.99, Tth, self.LOWER), np.maximum(self.UPPER, Tth)      # where the thermostat cannot reach 21 C the lower limit is its path; elsewhere LOWER (21 + margin)
        ub.append(row([('T', -I), ('sl', -I)])); bub.append(-lower)             # T + sl >= lower
        ub.append(row([('T', I), ('su', -I)])); bub.append(upper)               # T - su <= upper
        if bat is not None:
            eq.append(row([('c', -bat['eta1'] * I), ('u', I / bat['eta1']), ('Eb', I + sub(0.0))]))
            b0 = np.zeros(h); b0[0] = bat['e0']; beq.append(b0)
        ent = [('i', I), ('x', -I), ('Q', -sp.diags(1.0 / cop)), ('a', -sp.diags(1.0 / cop)), ('d', sp.diags(1.0 / cop))]
        if wt is not None:
            ent += [('a2', -sp.diags(1.0 / wt['cop'][sl])), ('d2', sp.diags(1.0 / wt['cop'][sl]))]
        if bat is not None:
            ent += [('c', -I), ('u', I)]
        eq.append(row(ent)); beq.append(base)
        if self.tv > 0:                                                         # terminal credits, as in the S1/S2 agent plus the heat stored in the room mass
            cvec[idx['E'] + h - 1] -= self.tv * self.p_low * ht['rho'] / float(cop[-1])
            if wt is not None:
                cvec[idx['E2'] + h - 1] -= self.tv * self.p_low * wt['rho'] / float(wt['cop'][sl][-1])
            if bat is not None:
                cvec[idx['Eb'] + h - 1] -= self.tv * self.p_low * bat['eta1']
            cvec[idx['T'] + h - 1] -= self.tv * self.p_low * (p['C_j_per_k_m2'] * A / 3.6e6) / float(cop[-1])
        tanks = [{**ht, 'kind': 'heating'}] + ([{**wt, 'kind': 'dhw'}] if wt is not None else [])
        lp = {'c': cvec, 'lo': lo, 'hi': hi, 'A_eq': sp.vstack(eq, format='csr'), 'b_eq': np.concatenate(beq), 'A_ub': sp.vstack(ub, format='csr'),
              'b_ub': np.concatenate(bub), 'idx': idx, 'n': h, 'nv': nv, 'has_dhw': wt is not None, 'maxout0': float(maxout[0]), 'bi': bi}
        return lp, tanks, bat

    def _first_actions(self, b, x, lp, tanks, bat):
        idx, inp = lp['idx'], self.inp
        first = lambda name: float(x[idx[name]])   # noqa: E731
        self.pred_T[lp['bi']] = first('T')
        out = {'tanks': {'heating': (first('a') - first('d')) / (tanks[0]['cap'] * inp.dt_h), 'dhw': 0.0}, 'heating_device': first('Q') / max(lp['maxout0'], 1e-9),
               'bat': ((first('c') - first('u')) / (float(b.electrical_storage.nominal_power) * inp.dt_h)) if bat is not None else 0.0}
        if lp['has_dhw']:
            out['tanks']['dhw'] = (first('a2') - first('d2')) / (tanks[1]['cap'] * inp.dt_h)
        return out


def play_mpc(win, inp, fc, horizon, tv, peak_w=0.0, warm=rl.WARM, perturb=1.0, margin=0.0, correct=False, K=1, share=1):
    s, e = win
    s0 = max(0, s - warm)
    env = rl.make_env(True, 'bill', windows=(s0, min(e + 1, rl.LAST_STEP)))
    ag = (MPCAgentRC(env, s0, inp, fc, horizon, tv, peak_w, perturb, margin, correct) if rl.SCENARIO == 's3' else MPCAgent(env, s0, inp, fc, horizon, tv, peak_w, K, share))
    obs, _ = env.reset()
    rewards = []
    while not env.terminated:
        obs, r, *_ = env.step(ag.predict(obs))
        rewards.append(float(np.sum(r)))
    m = rl.window_metrics(env, rewards, s0, s, e)
    m['solve_seconds'] = ag.solve_s
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', default='s2', choices=['s1', 's2', 's3'])
    ap.add_argument('--mode', default='naive', choices=['perfect', 'naive', 'noisy', 'weather', 'weather_lag'])
    ap.add_argument('--horizon', type=int, default=48)
    ap.add_argument('--level', type=float, default=0.0)
    ap.add_argument('--perfect-parts', nargs='*', default=[], help='weather modes: components replaced by the truth (load pv dem), for ablations')
    ap.add_argument('--peak-w', type=float, default=0.0, help='CHF per kW of the horizon-peak of the district net import (joint LP); 0 = per-building bill-only LPs')
    ap.add_argument('--rc-perturb', type=float, default=1.0, help='s3: factor on H and C in the PLANNER model (plant unchanged); 1 = exact model')
    ap.add_argument('--rc-margin', type=float, default=0.0, help='s3: plan to 21 + margin C (scored against 21 C)')
    ap.add_argument('--rc-correct', action='store_true', help='s3: online correction of the room-model bias from the observed temperature')
    ap.add_argument('--scenarios', type=int, default=1, help='stochastic MPC: K error scenarios (weather mode, s1/s2 only); 1 = deterministic')
    ap.add_argument('--err-scale', type=float, default=1.0, help='stochastic MPC: factor on the sampled forecast errors (diagnostic; 1 = as measured)')
    ap.add_argument('--share', type=int, default=1, help='stochastic MPC: number of leading steps whose storage actions are shared by all scenarios (1 = first action only)')
    ap.add_argument('--tv', type=float, default=1.0)
    ap.add_argument('--weeks', type=int, nargs='+', default=rl.TEST_WEEKS)
    ap.add_argument('--refs', action='store_true', help='also play the reference and the PV rule (r=0.1)')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    rl.use_scenario(a.scenario)
    from swiss.experiments import oracle_rc as orc
    inp = orc.RCInputs() if a.scenario == 's3' else o.Inputs()
    fc = Forecaster(inp, a.mode, a.level, perfect_parts=a.perfect_parts, rc=(a.scenario == 's3'), stoch=a.scenarios > 1, err_scale=a.err_scale)
    wins = [rl.window(k) for k in a.weeks]
    res = {'scenario': a.scenario, 'mode': a.mode, 'perfect_parts': a.perfect_parts, 'horizon': a.horizon, 'level': a.level, 'tv': a.tv, 'peak_w': a.peak_w, 'rc_perturb': a.rc_perturb, 'rc_margin': a.rc_margin, 'rc_correct': a.rc_correct, 'scenarios': a.scenarios, 'err_scale': a.err_scale, 'share': a.share, 'weeks': a.weeks, 'export_price_chf_kwh': EXPORT}
    t0 = time.time()
    rows = []
    for w in wins:
        rows.append(play_mpc(w, inp, fc, a.horizon, a.tv, a.peak_w, perturb=a.rc_perturb, margin=a.rc_margin, correct=a.rc_correct, K=a.scenarios, share=a.share))
        print(f'{a.scenario} {a.mode} H{a.horizon} L{a.level} week {w[0] // rl.WEEK}: cost {rows[-1]["cost_chf"]:.2f}  [{time.time() - t0:.0f}s]', flush=True)
    res['mpc'] = rl.aggregate(rows)
    res['mpc_windows'] = rows
    if a.refs:
        res['reference'] = rl.aggregate([rl.play(rl.reference_agent, True, 'bill', w) for w in wins])
        res['pv_rule_r0.1'] = rl.aggregate([rl.play(lambda env: rl.PVRule(env, 0.1), True, 'bill', w) for w in wins])
    os.makedirs(a.out, exist_ok=True)
    fn = f'mpc_{a.scenario}_{a.mode}{"_perfect-" + "-".join(a.perfect_parts) if a.perfect_parts else ""}_H{a.horizon}_L{a.level:g}_tv{a.tv:g}{"_peak" + format(a.peak_w, "g") if a.peak_w else ""}{"_rc" + format(a.rc_perturb, "g") if a.rc_perturb != 1.0 else ""}{"_m" + format(a.rc_margin, "g") if a.rc_margin else ""}{"_corr" if a.rc_correct else ""}{"_K" + str(a.scenarios) if a.scenarios > 1 else ""}{"_es" + format(a.err_scale, "g") if a.err_scale != 1.0 else ""}{"_sh" + str(a.share) if a.share != 1 else ""}.json'
    json.dump(res, open(os.path.join(a.out, fn), 'w'), indent=1)
    print('written', fn, flush=True)


if __name__ == '__main__':
    main()
