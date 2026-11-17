"""Contract v1 tests: schema drift, validity of the committed sample, physical consistency re-derived from the files,
cross-checks against INDEPENDENT sources (run traces, dataset CSVs), provenance IDs, carbon guard, freshness, reproducibility.

Run: PYTHONPATH=. cl/bin/python -m pytest swiss/tests/test_contract.py -q
"""
import glob
import hashlib
import json
import os

import numpy as np
import pandas as pd
import pytest

from swiss.contract import CONTRACT_VERSION, schema_gen, validate
from swiss.contract.variables import BUILDING_VARIABLES, CONDITION_VARIABLES, DISTRICT_VARIABLES, SITUATION_TAGS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SIM = os.path.join(ROOT, 'web', 'public', 'bundle', 'sim')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
REF = 'ALG-001_zero_action'


def load(rel):
    with open(os.path.join(SIM, rel), encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def manifest():
    return load('manifest.json')


@pytest.fixture(scope='module')
def runs(manifest):
    return {r['controller']: load(r['file']) for r in manifest['runs']}


@pytest.fixture(scope='module')
def cond():
    return load('conditions.json')


@pytest.fixture(scope='module')
def binfo():
    return load('buildings.json')['buildings']


# ------------------------------------------------------------------------------------------------ schema
def test_committed_schemas_equal_generated():
    for name, sch in schema_gen.schemas().items():
        with open(os.path.join(schema_gen.DIR, f'{name}.schema.json'), encoding='utf-8') as f:
            assert f.read() == schema_gen.render(sch), f'{name}.schema.json is stale: run swiss/contract/schema_gen.py'


def test_validator_catches_violations_and_unknown_keywords():
    s = {'type': 'object', 'properties': {'a': {'type': 'array', 'items': {'type': 'number'}}, 'm': {'enum': ['x']}}, 'required': ['a'], 'additionalProperties': False}
    assert validate.errors({'a': [1, 2.5]}, s) == []
    assert validate.errors({'a': [1, None]}, s)
    assert validate.errors({'a': [], 'zzz': 1}, s)
    assert validate.errors({}, s)
    assert validate.errors({'a': [], 'm': 'y'}, s)
    assert validate.errors({'a': [True]}, s)            # bool is not a number
    with pytest.raises(ValueError):
        validate.errors({}, {'type': 'object', 'patternProperties': {}})


def test_every_exported_file_validates(manifest):
    assert validate.validate_file(os.path.join(SIM, 'manifest.json'), 'manifest') == []
    for f, name in (('buildings.json', 'buildings'), ('components.json', 'components'), ('conditions.json', 'conditions'), ('comparisons.json', 'comparisons'),
                    ('comparisons_year.json', 'comparisons')):
        assert validate.validate_file(os.path.join(SIM, f), name) == [], f
    for r in manifest['runs']:
        assert validate.validate_file(os.path.join(SIM, r['file']), 'run') == [], r['file']


def test_contract_version_everywhere(manifest, runs):
    assert manifest['contract_version'] == CONTRACT_VERSION
    for f in ('buildings', 'components', 'conditions', 'comparisons'):
        assert load(f'{f}.json')['contract_version'] == CONTRACT_VERSION
    assert all(r['contract_version'] == CONTRACT_VERSION for r in runs.values())


def test_typescript_types_name_every_variable():
    ts = open(os.path.join(ROOT, 'web', 'src', 'lib', 'contract', 'types.ts'), encoding='utf-8').read()
    for k in list(BUILDING_VARIABLES) + list(DISTRICT_VARIABLES) + list(CONDITION_VARIABLES):
        assert f'{k}:' in ts, f'types.ts is missing {k}'
    assert CONTRACT_VERSION in ts


def test_manifest_dictionary_matches_python_dictionary(manifest):
    assert manifest['variables']['building'] == json.loads(json.dumps(BUILDING_VARIABLES))
    assert manifest['situation_tags'] == SITUATION_TAGS


# ------------------------------------------------------------------------------------------------ freshness and reproducibility
def test_sample_is_fresh_and_files_match_hashes(manifest):
    for rel, h in manifest['files'].items():
        assert hashlib.sha256(open(os.path.join(SIM, rel), 'rb').read()).hexdigest() == h, f'{rel} changed after export'
    stale = [f for f, h in manifest['inputs'].items() if hashlib.sha256(open(os.path.join(ROOT, f), 'rb').read()).hexdigest() != h]
    assert not stale, f'inputs changed since the sample was exported (regenerate with export_v1.py): {stale}'


def test_exporter_reproduces_committed_runs_byte_for_byte(tmp_path):
    """Re-runs real rollouts of two controllers (about 80 s) and compares files with the committed sample."""
    from swiss.contract import export_v1
    if not os.path.exists(os.path.join(SIM, 'manifest.json')):
        pytest.fail('no committed sample')
    start = load('manifest.json')['time_axis']['scope']['start_step']
    only = [REF, 'ALG-003_basic_rbc']
    export_v1.main(hours=48, start=start, out=str(tmp_path), only=only)
    for name in only:
        a = open(tmp_path / 'runs' / 'base' / f'{name}.json', 'rb').read()
        b = open(os.path.join(SIM, 'runs', 'base', f'{name}.json'), 'rb').read()
        assert a == b, f'{name} run file is not reproducible'
    for f in ('buildings.json', 'components.json', 'conditions.json'):
        assert open(tmp_path / f, 'rb').read() == open(os.path.join(SIM, f), 'rb').read(), f


# ------------------------------------------------------------------------------------------------ physics re-derived from the files
def arr(x):
    return np.asarray(x, dtype=float)


def test_scope_and_lengths(manifest, runs, cond):
    sc = manifest['time_axis']['scope']
    assert manifest['time_axis']['step_seconds'] == 3600 and sc['n_steps'] == 48 and manifest['kind'] == 'sample'
    assert cond['scope']['n_steps'] == sc['n_steps'] == len(cond['timestamps_utc'])
    for r in runs.values():
        assert r['scope'] == sc
        for b in r['buildings'].values():
            for k, v in b.items():
                assert v is None or len(v) == sc['n_steps'], k
        for v in r['district'].values():
            assert len(v) == sc['n_steps']


def test_electricity_and_heat_balances(runs, binfo):
    for name, r in runs.items():
        for role, b in r['buildings'].items():
            assert np.abs(arr(b['net_kwh_el']) - arr(b['hp_sh_kwh_el']) - arr(b['hp_hw_kwh_el']) - arr(b['household_kwh_el'])).max() < 1e-5, (name, role)
            assert arr(b['net_kwh_el']).min() >= 0, 'Phase A has no PV or battery: import is never negative'
            for p in ('sh', 'hw'):
                direct, to_tank = arr(b[f'hp_{p}_direct_kwh_th']), arr(b[f'hp_{p}_to_tank_kwh_th']) if b[f'hp_{p}_to_tank_kwh_th'] else 0.0
                out = arr(b[f'{p}_tank_to_demand_kwh_th']) if b[f'{p}_tank_to_demand_kwh_th'] else 0.0
                assert np.abs(arr(b[f'{p}_demand_kwh_th']) - direct - out).max() < 1e-5, (name, role, p, 'demand = direct + tank')
                el, cop = arr(b[f'hp_{p}_kwh_el']), arr(b[f'cop_{p}'])
                assert (np.abs(el * cop - direct - to_tank) <= 2e-3 + 1e-3 * (direct + to_tank)).all(), (name, role, p, 'heat = electricity x COP')
                assert (arr(b[f'hp_{p}_kwh_el']) >= 0).all() and (direct >= -1e-9).all()


def test_tank_energy_conservation_and_losses(runs, binfo):
    """loss(t) = in(t) - out(t) - (E(t) - E(t-1)) with E = soc x capacity. Checked from step 1 (step 0 needs the initial state)."""
    for name, r in runs.items():
        for role, b in r['buildings'].items():
            for p in ('sh', 'hw'):
                comp = binfo[role]['components'][f'tank_{p}']
                if not comp['present']:
                    continue
                cap = comp['attributes']['capacity_kwh_th']['value']
                soc, inn, out, loss = (arr(b[k]) for k in (f'{p}_tank_soc', f'hp_{p}_to_tank_kwh_th', f'{p}_tank_to_demand_kwh_th', f'{p}_tank_loss_kwh_th'))
                assert ((soc >= -1e-9) & (soc <= 1 + 1e-9)).all()
                expect = inn[1:] - out[1:] - (soc[1:] - soc[:-1]) * cap
                assert np.abs(loss[1:] - np.maximum(expect, 0)).max() < 2e-3, (name, role, p)
                assert expect.min() > -2e-3, 'a tank cannot create energy'
                assert (loss >= 0).all()


def test_absent_components_are_null_never_zero(runs, binfo):
    for role, info in binfo.items():
        for p in ('sh', 'hw'):
            present = info['components'][f'tank_{p}']['present']
            for name, r in runs.items():
                b = r['buildings'][role]
                for k, var in BUILDING_VARIABLES.items():
                    if var['absent_when'] and k.startswith((f'{p}_tank', f'hp_{p}_to_tank')):
                        assert (b[k] is None) == (not present), (role, k)
    assert binfo['SFH-low']['components']['tank_hw']['present'] is False
    assert all(binfo[r]['components']['tank_sh']['present'] for r in ROLES)


def test_district_is_sum_of_buildings_and_cost_matches_price(runs, cond):
    price = arr(cond['series']['price_chf_kwh'])
    for name, r in runs.items():
        B = r['buildings'].values()
        assert np.abs(arr(r['district']['net_kwh_el']) - sum(arr(b['net_kwh_el']) for b in B)).max() < 1e-5
        assert np.abs(arr(r['district']['cost_chf']) - sum(arr(b['cost_chf']) for b in B)).max() < 1e-5
        for b in B:
            assert np.abs(arr(b['cost_chf']) - np.maximum(arr(b['net_kwh_el']), 0) * price).max() < 2e-6
        d = r['district']
        assert np.abs(arr(d['reward']) - arr(d['reward_cost']) - arr(d['reward_peak']) - arr(d['reward_ramp'])).max() < 1e-4


def test_summary_and_peak_power_conversion(runs, manifest):
    h = manifest['time_axis']['step_seconds'] / 3600
    for r in runs.values():
        net = arr(r['district']['net_kwh_el'])
        assert abs(r['summary']['peak_kw_el'] - net.max() / h) < 1e-5 and r['summary']['peak_step'] == int(net.argmax())
        assert abs(r['summary']['import_kwh_el'] - sum(np.maximum(arr(b['net_kwh_el']), 0) for b in r['buildings'].values()).sum()) < 1e-4
        blocks = [net[i:i + 24].max() for i in range(0, len(net), 24)]     # window starts on a 24-step boundary (local midnight)
        assert abs(r['summary']['mean_daily_peak_kw_el'] - np.mean(blocks) / h) < 1e-5


def test_tank_modes_and_tags_agree_with_flows(runs, manifest, cond):
    eps = manifest['situation_thresholds']['flow_epsilon_kwh_th']
    for r in runs.values():
        for role, b in r['buildings'].items():
            tags = r['situations']['buildings'][role]
            for p in ('sh', 'hw'):
                if b[f'{p}_tank_mode'] is None:
                    assert not any(t.startswith(f'{p}_tank') for t in tags)
                    continue
                for i, m in enumerate(b[f'{p}_tank_mode']):
                    chg, dis = b[f'hp_{p}_to_tank_kwh_th'][i] > eps, b[f'{p}_tank_to_demand_kwh_th'][i] > eps
                    assert m == ('charging' if chg else 'discharging' if dis else 'idle')
                for mode in ('charging', 'discharging', 'idle'):
                    assert tags.get(f'{p}_tank_{mode}', []) == [i for i, m in enumerate(b[f'{p}_tank_mode']) if m == mode]
        tier = cond['series']['tariff_tier']
        assert r['situations']['district'].get('high_tariff', []) == [i for i, t in enumerate(tier) if t == 'high']
        assert set(r['situations']['district']).issubset(SITUATION_TAGS)
        assert all(t in SITUATION_TAGS for tags in r['situations']['buildings'].values() for t in tags)


# ------------------------------------------------------------------------------------------------ independent cross-checks
def test_runs_equal_independent_run_traces(runs, manifest):
    """The sample must equal swiss/experiments/results/traces (written by run_baselines.py, a different code path)."""
    s0, n = manifest['time_axis']['scope']['start_step'], manifest['time_axis']['scope']['n_steps']
    for name, r in runs.items():
        t = pd.read_csv(os.path.join(ROOT, 'swiss', 'experiments', 'results', 'traces', f'{name}.csv.gz')).iloc[s0:s0 + n]
        for i, role in enumerate(ROLES, 1):
            b = r['buildings'][role]
            assert np.abs(arr(b['net_kwh_el']) - t[f'b{i}_net_kwh'].to_numpy()).max() < 1e-5, (name, role)
            assert np.abs(arr(b['hp_sh_kwh_el']) + arr(b['hp_hw_kwh_el']) - (t[f'b{i}_heating_device_kwh_el'] + t[f'b{i}_dhw_device_kwh_el']).to_numpy()).max() < 1e-5
            assert np.abs(arr(b['sh_tank_soc']) - t[f'b{i}_heating_storage_soc'].to_numpy()).max() < 1e-5
            assert np.abs(arr(b['sh_demand_kwh_th']) - t[f'b{i}_heating_demand_kwh'].to_numpy()).max() < 1e-5
            if b['hw_tank_soc'] is not None:
                assert np.abs(arr(b['hw_tank_soc']) - t[f'b{i}_dhw_storage_soc'].to_numpy()).max() < 1e-5
        assert np.abs(arr(r['district']['reward']) - t['reward'].to_numpy()).max() < 1e-4


def test_inputs_equal_dataset_csvs(runs, manifest, cond):
    s0, n = manifest['time_axis']['scope']['start_step'], manifest['time_axis']['scope']['n_steps']
    ds = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023')
    r = runs[REF]
    for i, role in enumerate(ROLES, 1):
        d = pd.read_csv(os.path.join(ds, f'Building_{i}.csv')).iloc[s0:s0 + n]
        assert np.abs(arr(r['buildings'][role]['sh_demand_kwh_th']) - d.heating_demand.to_numpy()).max() < 1e-5
        assert np.abs(arr(r['buildings'][role]['hw_demand_kwh_th']) - d.dhw_demand.to_numpy()).max() < 1e-5
        assert np.abs(arr(r['buildings'][role]['household_kwh_el']) - d.non_shiftable_load.to_numpy()).max() < 1e-5
    w = pd.read_csv(os.path.join(ds, 'weather.csv')).iloc[s0:s0 + n]
    p = pd.read_csv(os.path.join(ds, 'pricing.csv')).iloc[s0:s0 + n]
    assert np.abs(arr(cond['series']['temp_c']) - w.outdoor_dry_bulb_temperature.to_numpy()).max() < 1e-9
    assert np.abs(arr(cond['series']['price_chf_kwh']) - p.electricity_pricing.to_numpy()).max() < 1e-9
    t0 = pd.Timestamp(manifest['time_axis']['start_utc']) + pd.Timedelta(hours=s0)
    assert cond['timestamps_utc'][0] == t0.strftime('%Y-%m-%dT%H:%M:%SZ')
    assert cond['local_time'][0].startswith('2023-12-04T00:00') and cond['local_hour'][0] == 0


def test_annual_totals_match_baselines_csv(manifest):
    for name, d in manifest['checks']['annual_totals_vs_baselines_2023_csv'].items():
        for k, v in d.items():
            assert v['rel_diff'] < 1e-9, (name, k, v)
    assert max(manifest['checks']['max_abs_residuals'].values()) < 1e-4


def test_comparisons_recomputed_from_run_files(runs, cond):
    comp = load('comparisons.json')['comparisons']
    ref = runs[REF]
    hi = np.array([t == 'high' for t in cond['series']['tariff_tier']])
    imp = lambda r: sum(np.maximum(arr(b['net_kwh_el']), 0) for b in r['buildings'].values())  # noqa: E731
    assert REF not in comp and set(comp) == set(runs) - {REF}
    for name, c in comp.items():
        r = runs[name]
        m = c['metrics']
        assert abs(m['import_kwh_el']['value'] - r['summary']['import_kwh_el']) < 1e-9
        assert abs(m['import_kwh_el']['delta'] - (r['summary']['import_kwh_el'] - ref['summary']['import_kwh_el'])) < 1e-9
        assert abs(c['mechanisms']['import_moved_out_of_high_tariff_kwh_el'] - (imp(ref)[hi].sum() - imp(r)[hi].sum())) < 1e-4
        assert abs(c['mechanisms']['extra_tank_loss_kwh_th'] - (r['summary']['tank_loss_kwh_th'] - ref['summary']['tank_loss_kwh_th'])) < 1e-3
        assert abs(m['cost_chf']['delta'] - (r['summary']['cost_chf'] - ref['summary']['cost_chf'])) < 1e-3


def test_bau_is_flagged_identical_to_no_control(manifest, runs):
    by = {c['id']: c for c in manifest['controllers']}
    assert by[REF]['reference'] and by[REF]['identical_to'] is None
    assert by['ALG-002_business_as_usual']['identical_to'] == REF
    assert all(by[c]['identical_to'] is None for c in by if c not in (REF, 'ALG-002_business_as_usual'))


# ------------------------------------------------------------------------------------------------ provenance, wording, carbon
def test_every_source_id_exists_in_the_audit_graph(manifest, binfo):
    nodes = set(json.load(open(os.path.join(ROOT, 'web', 'public', 'bundle', 'provenance.json'), encoding='utf-8'))['nodes'])
    ids = set()
    for grp in manifest['variables'].values():
        for v in grp.values():
            ids |= set(v['source_ids'])
    for c in load('components.json')['components']:
        ids |= set(c['source_ids'])
    for info in binfo.values():
        ids |= set(info['related_ids'])
        for a in info['attributes'].values():
            ids |= set(a['source_ids'])
        for comp in info['components'].values():
            for a in comp['attributes'].values():
                ids |= set(a['source_ids'])
    missing = sorted(i for i in ids if i not in nodes)
    assert not missing, f'source ids not in the audit graph (provenance.json): {missing}'


def test_provenance_classes_follow_owner_decisions(manifest, binfo):
    b = manifest['variables']['building']
    assert b['household_kwh_el']['provenance'] == {'SFH': 'measured', 'MFH': 'synthetic'}
    assert b['sh_demand_kwh_th']['provenance'] == 'derived'
    for info in binfo.values():
        for comp in info['components'].values():
            for k, a in comp['attributes'].items():
                if k in ('capacity_kwh_th', 'efficiency', 'loss_per_hour', 'supply_temperature_c'):
                    assert a['provenance'] == 'assumed_parameter', (info['id'], k)
        assert binfo[info['id']]['attributes']['household_electricity_source']['provenance'] == ('measured' if info['type'] == 'SFH' else 'synthetic')


def test_unavailable_attributes_are_not_zero(binfo):
    for role in ROLES:
        a = binfo[role]['attributes']
        assert a['floors']['available'] is False and a['floors']['value'] is None and a['floors']['provenance'] is None and a['floors']['unavailable_reason']
        if role.startswith('MFH'):
            assert a['floor_area_m2']['available'] is False and a['residents']['available'] is False and a['heat_pump_type']['available'] is False
    assert binfo['SFH-low']['attributes']['floor_area_m2']['value'] == 220.0 and binfo['SFH-high']['attributes']['residents']['value'] == 2.0
    assert binfo['MFH-large']['attributes']['housing_units']['value'] == 24 and binfo['MFH-small']['attributes']['housing_units']['value'] == 5


def test_hot_water_wording(manifest):
    for k, v in manifest['variables']['building'].items():
        if '_hw_' in k or k.startswith(('hw_', 'cop_hw')):
            assert 'hot water and other base load' in v['label'], k
        assert 'domestic' not in v['label'].lower()


def test_no_absolute_carbon_in_any_exported_file(manifest):
    parts = []
    for f in glob.glob(os.path.join(SIM, '**', '*.json'), recursive=True):
        d = json.load(open(f, encoding='utf-8'))
        if os.path.basename(f) == 'manifest.json':
            d = {k: v for k, v in d.items() if k != 'inputs'}   # `inputs` lists input FILE PATHS (the dataset's carbon CSV is one); it is not exported data
        parts.append(json.dumps(d))
    txt = ''.join(parts)
    import re
    for bad in ('carbon_intensity', 'gco2', 'g/kWh', 'co2_g'):
        assert bad.lower() not in txt.lower(), bad
    assert not re.search(r'(?<![a-z])g_kwh', txt.lower()), 'a standalone g_kwh token (grams per kWh) must not appear; "timing_kwh" is fine'
    assert manifest['variables']['conditions']['carbon_relative_rank']['relative_only'] is True
    for c in [*load('comparisons.json')['comparisons'].values(), *load('comparisons_year.json')['comparisons'].values()]:
        assert c['relative_only'] == ['carbon_from_timing_pct', 'carbon_from_extra_electricity_pct', 'relative_carbon_change_pct']


def test_future_phase_components_are_not_modeled():
    comps = {c['id']: c for c in load('components.json')['components']}
    for k in ('pv', 'battery', 'ev', 'energy_community', 'cooling'):
        assert comps[k]['status'] == 'not_modeled' and comps[k]['phase_available'] in ('B', 'C') and comps[k]['variables'] == []
    flows = load('components.json')['flows']
    ids = set(comps)
    assert all(f['from'] in ids and f['to'] in ids and f['status'] == 'modeled' for f in flows)
    assert not any(comps[f['from']]['status'] == 'not_modeled' or comps[f['to']]['status'] == 'not_modeled' for f in flows)
    # every flow variable is an exported variable
    names = set(BUILDING_VARIABLES) | {f'district.{k}' for k in DISTRICT_VARIABLES} | set(CONDITION_VARIABLES)
    assert all(f['variable'] in names for f in flows if f['variable'])


# ------------------------------------------------------------------------------------------------ annual comparisons and mechanisms
YEAR_TOL = {'import_kwh_el': ('district_import_kwh', 1e-9), 'peak_kw_el': ('district_peak_kw', 1e-9), 'mean_daily_peak_kw_el': ('mean_daily_peak_kw', 1e-9),
            'cost_chf': ('cost_chf_excl_vat', 1e-9), 'high_tariff_import_share': ('high_tariff_import_share', 1e-9)}


def test_year_comparisons_equal_the_independent_results_table():
    """comparisons_year.json (computed from the recorder) vs baselines_2023.csv (written by run_baselines.py, a different code path)."""
    cy = load('comparisons_year.json')
    assert cy['scope']['kind'] == 'year' and cy['scope']['start_step'] == 0 and cy['scope']['n_steps'] == 8759
    res = pd.read_csv(os.path.join(ROOT, 'swiss', 'experiments', 'results', 'baselines_2023.csv')).set_index('controller')
    ref = res.loc[REF]
    for name, c in cy['comparisons'].items():
        for k, (col, tol) in YEAR_TOL.items():
            m = c['metrics'][k]
            assert abs(m['value'] - res.loc[name, col]) <= tol * max(1.0, abs(res.loc[name, col])), (name, k)
            assert abs(m['reference'] - ref[col]) <= tol * max(1.0, abs(ref[col])), (name, k)
        carbon = 100 * (res.loc[name, 'term_carbon_sum'] / ref.term_carbon_sum - 1)
        assert abs(c['mechanisms']['relative_carbon_change_pct'] - carbon) < 1e-6, name


def test_mechanism_decompositions_are_exact_in_both_scopes():
    for f in ('comparisons.json', 'comparisons_year.json'):
        for name, c in load(f)['comparisons'].items():
            m, x = c['mechanisms'], c['metrics']
            tol = 1e-3 + 1e-6 * abs(m['tank_charging_electricity_kwh_el'])
            assert abs(m['extra_hp_electricity_kwh_el'] - (m['tank_charging_electricity_kwh_el'] - m['electricity_avoided_at_discharge_kwh_el'])) < tol, (f, name)
            assert abs(m['extra_hp_electricity_kwh_el'] - (m['electricity_from_tank_losses_kwh_el'] + m['electricity_from_stored_remainder_kwh_el']
                                                          + m['electricity_from_cop_timing_kwh_el'])) < tol, (f, name)
            assert abs(x['cost_chf']['delta'] - (m['cost_from_tariff_timing_chf'] + m['cost_from_extra_electricity_chf'])) < tol, (f, name)
            assert abs(x['import_kwh_el']['delta'] - m['extra_hp_electricity_kwh_el']) < tol, 'household electricity is unchanged by a controller'
            assert abs((m['tank_heat_in_kwh_th'] - m['tank_heat_out_kwh_th'] - m['stored_heat_change_kwh_th']) - m['extra_tank_loss_kwh_th']) < tol, (f, name)
            if m['relative_carbon_change_pct'] is not None:
                assert abs(m['relative_carbon_change_pct'] - (m['carbon_from_timing_pct'] + m['carbon_from_extra_electricity_pct'])) < 1e-4, (f, name)
            assert m['electricity_from_tank_losses_kwh_el'] >= -1e-6 and m['tank_heat_in_kwh_th'] >= m['tank_heat_out_kwh_th'] - 1e-6


def test_window_mechanisms_recomputed_from_run_arrays(runs, cond):
    """Independent re-implementation of the decomposition from the exported run arrays (test code only; no exporter code)."""
    price = arr(cond['series']['price_chf_kwh'])
    ref = runs[REF]
    for name, c in load('comparisons.json')['comparisons'].items():
        r = runs[name]
        t = dict(inn=0.0, out=0.0, A=0.0, B=0.0)
        for role in ROLES:
            for p in ('sh', 'hw'):
                b = r['buildings'][role]
                if b[f'{p}_tank_soc'] is None:
                    continue
                inn, out, cop = arr(b[f'hp_{p}_to_tank_kwh_th']), arr(b[f'{p}_tank_to_demand_kwh_th']), arr(b[f'cop_{p}'])
                t['inn'] += inn.sum(); t['out'] += out.sum()
                t['A'] += (inn / cop).sum(); t['B'] += (out / cop).sum()
        m = c['mechanisms']
        assert abs(t['inn'] - m['tank_heat_in_kwh_th']) < 1e-2, name
        assert abs(t['out'] - m['tank_heat_out_kwh_th']) < 1e-2, name
        assert abs(t['A'] - m['tank_charging_electricity_kwh_el']) < 1e-2, name
        assert abs(t['B'] - m['electricity_avoided_at_discharge_kwh_el']) < 1e-2, name
        assert abs((t['A'] - t['B']) - m['extra_hp_electricity_kwh_el']) < 1e-2, name
        # cost: sum_t price_t x (extra heat-pump electricity of the step) equals the cost delta
        dcost = sum(((arr(r['buildings'][ro]['net_kwh_el']) - arr(ref['buildings'][ro]['net_kwh_el'])) * price).sum() for ro in ROLES)
        assert abs(dcost - c['metrics']['cost_chf']['delta']) < 1e-3, name


def test_bau_has_no_mechanisms():
    for f in ('comparisons.json', 'comparisons_year.json'):
        m = load(f)['comparisons']['ALG-002_business_as_usual']['mechanisms']
        assert all(abs(v) < 1e-9 for k, v in m.items() if isinstance(v, float) and k != 'relative_carbon_change_pct')
        assert abs(m['relative_carbon_change_pct']) < 1e-9


def test_per_building_kpi_average_differs_from_district_total():
    """Documents why the KPI table and the district comparison differ: CityLearn's KPI is the unweighted MEAN OF BUILDING RATIOS."""
    res = pd.read_csv(os.path.join(ROOT, 'swiss', 'experiments', 'results', 'baselines_2023.csv')).set_index('controller')
    R = os.path.join(ROOT, 'swiss', 'experiments', 'results', 'traces')
    ref, t = (pd.read_csv(os.path.join(R, f'{n}.csv.gz')) for n in (REF, 'ALG-003_basic_rbc'))
    ci = t.carbon_intensity.to_numpy()
    ratios = [(np.maximum(t[f'b{i}_net_kwh'], 0) * ci).sum() / (np.maximum(ref[f'b{i}_net_kwh'], 0) * ci).sum() for i in range(1, 7)]
    assert abs(np.mean(ratios) - res.loc['ALG-003_basic_rbc', 'kpi_carbon_emissions_total']) < 1e-5
    district = load('comparisons_year.json')['comparisons']['ALG-003_basic_rbc']['mechanisms']['relative_carbon_change_pct']
    assert abs(district / 100 - (res.loc['ALG-003_basic_rbc', 'term_carbon_sum'] / res.loc[REF, 'term_carbon_sum'] - 1)) < 1e-9
    assert district / 100 > np.mean(ratios) - 1 + 1e-3, 'energy-weighted district total differs from the mean of building ratios'


# ------------------------------------------------------------------------------------------------ structured flag and user-facing wording
def test_electric_water_heater_is_a_boolean_flag(binfo):
    """The frontend must not parse free text: the survey fact is a boolean attribute (SFH-mid and SFH-high heat water electrically, ISS-027)."""
    for role in ROLES:
        a = binfo[role]['attributes']['electric_water_heater']
        if role.startswith('SFH'):
            assert a['available'] is True and a['provenance'] == 'measured' and 'ISS-027' in a['source_ids']
            assert a['value'] is (role in ('SFH-mid', 'SFH-high')), role
            assert ('electric water heater' in binfo[role]['attributes']['water_heating']['value']) == a['value'], 'flag and description must agree'
        else:
            assert a['available'] is False and a['value'] is None and a['provenance'] is None and a['unavailable_reason']


def test_situation_tag_texts_are_plain_language_and_match_the_thresholds(manifest):
    """The dashboard shows these texts as they are: no field names, and every quoted number comes from situation_thresholds."""
    import re
    thr = manifest['situation_thresholds']
    for tag, text in manifest['situation_tags'].items():
        assert tag in manifest['situation_tags'] and text.endswith('.') and text[0].isupper(), tag
        assert not re.search(r'[a-z]+_[a-z]+', text) and 'threshold' not in text.lower(), f'{tag}: internal wording leaks: {text}'
    pc = lambda x: f'{100 * x:.0f} %'  # noqa: E731
    assert pc(thr['tank_full_soc']) in manifest['situation_tags']['sh_tank_full']
    assert pc(thr['tank_empty_soc']) in manifest['situation_tags']['hw_tank_empty']
    assert pc(thr['storage_covers_demand_share']) in manifest['situation_tags']['sh_tank_covers_demand']
    assert pc(thr['near_capacity_fraction']) in manifest['situation_tags']['hp_sh_near_capacity']
