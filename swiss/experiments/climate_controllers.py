"""Controllers for the Phase C cells (WP3): thermostat with cooling, PV rule with cooling, receding-horizon MPC with a cooling variable.

Cells are S3 districts (PV, battery, RC building) with cooling in the cooled buildings (swiss/pipeline/build_climate_datasets.py); cooled buildings have the combined action
`cooling_or_heating_device` (positive = heating share of the heating capacity, negative = cooling share of the cooling capacity), the others `heating_device`.
  ThermostatAgentCool  heat to 21 C, cool to 26 C (the reference of every cell; identical to the thermostat baseline of oracle_climate)
  PVRuleCool           PVRule of rl.py (tanks charge 10-16 h, discharge 17-22 h, battery follows the PV surplus) on top of the cooling thermostat
  MPCClimate           receding-horizon MPC (mpc.MPCAgent machinery: horizon LP per building, optional district peak term, comfort margin, online model correction) with the
                       cooling variable Qc (heat removed, electricity Qc / COPc, capacity cooling_capacity_kwh), comfort lower 21 C (+ margin), upper 24 C in the heating season and
                       26 C in the cooling season (soft, high penalty), uncooled buildings float.
Forecasts (ClimateForecaster): 'perfect', or 'weather' = gradient boosting on calendar and weather features trained on the cell's own scenario (or another scenario for the
robustness test) outside the test weeks +- 1 week; the weather itself is taken as KNOWN over the horizon (A-028) unless a forecast-weather override is given (synthetic error,
labelled). Assumptions: docs/phases/phase_c_drafts/wp3_registry_draft.md.
"""
import os
import sys
import time

import numpy as np
from scipy.optimize import linprog

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import mpc, oracle_climate as oc, oracle_pvbat as o, rl  # noqa: E402
from swiss.models.rc_building import (COOL_SETPOINT_C, COOLING_MONTHS, COOLING_MIN_OUTDOOR_C, UPPER_HEATING_SEASON_C, cooling_capacity_kwh, cooling_cop,  # noqa: E402
                                      heat_for_target, step_temperature)

EXPORT = 0.08


# ------------------------------------------------------------------------------------------------------------------------------ thermostat and PV rule
class ThermostatAgentCool:
    """Heat to the setpoint, cool to 26 C when the free temperature would exceed it (cooled buildings only). Same logic as rc_building.simulate_thermostat."""

    def __init__(self, env):
        self.env = env

    def building_actions(self, b):
        t = b.time_step
        w = b.weather
        ghi = float(w.direct_solar_irradiance[t]) + float(w.diffuse_solar_irradiance[t])
        t_out = float(w.outdoor_dry_bulb_temperature[t])
        dt_h = b._dataset_step_hours()
        dyn = b.dynamics
        T, p, A = dyn.temperature, dyn.params, dyn.area_eff
        q_kw = max(heat_for_target(T, p['setpoint_c'], t_out, ghi, A, dt_s=3600.0 * dt_h, p=p), 0.0)
        maxout = b.heating_device.get_max_output_power(t_out, heating=True, max_electric_power=b.heating_device.nominal_power * dt_h)       # kWh thermal per step
        heat_share = float(np.clip(q_kw * dt_h / max(maxout, 1e-9), 0.0, 1.0))
        cool_share = 0.0
        if 'cooling_or_heating_device' in b.active_actions and heat_share <= 0.0:
            if getattr(dyn, 'cooled_fraction', 1.0) < 1.0:                 # archetype B: the room units cool their own zone (temperature and area of the cooled zone)
                T, A = dyn.t_cooled, dyn.cooled_fraction * dyn.area_eff
            t_free = step_temperature(T, t_out, ghi, 0.0, A, dt_s=3600.0 * dt_h, p=p)
            if t_free > COOL_SETPOINT_C:
                need = max(-heat_for_target(T, COOL_SETPOINT_C, t_out, ghi, A, dt_s=3600.0 * dt_h, p=p), 0.0) * dt_h
                cap = float(cooling_capacity_kwh(t_out, float(b.cooling_device.nominal_power), float(b.cooling_device.efficiency), dt_h))
                cool_share = float(np.clip(need / cap, 0.0, 1.0)) if cap > 0 else 0.0
        return heat_share, cool_share

    def predict(self, observations):
        acts = []
        for b in self.env.buildings:
            hs, cs = self.building_actions(b)
            for nm in b.active_actions:
                if nm == 'heating_device':
                    acts.append(hs)
                elif nm == 'cooling_or_heating_device':
                    acts.append(hs - cs)
                else:
                    acts.append(0.0)
        return [acts]


class PVRuleCool:
    """rl.PVRule with the cooling thermostat (rate: share of tank capacity per hour)."""

    def __init__(self, env, rate=0.1):
        self.env, self.rate = env, rate
        self.thermo = ThermostatAgentCool(env)

    def predict(self, observations):
        env = self.env
        t = env.time_step
        out = self.thermo.predict(observations)[0]
        acts, k = [], 0
        for b in env.buildings:
            hour = int(b.energy_simulation.hour[t]) - 1
            tank = self.rate if 10 <= hour < 16 else (-self.rate if 17 <= hour < 22 else 0.0)
            for nm in b.active_actions:
                if nm in ('heating_storage', 'dhw_storage'):
                    acts.append(tank)
                elif nm == 'electrical_storage':
                    dt_h = b.seconds_per_time_step / 3600.0
                    pv = float(b.energy_simulation.solar_generation[t]) * float(b.pv.nominal_power) / 1000.0 * dt_h
                    surplus = pv - float(b.energy_simulation.non_shiftable_load[t])
                    acts.append(float(np.clip(surplus / max(float(b.electrical_storage.nominal_power) * dt_h, 1e-9), -1.0, 1.0)))
                elif nm in ('heating_device', 'cooling_or_heating_device'):
                    acts.append(out[k])
                else:
                    acts.append(0.0)
                k += 1
        return [acts]


# ------------------------------------------------------------------------------------------------------------------------------ weather view and forecaster
class WeatherView:
    """Outdoor temperature, irradiance and the weather-dependent device limits per building, either the true ones or recomputed from a forecast weather (synthetic error)."""

    def __init__(self, inp, ta=None, ghi=None):
        self.true = ta is None
        self.ta = inp.ta if ta is None else np.asarray(ta, dtype=float)
        self.ghi = inp.ghi if ghi is None else np.asarray(ghi, dtype=float)
        n, dt_h = inp.N, inp.dt_h
        self.cop_h, self.maxout_h, self.cop_w, self.maxout_w, self.qc_max, self.copc = [], [], [], [], [], []
        for bi, b in enumerate(inp.env0.buildings):
            ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
            if self.true:
                self.cop_h.append(ht['cop']); self.maxout_h.append(ht['maxout'])
                self.cop_w.append(wt['cop'] if wt is not None else None); self.maxout_w.append(wt['maxout'] if wt is not None else None)
                self.qc_max.append(inp.qc_max[bi]); self.copc.append(inp.copc[bi])
            else:
                cop = np.array([b.heating_device.get_cop(t, heating=True) for t in self.ta[:n]])
                self.cop_h.append(cop); self.maxout_h.append(float(b.heating_device.nominal_power) * dt_h * cop)
                if wt is not None:
                    cw = np.array([b.dhw_device.get_cop(t, heating=True) for t in self.ta[:n]])
                    self.cop_w.append(cw); self.maxout_w.append(float(b.dhw_device.nominal_power) * dt_h * cw)
                else:
                    self.cop_w.append(None); self.maxout_w.append(None)
                if inp.cooled[bi]:
                    dev = b.cooling_device
                    self.qc_max.append(cooling_capacity_kwh(self.ta[:n], float(dev.nominal_power), float(dev.efficiency), dt_h))
                    self.copc.append(cooling_cop(self.ta[:n], float(dev.efficiency)))
                else:
                    self.qc_max.append(None); self.copc.append(None)


def weather_arrays(inp):
    w = inp.env0.buildings[0].weather
    n = inp.N
    return (np.asarray(w.outdoor_dry_bulb_temperature, dtype=float)[:n], np.asarray(w.diffuse_solar_irradiance, dtype=float)[:n],
            np.asarray(w.direct_solar_irradiance, dtype=float)[:n])


def features(ta, dif, dire):
    n = len(ta)
    t = np.arange(n)
    t24 = np.convolve(ta, np.ones(24) / 24, mode='full')[:n]
    return np.column_stack([t % 24, (t // 24) % 7, ta, dif, dire, t24])


def synthetic_weather_error(inp, bias_k=0.0, noise_k=0.0, ghi_noise=0.0, seed=0):
    """Forecast weather = truth + temperature bias + Gaussian temperature noise (K) and multiplicative Gaussian irradiance noise (fraction), fixed seed (labelled synthetic)."""
    rng = np.random.default_rng(seed)
    ta, dif, dire = weather_arrays(inp)
    ta_f = ta + bias_k + noise_k * rng.standard_normal(len(ta))
    f = np.clip(1.0 + ghi_noise * rng.standard_normal(len(ta)), 0.0, None)
    return ta_f, dif * f, dire * f


_FIT_CACHE = {}


def _train_mask(n):
    ok = np.ones(n, dtype=bool)
    for k in rl.TEST_WEEKS:
        ok[max(0, (k - 1) * rl.WEEK):(k + 2) * rl.WEEK] = False
    return ok


def fit_predict(train_inp, apply_inp, wf=None):
    """Per building: gradient-boosting predictions of (base load, DHW demand, PV) over the year of apply_inp, models trained on train_inp outside the test weeks +- 1 week;
    features of the applied year from its weather, or from the forecast weather wf = (ta, dif, dire). Cached per process."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    key = (train_inp.name, apply_inp.name, None if wf is None else (round(float(wf[0].sum()), 3), round(float(wf[1].sum()), 3), round(float(wf[2].sum()), 3)))
    if key in _FIT_CACHE:
        return _FIT_CACHE[key]
    n = min(train_inp.N, apply_inp.N)
    Xtr = features(*weather_arrays(train_inp))[:n]
    Xap = features(*(wf if wf is not None else weather_arrays(apply_inp)))[:n]
    ok = _train_mask(n)
    out = []
    for bi in range(len(train_inp.names)):
        comps = [train_inp.base[bi][:n], train_inp.dhw_tank[bi]['demand'][:n] if train_inp.dhw_tank[bi] is not None else None, train_inp.pv_gen[bi][:n]]
        preds = []
        for y in comps:
            if y is None:
                preds.append(None)
                continue
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, max_leaf_nodes=15, random_state=0).fit(Xtr[ok], y[ok])
            preds.append(np.clip(m.predict(Xap), 0.0, None))
        out.append(preds)
    _FIT_CACHE[key] = out
    return out


class ClimateForecaster:
    """get(bi, g, h) -> (net load without space conditioning minus PV, [DHW tank demand]) for steps g..g+h-1."""

    def __init__(self, inp, mode='perfect', train_inp=None, wf=None):
        self.inp, self.mode = inp, mode
        self.pred = fit_predict(train_inp or inp, inp, wf) if mode == 'weather' else None

    def get(self, bi, g, h):
        sl = slice(g, g + h)
        inp = self.inp
        has_dhw = inp.dhw_tank[bi] is not None
        if self.mode == 'perfect':
            return inp.base[bi][sl] - inp.pv_gen[bi][sl], ([inp.dhw_tank[bi]['demand'][sl]] if has_dhw else [])
        p = self.pred[bi]
        return p[0][sl] - p[2][sl], ([p[1][sl]] if has_dhw else [])


# ------------------------------------------------------------------------------------------------------------------------------ MPC with cooling
class MPCClimate(mpc.MPCAgent):
    LOWER, W_COLD, W_HOT_COOLED, W_HOT_FLOAT = 21.0, 5.0, 2.0, 0.05

    def __init__(self, env, s0, inp, fc, horizon=48, tv=1.0, peak_w=0.0, margin=0.0, correct=False, view=None):
        super().__init__(env, s0, inp, fc, horizon, tv, peak_w)
        self.LOWER = 21.0 + margin
        self.correct, self.pred_T, self.bias = correct, {}, {}
        self.wv = view if view is not None else WeatherView(inp)
        self.p_low = float(inp.price.min())
        self.Tth = {bi: oc.thermostat(inp, bi, inp.N)[2] for bi in range(len(env.buildings))}
        self.Tth_zones = {bi: oc.thermostat_zones(inp, bi, inp.N)[2:4] for bi in range(len(env.buildings)) if inp.two_zone[bi]}      # archetype B: (cooled zone, uncooled zone) thermostat paths

    def _lp(self, bi, b, t, g, fcst=None):
        if self.inp.two_zone[bi]:
            return self._lp_zones(bi, b, t, g, fcst)
        import scipy.sparse as sp
        inp, wv = self.inp, self.wv
        h = min(self.H, inp.N - g)
        sl = slice(g, g + h)
        ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
        cooled = inp.cooled[bi]
        p, A, dt_h = inp.params[bi], inp.area[bi], inp.dt_h
        st = self._state(b, t)
        base, dem = self.fc.get(bi, g, h)
        cop, maxout = wv.cop_h[bi][sl], wv.maxout_h[bi][sl]
        price = inp.price[sl]
        bat = o.battery_spec(inp.kwp[bi] * 1.0, dt_h)
        bat['e0'] = min(max(st['bat'], bat['emin']), bat['cap'])
        Tth = self.Tth[bi][sl]
        blocks, idx = [], {}

        def add(name, lo, hi, cost):
            idx[name] = sum(q[1] for q in blocks)
            blocks.append((name, h, np.broadcast_to(lo, (h,)), np.broadcast_to(hi, (h,)), np.broadcast_to(cost, (h,))))

        rate_h = ht['cap'] * dt_h
        add('a', 0.0, np.minimum(rate_h, maxout), 0.0); add('d', 0.0, rate_h, 0.0); add('E', 0.0, ht['cap'], 0.0); add('Q', 0.0, maxout, 0.0)
        add('T', -50.0, 80.0, 0.0); add('sl', 0.0, np.inf, self.W_COLD); add('su', 0.0, np.inf, self.W_HOT_COOLED if cooled else self.W_HOT_FLOAT)
        if cooled:
            add('Qc', 0.0, wv.qc_max[bi][sl], 0.0)
        if wt is not None:
            rate_w = wt['cap'] * dt_h
            add('a2', 0.0, np.minimum(rate_w, wv.maxout_w[bi][sl]), 0.0); add('d2', 0.0, np.minimum(rate_w, dem[0]), 0.0); add('E2', 0.0, wt['cap'], 0.0)
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
            ub.append(row([('a2', I), ('d2', -I)])); bub.append(wv.maxout_w[bi][sl] - dem[0])
        Hh = p['H_w_per_k_m2'] * A
        e = float(np.exp(-3600.0 * dt_h * p['H_w_per_k_m2'] / p['C_j_per_k_m2']))
        rhs = (1 - e) * (wv.ta[sl] + (p['g'] * A * wv.ghi[sl] + p['L_internal_w_m2'] * A) / Hh)
        if self.correct and bi in self.pred_T:
            r = float(np.clip(float(b.dynamics.temperature) - self.pred_T[bi], -2.0, 2.0))
            self.bias[bi] = 0.7 * self.bias.get(bi, 0.0) + 0.3 * r
            rhs = rhs + self.bias[bi]
        rhs = rhs.copy(); rhs[0] += e * float(b.dynamics.temperature)
        k_q = (1 - e) * 1000.0 / (Hh * dt_h)
        ent_t = [('T', I + sp.diags([np.full(h - 1, -e)], [-1], shape=(h, h), format='csr')), ('Q', -k_q * I)]
        if cooled:
            ent_t.append(('Qc', k_q * I))
        eq.append(row(ent_t)); beq.append(rhs)
        upper_season = np.where(np.isin(inp.local_month[sl], COOLING_MONTHS), COOL_SETPOINT_C, UPPER_HEATING_SEASON_C) if cooled else np.full(h, UPPER_HEATING_SEASON_C)
        lower, upper = np.where(Tth < 20.99, Tth, self.LOWER), np.maximum(upper_season, Tth)
        ub.append(row([('T', -I), ('sl', -I)])); bub.append(-lower)
        ub.append(row([('T', I), ('su', -I)])); bub.append(upper)
        eq.append(row([('c', -bat['eta1'] * I), ('u', I / bat['eta1']), ('Eb', I + sub(0.0))]))
        b0 = np.zeros(h); b0[0] = bat['e0']; beq.append(b0)
        ent = [('i', I), ('x', -I), ('Q', -sp.diags(1.0 / cop)), ('a', -sp.diags(1.0 / cop)), ('d', sp.diags(1.0 / cop)), ('c', -I), ('u', I)]
        if wt is not None:
            ent += [('a2', -sp.diags(1.0 / wv.cop_w[bi][sl])), ('d2', sp.diags(1.0 / wv.cop_w[bi][sl]))]
        if cooled:
            ent.append(('Qc', -sp.diags(1.0 / wv.copc[bi][sl])))
        eq.append(row(ent)); beq.append(base)
        if self.tv > 0:                                                         # credit the energy stored at the end of the horizon (A-029 as in mpc.py)
            cvec[idx['E'] + h - 1] -= self.tv * self.p_low * ht['rho'] / float(cop[-1])
            if wt is not None:
                cvec[idx['E2'] + h - 1] -= self.tv * self.p_low * wt['rho'] / float(wv.cop_w[bi][sl][-1])
            cvec[idx['Eb'] + h - 1] -= self.tv * self.p_low * bat['eta1']
            kwh_per_k = p['C_j_per_k_m2'] * A / 3.6e6
            if int(inp.local_month[g + h - 1]) in COOLING_MONTHS:
                if cooled:                                                      # a lower end temperature is stored coolness, valued at the cooling COP
                    cvec[idx['T'] + h - 1] += self.tv * self.p_low * kwh_per_k / float(wv.copc[bi][sl][-1])
            else:
                cvec[idx['T'] + h - 1] -= self.tv * self.p_low * kwh_per_k / float(cop[-1])
        tanks = [{**ht, 'kind': 'heating'}] + ([{**wt, 'kind': 'dhw'}] if wt is not None else [])
        lp = {'c': cvec, 'lo': lo, 'hi': hi, 'A_eq': sp.vstack(eq, format='csr'), 'b_eq': np.concatenate(beq), 'A_ub': sp.vstack(ub, format='csr'),
              'b_ub': np.concatenate(bub), 'idx': idx, 'n': h, 'nv': nv, 'has_dhw': wt is not None, 'maxout0': float(maxout[0]), 'bi': bi, 'cooled': cooled,
              'qc0': float(wv.qc_max[bi][g]) if cooled else 0.0}
        return lp, tanks, bat

    def _lp_zones(self, bi, b, t, g, fcst=None):
        """Archetype B horizon LP of a room-unit building: two independent zone nodes (cooled zone area f A with Qc, uncooled zone (1 - f) A), heat Q split by area, as
        oracle_climate.solve_building_zones; zone temperatures T (cooled) and T2 (uncooled) with soft bands: cold slack 5 CHF per K h in both zones, hot slack 2.0 CHF per K h in
        the cooled zone and 0.05 CHF per K h in the uncooled zone (the WP3 rerun fix: no free overheating, but no hard limit either). The online correction acts on the area-weighted mean."""
        import scipy.sparse as sp
        inp, wv = self.inp, self.wv
        h = min(self.H, inp.N - g)
        sl = slice(g, g + h)
        ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
        p, A, f, dt_h = inp.params[bi], inp.area[bi], inp.frac[bi], inp.dt_h
        dyn = b.dynamics
        st = self._state(b, t)
        base, dem = self.fc.get(bi, g, h)
        cop, maxout = wv.cop_h[bi][sl], wv.maxout_h[bi][sl]
        price = inp.price[sl]
        bat = o.battery_spec(inp.kwp[bi] * 1.0, dt_h)
        bat['e0'] = min(max(st['bat'], bat['emin']), bat['cap'])
        Tth1, Tth2 = self.Tth_zones[bi][0][sl], self.Tth_zones[bi][1][sl]
        blocks, idx = [], {}

        def add(name, lo, hi, cost):
            idx[name] = sum(q[1] for q in blocks)
            blocks.append((name, h, np.broadcast_to(lo, (h,)), np.broadcast_to(hi, (h,)), np.broadcast_to(cost, (h,))))

        rate_h = ht['cap'] * dt_h
        add('a', 0.0, np.minimum(rate_h, maxout), 0.0); add('d', 0.0, rate_h, 0.0); add('E', 0.0, ht['cap'], 0.0); add('Q', 0.0, maxout, 0.0)
        add('T', -50.0, 80.0, 0.0); add('sl', 0.0, np.inf, self.W_COLD); add('su', 0.0, np.inf, self.W_HOT_COOLED)
        add('T2', -50.0, 80.0, 0.0); add('sl2', 0.0, np.inf, self.W_COLD); add('su2', 0.0, np.inf, self.W_HOT_FLOAT)
        add('Qc', 0.0, wv.qc_max[bi][sl], 0.0)
        if wt is not None:
            rate_w = wt['cap'] * dt_h
            add('a2', 0.0, np.minimum(rate_w, wv.maxout_w[bi][sl]), 0.0); add('d2', 0.0, np.minimum(rate_w, dem[0]), 0.0); add('E2', 0.0, wt['cap'], 0.0)
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
            ub.append(row([('a2', I), ('d2', -I)])); bub.append(wv.maxout_w[bi][sl] - dem[0])
        Hh = p['H_w_per_k_m2'] * A
        e = float(np.exp(-3600.0 * dt_h * p['H_w_per_k_m2'] / p['C_j_per_k_m2']))
        rhs = (1 - e) * (wv.ta[sl] + (p['g'] * A * wv.ghi[sl] + p['L_internal_w_m2'] * A) / Hh)
        if self.correct and bi in self.pred_T:
            r = float(np.clip(float(dyn.temperature) - self.pred_T[bi], -2.0, 2.0))
            self.bias[bi] = 0.7 * self.bias.get(bi, 0.0) + 0.3 * r
            rhs = rhs + self.bias[bi]
        rhs1 = rhs.copy(); rhs1[0] += e * float(dyn.t_cooled)
        rhs2 = rhs.copy(); rhs2[0] += e * float(dyn.t_uncooled)
        k_q = (1 - e) * 1000.0 / (Hh * dt_h)
        decay = sp.diags([np.full(h - 1, -e)], [-1], shape=(h, h), format='csr')
        eq.append(row([('T', I + decay), ('Q', -k_q * I), ('Qc', (k_q / f) * I)])); beq.append(rhs1)
        eq.append(row([('T2', I + decay), ('Q', -k_q * I)])); beq.append(rhs2)
        upper_season = np.where(np.isin(inp.local_month[sl], COOLING_MONTHS), COOL_SETPOINT_C, UPPER_HEATING_SEASON_C)
        for tn, sln, sun, Tth, up in (('T', 'sl', 'su', Tth1, upper_season), ('T2', 'sl2', 'su2', Tth2, np.full(h, UPPER_HEATING_SEASON_C))):
            lower, upper = np.where(Tth < 20.99, Tth, self.LOWER), np.maximum(up, Tth)
            ub.append(row([(tn, -I), (sln, -I)])); bub.append(-lower)
            ub.append(row([(tn, I), (sun, -I)])); bub.append(upper)
        eq.append(row([('c', -bat['eta1'] * I), ('u', I / bat['eta1']), ('Eb', I + sub(0.0))]))
        b0 = np.zeros(h); b0[0] = bat['e0']; beq.append(b0)
        ent = [('i', I), ('x', -I), ('Q', -sp.diags(1.0 / cop)), ('a', -sp.diags(1.0 / cop)), ('d', sp.diags(1.0 / cop)), ('c', -I), ('u', I),
               ('Qc', -sp.diags(1.0 / wv.copc[bi][sl]))]
        if wt is not None:
            ent += [('a2', -sp.diags(1.0 / wv.cop_w[bi][sl])), ('d2', sp.diags(1.0 / wv.cop_w[bi][sl]))]
        eq.append(row(ent)); beq.append(base)
        if self.tv > 0:                                                         # terminal credit as MPCClimate, per zone
            cvec[idx['E'] + h - 1] -= self.tv * self.p_low * ht['rho'] / float(cop[-1])
            if wt is not None:
                cvec[idx['E2'] + h - 1] -= self.tv * self.p_low * wt['rho'] / float(wv.cop_w[bi][sl][-1])
            cvec[idx['Eb'] + h - 1] -= self.tv * self.p_low * bat['eta1']
            kwh_per_k = p['C_j_per_k_m2'] * A / 3.6e6
            if int(inp.local_month[g + h - 1]) in COOLING_MONTHS:
                cvec[idx['T'] + h - 1] += self.tv * self.p_low * f * kwh_per_k / float(wv.copc[bi][sl][-1])       # stored coolness of the cooled zone only
            else:
                cvec[idx['T'] + h - 1] -= self.tv * self.p_low * f * kwh_per_k / float(cop[-1])
                cvec[idx['T2'] + h - 1] -= self.tv * self.p_low * (1.0 - f) * kwh_per_k / float(cop[-1])
        tanks = [{**ht, 'kind': 'heating'}] + ([{**wt, 'kind': 'dhw'}] if wt is not None else [])
        lp = {'c': cvec, 'lo': lo, 'hi': hi, 'A_eq': sp.vstack(eq, format='csr'), 'b_eq': np.concatenate(beq), 'A_ub': sp.vstack(ub, format='csr'),
              'b_ub': np.concatenate(bub), 'idx': idx, 'n': h, 'nv': nv, 'has_dhw': wt is not None, 'maxout0': float(maxout[0]), 'bi': bi, 'cooled': True,
              'qc0': float(wv.qc_max[bi][g]), 'frac': f}
        return lp, tanks, bat

    def _first_actions(self, b, x, lp, tanks, bat):
        idx, inp = lp['idx'], self.inp
        first = lambda name: float(x[idx[name]])   # noqa: E731
        self.pred_T[lp['bi']] = first('T') if 'frac' not in lp else lp['frac'] * first('T') + (1.0 - lp['frac']) * first('T2')      # the mean temperature for the online correction
        out = {'tanks': {'heating': (first('a') - first('d')) / (tanks[0]['cap'] * inp.dt_h), 'dhw': 0.0},
               'heat_share': first('Q') / max(lp['maxout0'], 1e-9), 'cool_share': (first('Qc') / lp['qc0']) if lp['cooled'] and lp['qc0'] > 0 else 0.0,
               'bat': (first('c') - first('u')) / (float(b.electrical_storage.nominal_power) * inp.dt_h)}
        if lp['has_dhw']:
            out['tanks']['dhw'] = (first('a2') - first('d2')) / (tanks[1]['cap'] * inp.dt_h)
        return out

    def predict(self, observations):
        t = self.env.time_step
        g = self.s0 + t
        t0 = time.time()
        plans = self.plan_district(t, g) if (self.peak_w > 0 and g < self.inp.N) else None
        acts = []
        for bi, b in enumerate(self.env.buildings):
            if g >= self.inp.N:
                plan = None
            elif self.peak_w > 0:
                plan = plans[bi] if plans else None
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
                    acts.append(float(np.clip(plan['heat_share'], 0.0, 1.0)))
                elif nm == 'cooling_or_heating_device':
                    acts.append(float(np.clip(plan['heat_share'] - plan['cool_share'], -1.0, 1.0)))
                else:
                    acts.append(0.0)
        self.solve_s += time.time() - t0
        return [acts]


# ------------------------------------------------------------------------------------------------------------------------------ scoring of controller windows
def play_window(cell_dir, make_agent, win, warm=rl.WARM):
    """Deterministic rollout of a controller over the window win=(s, e) of a cell dataset (warm-up steps from empty tanks as in rl.play); returns window metrics,
    cooling electricity, degree-hours above 26 C and the weekly/highest-hour peaks. make_agent(env, s0) -> agent."""
    from swiss.experiments import climate_metrics as cm
    rl.SCHEMA = os.path.join(cell_dir, 'schema.json')
    s, e = win
    s0 = max(0, s - warm)
    env = rl.make_env(True, 'bill', windows=(s0, min(e + 1, rl.LAST_STEP)))
    agent = make_agent(env, s0)
    obs, _ = env.reset()
    rewards = []
    while not env.terminated:
        obs, r, *_ = env.step(agent.predict(obs))
        rewards.append(float(np.sum(r)))
    m = rl.window_metrics(env, rewards, s0, s, e)
    i0, i1 = s - s0, e - s0
    ser = cm.series_from_env(env, i0, i1)
    m['cooling_electricity_kwh'] = float(sum(x['cool'].sum() for x in ser))
    m['heating_electricity_kwh'] = float(sum(x['heat'].sum() for x in ser))
    dhs = [cm.degree_hours(x) for x in ser]
    m['degree_hours_above_26'] = float(sum(d[0] for d in dhs))
    if any(d[1] is not None for d in dhs):                                  # archetype B: zone values of the room-unit buildings (raw K h, not area-weighted)
        m['degree_hours_above_26_cooled_zone'] = float(sum(d[1] for d in dhs if d[1] is not None))
        m['degree_hours_above_26_uncooled_zone'] = float(sum(d[2] for d in dhs if d[2] is not None))
        m['comfort_cold_kh_cooled_zone'] = float(sum(np.nansum(np.maximum(21.0 - x['temp_cooled'], 0.0)) for x in ser if 'temp_cooled' in x))
        m['comfort_cold_kh_uncooled_zone'] = float(sum(np.nansum(np.maximum(21.0 - x['temp_uncooled'], 0.0)) for x in ser if 'temp_uncooled' in x))
    m['solve_seconds'] = float(getattr(agent, 'solve_s', 0.0))
    return m


def aggregate_windows(rows):
    """District aggregate of several windows (sums of bills and energies, max of peaks)."""
    agg = rl.aggregate(rows)
    agg['cooling_electricity_kwh'] = float(sum(r['cooling_electricity_kwh'] for r in rows))
    agg['heating_electricity_kwh'] = float(sum(r['heating_electricity_kwh'] for r in rows))
    agg['degree_hours_above_26'] = float(sum(r['degree_hours_above_26'] for r in rows))
    for k in ('degree_hours_above_26_cooled_zone', 'degree_hours_above_26_uncooled_zone', 'comfort_cold_kh_cooled_zone', 'comfort_cold_kh_uncooled_zone'):
        if k in rows[0]:
            agg[k] = float(sum(r[k] for r in rows))
    agg['solve_seconds'] = float(sum(r['solve_seconds'] for r in rows))
    return agg
