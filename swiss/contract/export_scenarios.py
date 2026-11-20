"""Export the scenario files of contract v1.1 to web/public/bundle/sim_scenarios/<scenario>/ from REAL CityLearn rollouts (no numbers are typed in here).

Scenarios are listed in SCENARIOS (data, not code paths): Phase B = S3 in 2023 weather (assumed PV, battery, export price, RC room model, no cooling) and
Phase C = the climate cell gwl2.0_hw99_medium (+2 C global warming level, inserted 99th-percentile heat-wave week, medium cooling adoption, central reversible heat pump,
plus the S3 setup). Each scenario has two controllers on the full simulated year, hourly:
  thermostat   heat to 21 C (cool to 26 C where a cooling device exists), tanks and battery idle                       (ALG-009)
  optimum      exact perfect-foresight bill optimum (linear program, comfort band) replayed in CityLearn (band 21-24 for Phase B)   (ALG-008 / ALG-012)
Only the fields the district view draws are stored (variables_scenario.py). Every hour is checked: import - export + pv = household + heat pumps + battery charge - discharge.

Files per scenario: manifest.json, conditions.json, runs/thermostat.json, runs/optimum.json; plus sim_scenarios/index.json (list of the exported scenarios).
Run: PYTHONPATH=. cl/bin/python -I swiss/contract/export_scenarios.py [--only ID ...] [--out DIR] [--cache DIR]
"""
import argparse
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn import __version__ as CL_VERSION  # noqa: E402
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.contract import CONTRACT_VERSION  # noqa: E402
from swiss.contract import variables_scenario as vs  # noqa: E402
from swiss.contract.export_v1 import ROLES, STEP_S, attr, git, r6, rd, sha  # noqa: E402
from swiss.dashboard import bundle_io, figures  # noqa: E402
from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402

OUT = os.path.join(ROOT, 'web', 'public', 'bundle', 'sim_scenarios')
EXPORT_RP = 8.0                       # assumed export price (A-015), the value of every oracle run
EXPORT_HOUR_KWH = 0.5
TEMP_LIMIT_C = 26.0
SCENARIOS = [
    {'id': 'phase_b_s3_2023', 'phase': 'B', 'kind': 'rc2023', 'dataset': 'swiss/datasets/swiss_rc_2023', 'cooling': False, 'climate': False,
     'label': 'Phase B (solar, battery, 2023)', 'short_label': 'Phase B',
     'description': 'The same six buildings in observed 2023 weather with assumed rooftop solar panels, an assumed battery (1 kWh per kWp), an export price and a room temperature model. No cooling.',
     'algorithms': {'thermostat': 'ALG-009', 'optimum': 'ALG-008'}, 'jump': []},
    {'id': 'phase_c_gwl2_hw99_medium', 'phase': 'C', 'kind': 'climate_cell', 'cell': 'gwl2.0_hw99_medium', 'dataset': 'swiss/datasets/climate/gwl2.0_hw99_medium', 'cooling': True,
     'climate': True, 'label': 'Phase C (+2 °C heat wave)', 'short_label': 'Phase C',
     'description': 'The district in a climate with two degrees of global warming and an inserted heat-wave week, with medium cooling adoption (one apartment building has a reversible heat pump), '
                    'rooftop solar, battery and the room temperature model.',
     'algorithms': {'thermostat': 'ALG-009', 'optimum': 'ALG-012'}, 'heat_wave_steps': [4872, 5040],
     'jump': [{'id': 'heat_wave', 'label': 'Heat-wave week', 'description': 'The hottest day of the inserted heat-wave week (week 29).'}]},
]
CONTROLLERS = [
    {'id': 'thermostat', 'display_name': 'Thermostat (reference)', 'short_name': 'Thermostat', 'reference': True,
     'note': 'Heats to the set point every hour; tanks and battery idle; cools to 26 C where a cooling device exists.'},
    {'id': 'optimum', 'display_name': 'Exact optimum (perfect foresight)', 'short_name': 'Exact optimum', 'reference': False,
     'note': 'Upper bound on what any controller could save: a linear program that knows the whole year, replayed in CityLearn. Not deployable.'},
]
DS_INPUTS = ('build_manifest.json', 'weather.csv', 'pricing.csv', 'carbon_intensity.csv', 'schema.json', 'rc_params.json')
CODE_INPUTS = ['swiss/experiments/oracle_rc.py', 'swiss/experiments/oracle_climate.py', 'swiss/experiments/climate_controllers.py', 'swiss/experiments/thermostat.py',
               'swiss/models/rc_building.py', 'swiss/contract/variables_scenario.py', 'data/canonical/weather_klo_2023_hourly.csv', 'data/canonical/tariff_ekz_standard_2023_hourly.csv']


# ------------------------------------------------------------------------------------------------ rollouts
def play(env, agent):
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(agent.predict(obs))
    return env


def record(env, cop_cool):
    """Per-building arrays (kWh per step) of a finished full-year rollout. Also the heat-side quantities used for the exported heat-balance residuals."""
    n = env.time_steps - 1
    out = []
    for bi, b in enumerate(env.buildings):
        g = lambda name: np.asarray(getattr(b, name), dtype=float)[:n]   # noqa: E731
        T = np.asarray(b.weather.outdoor_dry_bulb_temperature, dtype=float)[:n]
        d = {'household': g('non_shiftable_load'), 'hp_hw': g('dhw_electricity_consumption'), 'hp_sh': g('heating_electricity_consumption'),
             'hp_cool': g('cooling_electricity_consumption'), 'pv': -g('solar_generation'), 'batt': g('electrical_storage_electricity_consumption'),
             'net': g('net_electricity_consumption'), 'soc': np.asarray(b.electrical_storage.soc, dtype=float)[:n],
             'temp_in': np.asarray(b.energy_simulation.indoor_dry_bulb_temperature, dtype=float)[:n],
             'has_cooling': getattr(b, 'cooling_device', None) is not None and float(b.cooling_device.nominal_power) > 0,
             'battery_kwh': float(b.electrical_storage.capacity), 'pv_kwp': float(b.pv.nominal_power)}
        for pre, cl in (('sh', 'heating'), ('hw', 'dhw')):
            cop = np.array([getattr(b, f'{cl}_device').get_cop(t, heating=True) for t in T])
            d[f'heat_{pre}_el_x_cop'] = d[f'hp_{pre}'] * cop
            d[f'heat_{pre}_out'] = g(f'energy_from_{cl}_device') + g(f'energy_from_{cl}_device_to_{cl}_storage')
            d[f'heat_{pre}_demand'] = g(f'{cl}_demand')
            d[f'heat_{pre}_met'] = g(f'energy_from_{cl}_device') + g(f'energy_from_{cl}_storage')
        d['cool_demand'] = g('cooling_demand')
        d['cool_el_x_cop'] = d['hp_cool'] * cop_cool[bi] if cop_cool[bi] is not None else np.zeros(n)
        out.append(d)
    return out


def rollouts_rc2023():
    from swiss.experiments import oracle_rc
    from swiss.experiments.thermostat import ThermostatAgent
    from swiss.experiments import oracle
    inp = oracle_rc.RCInputs()
    schema = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_rc_2023', 'schema.json')
    mk = lambda: CityLearnEnv(schema, central_agent=True, reward_function=SwissDistrictReward)   # noqa: E731
    t0 = time.time()
    env_th = mk()
    play(env_th, ThermostatAgent(env_th))
    tot, sols = oracle_rc.scenario(inp, {}, 'band 21-24', EXPORT_RP, with_solution=True)
    env_op = mk()
    play(env_op, oracle.Replay(oracle_rc.schedule(env_op, inp, sols, inp.N, inp.kwp[1.0], 1.0)))
    none = [None] * len(env_th.buildings)
    return {'thermostat': record(env_th, none), 'optimum': record(env_op, none), 'seconds': time.time() - t0,
            'summary_program': {'zero_bill_chf': tot['zero_bill'], 'opt_bill_chf': tot['opt_bill'], 'saving_pct': tot['saving_pct']}}


def rollouts_climate(cell):
    from swiss.experiments import climate_controllers as cc, oracle, oracle_climate as oc
    inp = oc.ClimateInputs(cell)
    schema = os.path.join(inp.dir, 'schema.json')
    mk = lambda: CityLearnEnv(schema, central_agent=True, reward_function=SwissDistrictReward)   # noqa: E731
    t0 = time.time()
    env_th = mk()
    play(env_th, cc.ThermostatAgentCool(env_th))
    tot, sols = oc.solve_cell(inp, 'band', EXPORT_RP, inp.N)
    env_op = mk()
    play(env_op, oracle.Replay(oc.schedule(env_th, inp, sols, inp.N)))
    cop = [c if c is not None else None for c in inp.copc]
    cop = [None if c is None else np.asarray(c)[:inp.N] for c in cop]
    return {'thermostat': record(env_th, cop), 'optimum': record(env_op, cop), 'seconds': time.time() - t0,
            'summary_program': {'zero_bill_chf': tot['zero_bill_chf'], 'opt_bill_chf': tot['opt_bill_chf'], 'saving_pct': tot['saving_pct']}}


def get_rollouts(scn, cache):
    fn = os.path.join(cache, scn['id'] + '.pkl') if cache else None
    if fn and os.path.exists(fn):
        return pickle.load(open(fn, 'rb'))
    rec = rollouts_rc2023() if scn['kind'] == 'rc2023' else rollouts_climate(scn['cell'])
    if fn:
        os.makedirs(cache, exist_ok=True)
        pickle.dump(rec, open(fn, 'wb'))
    return rec


# ------------------------------------------------------------------------------------------------ checks and files
def checks(rec, scn):
    """Largest absolute residuals over every building, controller and step (before rounding)."""
    r = {'electricity_balance_kwh_el': 0.0, 'sh_heat_demand_eq_delivered_kwh_th': 0.0, 'hw_heat_demand_eq_delivered_kwh_th': 0.0, 'hp_sh_electricity_x_cop_eq_heat_kwh_th': 0.0,
         'hp_hw_electricity_x_cop_eq_heat_kwh_th': 0.0, 'cooling_electricity_x_cop_eq_demand_kwh_th': 0.0, 'battery_soc_range_violation': 0.0}
    for ctrl in ('thermostat', 'optimum'):
        for d in rec[ctrl]:
            imp, exp = np.maximum(d['net'], 0), np.maximum(-d['net'], 0)
            lhs = imp - exp + d['pv']
            rhs = d['household'] + d['hp_sh'] + d['hp_hw'] + d['hp_cool'] + d['batt']
            r['electricity_balance_kwh_el'] = max(r['electricity_balance_kwh_el'], float(np.abs(lhs - rhs).max()))
            for pre in ('sh', 'hw'):
                r[f'{pre}_heat_demand_eq_delivered_kwh_th'] = max(r[f'{pre}_heat_demand_eq_delivered_kwh_th'], float(np.abs(d[f'heat_{pre}_demand'] - d[f'heat_{pre}_met']).max()))
                r[f'hp_{pre}_electricity_x_cop_eq_heat_kwh_th'] = max(r[f'hp_{pre}_electricity_x_cop_eq_heat_kwh_th'], float(np.abs(d[f'heat_{pre}_el_x_cop'] - d[f'heat_{pre}_out']).max()))
            if d['has_cooling']:
                r['cooling_electricity_x_cop_eq_demand_kwh_th'] = max(r['cooling_electricity_x_cop_eq_demand_kwh_th'], float(np.abs(d['cool_el_x_cop'] - d['cool_demand']).max()))
            r['battery_soc_range_violation'] = max(r['battery_soc_range_violation'], float(max(-d['soc'].min(), d['soc'].max() - 1.0, 0.0)))
    return {k: round(v, 8) for k, v in r.items()}


def run_file(scn, ctrl, rec, S, price, n, thr_cold, tier_high, local_day, algo):
    B = rec[ctrl]
    cooling = scn['cooling']
    arrays = {}
    for role, d in zip(ROLES, B):
        imp, exp = np.maximum(d['net'], 0), np.maximum(-d['net'], 0)
        a = {'import_kwh_el': r6(imp, 4), 'export_kwh_el': r6(exp, 4), 'pv_kwh_el': r6(d['pv'], 4), 'household_kwh_el': r6(d['household'], 4),
             'hp_sh_kwh_el': r6(d['hp_sh'], 4), 'hp_hw_kwh_el': r6(d['hp_hw'], 4),
             'hp_cool_kwh_el': r6(d['hp_cool'], 4) if cooling and d['has_cooling'] else None,
             'battery_charge_kwh_el': r6(np.maximum(d['batt'], 0), 4), 'battery_discharge_kwh_el': r6(np.maximum(-d['batt'], 0), 4),
             'battery_soc': r6(d['soc'], 3), 'temp_in_c': r6(d['temp_in'], 2)}
        arrays[role] = a
    tot = lambda key: np.sum([np.asarray(a[key], dtype=float) for a in arrays.values() if a[key] is not None], axis=0)   # noqa: E731
    district = {k: r6(tot(k), 4) for k in ('import_kwh_el', 'export_kwh_el', 'pv_kwh_el', 'battery_charge_kwh_el', 'battery_discharge_kwh_el')}
    district['hp_cool_kwh_el'] = r6(tot('hp_cool_kwh_el'), 4) if cooling else None
    imp, exp = np.array(district['import_kwh_el']), np.array(district['export_kwh_el'])
    daily_peak = (pd.Series(imp).groupby(local_day).transform('max').to_numpy() == imp) & (imp > 0)
    temp = np.asarray(S['temp'], dtype=float)[:n]
    steps = lambda m: [int(i) for i in np.nonzero(m)[0]]   # noqa: E731
    situations = {'district': {k: v for k, v in {'district_daily_peak': steps(daily_peak), 'high_tariff': steps(tier_high), 'cold_hour': steps(temp <= thr_cold),
                                                 'district_exporting': steps(exp >= EXPORT_HOUR_KWH)}.items() if v}}
    pv_total = sum(float(np.sum(a['pv_kwh_el'])) for a in arrays.values())
    bill = float((imp * price).sum() - EXPORT_RP / 100.0 * exp.sum())
    dh = float(sum(np.maximum(d['temp_in'] - TEMP_LIMIT_C, 0).sum() for d in B))
    summary = {'import_kwh_el': float(imp.sum()), 'export_kwh_el': float(exp.sum()), 'pv_kwh_el': pv_total, 'hp_cool_kwh_el': float(np.sum(district['hp_cool_kwh_el'])) if cooling else None,
               'bill_chf': bill, 'peak_kw_el': float(imp.max() / (STEP_S / 3600)), 'peak_step': int(imp.argmax()), 'degree_hours_above_26_c': dh}
    return {'contract_version': CONTRACT_VERSION, 'scenario': scn['id'], 'controller': ctrl, 'algorithm_id': algo, 'scope': {'kind': 'year', 'start_step': 0, 'n_steps': n},
            'buildings': arrays, 'district': district, 'situations': situations, 'summary': summary}


def timeline(S, n_inputs):
    idx = pd.date_range(S['start_utc'], periods=n_inputs, freq='h', tz='UTC').tz_convert('Europe/Zurich')
    return idx


def export_scenario(scn, out, cache=None):
    t0 = time.time()
    rec = get_rollouts(scn, cache)
    S = figures.build_inputs(rd)
    ds = os.path.join(ROOT, scn['dataset'])
    env = CityLearnEnv(os.path.join(ds, 'schema.json'), central_agent=True, reward_function=SwissDistrictReward)
    n = env.time_steps - 1
    n_in = n + 1
    w = env.buildings[0].weather
    temp = np.asarray(w.outdoor_dry_bulb_temperature, dtype=float)[:n_in]
    ghi = (np.asarray(w.diffuse_solar_irradiance, dtype=float) + np.asarray(w.direct_solar_irradiance, dtype=float))[:n_in]
    price = pd.read_csv(os.path.join(ds, 'pricing.csv')).electricity_pricing.to_numpy(dtype=float)[:n_in]
    tier_high = np.asarray(S['tier_high'], dtype=int)[:n_in].astype(bool)
    assert ((price > price.min() + 1e-9) == tier_high).all(), 'tariff tiers of the dataset differ from the calendar rule'
    idx = timeline(S, n_in)
    local_day = pd.Series(idx.date)[:n].to_numpy()
    S2 = {'temp': temp}
    thr_cold = float(np.round(np.nanpercentile(temp, 10), 1))
    chk = checks(rec, scn)
    assert chk["electricity_balance_kwh_el"] < 1e-4, chk
    files = {}

    def emit(rel, obj):
        p = os.path.join(out, scn['id'], rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        bundle_io.write_json_file(p, obj)
        files[rel] = sha(p)

    cooling = scn['cooling']
    cond_vars = vs.condition_variables(scn['climate'])
    emit('conditions.json', {'contract_version': CONTRACT_VERSION, 'scenario': scn['id'], 'scope': {'kind': 'year', 'start_step': 0, 'n_steps': n_in},
                             'local_time': [t.strftime('%Y-%m-%dT%H:%M%z') for t in idx],
                             'series': {'temp_c': r6(temp, 1), 'ghi_wm2': r6(ghi, 0), 'price_chf_kwh': r6(price), 'tariff_tier': ['high' if x else 'low' for x in tier_high]}})
    ctrl_meta = []
    for c in CONTROLLERS:
        algo = scn['algorithms'][c['id']]
        emit(f'runs/{c["id"]}.json', run_file(scn, c['id'], rec, S2, price[:n], n, thr_cold, tier_high[:n], local_day, algo))
        ctrl_meta.append({**c, 'algorithm_id': algo, 'file': f'runs/{c["id"]}.json'})
    # equipment (the same six buildings as Phase A; names and housing data come from sim_full/buildings.json)
    eq = {}
    for role, d in zip(ROLES, rec['thermostat']):
        cap = float(d['battery_kwh'])
        eq[role] = {'pv_kwp': attr(round(d['pv_kwp'], 3), 'kW_p', 'assumed_parameter', ['M-003', 'A-047'], True),
                    'battery_kwh': attr(round(cap, 3), 'kWh_el', 'assumed_parameter', ['M-004', 'A-017'], True),
                    'cooling': attr(bool(cooling and d['has_cooling']), None, 'assumed_parameter' if cooling else 'derived', ['A-044', 'A-040'] if cooling else ['M-005'], True)}
    jump = []
    for j in scn['jump']:
        if j['id'] == 'heat_wave':
            a, b = scn['heat_wave_steps']
            day = int(np.argmax(temp[a:b].reshape(-1, 24).max(axis=1)))
            jump.append({**j, 'steps': [a + 24 * day], 'window': [a, b - 1]})
    tags = {k: t.format(export_hour_kwh=EXPORT_HOUR_KWH) for k, t in vs.TAGS.items()}
    dirty = [ln for ln in git('status', '--porcelain').splitlines() if 'web/public/bundle/' not in ln]
    inputs = [f'{scn["dataset"]}/{f}' for f in DS_INPUTS if os.path.exists(os.path.join(ROOT, scn['dataset'], f))] + CODE_INPUTS + \
             [f'{scn["dataset"]}/Building_{i}.csv' for i in range(1, 7)]
    manifest = {
        'contract_version': CONTRACT_VERSION, 'phase': scn['phase'], 'kind': 'scenario_year',
        'scenario': {'id': scn['id'], 'label': scn['label'], 'short_label': scn['short_label'], 'description': scn['description'], 'dataset': scn['dataset']},
        'description': f'Full simulated year of {scn["label"]}, two controllers, hourly. Produced by swiss/contract/export_scenarios.py from real CityLearn {CL_VERSION} rollouts.',
        'district_note': 'The six buildings are a constructed composite of representative models from two datasets. They are not neighbours, share no grid connection and exchange no energy in the model.',
        'year': 2023, 'timezone': 'Europe/Zurich',
        'index_convention': 'UTC, start of hour; step 0 = 2022-12-31T23:00Z = 2023-01-01 00:00 local (D-007). Run arrays and conditions use the same step index.',
        'time_axis': {'start_utc': S['start_utc'], 'step_seconds': STEP_S, 'n_steps_inputs': n_in, 'n_steps_simulated': n, 'scope': {'kind': 'year', 'start_step': 0, 'n_steps': n_in}},
        'buildings': ROLES, 'equipment': eq,
        'features': {'pv': True, 'battery': True, 'export': True, 'cooling': cooling, 'room_temperature': True},
        'export_price_chf_kwh': attr(EXPORT_RP / 100.0, 'CHF/kWh', 'assumed_parameter', ['A-015'], True),
        'controllers': ctrl_meta, 'jump_targets': jump,
        'variables': {'building': vs.building_variables(cooling), 'district': vs.district_variables(cooling), 'conditions': cond_vars},
        'situation_tags': tags, 'situation_thresholds': {'cold_temp_c': thr_cold, 'export_hour_kwh': EXPORT_HOUR_KWH, 'temp_limit_c': TEMP_LIMIT_C},
        'units': {'kWh_el': 'electrical energy in one step', 'CHF': 'Swiss francs excl. VAT', 'CHF/kWh': 'tariff', 'fraction 0-1': 'dimensionless fill level', '°C': 'degrees Celsius',
                  'kW_p': 'peak power of the panels', 'W/m²': 'irradiance'},
        'checks': {'max_abs_residuals': chk, 'program_vs_replay': rec['summary_program']},
        'compute': {'rollout_and_lp_seconds': round(rec['seconds'], 1)},
        'generated': {'git_commit': git('rev-parse', '--short', 'HEAD'), 'git_dirty': bool(dirty), 'python': sys.version.split()[0], 'citylearn': CL_VERSION},
        'files': dict(sorted(files.items())), 'inputs': {f: sha(os.path.join(ROOT, f)) for f in sorted(set(inputs)) if os.path.exists(os.path.join(ROOT, f))},
    }
    bundle_io.write_json_file(os.path.join(out, scn['id'], 'manifest.json'), manifest)
    print(f'{scn["id"]}: wrote {len(files) + 1} files in {time.time() - t0:.0f}s, residuals {chk}')


def write_index(out):
    items = []
    for scn in SCENARIOS:
        p = os.path.join(out, scn['id'], 'manifest.json')
        if os.path.exists(p):
            m = json.load(open(p, encoding='utf-8'))
            items.append({'id': scn['id'], 'phase': scn['phase'], 'label': scn['label'], 'short_label': scn['short_label'], 'description': scn['description'],
                          'features': m['features'], 'controllers': [c['id'] for c in m['controllers']], 'default_controller': 'optimum',
                          'jump_targets': [{k: j[k] for k in ('id', 'label')} for j in m['jump_targets']]})
    bundle_io.write_json_file(os.path.join(out, 'index.json'), {'contract_version': CONTRACT_VERSION, 'scenarios': items})


def main(out=OUT, only=None, cache=None):
    for scn in SCENARIOS:
        if only is None or scn['id'] in only:
            export_scenario(scn, out, cache)
    write_index(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--only', nargs='*', default=None)
    ap.add_argument('--cache', default=None, help='directory for pickled rollouts (development only)')
    a = ap.parse_args()
    main(a.out, a.only, a.cache)
