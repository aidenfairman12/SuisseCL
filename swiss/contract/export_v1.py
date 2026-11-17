"""Export contract v1 files to web/public/bundle/sim/ from REAL CityLearn rollouts (no numbers are typed in here).

  manifest.json, buildings.json, components.json, conditions.json, comparisons.json, comparisons_year.json, runs/<scenario>/<controller>.json

Default: a 48-hour SAMPLE (kind "sample") = the coldest weekday of the year (local calendar day, Mon-Fri) and the following
day, all six controllers. `--full` exports the whole simulated year (8,759 steps; inputs 8,760) with the same code.
Everything derived here (tank mode, tank loss, situation tags, comparisons) is computed in Python from CityLearn's own flow
properties, so the frontend never has to reconstruct physics.

Run: cl/bin/python -I swiss/contract/export_v1.py [--full] [--hours 48] [--start-step N] [--out DIR]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn import __version__ as CL_VERSION  # noqa: E402

from swiss.contract import CONTRACT_VERSION  # noqa: E402
from swiss.contract import recorder  # noqa: E402
from swiss.contract.registry import registry  # noqa: E402
from swiss.contract.variables import (BUILDING_VARIABLES, CONDITION_VARIABLES, DISTRICT_VARIABLES, SITUATION_TAGS, THRESHOLDS, UNITS)  # noqa: E402
from swiss.dashboard import bundle_io, figures  # noqa: E402
from swiss.dashboard.parse_registries import parse_csv_registry  # noqa: E402
from swiss.experiments.rewards import TERMS  # noqa: E402

OUT = os.path.join(ROOT, 'web', 'public', 'bundle', 'sim')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
REF = 'ALG-001_zero_action'
SCENARIO = 'base'
STEP_S = 3600
DATASET = 'swiss/datasets/swiss_district_2023'
INPUT_FILES = [f'{DATASET}/{f}' for f in ('build_manifest.json', 'weather.csv', 'pricing.csv', 'carbon_intensity.csv')] + \
              [f'{DATASET}/Building_{i}.csv' for i in range(1, 7)] + \
              ['data/canonical/weather_klo_2023_hourly.csv', 'data/canonical/tariff_ekz_standard_2023_hourly.csv',
               'data/canonical/carbon_ch_2023_hourly.csv', 'data/canonical/thermal/thermal_params.json', 'data/interim/selected_buildings.csv',
               'swiss/experiments/results/baselines_2023.csv', 'swiss/experiments/results/reward_scales.json', 'swiss/dashboard/ui_map.yaml']
_read = set()


def rd(p):
    _read.add(p)
    return pd.read_csv(os.path.join(ROOT, p))


def rj(p):
    _read.add(p)
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return json.load(f)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def r6(a, nd=6):
    return [float(x) for x in np.round(np.asarray(a, dtype=float), nd) + 0.0]


# ------------------------------------------------------------------------------------------------ window
def pick_window(S, hours):
    """Start of the local calendar day with the lowest mean temperature among weekdays Mon-Fri; the window is `hours` long from local midnight."""
    idx = pd.date_range(S['start_utc'], periods=S['n'], freq='h', tz='UTC').tz_convert('Europe/Zurich')
    t = pd.Series(S['series']['temp_c']['values'], dtype=float)
    df = pd.DataFrame({'date': idx.date, 'wd': idx.weekday, 'h': idx.hour, 't': t.to_numpy()})
    full = df.groupby('date').filter(lambda g: len(g) == 24 and g.wd.iloc[0] < 5 and not g.t.isna().any())
    day = full.groupby('date').t.mean().idxmin()
    start = int(df.index[(df.date == day) & (df.h == 0)][0])
    return start, str(day)


# ------------------------------------------------------------------------------------------------ situations
def situations(rec, S, thr_cold, start, n):
    """Sparse situation tags: tag -> list of step indices (relative to the window start). Computed on the full year, then sliced."""
    N = rec['n']
    sl = slice(start, start + n)
    temp = np.asarray(S['series']['temp_c']['values'], dtype=float)[:N]
    high = np.asarray(S['tier_high'], dtype=int)[:N].astype(bool)
    idx = pd.date_range(S['start_utc'], periods=N, freq='h', tz='UTC').tz_convert('Europe/Zurich')
    net = np.sum([b['net_kwh_el'] for b in rec['buildings']], axis=0)
    day = pd.Series(idx.date)
    daily_peak = (pd.Series(net).groupby(day.to_numpy()).transform('max').to_numpy() == net) & (net > 0)
    steps = lambda m: [int(i) for i in np.nonzero(m[sl])[0]]  # noqa: E731
    district = {'cold_hour': steps(temp <= thr_cold), 'high_tariff': steps(high), 'low_tariff': steps(~high), 'district_daily_peak': steps(daily_peak)}
    eps = THRESHOLDS['flow_epsilon_kwh_th']
    per = {}
    for role, b in zip(ROLES, rec['buildings']):
        tags = {}
        for pre in ('sh', 'hw'):
            if b[f'{pre}_tank_capacity_kwh_th'] <= 0:
                continue
            chg, dis = b[f'hp_{pre}_to_tank_kwh_th'] > eps, b[f'{pre}_tank_to_demand_kwh_th'] > eps
            soc, dem = b[f'{pre}_tank_soc'], b[f'{pre}_demand_kwh_th']
            tags[f'{pre}_tank_charging'], tags[f'{pre}_tank_discharging'] = steps(chg), steps(dis)
            tags[f'{pre}_tank_idle'] = steps(~chg & ~dis)
            tags[f'{pre}_tank_full'], tags[f'{pre}_tank_empty'] = steps(soc >= THRESHOLDS['tank_full_soc']), steps(soc <= THRESHOLDS['tank_empty_soc'])
            tags[f'{pre}_tank_covers_demand'] = steps((dem > eps) & (b[f'{pre}_tank_to_demand_kwh_th'] >= THRESHOLDS['storage_covers_demand_share'] * dem))
        tags['hp_sh_near_capacity'] = steps(b['hp_sh_kwh_el'] >= THRESHOLDS['near_capacity_fraction'] * b['hp_sh_nominal_kw_el'] * STEP_S / 3600)
        per[role] = {k: v for k, v in tags.items() if v}
    return {'district': {k: v for k, v in district.items() if v}, 'buildings': per}


# ------------------------------------------------------------------------------------------------ one run
def run_arrays(rec, price, start, n):
    sl = slice(start, start + n)
    out, net_all = {}, []
    for role, b in zip(ROLES, rec['buildings']):
        d = {}
        for k in BUILDING_VARIABLES:
            if k.endswith('_tank_mode'):
                continue
            if k == 'cost_chf':
                d[k] = r6(np.maximum(b['net_kwh_el'][sl], 0) * price[sl])
                continue
            pre = k.split('_')[0] if k.startswith(('sh_', 'hw_')) else (k.split('_')[1] if k.startswith('hp_') else None)
            absent = pre == 'hw' and b['hw_tank_capacity_kwh_th'] <= 0 and BUILDING_VARIABLES[k]['absent_when']
            if absent:
                d[k] = None
                continue
            d[k] = r6(b[k][sl], 4 if k.startswith('cop_') or k.endswith('_action') else 6)
        for pre in ('sh', 'hw'):
            if b[f'{pre}_tank_capacity_kwh_th'] <= 0:
                d[f'{pre}_tank_mode'] = None
                continue
            eps = THRESHOLDS['flow_epsilon_kwh_th']
            chg, dis = b[f'hp_{pre}_to_tank_kwh_th'][sl] > eps, b[f'{pre}_tank_to_demand_kwh_th'][sl] > eps
            d[f'{pre}_tank_mode'] = ['charging' if c else 'discharging' if x else 'idle' for c, x in zip(chg, dis)]
        out[role] = d
        net_all.append(b['net_kwh_el'][sl])
    B = rec['buildings']
    imp = np.sum([np.maximum(b['net_kwh_el'][sl], 0) for b in B], axis=0)
    parts = rec['reward_parts'][sl]
    district = {'net_kwh_el': r6(np.sum(net_all, axis=0)), 'hp_kwh_el': r6(np.sum([b['hp_sh_kwh_el'][sl] + b['hp_hw_kwh_el'][sl] for b in B], axis=0)),
                'household_kwh_el': r6(np.sum([b['household_kwh_el'][sl] for b in B], axis=0)),
                'sh_demand_kwh_th': r6(np.sum([b['sh_demand_kwh_th'][sl] for b in B], axis=0)),
                'hw_demand_kwh_th': r6(np.sum([b['hw_demand_kwh_th'][sl] for b in B], axis=0)),
                'cost_chf': r6(imp * price[sl]), 'reward': r6(rec['reward'][sl], 6),
                'reward_cost': r6(parts[:, 0]), 'reward_peak': r6(parts[:, 1]), 'reward_ramp': r6(parts[:, 2])}
    return out, district


def summarise(rec, price, tier_high, start, n):
    sl = slice(start, start + n)
    B = rec['buildings']
    net = np.sum([b['net_kwh_el'][sl] for b in B], axis=0)
    imp = np.sum([np.maximum(b['net_kwh_el'][sl], 0) for b in B], axis=0)
    hi = tier_high[sl].astype(bool)
    loss = sum(b[f'{p}_tank_loss_kwh_th'][sl].sum() for b in B for p in ('sh', 'hw') if b[f'{p}_tank_capacity_kwh_th'] > 0)
    from_tank = sum(b[f'{p}_tank_to_demand_kwh_th'][sl].sum() for b in B for p in ('sh', 'hw') if b[f'{p}_tank_capacity_kwh_th'] > 0)
    blocks = (np.arange(rec['n']) // 24)[sl]          # 24-step blocks from step 0 (= local midnight), the convention of baselines_2023.csv
    daily = float(pd.Series(net).groupby(blocks).max().mean())
    return {'import_kwh_el': float(imp.sum()), 'peak_kw_el': float(net.max() / (STEP_S / 3600)), 'peak_step': int(net.argmax()),
            'mean_daily_peak_kw_el': daily / (STEP_S / 3600),
            'cost_chf': float((imp * price[sl]).sum()), 'high_tariff_import_share': float(imp[hi].sum() / imp.sum()) if imp.sum() else 0.0,
            'hp_kwh_el': float(sum((b['hp_sh_kwh_el'][sl] + b['hp_hw_kwh_el'][sl]).sum() for b in B)), 'tank_loss_kwh_th': float(loss),
            'heat_from_tanks_kwh_th': float(from_tank), 'reward_sum': float(rec['reward'][sl].sum())}


def tank_terms(rec, ref, price, ci, start, n):
    """EXACT decomposition of what a controller changes relative to the no-control reference, per tank device and summed.

    With demand fixed, a controller changes only the heat that passes through tanks: in_t (heat pump -> tank) and out_t (tank -> demand), so
        extra heat-pump electricity   = sum_t (in_t - out_t) / COP_t          (A - B below, A = charging electricity, B = avoided electricity)
        extra cost                    = sum_t price_t (in_t - out_t) / COP_t   (same weights with the price; carbon likewise with the carbon series)
    and, with c = mean COP weighted by charging heat, pc / pd = the electricity-weighted mean price at charging / discharge time,
        extra electricity = (loss + stored change) / c  +  B (1/c - 1/d)  = losses + stored remainder + COP timing      [d = discharge-side mean COP]
        extra cost        = B (pc - pd)  +  (A - B) pc                      = tariff timing + extra electricity bought at the charging price
    All identities are exact; the reference must not use its tanks (asserted)."""
    sl = slice(start, start + n)
    t = {k: 0.0 for k in ('heat_in', 'heat_out', 'stored_change', 'charge_el', 'avoided_el', 'loss_el', 'stored_el', 'timing_el',
                          'cost_timing', 'cost_extra_el', 'carbon_timing', 'carbon_extra_el')}
    for b, br in zip(rec['buildings'], ref['buildings']):
        for pre in ('sh', 'hw'):
            cap = b[f'{pre}_tank_capacity_kwh_th']
            if cap <= 0:
                continue
            if abs(br[f'hp_{pre}_to_tank_kwh_th'][sl]).sum() + abs(br[f'{pre}_tank_to_demand_kwh_th'][sl]).sum() > 1e-6:
                raise ValueError('the reference controller must not use its tanks')
            inn, out, cop, soc = b[f'hp_{pre}_to_tank_kwh_th'][sl], b[f'{pre}_tank_to_demand_kwh_th'][sl], b[f'cop_{pre}'][sl], b[f'{pre}_tank_soc']
            e_end = soc[start + n - 1] * cap
            e_start = soc[start - 1] * cap if start > 0 else 0.0
            d_e = e_end - e_start
            a, bv = (inn / cop).sum(), (out / cop).sum()
            if a <= 0:
                continue
            c_bar = inn.sum() / a
            loss = inn.sum() - out.sum() - d_e
            t['heat_in'] += inn.sum(); t['heat_out'] += out.sum(); t['stored_change'] += d_e
            t['charge_el'] += a; t['avoided_el'] += bv
            t['loss_el'] += loss / c_bar; t['stored_el'] += d_e / c_bar
            t['timing_el'] += (a - bv) - (loss + d_e) / c_bar
            for sig, key in ((price[sl], 'cost'), (ci[sl], 'carbon')):
                ac, bc = (sig * inn / cop).sum(), (sig * out / cop).sum()
                pc, pd_ = ac / a, (bc / bv if bv > 0 else 0.0)
                t[f'{key}_timing'] += bv * (pc - pd_)
                t[f'{key}_extra_el'] += (a - bv) * pc
    return t


def compare(recs, price, tier_high, ci, start, n):
    sl = slice(start, start + n)
    ref = summarise(recs[REF], price, tier_high, start, n)
    imp_ref = np.sum([np.maximum(b['net_kwh_el'][sl], 0) for b in recs[REF]['buildings']], axis=0)
    out = {}
    hi = tier_high[sl].astype(bool)
    for name, rec in recs.items():
        if name == REF:
            continue
        s = summarise(rec, price, tier_high, start, n)
        imp = np.sum([np.maximum(b['net_kwh_el'][sl], 0) for b in rec['buildings']], axis=0)
        units = {'import_kwh_el': 'kWh_el', 'peak_kw_el': 'kW_el', 'mean_daily_peak_kw_el': 'kW_el', 'cost_chf': 'CHF', 'high_tariff_import_share': 'fraction', 'hp_kwh_el': 'kWh_el',
                 'tank_loss_kwh_th': 'kWh_th', 'heat_from_tanks_kwh_th': 'kWh_th'}
        metrics = {k: {'unit': u, 'value': s[k], 'reference': ref[k], 'delta': s[k] - ref[k],
                       'delta_pct': (100.0 * (s[k] - ref[k]) / abs(ref[k])) if ref[k] else None} for k, u in units.items()}
        ref_carbon = (imp_ref * ci[sl]).sum()
        carbon = (imp * ci[sl]).sum() / ref_carbon - 1.0 if ref_carbon else None
        t = tank_terms(rec, recs[REF], price, ci, start, n)
        pct = (lambda x: None if not ref_carbon else float(100.0 * x / ref_carbon))  # noqa: E731
        out[name] = {'metrics': metrics,
                     'mechanisms': {'import_moved_out_of_high_tariff_kwh_el': float(imp_ref[hi].sum() - imp[hi].sum()),
                                    'extra_tank_loss_kwh_th': s['tank_loss_kwh_th'] - ref['tank_loss_kwh_th'],
                                    'extra_hp_electricity_kwh_el': s['hp_kwh_el'] - ref['hp_kwh_el'],
                                    'tank_heat_in_kwh_th': float(t['heat_in']), 'tank_heat_out_kwh_th': float(t['heat_out']),
                                    'stored_heat_change_kwh_th': float(t['stored_change']),
                                    'tank_charging_electricity_kwh_el': float(t['charge_el']), 'electricity_avoided_at_discharge_kwh_el': float(t['avoided_el']),
                                    'electricity_from_tank_losses_kwh_el': float(t['loss_el']), 'electricity_from_stored_remainder_kwh_el': float(t['stored_el']),
                                    'electricity_from_cop_timing_kwh_el': float(t['timing_el']),
                                    'cost_from_tariff_timing_chf': float(t['cost_timing']), 'cost_from_extra_electricity_chf': float(t['cost_extra_el']),
                                    'carbon_from_timing_pct': pct(t['carbon_timing']), 'carbon_from_extra_electricity_pct': pct(t['carbon_extra_el']),
                                    'relative_carbon_change_pct': None if carbon is None else float(100.0 * carbon),
                                    'peak_step_reference': ref['peak_step'], 'peak_step': s['peak_step']},
                     'relative_only': ['carbon_from_timing_pct', 'carbon_from_extra_electricity_pct', 'relative_carbon_change_pct']}
    return out


# ------------------------------------------------------------------------------------------------ checks
def checks(recs, price, res_csv):
    chk = {'max_abs_residuals': {}, 'annual_totals_vs_baselines_2023_csv': {}}
    mr = chk['max_abs_residuals']
    for k in ('net_eq_hp_plus_household_kwh_el', 'demand_eq_direct_plus_tank_kwh_th', 'hp_electricity_x_cop_eq_heat_kwh_th', 'reward_eq_parts'):
        mr[k] = 0.0
    for rec in recs.values():
        for b in rec['buildings']:
            mr['net_eq_hp_plus_household_kwh_el'] = max(mr['net_eq_hp_plus_household_kwh_el'], float(np.abs(b['net_kwh_el'] - b['hp_sh_kwh_el'] - b['hp_hw_kwh_el'] - b['household_kwh_el']).max()))
            for p in ('sh', 'hw'):
                mr['demand_eq_direct_plus_tank_kwh_th'] = max(mr['demand_eq_direct_plus_tank_kwh_th'], float(np.abs(b[f'{p}_demand_kwh_th'] - b[f'hp_{p}_direct_kwh_th'] - b[f'{p}_tank_to_demand_kwh_th']).max()))
                mr['hp_electricity_x_cop_eq_heat_kwh_th'] = max(mr['hp_electricity_x_cop_eq_heat_kwh_th'], float(np.abs(b[f'hp_{p}_kwh_el'] * b[f'cop_{p}'] - b[f'hp_{p}_direct_kwh_th'] - b[f'hp_{p}_to_tank_kwh_th']).max()))
        mr['reward_eq_parts'] = max(mr['reward_eq_parts'], float(np.abs(rec['reward'] - rec['reward_parts'].sum(axis=1)).max()))
    mr = {k: round(v, 8) for k, v in mr.items()}
    chk['max_abs_residuals'] = mr
    for name, rec in recs.items():
        row = res_csv[res_csv.controller == name].iloc[0]
        imp = np.sum([np.maximum(b['net_kwh_el'], 0) for b in rec['buildings']], axis=0)
        net = np.sum([b['net_kwh_el'] for b in rec['buildings']], axis=0)
        mine = {'district_import_kwh': float(imp.sum()), 'district_peak_kw': float(net.max()), 'cost_chf_excl_vat': float((imp * price[:rec['n']]).sum())}
        chk['annual_totals_vs_baselines_2023_csv'][name] = {k: {'export': v, 'results_csv': float(row[k]), 'rel_diff': abs(v - float(row[k])) / abs(float(row[k]))} for k, v in mine.items()}
    return chk


# ------------------------------------------------------------------------------------------------ static files
def attr(value, unit, prov, sources, available=True, reason=None):
    return {'value': value, 'unit': unit, 'provenance': prov, 'source_ids': sources, 'available': available, 'unavailable_reason': reason}


def na(reason, sources=()):
    return attr(None, None, None, list(sources), False, reason)


def buildings_file(ui):
    dist = figures.district(rd, rj)['buildings']
    sch = rj(f'{DATASET}/schema.json')
    tp = rj('data/canonical/thermal/thermal_params.json')
    sel = rd('data/interim/selected_buildings.csv').set_index('role')
    names = ui['_buildings']
    out = {}
    for b in dist:
        role, sfh = b['role'], b['type'] == 'SFH'
        sb = sch['buildings'][b['building']]
        hs, ds = sb['heating_storage']['attributes'], sb.get('dhw_storage', {}).get('attributes')
        p = tp[role]
        hp = lambda pre, dev, eta, tsup, spf: {  # noqa: E731
            'present': True, 'label': 'Heat pump, space heating' if pre == 'sh' else 'Heat pump, hot water and other base load',
            'attributes': {'nominal_kw_el': attr(dev['attributes']['nominal_power'], 'kW_el', 'derived', ['TR-009'], True),
                           'eta_carnot_fraction': attr(eta, 'ratio', 'modeled', ['M-001', 'D-014d'], True),
                           'supply_temperature_c': attr(tsup, '°C', 'assumed_parameter', ['A-002'] if (pre == 'sh' and sfh) else ['A-003'] if pre == 'sh' else ['A-004'], True),
                           'spf_target': attr(spf, 'ratio', 'assumed_parameter', ['D-014d'], True)}}
        tank = lambda label, a: ({'present': False, 'label': label, 'attributes': {}} if a is None else {  # noqa: E731
            'present': True, 'label': label,
            'attributes': {'capacity_kwh_th': attr(a['capacity'], 'kWh_th', 'assumed_parameter', ['D-017a'], True),
                           'efficiency': attr(a['efficiency'], 'ratio', 'assumed_parameter', ['D-017a'], True),
                           'loss_per_hour': attr(a['loss_coefficient'], '1/h', 'assumed_parameter', ['D-017a', 'ISS-032'], True)}})
        spf_sh = p['spf_target']
        a = {
            'type': attr(b['type'], None, 'derived', ['DER-003'], True),
            'source_id': attr(f"{b['source']} {b['source_id']}", None, 'measured', ['SRC-001'] if sfh else ['SRC-002'], True),
            'housing_units': attr(b['units'], 'units', 'derived' if sfh else 'measured', ['DER-003'] if sfh else ['SRC-002', 'DER-003'], True),
            'floor_area_m2': attr(b['area_m2'], 'm²', 'measured', ['SRC-001', 'DER-003'], True) if sfh else na('not in the EKZ metadata', ['SRC-002']),
            'residents': attr(b['residents'], 'persons', 'measured', ['SRC-001', 'DER-003'], True) if sfh else na('not in the EKZ metadata', ['SRC-002']),
            'floors': na('no source provides the number of floors'),
            'heat_pump_type': attr('air-source', None, 'measured', ['SRC-001'], True) if sfh else na('EKZ does not state air- or ground-source', ['ISS-019']),
            'heat_delivery': attr('floor heating', None, 'measured', ['SRC-001', 'A-002'], True) if sfh else na('no distribution-system information in EKZ', ['A-003']),
            'water_heating': (attr('heat pump (survey); warm-weather draw near zero', None, 'measured', ['SRC-001', 'ISS-026'], True) if role == 'SFH-low' else
                              attr('electric water heater (its electricity is inside household electricity)', None, 'measured', ['SRC-001', 'ISS-027', 'D-014a'], True)) if sfh
            else na('not in the EKZ metadata', ['SRC-002']),
            'household_electricity_source': attr('metered (HEAPO)', None, 'measured', ['SRC-001'], True) if sfh else
            attr('synthetic composite of sampled EKZ apartment meters scaled by housing units; not measured in this building', None, 'synthetic', ['D-015', 'SRC-002'], True),
            'pv_status': attr('none reported in the survey; PV is not modeled in Phase A', None, 'measured', ['ISS-021'], True) if role == 'SFH-low'
            else na('PV status unknown (HEAPO flag empty or no EKZ metadata); PV is not modeled in Phase A', ['ISS-021']),
            'gap_filled_hours': attr(b['gap_filled_hours'], 'h', 'synthetic' if b['gap_filled_hours'] else 'measured', ['D-011'] if b['gap_filled_hours'] else ['SRC-002'], True),
        }
        out[role] = {'id': role, 'citylearn_name': b['building'], 'display_name': names[role], 'type': b['type'],
                     'source_dataset': 'HEAPO' if sfh else 'ETH/EKZ',
                     'attributes': a,
                     'components': {'hp_sh': hp('sh', sb['heating_device'], p['eta_sh'], p['T_sup_sh_c'], spf_sh),
                                    'hp_hw': hp('hw', sb['dhw_device'], p['eta_dhw'], p['T_sup_dhw_c'], p['spf_dhw']),
                                    'tank_sh': tank('Heating tank', hs), 'tank_hw': tank('Hot-water / base-load tank', ds)},
                     'related_ids': sorted({'ISS-029', 'ISS-030', 'ISS-032', 'D-017a'} | ({'ISS-026'} if role == 'SFH-low' else set()) |
                                           ({'ISS-027', 'ISS-021'} if role in ('SFH-mid', 'SFH-high') else set()) | ({'ISS-019', 'D-015'} if not sfh else set()))}
    return out


def conditions_file(S, price_chf, start, n):
    sl = slice(start, start + n)
    idx = pd.date_range(S['start_utc'], periods=S['n'], freq='h', tz='UTC')
    loc = idx.tz_convert('Europe/Zurich')
    ser = S['series']
    g = lambda k: ser[k]['values'][sl]  # noqa: E731
    tier = ['high' if x else 'low' for x in S['tier_high'][sl]]
    return {'contract_version': CONTRACT_VERSION, 'scope': {'kind': 'window', 'start_step': start, 'n_steps': n},
            'timestamps_utc': [t.strftime('%Y-%m-%dT%H:%M:%SZ') for t in idx[sl]],
            'local_time': [t.strftime('%Y-%m-%dT%H:%M%z') for t in loc[sl]],
            'local_hour': S['local_hour'][sl], 'weekday': S['weekday'][sl],
            'series': {'temp_c': g('temp_c'), 'ghi_wm2': g('ghi'), 'diffuse_wm2': g('diffuse'), 'beam_horizontal_wm2': g('beam'),
                       'price_chf_kwh': r6(price_chf[sl]), 'tariff_tier': tier, 'carbon_relative_rank': S['carbon_rank']['values'][sl]},
            'building_flags': {r: {'gap_filled': S['buildings'][r]['gap_filled_flag'][sl]} for r in ROLES}}


def git(*a):
    return subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True).stdout.strip()


def main(hours=48, start=None, full=False, out=OUT, only=None):
    os.makedirs(os.path.join(out, 'runs', SCENARIO), exist_ok=True)
    with open(os.path.join(ROOT, 'swiss/dashboard/ui_map.yaml'), encoding='utf-8') as f:
        ui = yaml.safe_load(f)
    _read.add('swiss/dashboard/ui_map.yaml')
    S = figures.build_inputs(rd)
    price_chf = rd('data/canonical/tariff_ekz_standard_2023_hourly.csv').total_chf_kwh.to_numpy(dtype=float)
    names = [c for c in recorder.CONTROLLERS if only is None or c in only]
    recs = {c: recorder.record(c) for c in names}
    N = recs[REF]['n']
    if full:
        start, n, day = 0, N, None
    else:
        s0, day = pick_window(S, hours) if start is None else (start, None)
        start, n = s0, hours
    n_cond = S['n'] if full else n
    thr_cold = float(np.round(np.nanpercentile(np.asarray(S['series']['temp_c']['values'], dtype=float), 10), 1))
    thresholds = {'cold_temp_c': thr_cold, **THRESHOLDS}
    tier_high = np.asarray(S['tier_high'], dtype=int)[:N]
    ci = recs[REF]['carbon_intensity_internal']
    res_csv = rd('swiss/experiments/results/baselines_2023.csv')
    chk = checks(recs, price_chf, res_csv)
    _, exp_rows = parse_csv_registry(os.path.join(ROOT, 'docs/experiments/experiment_registry.csv'))
    exp_of = figures.build_results(rd, rj, [r['cells'] for r in exp_rows])[0]['experiment_of']
    scales = recs[REF]['reward_scales']
    reward_meta = {'id': 'R-001', 'weights': recs[REF]['reward_weights'], 'scales': {k: scales[k] for k in TERMS}}
    files = {}

    def emit(rel, obj):
        p = os.path.join(out, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        bundle_io.write_json_file(p, obj)
        files[rel] = sha(p)

    scope = {'kind': 'year' if full else 'window', 'start_step': start, 'n_steps': n}
    comps, flows = registry()
    emit('buildings.json', {'contract_version': CONTRACT_VERSION, 'buildings': buildings_file(ui)})
    emit('components.json', {'contract_version': CONTRACT_VERSION, 'components': comps, 'flows': flows})
    cond = conditions_file(S, price_chf, 0 if full else start, n_cond)
    if full:
        cond['scope'] = {'kind': 'year', 'start_step': 0, 'n_steps': n_cond}
    emit('conditions.json', cond)
    ctrl_meta, runs = [], []
    for name in names:
        info = ui['_controllers'][name]
        arrays, district = run_arrays(recs[name], price_chf, start, n)
        same = name != REF and all(np.array_equal(a['net_kwh_el'], b['net_kwh_el']) and np.array_equal(a['sh_tank_soc'], b['sh_tank_soc'])
                                   for a, b in zip(recs[name]['buildings'], recs[REF]['buildings']))
        ident = REF if same else None
        params = {}
        if 'tariff_r' in name:
            params['rate'] = float(name.split('_r')[-1])
        ctrl_meta.append({'id': name, 'key': info['key'], 'display_name': info['display_name'], 'short_name': info['short_name'], 'algorithm_id': info['node'],
                          'reference': name == REF, 'identical_to': ident, 'note': info.get('note'), 'parameters': params})
        emit(f'runs/{SCENARIO}/{name}.json', {
            'contract_version': CONTRACT_VERSION, 'scenario': SCENARIO, 'controller': name, 'algorithm_id': info['node'], 'identical_to': ident,
            'experiment_ids': exp_of.get(name, []), 'seed': 0, 'reward': reward_meta, 'scope': scope, 'buildings': arrays, 'district': district,
            'situations': situations(recs[name], S, thr_cold, start, n), 'summary': summarise(recs[name], price_chf, tier_high, start, n)})
        runs.append({'scenario': SCENARIO, 'controller': name, 'file': f'runs/{SCENARIO}/{name}.json'})
    emit('comparisons.json', {'contract_version': CONTRACT_VERSION, 'scenario': SCENARIO, 'reference_controller': REF, 'scope': scope,
                              'comparisons': compare(recs, price_chf, tier_high, ci, start, n)})
    emit('comparisons_year.json', {'contract_version': CONTRACT_VERSION, 'scenario': SCENARIO, 'reference_controller': REF,
                                   'scope': {'kind': 'year', 'start_step': 0, 'n_steps': N}, 'comparisons': compare(recs, price_chf, tier_high, ci, 0, N)})
    rel_out = os.path.relpath(out, ROOT).replace(os.sep, '/') + '/'
    dirty = [ln for ln in git('status', '--porcelain').splitlines() if rel_out not in ln]   # the output folder itself does not make the tree dirty
    cond_scope = cond['scope']
    manifest = {
        'contract_version': CONTRACT_VERSION, 'phase': 'A', 'kind': 'full' if full else 'sample',
        'description': ('Full simulated year' if full else f'Sample: {hours} hours from local midnight of the coldest weekday ({day}), step {start}') +
                       '. Produced by swiss/contract/export_v1.py from real CityLearn 3.3.0 rollouts.',
        'district_note': 'The six buildings are a constructed composite of representative models from two datasets (HEAPO houses, ETH/EKZ apartment-building heat-pump meters). '
                         'They are not neighbours, share no grid connection and exchange no energy in the model.',
        'year': 2023, 'timezone': 'Europe/Zurich',
        'index_convention': 'UTC, start of hour; step 0 = 2022-12-31T23:00Z = 2023-01-01 00:00 local (D-007). Run arrays and conditions use the same step index (window arrays start at scope.start_step).',
        'time_axis': {'start_utc': S['start_utc'], 'step_seconds': STEP_S, 'n_steps_inputs': S['n'], 'n_steps_simulated': N, 'scope': cond_scope},
        'buildings': ROLES, 'controllers': ctrl_meta,
        'scenarios': [{'id': SCENARIO, 'label': 'Base district 2023', 'dataset': DATASET, 'description': 'Six-building Swiss district, local year 2023, assumed tanks as in D-017a.'}],
        'runs': runs,
        'variables': {'building': BUILDING_VARIABLES, 'district': DISTRICT_VARIABLES, 'conditions': CONDITION_VARIABLES},
        'situation_tags': SITUATION_TAGS, 'situation_thresholds': thresholds, 'units': UNITS, 'checks': chk,
        'generated': {'git_commit': git('rev-parse', '--short', 'HEAD'), 'git_dirty': bool(dirty), 'python': sys.version.split()[0], 'citylearn': CL_VERSION},
        'files': dict(sorted(files.items())),
        'inputs': {f: sha(os.path.join(ROOT, f)) for f in sorted(set(INPUT_FILES) | _read) if os.path.exists(os.path.join(ROOT, f))},
    }
    bundle_io.write_json_file(os.path.join(out, 'manifest.json'), manifest)
    print(f'wrote {len(files) + 1} files to {os.path.relpath(out, ROOT)}  scope={scope}  window day={day}')
    print('checks:', json.dumps(chk['max_abs_residuals']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--hours', type=int, default=48)
    ap.add_argument('--start-step', type=int, default=None)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--only', nargs='*', default=None, help='controller ids (must include ALG-001_zero_action); for quick tests')
    a = ap.parse_args()
    main(a.hours, a.start_step, a.full, a.out, a.only)
