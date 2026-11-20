"""Scenario files of contract v1.1 (web/public/bundle/sim_scenarios/: Phase B and Phase C full-year scenarios): schema validity, electricity balances re-derived from
the files, cooling absent (not zero) where there is no cooling device, battery and PV consistency, independent cross-checks against the dataset CSVs, manifest freshness.

Run: PYTHONPATH=. cl/bin/python -m pytest swiss/tests/test_contract_scenarios.py -q
"""
import glob
import hashlib
import json
import os

import numpy as np
import pandas as pd
import pytest

from swiss.contract import CONTRACT_VERSION, schema_gen, validate
from swiss.contract import variables_scenario as vs
from swiss.contract.export_scenarios import CONTROLLERS, EXPORT_RP, SCENARIOS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASE = os.path.join(ROOT, 'web', 'public', 'bundle', 'sim_scenarios')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
N = 8759
BAL_TOL = 1e-3          # eight per-step values are rounded to 4 decimals (+-5e-5 each)
IDS = [s['id'] for s in SCENARIOS]


def load(*parts):
    with open(os.path.join(BASE, *parts), encoding='utf-8') as f:
        return json.load(f)


def arr(x):
    return np.asarray(x, dtype=float)


@pytest.fixture(scope='module', params=IDS)
def scn(request):
    sid = request.param
    m = load(sid, 'manifest.json')
    return {'id': sid, 'spec': next(s for s in SCENARIOS if s['id'] == sid), 'manifest': m, 'cond': load(sid, 'conditions.json'),
            'runs': {c['id']: load(sid, c['file']) for c in m['controllers']}}


def test_scenarios_are_a_list_and_every_one_is_exported():
    assert len(IDS) == len(set(IDS)) >= 2
    index = load('index.json')
    assert validate.validate_file(os.path.join(BASE, 'index.json'), 'scenario_index') == []
    assert [e['id'] for e in index['scenarios']] == IDS
    assert index['contract_version'] == CONTRACT_VERSION


def test_every_file_validates_against_the_schemas(scn):
    d = os.path.join(BASE, scn['id'])
    assert validate.validate_file(os.path.join(d, 'manifest.json'), 'scenario_manifest') == []
    assert validate.validate_file(os.path.join(d, 'conditions.json'), 'scenario_conditions') == []
    assert [c['id'] for c in scn['manifest']['controllers']] == [c['id'] for c in CONTROLLERS]
    for c in scn['manifest']['controllers']:
        assert validate.validate_file(os.path.join(d, c['file']), 'scenario_run') == [], c['file']


def test_committed_scenario_schemas_equal_generated():
    for name, sch in schema_gen.schemas().items():
        if name.startswith('scenario_'):
            with open(os.path.join(schema_gen.DIR, f'{name}.schema.json'), encoding='utf-8') as f:
                assert f.read() == schema_gen.render(sch), f'{name}.schema.json is stale: run swiss/contract/schema_gen.py'


def test_version_scope_and_lengths(scn):
    m = scn['manifest']
    assert m['contract_version'] == CONTRACT_VERSION == '1.1.0' and m['phase'] == scn['spec']['phase'] and m['buildings'] == ROLES
    assert m['time_axis']['step_seconds'] == 3600 and m['time_axis']['n_steps_simulated'] == N and m['time_axis']['n_steps_inputs'] == 8760
    assert len(scn['cond']['local_time']) == 8760 and all(len(v) == 8760 for v in scn['cond']['series'].values())
    assert scn['cond']['contract_version'] == CONTRACT_VERSION
    for r in scn['runs'].values():
        assert r['contract_version'] == CONTRACT_VERSION and r['scope'] == {'kind': 'year', 'start_step': 0, 'n_steps': N}
        assert set(r['buildings']) == set(ROLES)
        for b in r['buildings'].values():
            assert all(v is None or len(v) == N for v in b.values())
        assert all(v is None or len(v) == N for v in r['district'].values())


def test_exported_variables_equal_the_python_dictionary(scn):
    cool = scn['manifest']['features']['cooling']
    v = scn['manifest']['variables']
    assert v['building'] == json.loads(json.dumps(vs.building_variables(cool))) and v['district'] == json.loads(json.dumps(vs.district_variables(cool)))
    assert v['conditions'] == json.loads(json.dumps(vs.condition_variables(scn['spec']['climate'])))


def test_hourly_electricity_balance_from_the_files(scn):
    """import - export + pv = household + hp_sh + hp_hw + hp_cool + battery charge - battery discharge, every building, every hour, both controllers."""
    for name, r in scn['runs'].items():
        for role, b in r['buildings'].items():
            lhs = arr(b['import_kwh_el']) - arr(b['export_kwh_el']) + arr(b['pv_kwh_el'])
            rhs = arr(b['household_kwh_el']) + arr(b['hp_sh_kwh_el']) + arr(b['hp_hw_kwh_el']) + (arr(b['hp_cool_kwh_el']) if b['hp_cool_kwh_el'] else 0.0) \
                + arr(b['battery_charge_kwh_el']) - arr(b['battery_discharge_kwh_el'])
            assert np.abs(lhs - rhs).max() < BAL_TOL, (scn['id'], name, role, np.abs(lhs - rhs).max())
            assert arr(b['import_kwh_el']).min() >= 0 and arr(b['export_kwh_el']).min() >= 0
            assert (np.minimum(arr(b['import_kwh_el']), arr(b['export_kwh_el'])) < 1e-9).all(), 'a building does not buy and sell in the same hour'
            assert (np.minimum(arr(b['battery_charge_kwh_el']), arr(b['battery_discharge_kwh_el'])) < 1e-9).all()


def test_export_time_residuals_are_small(scn):
    res = scn['manifest']['checks']['max_abs_residuals']
    assert res['electricity_balance_kwh_el'] < 1e-4
    for k, v in res.items():
        assert v < 1e-4, k


def test_district_is_the_sum_of_the_buildings(scn):
    for r in scn['runs'].values():
        for k in ('import_kwh_el', 'export_kwh_el', 'pv_kwh_el', 'battery_charge_kwh_el', 'battery_discharge_kwh_el'):
            tot = sum(arr(b[k]) for b in r['buildings'].values())
            assert np.abs(tot - arr(r['district'][k])).max() < 1e-3, k


def test_cooling_is_absent_not_zero_where_there_is_no_device(scn):
    cool_flags = {role: scn['manifest']['equipment'][role]['cooling']['value'] for role in ROLES}
    for r in scn['runs'].values():
        for role, b in r['buildings'].items():
            if not cool_flags[role]:
                assert b['hp_cool_kwh_el'] is None, (scn['id'], role)
            else:
                assert b['hp_cool_kwh_el'] is not None and max(b['hp_cool_kwh_el']) > 0
        if scn['manifest']['features']['cooling']:
            assert r['district']['hp_cool_kwh_el'] is not None and abs(sum(r['district']['hp_cool_kwh_el']) - r['summary']['hp_cool_kwh_el']) < 1e-2
        else:
            assert r['district']['hp_cool_kwh_el'] is None and r['summary']['hp_cool_kwh_el'] is None and not any(cool_flags.values())


def test_phase_c_cools_only_the_medium_adoption_building_and_has_the_heat_wave_jump():
    m = load('phase_c_gwl2_hw99_medium', 'manifest.json')
    assert [r for r in ROLES if m['equipment'][r]['cooling']['value']] == ['MFH-medium']
    jt = m['jump_targets']
    assert len(jt) == 1 and jt[0]['id'] == 'heat_wave' and jt[0]['window'][0] <= jt[0]['steps'][0] <= jt[0]['window'][1]
    cond = load('phase_c_gwl2_hw99_medium', 'conditions.json')
    t = arr(cond['series']['temp_c'])
    lo, hi = jt[0]['window']
    assert t[lo:hi + 1].max() > 33 and t[lo:hi + 1].mean() > t.mean() + 8, 'the inserted week is a heat wave'
    assert t[jt[0]['steps'][0]:jt[0]['steps'][0] + 24].max() == t[lo:hi + 1].max()
    th = load('phase_c_gwl2_hw99_medium', 'runs', 'thermostat.json')
    assert max(th['buildings']['MFH-medium']['temp_in_c']) <= 26.5, 'the thermostat keeps the cooled building at its 26 C set point'
    assert max(th['buildings']['SFH-low']['temp_in_c']) > 30, 'uncooled buildings float in the heat wave'


def test_phase_b_has_no_cooling_and_no_heat_wave_jump():
    m = load('phase_b_s3_2023', 'manifest.json')
    assert m['features']['cooling'] is False and m['jump_targets'] == []
    th = load('phase_b_s3_2023', 'runs', 'thermostat.json')
    for b in th['buildings'].values():
        t = arr(b['temp_in_c'])
        assert 18 < t.min() and t.max() < 45, 'indoor temperature stays physical in 2023 weather'


def test_battery_and_pv_consistency(scn):
    th, op = scn['runs']['thermostat'], scn['runs']['optimum']
    for role in ROLES:
        a, b = th['buildings'][role], op['buildings'][role]
        assert arr(a['pv_kwh_el']).max() > 0 and np.abs(arr(a['pv_kwh_el']) - arr(b['pv_kwh_el'])).max() < 1e-9, 'same weather and panels in both runs'
        assert max(a['battery_charge_kwh_el']) == 0 and max(a['battery_discharge_kwh_el']) == 0, 'the thermostat reference never uses the battery'
        assert max(b['battery_charge_kwh_el']) > 0 and max(b['battery_discharge_kwh_el']) > 0
        for x in (a, b):
            soc = arr(x['battery_soc'])
            assert soc.min() >= 0 and soc.max() <= 1
        soc = arr(b['battery_soc'])
        d = np.diff(soc)
        net = (arr(b['battery_charge_kwh_el']) - arr(b['battery_discharge_kwh_el']))[1:]
        assert ((d > 1e-6) <= (net > 0)).all() and ((d < -1e-6) <= (net < 0)).all(), 'fill level moves in the direction of the bus flow'
    eq = scn['manifest']['equipment']
    pv = {r: eq[r]['pv_kwp']['value'] for r in ROLES}
    assert all(eq[r]['battery_kwh']['value'] == pv[r] for r in ROLES), 'battery 1 kWh per kWp (A-017)'


def test_pv_follows_irradiance(scn):
    cond = scn['cond']
    ghi = arr(cond['series']['ghi_wm2'])[:N]
    pv = sum(arr(b['pv_kwh_el']) for b in scn['runs']['thermostat']['buildings'].values())
    assert pv[ghi <= 0].sum() < 0.01 * pv.sum(), 'at most a dawn/dusk hour-convention sliver of PV in hours without irradiance'
    assert np.corrcoef(pv, ghi)[0, 1] > 0.9


def test_summary_matches_arrays_and_bill_formula(scn):
    price = arr(scn['cond']['series']['price_chf_kwh'])[:N]
    for name, r in scn['runs'].items():
        imp, exp = arr(r['district']['import_kwh_el']), arr(r['district']['export_kwh_el'])
        s = r['summary']
        assert abs(s['import_kwh_el'] - imp.sum()) < 1e-6 and abs(s['export_kwh_el'] - exp.sum()) < 1e-6
        assert abs(s['bill_chf'] - ((imp * price).sum() - EXPORT_RP / 100 * exp.sum())) < 1e-6
        assert abs(s['peak_kw_el'] - imp.max()) < 1e-9 and s['peak_step'] == int(imp.argmax())
        dh = sum(np.maximum(arr(b['temp_in_c']) - 26.0, 0).sum() for b in r['buildings'].values())
        assert abs(s['degree_hours_above_26_c'] - dh) < 1.0
        for tag, steps in r['situations']['district'].items():
            assert tag in scn['manifest']['situation_tags'] and steps == sorted(set(steps)) and max(steps) < N
        for k in r['situations']['district'].get('district_exporting', []):
            assert exp[k] >= scn['manifest']['situation_thresholds']['export_hour_kwh'] - 1e-9


def test_optimum_beats_the_thermostat_on_the_bill_and_matches_the_program(scn):
    th, op = scn['runs']['thermostat']['summary'], scn['runs']['optimum']['summary']
    prog = scn['manifest']['checks']['program_vs_replay']
    assert op['bill_chf'] < th['bill_chf']
    assert abs(th['bill_chf'] - prog['zero_bill_chf']) <= 2e-3 * prog['zero_bill_chf'], 'replayed thermostat bill = the baseline bill of the linear program'
    assert abs(op['bill_chf'] - prog['opt_bill_chf']) <= 2e-3 * prog['opt_bill_chf'], 'replay in CityLearn realises the program (perfect-foresight optimum)'


def test_conditions_equal_the_dataset_csvs(scn):
    ds = os.path.join(ROOT, scn['spec']['dataset'])
    if not os.path.exists(os.path.join(ds, 'weather.csv')):
        pytest.skip('dataset not built locally (docs/reproduction.md, 4c)')
    w = pd.read_csv(os.path.join(ds, 'weather.csv'))
    p = pd.read_csv(os.path.join(ds, 'pricing.csv'))
    c = scn['cond']['series']
    assert np.abs(arr(c['temp_c']) - w.outdoor_dry_bulb_temperature.to_numpy()[:8760]).max() < 0.051
    assert np.abs(arr(c['ghi_wm2']) - (w.diffuse_solar_irradiance + w.direct_solar_irradiance).to_numpy()[:8760]).max() < 0.51
    assert np.abs(arr(c['price_chf_kwh']) - p.electricity_pricing.to_numpy()[:8760]).max() < 1e-6
    high = np.array([t == 'high' for t in c['tariff_tier']])
    assert (high == (p.electricity_pricing.to_numpy()[:8760] > p.electricity_pricing.min() + 1e-9)).all()


def test_source_ids_exist_in_the_audit_graph(scn):
    nodes = set(json.load(open(os.path.join(ROOT, 'web', 'public', 'bundle', 'provenance.json'), encoding='utf-8'))['nodes'])
    ids = set(c['algorithm_id'] for c in scn['manifest']['controllers'])
    for grp in scn['manifest']['variables'].values():
        for v in grp.values():
            ids |= set(v['source_ids'])
    for eq in scn['manifest']['equipment'].values():
        for a in eq.values():
            ids |= set(a['source_ids'])
    ids |= set(scn['manifest']['export_price_chf_kwh']['source_ids'])
    missing = sorted(i for i in ids if i not in nodes)
    assert not missing, f'ids not in the audit graph: {missing}'


def test_provenance_labels_follow_owner_decisions(scn):
    b = scn['manifest']['variables']['building']
    assert b['household_kwh_el']['provenance'] == {'SFH': 'measured', 'MFH': 'synthetic'}
    for k in ('pv_kwh_el', 'battery_charge_kwh_el', 'temp_in_c', 'hp_cool_kwh_el'):
        assert b[k]['provenance'] == 'modeled'
    for role, eq in scn['manifest']['equipment'].items():
        assert eq['pv_kwp']['provenance'] == 'assumed_parameter' and eq['battery_kwh']['provenance'] == 'assumed_parameter'
    assert scn['manifest']['variables']['conditions']['temp_c']['provenance'] == ('modeled' if scn['spec']['climate'] else 'measured')


def test_no_absolute_carbon_and_no_role_codes_in_labels():
    for f in glob.glob(os.path.join(BASE, '**', '*.json'), recursive=True):
        txt = json.dumps({k: v for k, v in json.load(open(f, encoding='utf-8')).items() if k != 'inputs'}).lower()
        for bad in ('carbon_intensity', 'gco2', 'g/kwh', 'co2_g'):
            assert bad not in txt, (f, bad)


def test_typescript_types_name_every_scenario_variable():
    ts = open(os.path.join(ROOT, 'web', 'src', 'lib', 'contract', 'types.ts'), encoding='utf-8').read()
    for k in list(vs.building_variables(True)) + list(vs.district_variables(True)) + list(vs.condition_variables(True)):
        assert f'{k}:' in ts, f'types.ts is missing {k}'


def test_files_match_hashes_and_inputs_are_fresh(scn):
    d = os.path.join(BASE, scn['id'])
    for rel, h in scn['manifest']['files'].items():
        assert hashlib.sha256(open(os.path.join(d, rel), 'rb').read()).hexdigest() == h, f'{rel} changed after export'
    stale = [f for f, h in scn['manifest']['inputs'].items() if hashlib.sha256(open(os.path.join(ROOT, f), 'rb').read()).hexdigest() != h]
    assert not stale, f'inputs changed since the export (regenerate with swiss/contract/export_scenarios.py): {stale}'


def test_full_year_size_budget():
    """Per-scenario size comparable to the Phase A full-year export (about 10 MB per run): the scenario files hold only the fields the view draws."""
    for sid in IDS:
        total = sum(os.path.getsize(f) for f in glob.glob(os.path.join(BASE, sid, '**', '*.json'), recursive=True))
        assert total < 15e6, (sid, total)


def test_exporter_reproduces_the_committed_files(tmp_path):
    """Re-runs the real rollouts of the Phase B scenario (about 2 minutes) and compares the files byte for byte."""
    from swiss.contract import export_scenarios
    export_scenarios.main(out=str(tmp_path), only=['phase_b_s3_2023'])
    for rel in ('conditions.json', 'runs/thermostat.json', 'runs/optimum.json'):
        assert open(tmp_path / 'phase_b_s3_2023' / rel, 'rb').read() == open(os.path.join(BASE, 'phase_b_s3_2023', rel), 'rb').read(), rel
