"""Full-year contract bundle (web/public/bundle/sim_full/) tests: schema validity, consistency with the 48-hour sample (the sample must be an
exact slice of the full year), annual totals against the independent results table, balances over the whole year, freshness.

Run: PYTHONPATH=. cl/bin/python -m pytest swiss/tests/test_contract_full.py -q
"""
import glob
import hashlib
import json
import os
import re

import numpy as np
import pandas as pd
import pytest

from swiss.contract import CONTRACT_VERSION, validate
from swiss.contract.variables import BUILDING_VARIABLES, DISTRICT_VARIABLES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FULL = os.path.join(ROOT, 'web', 'public', 'bundle', 'sim_full')
SAMPLE = os.path.join(ROOT, 'web', 'public', 'bundle', 'sim')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
REF = 'ALG-001_zero_action'
N = 8759


def load(base, rel):
    with open(os.path.join(base, rel), encoding='utf-8') as f:
        return json.load(f)


def arr(x):
    return np.asarray(x, dtype=float)


@pytest.fixture(scope='module')
def manifest():
    return load(FULL, 'manifest.json')


@pytest.fixture(scope='module')
def runs(manifest):
    return {r['controller']: load(FULL, r['file']) for r in manifest['runs']}


@pytest.fixture(scope='module')
def sample_manifest():
    return load(SAMPLE, 'manifest.json')


@pytest.fixture(scope='module')
def sample_runs(sample_manifest):
    return {r['controller']: load(SAMPLE, r['file']) for r in sample_manifest['runs']}


def test_every_full_year_file_validates_against_the_schemas(manifest):
    for f, name in (('manifest.json', 'manifest'), ('buildings.json', 'buildings'), ('components.json', 'components'), ('conditions.json', 'conditions'),
                    ('comparisons.json', 'comparisons'), ('comparisons_year.json', 'comparisons')):
        assert validate.validate_file(os.path.join(FULL, f), name) == [], f
    assert len(manifest['runs']) == 6
    for r in manifest['runs']:
        assert validate.validate_file(os.path.join(FULL, r['file']), 'run') == [], r['file']


def test_full_manifest_scope_and_integrity(manifest, sample_manifest):
    assert manifest['contract_version'] == CONTRACT_VERSION and manifest['kind'] == 'full'
    ta = manifest['time_axis']
    assert ta['step_seconds'] == 3600 and ta['n_steps_simulated'] == N and ta['n_steps_inputs'] == 8760
    assert ta['scope'] == {'kind': 'year', 'start_step': 0, 'n_steps': 8760}
    assert manifest['controllers'] == sample_manifest['controllers'] and manifest['buildings'] == ROLES
    assert manifest['variables'] == sample_manifest['variables'] and manifest['situation_thresholds'] == sample_manifest['situation_thresholds']
    for rel, h in manifest['files'].items():
        assert hashlib.sha256(open(os.path.join(FULL, rel), 'rb').read()).hexdigest() == h, rel
    stale = [f for f, h in manifest['inputs'].items() if hashlib.sha256(open(os.path.join(ROOT, f), 'rb').read()).hexdigest() != h]
    assert not stale, f'inputs changed since the full-year export (regenerate with export_v1.py --full --out web/public/bundle/sim_full): {stale}'
    assert manifest['inputs'] == sample_manifest['inputs'], 'sample and full year were built from different inputs'


def test_run_shapes(runs):
    for name, r in runs.items():
        assert r['scope'] == {'kind': 'year', 'start_step': 0, 'n_steps': N}
        assert set(r['district']) == set(DISTRICT_VARIABLES) and all(len(v) == N for v in r['district'].values())
        for role, b in r['buildings'].items():
            assert set(b) == set(BUILDING_VARIABLES), (name, role)
            for k, v in b.items():
                assert v is None or len(v) == N, (name, role, k)


def test_sample_is_an_exact_slice_of_the_full_year(runs, sample_runs, sample_manifest):
    """Same exporter, same rounding: every sample value must equal the corresponding full-year value."""
    s0, n = sample_manifest['time_axis']['scope']['start_step'], sample_manifest['time_axis']['scope']['n_steps']
    for name, sr in sample_runs.items():
        fr = runs[name]
        for role in ROLES:
            for k, v in sr['buildings'][role].items():
                full = fr['buildings'][role][k]
                assert (v is None) == (full is None), (name, role, k)
                if v is not None:
                    assert v == full[s0:s0 + n], (name, role, k)
        for k, v in sr['district'].items():
            assert v == fr['district'][k][s0:s0 + n], (name, k)
        # sparse tags: window tags are the full-year tags that fall in the window, shifted to window-relative steps
        for tag, steps in sr['situations']['district'].items():
            assert steps == [i - s0 for i in fr['situations']['district'][tag] if s0 <= i < s0 + n], (name, tag)
        for role in ROLES:
            for tag, steps in sr['situations']['buildings'][role].items():
                assert steps == [i - s0 for i in fr['situations']['buildings'][role][tag] if s0 <= i < s0 + n], (name, role, tag)
    fc, sc = load(FULL, 'conditions.json'), load(SAMPLE, 'conditions.json')
    for k, v in sc['series'].items():
        assert v == fc['series'][k][s0:s0 + n], k
    assert sc['timestamps_utc'] == fc['timestamps_utc'][s0:s0 + n] and sc['local_time'] == fc['local_time'][s0:s0 + n]
    for role in ROLES:
        assert sc['building_flags'][role]['gap_filled'] == fc['building_flags'][role]['gap_filled'][s0:s0 + n]
    assert load(SAMPLE, 'buildings.json') == load(FULL, 'buildings.json') and load(SAMPLE, 'components.json') == load(FULL, 'components.json')


def test_full_year_totals_equal_the_independent_results_table(runs):
    res = pd.read_csv(os.path.join(ROOT, 'swiss', 'experiments', 'results', 'baselines_2023.csv')).set_index('controller')
    cond = load(FULL, 'conditions.json')
    price, tier = arr(cond['series']['price_chf_kwh'])[:N], np.array([t == 'high' for t in cond['series']['tariff_tier']])[:N]
    for name, r in runs.items():
        imp = sum(np.maximum(arr(b['net_kwh_el']), 0) for b in r['buildings'].values())
        net = sum(arr(b['net_kwh_el']) for b in r['buildings'].values())
        daily = pd.Series(net).groupby(np.arange(N) // 24).max().mean()
        row = res.loc[name]
        # arrays are rounded to 6 decimals per value: allow 1e-6 relative on annual sums
        assert abs(imp.sum() - row.district_import_kwh) <= 1e-6 * row.district_import_kwh, name
        assert abs(net.max() - row.district_peak_kw) <= 1e-6 * row.district_peak_kw, name
        assert abs(daily - row.mean_daily_peak_kw) <= 1e-6 * row.mean_daily_peak_kw, name
        assert abs((imp * price).sum() - row.cost_chf_excl_vat) <= 1e-6 * row.cost_chf_excl_vat, name
        assert abs(imp[tier].sum() / imp.sum() - row.high_tariff_import_share) <= 1e-6, name
        assert abs(r['summary']['import_kwh_el'] - row.district_import_kwh) <= 1e-9 * row.district_import_kwh, name


def test_full_year_balances_and_tank_conservation(runs):
    binfo = load(FULL, 'buildings.json')['buildings']
    for name, r in runs.items():
        for role, b in r['buildings'].items():
            assert np.abs(arr(b['net_kwh_el']) - arr(b['hp_sh_kwh_el']) - arr(b['hp_hw_kwh_el']) - arr(b['household_kwh_el'])).max() < 1e-5, (name, role)
            assert arr(b['net_kwh_el']).min() >= 0
            for p in ('sh', 'hw'):
                direct = arr(b[f'hp_{p}_direct_kwh_th'])
                out = arr(b[f'{p}_tank_to_demand_kwh_th']) if b[f'{p}_tank_to_demand_kwh_th'] else 0.0
                inn = arr(b[f'hp_{p}_to_tank_kwh_th']) if b[f'hp_{p}_to_tank_kwh_th'] else 0.0
                assert np.abs(arr(b[f'{p}_demand_kwh_th']) - direct - out).max() < 1e-5, (name, role, p)
                assert (np.abs(arr(b[f'hp_{p}_kwh_el']) * arr(b[f'cop_{p}']) - direct - inn) <= 2e-3 + 1e-3 * (direct + inn)).all(), (name, role, p)
                comp = binfo[role]['components'][f'tank_{p}']
                if not comp['present']:
                    assert b[f'{p}_tank_soc'] is None
                    continue
                cap = comp['attributes']['capacity_kwh_th']['value']
                soc = arr(b[f'{p}_tank_soc'])
                assert ((soc >= -1e-9) & (soc <= 1 + 1e-9)).all()
                stored = soc * cap
                expect = inn - out - np.diff(np.r_[0.0, stored])           # the first step starts from an empty tank (initial soc 0)
                assert np.abs(arr(b[f'{p}_tank_loss_kwh_th']) - np.maximum(expect, 0)).max() < 2e-3, (name, role, p)
                assert expect.min() > -2e-3, 'a tank cannot create energy'


def test_reference_controllers_do_not_use_tanks_and_bau_is_identical(runs, manifest):
    for name in (REF, 'ALG-002_business_as_usual'):
        for b in runs[name]['buildings'].values():
            for p in ('sh', 'hw'):
                if b[f'hp_{p}_to_tank_kwh_th'] is not None:
                    assert max(b[f'hp_{p}_to_tank_kwh_th']) == 0 and max(b[f'{p}_tank_to_demand_kwh_th']) == 0
    assert runs['ALG-002_business_as_usual']['buildings'] == runs[REF]['buildings']
    assert {c['id']: c['identical_to'] for c in manifest['controllers']}['ALG-002_business_as_usual'] == REF


def test_full_comparisons_are_consistent(runs):
    year, window_file = load(FULL, 'comparisons_year.json'), load(FULL, 'comparisons.json')
    assert year['scope'] == {'kind': 'year', 'start_step': 0, 'n_steps': N} and window_file == year, 'in the full bundle comparisons.json has the year scope'
    assert year['comparisons'] == load(SAMPLE, 'comparisons_year.json')['comparisons'], 'annual comparisons must not depend on the export window'
    for name, c in year['comparisons'].items():
        assert abs(c['metrics']['import_kwh_el']['value'] - runs[name]['summary']['import_kwh_el']) < 1e-6


def test_no_absolute_carbon_in_the_full_year_bundle():
    parts = []
    for f in glob.glob(os.path.join(FULL, '**', '*.json'), recursive=True):
        d = json.load(open(f, encoding='utf-8'))
        if os.path.basename(f) == 'manifest.json':
            d = {k: v for k, v in d.items() if k != 'inputs'}
        parts.append(json.dumps(d))
    txt = ''.join(parts).lower()
    for bad in ('carbon_intensity', 'gco2', 'g/kwh', 'co2_g'):
        assert bad not in txt, bad
    assert not re.search(r'(?<![a-z])g_kwh', txt)
