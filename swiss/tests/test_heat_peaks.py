"""Heat peaks and load-duration curves (swiss/experiments/heat_peaks.py): checks on the committed result file and its bundle form."""
import json
import os

import numpy as np
import pytest

from swiss.experiments import heat_peaks as hp

ROOT = hp.ROOT


@pytest.fixture(scope='module')
def res():
    return json.load(open(hp.OUT))


def test_stats_function_on_a_known_series():
    s = hp.stats([0.0, 2.0, 4.0, 2.0, 0.0] * 40)
    assert s['annual_kwh'] == 320.0 and s['peak_kw'] == 4.0 and s['full_load_hours'] == pytest.approx(80.0)
    assert s['ldc']['kw'][0] == 4.0 and s['ldc']['rank_hour'][0] == 0 and s['ldc']['rank_hour'][-1] == 199


def test_full_load_hours_curves_and_district_sum(res):
    for cell, rows in res['cells'].items():
        for role, kinds in rows.items():
            for kind, st in kinds.items():
                assert st['full_load_hours'] == pytest.approx(st['annual_kwh'] / st['peak_kw'])
                kw = np.array(st['ldc']['kw'])
                assert np.all(np.diff(kw) <= 1e-9), (cell, role, kind)            # sorted from high to low
                assert kw[0] == pytest.approx(st['peak_kw'], abs=1e-3) and 100 <= len(kw) <= 200
        for kind in hp.KINDS:                                                       # district energy is the sum of the buildings; the coincident peak is below the sum of the peaks
            assert rows['district'][kind]['annual_kwh'] == pytest.approx(sum(rows[r][kind]['annual_kwh'] for r in res['roles']), rel=1e-9)
            assert rows['district'][kind]['peak_kw'] <= sum(rows[r][kind]['peak_kw'] for r in res['roles']) + 1e-6


def test_hist_annual_heat_matches_the_climate_summary(res):
    cool = json.load(open(os.path.join(ROOT, 'web', 'public', 'bundle', 'cooling.json')))
    cell = next(c for c in cool['cells'] if c['id'] == 'hist_none' and c['archetype'] == 'central')
    assert res['cells']['hist_none']['district']['heat_el']['annual_kwh'] == pytest.approx(cell['heating_kwh']['baseline'], rel=1e-4)
    assert round(res['cells']['hist_none']['district']['heat_el']['annual_kwh']) == 70388          # the district value quoted on the story page


def test_warming_lowers_the_peak_less_than_the_annual_heat(res):
    d0, d3 = (res['cells'][c]['district']['heat_el'] for c in ('hist_none', 'gwl3.0_none'))
    annual, peak = 1 - d3['annual_kwh'] / d0['annual_kwh'], 1 - d3['peak_kw'] / d0['peak_kw']
    assert 0 < peak < annual
    assert d3['full_load_hours'] < d0['full_load_hours']


def test_bundle_file_matches_the_result_file(res):
    from swiss.dashboard import build_bundle as bb, insights
    obj = insights.build_heat_peaks(bb)
    assert obj['cells']['gwl3.0_none']['district']['heat_el']['peak_kw'] == res['cells']['gwl3.0_none']['district']['heat_el']['peak_kw']
    d0, d3 = res['cells']['hist_none']['district']['heat_el'], res['cells']['gwl3.0_none']['district']['heat_el']
    assert obj['changes']['gwl3.0_none']['district']['heat_el']['peak_pct'] == pytest.approx(100 * (d3['peak_kw'] / d0['peak_kw'] - 1))


def test_pipeline_view_takes_names_and_licences_from_the_source_registry():
    import csv
    from swiss.dashboard import build_bundle as bb, insights
    reg = {r['dataset_id']: r for r in csv.DictReader(open(os.path.join(ROOT, insights.SRC_REG), encoding='utf-8', newline=''))}
    stages = insights.build_pipeline(bb)['stages']
    assert [s['id'] for s in stages] == ['raw', 'canonical', 'model', 'env', 'controllers', 'audit']
    for s in stages:
        for d in s['datasets']:
            assert d['name'] == reg[d['id']]['name'] and d['licence'] == reg[d['id']]['licence']
    assert all(d['licence'] for d in stages[0]['datasets'])


def test_cap_check_agrees_with_the_peaks(res):
    cap = json.load(open(os.path.join(hp.RES, 'heat_cap_check.json')))['cells']
    for cell, rows in cap.items():
        for role, v in rows.items():
            assert v['peak_kw'] == pytest.approx(res['cells'][cell][role]['heat_el']['peak_kw'], rel=1e-6)    # the same rollout
            assert v['peak_kw'] <= v['rated_kw'] + 1e-6
            if v['hours_at_cap']:
                assert v['peak_kw'] == pytest.approx(v['rated_kw'], rel=1e-3)
            assert v['hours_below_comfort_lower'] == 0
    assert cap['hist_none']['MFH-small']['hours_at_cap'] > cap['gwl3.0_none']['MFH-small']['hours_at_cap'] > 0


def test_hp_sizing_thermal_check_numbers():
    from swiss.experiments import hp_sizing_ratio as hs
    from swiss.models.heat_pump import cop
    d = json.load(open(hs.OUT))
    m = hs.model_side()
    for role, v in m.items():
        assert v['cap_a2_own_kw_th'] == pytest.approx(v['nominal_el_kw'] * cop(2.0, v['eta'], v['t_sup_c']))
        assert v['cap_design_kw_th'] < v['cap_a2_own_kw_th']                       # colder outdoor air, lower COP
        assert v['ratio_a2_own'] == pytest.approx(v['cap_a2_own_kw_th'] / v['peak_delivered_kw_th'])
    rows = [r for r in d['rows'] if 'excluded' not in r]
    assert len(rows) == 14 and all(r['thermal_ratio'] == pytest.approx(r['capacity_kw'] / r['peak_heat_kwh_th']) for r in rows)
    sl = next(r for r in d['rows'] if r['household'] == hs.SFH_LOW)
    assert m['SFH-low']['cap_a2_w35_kw_th'] / sl['capacity_kw'] > 1.0              # model nameplate above the real one
