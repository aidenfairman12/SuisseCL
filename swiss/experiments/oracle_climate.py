"""Exact perfect-foresight optimum of the BILL for a Phase C cell (climate scenario x cooling adoption), S3 district with cooling (WP2).

Extends swiss/experiments/oracle_rc.py (not changed): the same per-building linear program over the year (tanks, battery, single-node RC room, export 8 Rp/kWh), plus
  Qc >= 0   heat removed from the room (kWh thermal per step) in COOLED buildings only; electricity Qc / COPc, COPc = CityLearn Carnot-fraction cooling COP at the outdoor
            temperature; capacity = nominal electric power x step x COPc, zero when the outdoor temperature is below 15 C (rc_building.COOLING_MIN_OUTDOOR_C, A-040)
  T_t = e T_{t-1} + (1 - e) [T_amb + (g A I + L A + 1000 (Q - Qc)) / H]                      (the RC step with net heat Q - Qc)
Comfort (hard constraints, as oracle_rc; the MPC uses soft ones):
  cooled buildings   lower 21 C; upper 24 C in the heating season and 26 C in the cooling season (June to September, local months), never below the thermostat path T_th
  uncooled buildings  unchanged from oracle_rc: lower 21 C, upper 24 C (never below T_th); they have no cooling variable and float in summer
  T_th = thermostat baseline (rc_building.simulate_thermostat): heat to 21 C, cool to 26 C if a cooling device exists; the baseline bill uses it, tanks and battery idle
Flexibility settings: 'band' (flexible, above), 'no thermal flexibility' (oracle_rc definition: lower 21 C, upper = max(21 C, T_th)) and 'pinned' (T equal to the thermostat path:
no building mass flexibility at all; the difference to 'band' is what thermal mass adds).
Inputs come from the cell's CityLearn dataset (swiss/datasets/climate/<scenario>_<adoption>/, swiss/pipeline/build_climate_datasets.py): weather, COP, tanks, PV, tariff and
carbon from the dataset; building areas from the dataset's RC parameters (the 2023-calibrated areas stay fixed in every scenario: the building does not change with the climate).
Household base load = non-shiftable load + DHW demand / DHW COP (the zero-action electricity of everything except space heat and PV; equal to oracle_rc's `net_s0 - derived heat / cop`).
Replay: the optimum is played in CityLearn through the combined `cooling_or_heating_device` action (negative = cooling); stop condition as Phase B: more than 0.5 % of the saving apart.

Run: PYTHONPATH=. cl/bin/python swiss/experiments/oracle_climate.py --cell hist_high [--band band] [--replay 5100]
Output: swiss/experiments/oracle_results/climate/<cell>__<band>.json (and .npz with the schedules if --save-schedules)
"""
import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.optimize import linprog

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.experiments import oracle  # noqa: E402
from swiss.experiments.oracle_pvbat import battery_spec  # noqa: E402
from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402
from swiss.models.rc_building import (COOL_SETPOINT_C, COOLING_MONTHS, UPPER_HEATING_SEASON_C, cooling_capacity_kwh, cooling_cop,  # noqa: E402
                                      simulate_thermostat, simulate_thermostat_zones)

CELLS = os.path.join(ROOT, 'swiss', 'datasets', 'climate')
OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'climate')
LOWER_C = 21.0
BANDS = ('band', 'no thermal flexibility', 'pinned')
SUMMER = (6, 7, 8)                       # months of the summer metrics
OVERHEAT_C = 26.0                        # degree-hour threshold (all buildings)


def tank_inputs(env):
    """oracle.tank_inputs for an environment that has not been played: demand series from the energy simulation (full year), everything else as in oracle.tank_inputs."""
    n = env.time_steps - 1
    dt_h = env.seconds_per_time_step / 3600.0
    T = np.asarray(env.buildings[0].weather.outdoor_dry_bulb_temperature, dtype=float)[:n]
    out = []
    for bi, b in enumerate(env.buildings):
        for kind, act in (('heating', 0), ('dhw', 1)):
            tank, dev = getattr(b, f'{kind}_storage'), getattr(b, f'{kind}_device')
            cap = float(tank.capacity)
            if cap <= 0:
                continue
            cop = np.array([dev.get_cop(t, heating=True) for t in T])
            out.append({'building': bi, 'kind': kind, 'action_index': act, 'cap': cap, 'cop': cop, 'maxout': float(dev.nominal_power) * dt_h * cop, 'dt_h': dt_h,
                        'demand': np.asarray(getattr(b.energy_simulation, f'{kind}_demand'), dtype=float)[:n], 'rho': float(tank.round_trip_efficiency),
                        'loss': float(tank.loss_coefficient), 'e0': float(tank.initial_soc) * cap})
    return out


class ClimateInputs:
    """Everything the programs need for one cell, read once from the cell's dataset."""

    def __init__(self, cell, root=CELLS):
        d = cell if os.path.isdir(cell) else os.path.join(root, cell)
        self.dir = d
        self.name = os.path.basename(d.rstrip('/'))
        self.meta = json.load(open(os.path.join(d, 'build_meta.json'))) if os.path.exists(os.path.join(d, 'build_meta.json')) else {}
        self.manifest = json.load(open(os.path.join(d, 'build_manifest.json')))
        self.env0 = CityLearnEnv(os.path.join(d, 'schema.json'), central_agent=True, reward_function=SwissDistrictReward)
        env = self.env0
        self.N = env.time_steps - 1
        N = self.N
        self.dt_h = env.seconds_per_time_step / 3600.0
        self.price = pd.read_csv(os.path.join(d, 'pricing.csv')).electricity_pricing.to_numpy()[:N]
        w = env.buildings[0].weather
        self.ta = np.asarray(w.outdoor_dry_bulb_temperature, dtype=float)[:N]
        self.ghi = (np.asarray(w.diffuse_solar_irradiance, dtype=float) + np.asarray(w.direct_solar_irradiance, dtype=float))[:N]
        self.month = np.asarray(env.buildings[0].energy_simulation.month)[:N].astype(int)
        self.carbon = np.asarray(env.buildings[0].carbon_intensity.carbon_intensity, dtype=float)[:N]
        allt = tank_inputs(env)
        self.tanks = [[t for t in allt if t['building'] == bi] for bi in range(len(env.buildings))]
        self.heat_tank = [next(t for t in ts if t['kind'] == 'heating') for ts in self.tanks]
        self.dhw_tank = [next((t for t in ts if t['kind'] == 'dhw'), None) for ts in self.tanks]
        pvf = os.path.join(ROOT, self.meta['pv_file']) if self.meta.get('pv_file') else os.path.join(ROOT, 'data', 'canonical', 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv')
        self.pv_per_kwp = pd.read_csv(pvf).pv_ac_w_per_kwp.to_numpy()[:N] / 1000.0 * self.dt_h
        self.names = list(self.manifest.keys())
        self.kwp = [float(self.manifest[n]['pv_kwp']) for n in self.names]
        self.area = [float(b.dynamics.area_eff) for b in env.buildings]
        self.params = [dict(b.dynamics.params) for b in env.buildings]
        self.cooled = [bool(self.manifest[n].get('cooled', False)) for n in self.names]
        self.frac = [float(self.manifest[n].get('cooled_fraction', 1.0)) if c else 1.0 for n, c in zip(self.names, self.cooled)]       # archetype B: cooled fraction of the floor area
        self.two_zone = [c and f < 1.0 for c, f in zip(self.cooled, self.frac)]
        self.roles = [self.manifest[n]['role'] for n in self.names]
        self.base = []
        for b in env.buildings:                                           # zero-action electricity of everything except space heat and PV
            cop_dhw = np.array([b.dhw_device.get_cop(t, heating=True) for t in self.ta])
            es = b.energy_simulation                                          # full-year arrays (the Building properties only return the steps played so far)
            self.base.append(np.asarray(es.non_shiftable_load, dtype=float)[:N] + np.asarray(es.dhw_demand, dtype=float)[:N] / cop_dhw)
        self.qc_max, self.copc = [], []
        for b, c in zip(env.buildings, self.cooled):
            if c:
                dev = b.cooling_device
                self.qc_max.append(cooling_capacity_kwh(self.ta, float(dev.nominal_power), float(dev.efficiency), self.dt_h))
                self.copc.append(cooling_cop(self.ta, float(dev.efficiency)))
            else:
                self.qc_max.append(None); self.copc.append(None)
        self.pv_gen = [k * self.pv_per_kwp for k in self.kwp]
        self.local_month = self.month

    def season_upper(self, cooled):
        """Upper comfort limit per step: 26 C in the cooling season of cooled buildings, otherwise 24 C."""
        if not cooled:
            return np.full(self.N, UPPER_HEATING_SEASON_C)
        return np.where(np.isin(self.local_month, COOLING_MONTHS), COOL_SETPOINT_C, UPPER_HEATING_SEASON_C)


def thermostat_zones(inp, bi, n):
    """Archetype B thermostat: (heat, cooling removed from the cooled zone) in kWh thermal per step, temperatures of the cooled zone, the uncooled zone and their area-weighted mean."""
    ht = inp.heat_tank[bi]
    q, qc, t1, t2, tm = simulate_thermostat_zones(inp.area[bi], inp.frac[bi], inp.ta[:n], inp.ghi[:n], inp.params[bi], dt_s=3600.0 * inp.dt_h,
                                                  q_heat_max=ht['maxout'][:n] / inp.dt_h, q_cool_max=inp.qc_max[bi][:n] / inp.dt_h)
    return q * inp.dt_h, qc * inp.dt_h, t1, t2, tm


def thermostat(inp, bi, n):
    if inp.two_zone[bi]:
        q, qc, _, _, tm = thermostat_zones(inp, bi, n)
        return q, qc, tm                                                   # the area-weighted mean temperature follows the single-node equation (rc_building)
    ht = inp.heat_tank[bi]
    qcm = None if not inp.cooled[bi] else inp.qc_max[bi][:n] / inp.dt_h
    q, qc, T = simulate_thermostat(inp.area[bi], inp.ta[:n], inp.ghi[:n], inp.params[bi], dt_s=3600.0 * inp.dt_h, q_heat_max=ht['maxout'][:n] / inp.dt_h, q_cool_max=qcm)
    return q * inp.dt_h, qc * inp.dt_h, T                                 # kWh thermal per step


def solve_building(inp, bi, p_exp, band, n=None):
    n = n or inp.N
    if inp.two_zone[bi]:
        return solve_building_zones(inp, bi, p_exp, band, n)
    p = inp.params[bi]
    A = inp.area[bi]
    cooled = inp.cooled[bi]
    price = inp.price[:n]
    ta, ghi = inp.ta[:n], inp.ghi[:n]
    ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
    cop = ht['cop'][:n]
    q_th, qc_th, T_th = thermostat(inp, bi, n)
    pv = inp.pv_gen[bi][:n]
    base = inp.base[bi][:n] - pv
    dt_h = inp.dt_h
    bat = battery_spec(inp.kwp[bi] * 1.0, dt_h)                            # 1 kWh per kWp, as every cell dataset
    blocks, idx = [], {}

    def add(name, lo, hi, cost):
        idx[name] = sum(b[1] for b in blocks)
        blocks.append((name, n, np.broadcast_to(lo, (n,)), np.broadcast_to(hi, (n,)), np.broadcast_to(cost, (n,))))

    caph = ht['cap']
    rate_h = caph * dt_h
    add('a', 0.0, np.minimum(rate_h, ht['maxout'][:n]), 0.0); add('d', 0.0, rate_h, 0.0); add('E', 0.0, caph, 0.0)
    add('Q', 0.0, ht['maxout'][:n], 0.0)
    upper = inp.season_upper(cooled)[:n]
    if band == 'band':
        t_lo, t_hi = np.minimum(LOWER_C, T_th), np.maximum(upper, T_th)
    elif band == 'no thermal flexibility':
        t_lo, t_hi = np.minimum(LOWER_C, T_th), np.maximum(LOWER_C, T_th)
    elif band == 'pinned':
        t_lo, t_hi = T_th, T_th
    else:
        raise ValueError(band)
    add('T', t_lo, t_hi, 0.0)
    if cooled:
        add('Qc', 0.0, inp.qc_max[bi][:n], 0.0)
    if wt is not None:
        rate_w = wt['cap'] * dt_h
        add('a2', 0.0, np.minimum(rate_w, wt['maxout'][:n]), 0.0); add('d2', 0.0, np.minimum(rate_w, wt['demand'][:n]), 0.0); add('E2', 0.0, wt['cap'], 0.0)
    add('c', 0.0, bat['power'], 0.0); add('u', 0.0, bat['power'], 0.0); add('Eb', bat['emin'], bat['cap'], 0.0)
    p_exp = np.broadcast_to(np.asarray(p_exp, dtype=float), (n,))
    assert (p_exp <= price + 1e-12).all()
    add('i', 0.0, np.inf, price); add('x', 0.0, np.inf, -p_exp)
    names = [b[0] for b in blocks]
    cvec = np.concatenate([b[4] for b in blocks]); lo = np.concatenate([b[2] for b in blocks]).astype(float).copy(); hi = np.concatenate([b[3] for b in blocks]).astype(float)
    last = idx['T'] + n - 1
    lo[last] = max(lo[last], min(p['setpoint_c'], T_th[-1]))              # no end-of-horizon cool-down gain (as oracle_rc)
    if band == 'pinned':
        lo[last] = T_th[-1]
    I = sp.identity(n, format='csr'); Z = sp.csr_matrix((n, n))

    def sub(lam):
        return sp.diags([np.full(n - 1, -(1.0 - lam))], [-1], shape=(n, n), format='csr')

    def row(entries):
        m = [Z] * len(blocks)
        for nm, mat in entries:
            m[names.index(nm)] = mat
        return sp.hstack(m, format='csr')

    eq, beq, ub, bub = [], [], [], []
    for t, qa, qd, qe in ((ht, 'a', 'd', 'E'), (wt, 'a2', 'd2', 'E2')):
        if t is None:
            continue
        rho, lam = t['rho'], t['loss']
        eq.append(row([(qa, -rho * I), (qd, I / rho), (qe, I + sub(lam))]))
        b = np.zeros(n); b[0] = (1.0 - lam) * t['e0']; beq.append(b)
    ub.append(row([('Q', I), ('d', -I), ('a', I)])); bub.append(ht['maxout'][:n])
    ub.append(row([('d', I), ('Q', -I)])); bub.append(np.zeros(n))
    if wt is not None:
        ub.append(row([('a2', I), ('d2', -I)])); bub.append(wt['maxout'][:n] - wt['demand'][:n])
    Hh = p['H_w_per_k_m2'] * A
    e = float(np.exp(-3600.0 * dt_h * p['H_w_per_k_m2'] / p['C_j_per_k_m2']))
    rhs = (1 - e) * (ta + (p['g'] * A * ghi + p['L_internal_w_m2'] * A) / Hh)
    rhs = rhs.copy(); rhs[0] += e * p['setpoint_c']
    k_q = (1 - e) * 1000.0 / (Hh * dt_h)
    ent_t = [('T', I + sp.diags([np.full(n - 1, -e)], [-1], shape=(n, n), format='csr')), ('Q', -k_q * I)]
    if cooled:
        ent_t.append(('Qc', k_q * I))
    eq.append(row(ent_t)); beq.append(rhs)
    eq.append(row([('c', -bat['eta1'] * I), ('u', I / bat['eta1']), ('Eb', I + sub(0.0))]))
    b = np.zeros(n); b[0] = bat['e0']; beq.append(b)
    ent = [('i', I), ('x', -I), ('Q', -sp.diags(1.0 / cop)), ('a', -sp.diags(1.0 / cop)), ('d', sp.diags(1.0 / cop)), ('c', -I), ('u', I)]
    if wt is not None:
        ent += [('a2', -sp.diags(1.0 / wt['cop'][:n])), ('d2', sp.diags(1.0 / wt['cop'][:n]))]
    if cooled:
        ent.append(('Qc', -sp.diags(1.0 / inp.copc[bi][:n])))
    eq.append(row(ent)); beq.append(base)
    r = linprog(cvec, A_ub=sp.vstack(ub, format='csr'), b_ub=np.concatenate(bub), A_eq=sp.vstack(eq, format='csr'), b_eq=np.concatenate(beq),
                bounds=np.column_stack([lo, hi]), method='highs')
    if r.status != 0:
        raise RuntimeError(f'LP failed ({inp.names[bi]}, {band}): {r.message}')
    x = r.x
    get = lambda nm: x[idx[nm]: idx[nm] + n]   # noqa: E731
    imp, exp = get('i'), get('x')
    net_base = base + q_th / cop + (qc_th / inp.copc[bi][:n] if cooled else 0.0)
    zero = float((price * np.maximum(net_base, 0)).sum() - (p_exp * np.maximum(-net_base, 0)).sum())
    z = np.zeros(n)
    return {'bill': float(r.fun), 'zero_bill': zero, 'imp': imp, 'exp': exp, 'Q': get('Q'), 'a': get('a'), 'd': get('d'), 'T': get('T'),
            'Qc': get('Qc') if cooled else z, 'a2': get('a2') if wt is not None else z, 'd2': get('d2') if wt is not None else z, 'c': get('c'), 'u': get('u'),
            'net_base': net_base, 'q_th': q_th, 'qc_th': qc_th, 'T_th': T_th, 'cop': cop, 'copc': inp.copc[bi][:n] if cooled else None, 'cop_dhw_tank': wt['cop'][:n] if wt is not None else None}


def solve_building_zones(inp, bi, p_exp, band, n):
    """Archetype B (room units, WP2b): as solve_building, with TWO independent room nodes of the same per-m2 parameters, a cooled zone (area f A, temperature T, cooling Qc) and an
    uncooled zone (area (1 - f) A, temperature T2); heating Q is one variable split by area (both zones get Q / A per m2). Per zone, with k_q = (1 - e) 1000 / (H A dt):
        zone 2:  T2_t - e T2_{t-1} - k_q Q_t               = (1 - e) (T_amb + (g I + L) / H)        (per m2 the external terms do not depend on the area)
        zone 1:  T_t  - e T_{t-1}  - k_q Q_t + (k_q / f) Qc_t = the same right-hand side
    Bands per zone as solve_building: cooled zone lower 21 C, upper 24 C (26 C in the cooling season), uncooled zone lower 21 C, upper 24 C, each never below its own thermostat
    path; 'pinned' = both zones on their thermostat paths. The reported temperature T is the area-weighted mean (what CityLearn reports); T1 and T2 are the zones."""
    p = inp.params[bi]
    A, f = inp.area[bi], inp.frac[bi]
    price = inp.price[:n]
    ta, ghi = inp.ta[:n], inp.ghi[:n]
    ht, wt = inp.heat_tank[bi], inp.dhw_tank[bi]
    cop = ht['cop'][:n]
    q_th, qc_th, T1_th, T2_th, Tm_th = thermostat_zones(inp, bi, n)
    pv = inp.pv_gen[bi][:n]
    base = inp.base[bi][:n] - pv
    dt_h = inp.dt_h
    bat = battery_spec(inp.kwp[bi] * 1.0, dt_h)
    blocks, idx = [], {}

    def add(name, lo, hi, cost):
        idx[name] = sum(b[1] for b in blocks)
        blocks.append((name, n, np.broadcast_to(lo, (n,)), np.broadcast_to(hi, (n,)), np.broadcast_to(cost, (n,))))

    caph = ht['cap']
    rate_h = caph * dt_h
    add('a', 0.0, np.minimum(rate_h, ht['maxout'][:n]), 0.0); add('d', 0.0, rate_h, 0.0); add('E', 0.0, caph, 0.0)
    add('Q', 0.0, ht['maxout'][:n], 0.0)
    zone_bounds = []
    for T_th, upper in ((T1_th, inp.season_upper(True)[:n]), (T2_th, np.full(n, UPPER_HEATING_SEASON_C))):
        if band == 'band':
            zone_bounds.append((np.minimum(LOWER_C, T_th), np.maximum(upper, T_th)))
        elif band == 'no thermal flexibility':
            zone_bounds.append((np.minimum(LOWER_C, T_th), np.maximum(LOWER_C, T_th)))
        elif band == 'pinned':
            zone_bounds.append((T_th, T_th))
        else:
            raise ValueError(band)
    add('T', *zone_bounds[0], 0.0)
    add('T2', *zone_bounds[1], 0.0)
    add('Qc', 0.0, inp.qc_max[bi][:n], 0.0)
    if wt is not None:
        rate_w = wt['cap'] * dt_h
        add('a2', 0.0, np.minimum(rate_w, wt['maxout'][:n]), 0.0); add('d2', 0.0, np.minimum(rate_w, wt['demand'][:n]), 0.0); add('E2', 0.0, wt['cap'], 0.0)
    add('c', 0.0, bat['power'], 0.0); add('u', 0.0, bat['power'], 0.0); add('Eb', bat['emin'], bat['cap'], 0.0)
    p_exp = np.broadcast_to(np.asarray(p_exp, dtype=float), (n,))
    assert (p_exp <= price + 1e-12).all()
    add('i', 0.0, np.inf, price); add('x', 0.0, np.inf, -p_exp)
    names = [b[0] for b in blocks]
    cvec = np.concatenate([b[4] for b in blocks]); lo = np.concatenate([b[2] for b in blocks]).astype(float).copy(); hi = np.concatenate([b[3] for b in blocks]).astype(float)
    for nm, T_th in (('T', T1_th), ('T2', T2_th)):
        last = idx[nm] + n - 1
        lo[last] = max(lo[last], min(p['setpoint_c'], T_th[-1]))
        if band == 'pinned':
            lo[last] = T_th[-1]
    I = sp.identity(n, format='csr'); Z = sp.csr_matrix((n, n))

    def sub(lam):
        return sp.diags([np.full(n - 1, -(1.0 - lam))], [-1], shape=(n, n), format='csr')

    def row(entries):
        m = [Z] * len(blocks)
        for nm, mat in entries:
            m[names.index(nm)] = mat
        return sp.hstack(m, format='csr')

    eq, beq, ub, bub = [], [], [], []
    for t, qa, qd, qe in ((ht, 'a', 'd', 'E'), (wt, 'a2', 'd2', 'E2')):
        if t is None:
            continue
        rho, lam = t['rho'], t['loss']
        eq.append(row([(qa, -rho * I), (qd, I / rho), (qe, I + sub(lam))]))
        b = np.zeros(n); b[0] = (1.0 - lam) * t['e0']; beq.append(b)
    ub.append(row([('Q', I), ('d', -I), ('a', I)])); bub.append(ht['maxout'][:n])
    ub.append(row([('d', I), ('Q', -I)])); bub.append(np.zeros(n))
    if wt is not None:
        ub.append(row([('a2', I), ('d2', -I)])); bub.append(wt['maxout'][:n] - wt['demand'][:n])
    Hh = p['H_w_per_k_m2'] * A
    e = float(np.exp(-3600.0 * dt_h * p['H_w_per_k_m2'] / p['C_j_per_k_m2']))
    rhs = (1 - e) * (ta + (p['g'] * A * ghi + p['L_internal_w_m2'] * A) / Hh)
    rhs = rhs.copy(); rhs[0] += e * p['setpoint_c']
    k_q = (1 - e) * 1000.0 / (Hh * dt_h)
    decay = sp.diags([np.full(n - 1, -e)], [-1], shape=(n, n), format='csr')
    eq.append(row([('T', I + decay), ('Q', -k_q * I), ('Qc', (k_q / f) * I)])); beq.append(rhs)
    eq.append(row([('T2', I + decay), ('Q', -k_q * I)])); beq.append(rhs)
    eq.append(row([('c', -bat['eta1'] * I), ('u', I / bat['eta1']), ('Eb', I + sub(0.0))]))
    b = np.zeros(n); b[0] = bat['e0']; beq.append(b)
    ent = [('i', I), ('x', -I), ('Q', -sp.diags(1.0 / cop)), ('a', -sp.diags(1.0 / cop)), ('d', sp.diags(1.0 / cop)), ('c', -I), ('u', I), ('Qc', -sp.diags(1.0 / inp.copc[bi][:n]))]
    if wt is not None:
        ent += [('a2', -sp.diags(1.0 / wt['cop'][:n])), ('d2', sp.diags(1.0 / wt['cop'][:n]))]
    eq.append(row(ent)); beq.append(base)
    r = linprog(cvec, A_ub=sp.vstack(ub, format='csr'), b_ub=np.concatenate(bub), A_eq=sp.vstack(eq, format='csr'), b_eq=np.concatenate(beq),
                bounds=np.column_stack([lo, hi]), method='highs')
    if r.status != 0:
        raise RuntimeError(f'LP failed ({inp.names[bi]}, {band}, two zones): {r.message}')
    x = r.x
    get = lambda nm: x[idx[nm]: idx[nm] + n]   # noqa: E731
    imp, exp = get('i'), get('x')
    net_base = base + q_th / cop + qc_th / inp.copc[bi][:n]
    zero = float((price * np.maximum(net_base, 0)).sum() - (p_exp * np.maximum(-net_base, 0)).sum())
    z = np.zeros(n)
    T1, T2 = get('T'), get('T2')
    return {'bill': float(r.fun), 'zero_bill': zero, 'imp': imp, 'exp': exp, 'Q': get('Q'), 'a': get('a'), 'd': get('d'), 'T': f * T1 + (1.0 - f) * T2, 'T1': T1, 'T2': T2,
            'Qc': get('Qc'), 'a2': get('a2') if wt is not None else z, 'd2': get('d2') if wt is not None else z, 'c': get('c'), 'u': get('u'), 'frac': f,
            'net_base': net_base, 'q_th': q_th, 'qc_th': qc_th, 'T_th': Tm_th, 'T1_th': T1_th, 'T2_th': T2_th, 'cop': cop, 'copc': inp.copc[bi][:n],
            'cop_dhw_tank': wt['cop'][:n] if wt is not None else None}


def cell_metrics(inp, sols, p_exp_rp, n):
    """District totals and the summer, peak, overheating and emissions metrics of a solved cell."""
    price = inp.price[:n]
    pexp = p_exp_rp / 100.0
    summer = np.isin(inp.local_month[:n], SUMMER)
    dt = inp.dt_h
    net_opt = sum(s['imp'] - s['exp'] for s in sols)
    net_base = sum(s['net_base'] for s in sols)
    imp_opt = sum(s['imp'] for s in sols); exp_opt = sum(s['exp'] for s in sols)
    imp_base = sum(np.maximum(s['net_base'], 0) for s in sols); exp_base = sum(np.maximum(-s['net_base'], 0) for s in sols)
    pv = sum(inp.pv_gen[bi][:n] for bi in range(len(sols)))
    heat_opt = sum((s['Q'] - s['d'] + s['a']) / s['cop'] for s in sols)
    heat_base = sum(s['q_th'] / s['cop'] for s in sols)
    cool_opt = sum(s['Qc'] / s['copc'] for s in sols if s['copc'] is not None)
    cool_base = sum(s['qc_th'] / s['copc'] for s in sols if s['copc'] is not None)
    ci = inp.carbon[:n]
    dh = lambda T: float(np.maximum(T - OVERHEAT_C, 0).sum() * dt)   # noqa: E731

    def dhb(s, which):
        """Degree-hours above 26 C of a building: the single-node temperature, or for room units the area-weighted sum of the zone values (f x cooled zone + (1 - f) x uncooled zone)."""
        if 'T1' in s:
            t1, t2 = (s['T1'], s['T2']) if which == 'opt' else (s['T1_th'], s['T2_th'])
            return s['frac'] * dh(t1) + (1.0 - s['frac']) * dh(t2)
        return dh(s['T'] if which == 'opt' else s['T_th'])
    zero_bill = sum(s['zero_bill'] for s in sols); opt_bill = sum(s['bill'] for s in sols)
    return {
        'cell': inp.name, 'steps': int(n), 'export_price_rp': float(p_exp_rp), 'cooled_buildings': [r for r, c in zip(inp.roles, inp.cooled) if c],
        'zero_bill_chf': zero_bill, 'opt_bill_chf': opt_bill, 'saving_chf': zero_bill - opt_bill, 'saving_pct': 100.0 * (zero_bill - opt_bill) / zero_bill,
        'import_kwh': {'baseline': float(imp_base.sum()), 'optimum': float(imp_opt.sum()), 'summer_baseline': float(imp_base[summer].sum()), 'summer_optimum': float(imp_opt[summer].sum())},
        'export_kwh': {'baseline': float(exp_base.sum()), 'optimum': float(exp_opt.sum()), 'summer_baseline': float(exp_base[summer].sum()), 'summer_optimum': float(exp_opt[summer].sum())},
        'peak_kw': {'baseline': float(net_base.max() / dt), 'optimum': float(net_opt.max() / dt),
                    'summer_baseline': float(net_base[summer].max() / dt) if summer.any() else None, 'summer_optimum': float(net_opt[summer].max() / dt) if summer.any() else None},
        'pv_generation_kwh': float(pv.sum()),
        'pv_self_consumption': {'baseline': float(1.0 - exp_base.sum() / max(pv.sum(), 1e-9)), 'optimum': float(1.0 - exp_opt.sum() / max(pv.sum(), 1e-9))},
        'heating_electricity_kwh': {'baseline': float(heat_base.sum()), 'optimum': float(heat_opt.sum())},
        'cooling_electricity_kwh': {'baseline': float(np.sum(cool_base)), 'optimum': float(np.sum(cool_opt))},
        'emissions_kg': {'baseline': float((imp_base * ci).sum()), 'optimum': float((imp_opt * ci).sum())},
        'emissions_index_optimum_vs_baseline': float((imp_opt * ci).sum() / max((imp_base * ci).sum(), 1e-9)),
        'degree_hours_above_26': {'baseline': float(sum(dhb(s, 'th') for s in sols)), 'optimum': float(sum(dhb(s, 'opt') for s in sols)),
                                  'by_building_optimum': {r: dhb(s, 'opt') for r, s in zip(inp.roles, sols)}, 'by_building_baseline': {r: dhb(s, 'th') for r, s in zip(inp.roles, sols)},
                                  'zones': zone_dh(sols, dh)},
        'mean_indoor_c': {'baseline': float(np.mean([s['T_th'].mean() for s in sols])), 'optimum': float(np.mean([s['T'].mean() for s in sols]))},
    }


def zone_dh(sols, dh):
    """Raw zone degree-hours above 26 C summed over buildings (not area-weighted), room-unit buildings only: cooled zone and uncooled zone, baseline and optimum."""
    z = [s for s in sols if 'T1' in s]
    if not z:
        return None
    return {'cooled_zone': {'baseline': float(sum(dh(s['T1_th']) for s in z)), 'optimum': float(sum(dh(s['T1']) for s in z))},
            'uncooled_zone': {'baseline': float(sum(dh(s['T2_th']) for s in z)), 'optimum': float(sum(dh(s['T2']) for s in z))}}


def solve_cell(inp, band='band', p_exp_rp=8.0, n=None):
    n = n or inp.N
    pe = p_exp_rp / 100.0
    sols = [solve_building(inp, bi, pe, band, n) for bi in range(len(inp.names))]
    return cell_metrics(inp, sols, p_exp_rp, n), sols


def schedule(env, inp, sols, n_total):
    """Action matrix (steps x action slots of the central agent) that realises the solutions."""
    from swiss.citylearn_build.build_dataset import BATTERY
    cols = [(bi, nm) for bi, b in enumerate(env.buildings) for nm in b.active_actions]
    act = np.zeros((n_total, len(cols)))
    for j, (bi, nm) in enumerate(cols):
        s = sols[bi]; m = len(s['imp']); ht = inp.heat_tank[bi]
        if nm == 'heating_storage':
            act[:m, j] = np.clip((s['a'] - s['d']) / (ht['cap'] * inp.dt_h), -1, 1)
        elif nm == 'dhw_storage' and inp.dhw_tank[bi] is not None:
            wt = inp.dhw_tank[bi]; act[:m, j] = np.clip((s['a2'] - s['d2']) / (wt['cap'] * inp.dt_h), -1, 1)
        elif nm == 'heating_device':
            act[:m, j] = np.clip(s['Q'] / ht['maxout'][:m], 0, 1)
        elif nm == 'cooling_or_heating_device':
            heat = s['Q'] / ht['maxout'][:m]
            cool = np.divide(s['Qc'], inp.qc_max[bi][:m], out=np.zeros(m), where=inp.qc_max[bi][:m] > 0)
            act[:m, j] = np.clip(heat - cool, -1, 1)
        elif nm == 'electrical_storage':
            act[:m, j] = np.clip((s['c'] - s['u']) / (BATTERY['c_rate'] * inp.kwp[bi] * 1.0 * inp.dt_h), -1, 1)
    return act


def replay(inp, band='band', p_exp_rp=8.0, n=None):
    """Play the optimum over the first n steps in CityLearn and compare the realised bill with the program."""
    n = n or inp.N
    tot, sols = solve_cell(inp, band, p_exp_rp, n)
    env = CityLearnEnv(os.path.join(inp.dir, 'schema.json'), central_agent=True, reward_function=SwissDistrictReward)
    ag = oracle.Replay(schedule(env, inp, sols, inp.N))
    obs, _ = env.reset()
    for _ in range(n):
        if env.terminated:
            break
        obs, *_ = env.step(ag.predict(obs))
    net = np.stack([np.asarray(b.net_electricity_consumption, dtype=float)[:n] for b in env.buildings], axis=1)
    price = inp.price[:n]
    imp, exp = np.maximum(net, 0), np.maximum(-net, 0)
    realised = float((imp * price[:, None]).sum() - p_exp_rp / 100.0 * exp.sum())
    temps = np.stack([np.asarray(b.energy_simulation.indoor_dry_bulb_temperature, dtype=float)[:n] for b in env.buildings], axis=1)
    pred_T = np.stack([s['T'] for s in sols], axis=1)
    cool_el = sum(np.asarray(b.cooling_electricity_consumption, dtype=float)[:n].sum() for b in env.buildings)
    return {'cell': inp.name, 'band': band, 'steps': int(n), 'predicted_bill_chf': tot['opt_bill_chf'], 'realised_bill_chf': realised, 'zero_bill_chf': tot['zero_bill_chf'],
            'predicted_saving_chf': tot['saving_chf'], 'realised_saving_chf': tot['zero_bill_chf'] - realised,
            'rel_diff_saving_pct': 100.0 * abs((tot['zero_bill_chf'] - realised) - tot['saving_chf']) / max(abs(tot['saving_chf']), 1e-9),
            'max_temperature_difference_k': float(np.abs(temps - pred_T).max()),
            'cooling_electricity_kwh_predicted': tot['cooling_electricity_kwh']['optimum'], 'cooling_electricity_kwh_realised': float(cool_el)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--cell', required=True, help='dataset folder name under swiss/datasets/climate, e.g. hist_high')
    ap.add_argument('--band', default='band', choices=BANDS)
    ap.add_argument('--export', type=float, default=8.0, help='export price Rp/kWh')
    ap.add_argument('--steps', type=int, default=None)
    ap.add_argument('--replay', type=int, default=0, help='also replay the first N steps in CityLearn')
    ap.add_argument('--save-schedules', action='store_true')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    t0 = time.time()
    inp = ClimateInputs(a.cell)
    tot, sols = solve_cell(inp, a.band, a.export, a.steps)
    print(f'{a.cell} {a.band}: baseline {tot["zero_bill_chf"]:.0f} optimum {tot["opt_bill_chf"]:.0f} saving {tot["saving_pct"]:.2f} % '
          f'peak {tot["peak_kw"]["baseline"]:.1f} -> {tot["peak_kw"]["optimum"]:.1f} kW, summer peak {tot["peak_kw"]["summer_baseline"]} -> {tot["peak_kw"]["summer_optimum"]} [{time.time() - t0:.0f}s]', flush=True)
    res = {'metrics': tot, 'band': a.band}
    if a.replay:
        res['replay'] = replay(inp, a.band, a.export, a.replay)
        r = res['replay']
        print(f'replay {r["steps"]} steps: predicted {r["predicted_bill_chf"]:.2f} realised {r["realised_bill_chf"]:.2f} saving diff {r["rel_diff_saving_pct"]:.3f} % '
              f'max T diff {r["max_temperature_difference_k"]:.3f} K cooling el {r["cooling_electricity_kwh_predicted"]:.1f} / {r["cooling_electricity_kwh_realised"]:.1f} kWh', flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, f'{a.cell}__{a.band.replace(" ", "_")}.json'), 'w'), indent=1)
    if a.save_schedules:
        np.savez_compressed(os.path.join(a.out, f'{a.cell}__{a.band.replace(" ", "_")}.npz'), **{f'{k}_{i}': v for i, s in enumerate(sols) for k, v in s.items() if isinstance(v, np.ndarray)})
    return res


if __name__ == '__main__':
    main()
