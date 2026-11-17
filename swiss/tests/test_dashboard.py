"""Tests for the audit dashboard (docs/dashboard/dashboard_implementation_plan.md §8).

Run: cl/bin/python -m pytest swiss/tests/test_dashboard.py
"""
import csv
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from swiss.dashboard import build_bundle as bb  # noqa: E402
from swiss.dashboard import lint  # noqa: E402
from swiss.dashboard.bundle_io import read_bundle_file  # noqa: E402
from swiss.dashboard.parse_registries import (extract_ids, normalise_classification, parse_csv_registry,  # noqa: E402
                                              parse_md_registry, parse_md_tables)

BUNDLE = os.path.join(ROOT, 'web', 'public', 'bundle')


def p(rel):
    return os.path.join(ROOT, rel)


@pytest.fixture(scope='module')
def prov():
    return read_bundle_file(os.path.join(BUNDLE, 'provenance.json'))['nodes']


@pytest.fixture(scope='module')
def meta():
    return read_bundle_file(os.path.join(BUNDLE, 'meta.json'))


# ---------------------------------------------------------------- parsers

@pytest.mark.parametrize('path,id_col,n', [
    ('docs/data/transformation_log.md', 'ID', 11),
    ('docs/decisions/issues_and_risks.md', 'ID', 45),      # 45 rows incl. update rows
    ('docs/decisions/decision_log.md', 'ID', 36),
    ('docs/decisions/assumptions_log.md', 'ID', 10),
    ('docs/models/model_registry.md', 'ID', 2),
    ('docs/algorithms/algorithm_registry.md', 'ID', 4),
    ('docs/experiments/validation_reports/validation_phase_a.md', 'ID', 9),
])
def test_md_row_counts(path, id_col, n):
    assert len(parse_md_registry(p(path), id_col)) == n


def test_md_cell_with_escaped_pipe_does_not_split_row():
    rows = parse_md_registry(p('docs/algorithms/reward_function_documentation.md'), id_col='Term')
    ramp = next(r for r in rows if r['cells']['Term'] == 'ramp')
    assert ramp['cells']['Definition'].startswith('|district net(t)')
    assert not ramp['_parse_warnings']


def test_md_parser_pipe_in_code_span_and_short_row():
    t = parse_md_tables('| ID | A | B |\n|---|---|---|\n| X-1 | `a|b` | c |\n| X-2 | only |\n')[0]
    assert t['rows'][0]['cells'] == {'ID': 'X-1', 'A': '`a|b`', 'B': 'c'}
    assert t['rows'][1]['cells']['B'] == '' and t['rows'][1]['_parse_warnings']


@pytest.mark.parametrize('path,n', [
    ('docs/data/data_source_registry.csv', 22),
    ('docs/models/parameter_registry.csv', 31),
    ('docs/experiments/experiment_registry.csv', 12),
])
def test_csv_row_counts_and_alignment(path, n):
    hdr, rows = parse_csv_registry(p(path), anchor_col='classification')
    assert len(rows) == n
    assert all(len(r['cells']) == len(hdr) for r in rows)


def test_csv_repairs_unquoted_commas():
    hdr, rows = parse_csv_registry(p('docs/data/data_source_registry.csv'), anchor_col='classification')
    by = {r['cells']['dataset_id']: r for r in rows}
    assert by['SRC-003']['cells']['classification'] == 'modeled'
    assert '9,747,041 B' in by['SRC-003']['cells']['processing_status']
    assert by['SRC-011']['cells']['name'].endswith('CH, FR, DE, AT, IT')
    assert by['DER-003']['cells']['classification'] == 'derived'      # aligned on the classification column
    assert by['DER-003']['_parse_warnings']
    hdr, rows = parse_csv_registry(p('docs/models/parameter_registry.csv'))
    hydro = next(r for r in rows if r['cells']['name'].startswith('EF Hydropower'))
    assert hydro['cells']['value'] == '24' and hydro['cells']['unit'] == 'gCO2eq/kWh'


def test_extract_ids():
    assert extract_ids('A-006..A-009') == ['A-006', 'A-007', 'A-008', 'A-009']
    assert extract_ids('accepted (D-014/a-e, D-016)')[:7] == ['D-014', 'D-014a', 'D-014b', 'D-014c', 'D-014d', 'D-014e', 'D-016']
    assert extract_ids('D-013/D-013a/D-013b') == ['D-013', 'D-013a', 'D-013b']
    assert extract_ids('EXP-001..006') == [f'EXP-00{i}' for i in range(1, 7)]
    assert extract_ids('tasks A4/A5, v2 API, EL-0010') == []          # plan task names and versions are not IDs
    assert extract_ids('see V1 and V8; R-001') == ['V1', 'V8', 'R-001']


def test_classification_normalisation():
    assert normalise_classification('MODELED (first-order flow tracing)') == 'modeled'
    assert normalise_classification('derived/modeled/synthetic mix (see columns.json)') == 'mixed'
    assert normalise_classification('measured (HP, other) + synthetic apartments') == 'mixed'
    assert normalise_classification('measured') == 'measured'


# ---------------------------------------------------------------- graph and lint (§8.1-8.3, §8.5)

def test_lint_passes_and_bundle_is_fresh():
    errs, _ = lint.lint(check_fresh_flag=True)
    assert errs == []


def test_prose_digit_check_catches_invented_numbers():
    assert lint.prose_digits('Mean {qc_carbon.mean_consumption_g_kwh:.1f} g/kWh (D-013, A-006..A-009)', []) == []
    assert lint.prose_digits('Mean 58.1 g/kWh', []) == ['58.1']


def test_every_registry_row_is_a_node(prov):
    ids = lint.registry_ids()
    assert len(ids) >= 22 + 12 + 11 + 2 + 27 + 10 + 33 + 4 + 9 + 1
    assert ids <= set(prov)


def test_issue_update_rows_are_merged(prov):
    assert len(prov['ISS-013']['history']) == 3
    assert prov['ISS-013']['open'] is False
    assert prov['ISS-033']['open'] is True


def test_lineage_reaches_source_or_decision(prov):
    assert 'SRC-011' in prov['series:carbon_intensity']['lineage']
    assert 'SRC-004' in prov['series:outdoor_temperature']['lineage']
    assert 'SRC-001' in prov['kpi:cost_chf_excl_vat']['lineage']
    assert prov['card:tanks']['lineage'][-1] == 'D-017a'


def test_code_excerpt_embedded_with_commit(prov):
    c = prov['card:controller_tariff_map']['code'][0]
    assert c['source'].startswith('def tariff_map(rate):') and c['commit']


def test_meta_snapshot_integrity(meta):
    assert meta['manifest']['verified'] is True and meta['manifest']['files_listed'] > 0
    assert set(meta['git']) >= {'commit', 'dirty'}
    for f in ('docs/decisions/decision_log.md', 'swiss/dashboard/ui_map.yaml', 'data/canonical/MANIFEST.sha256'):
        assert f in meta['inputs']


def test_check_fresh_detects_a_changed_input(meta):
    stale = dict(meta, inputs=dict(meta['inputs']))
    stale['inputs']['docs/decisions/decision_log.md'] = '0' * 64
    assert any('decision_log.md' in e for e in lint.check_fresh(stale))


# ---------------------------------------------------------------- numbers equal the source files (§8.4)

def _number(prov, key, label):
    return next(n['value'] for n in prov[key]['numbers'] if n['label'] == label)


def test_values_match_sources(prov):
    qc_carbon = json.load(open(p('docs/data/data_quality_reports/qc_carbon_2023.json')))
    qc_tariff = json.load(open(p('docs/data/data_quality_reports/qc_tariff_2023.json')))
    manifest = json.load(open(p('swiss/datasets/swiss_district_2023/build_manifest.json')))
    scales = json.load(open(p('swiss/experiments/results/reward_scales.json')))
    assert _number(prov, 'series:carbon_intensity', 'Mean (consumption-based)') == '58.1'
    assert float(_number(prov, 'series:carbon_intensity', 'Mean (consumption-based)')) == round(qc_carbon['mean_consumption_g_kwh'], 1)
    assert _number(prov, 'series:price', 'Low tariff') == str(qc_tariff['distinct_total_rp'][0]) == '15.05'
    assert _number(prov, 'series:price', 'High tariff') == '19.05'
    assert float(_number(prov, 'card:tanks', 'Building_1 heating tank')) == manifest['Building_1']['heating_tank_kwh_th']
    assert float(_number(prov, 'card:reward', 'Cost scale')) == pytest.approx(scales['cost'], abs=1e-4)
    eta = {n['fields']['name']: float(n['fields']['value']) for n in prov.values() if n['kind'] == 'parameter' and n['fields']['parameter'] in ('eta_sh', 'eta_dhw')}
    tp = json.load(open(p('data/canonical/thermal/thermal_params.json')))
    assert eta['eta Carnot fraction space heating SFH-low'] == round(tp['SFH-low']['eta_sh'], 4)
    with open(p('swiss/experiments/results/baselines_2023.csv')) as f:
        rows = {r['controller']: r for r in csv.DictReader(f)}
    assert round(float(rows['ALG-003_basic_rbc']['cost_chf_excl_vat']), 2) == 35930.58


# ---------------------------------------------------------------- input series (milestone 3)

@pytest.fixture(scope='module')
def series():
    return read_bundle_file(os.path.join(BUNDLE, 'series_inputs.json'))


def test_series_match_canonical_files(series):
    import numpy as np
    import pandas as pd
    assert series['n'] == 8760 and series['start_utc'] == '2022-12-31T23:00:00Z'
    c = pd.read_csv(p('data/canonical/carbon_ch_2023_hourly.csv'))
    v = np.array([np.nan if x is None else x for x in series['series']['carbon']['values']])
    assert np.nanmean(v) == pytest.approx(c.ci_consumption_lifecycle_g_per_kwh.mean(), abs=0.01)
    assert int(np.isnan(v).sum()) == 4                                   # missing hours stay missing (not filled)
    assert sum(series['flags']['neighbour_intensity_fallback_flag']['values']) == 120
    assert sum(series['flags']['gap_interpolated_flag']['values']) == 4
    assert sorted(set(series['series']['price']['values'])) == [15.05, 19.05]
    assert sum(series['buildings']['SFH-low']['gap_filled_flag']) == 24
    w = pd.read_csv(p('data/canonical/weather_klo_2023_hourly.csv'))
    assert series['series']['temp_c']['values'][:24] == [round(x, 1) for x in w.temp_c[:24]]
    apt = next(x for x in series['buildings']['MFH-large']['components'] if x['key'] == 'apartments')
    assert apt['classification'] == 'synthetic'
    assert series['local_hour'][0] == 0 and series['utc_offset_h'][0] == 1   # 2022-12-31 23:00 UTC = 00:00 CET


def test_selection_figure_matches_selection_file():
    f = read_bundle_file(os.path.join(BUNDLE, 'figures.json'))
    assert f['building_selection']['pool_sizes'] == {'sfh': 26, 'mfh': 59}
    with open(p('data/interim/selected_buildings.csv')) as fh:
        ids = [int(r['id']) for r in csv.DictReader(fh)]
    assert [x['id'] for x in f['building_selection']['picks']] == ids
    rows = {r['shift_h']: r for r in f['klo_vs_heapo_8jb']['rows']}
    assert rows[-1]['max_abs_diff_c'] == 0.0                            # KLO == HEAPO 8jB after the D-009 relabel


# ---------------------------------------------------------------- model figures (milestone 4)

def test_model_figures_match_sources():
    import numpy as np
    from swiss.models.heat_pump import cop
    f = read_bundle_file(os.path.join(BUNDLE, 'figures.json'))
    tp = json.load(open(p('data/canonical/thermal/thermal_params.json')))
    c = f['cop_curves']
    i = c['t_out_c'].index(0.0)
    assert c['buildings']['MFH-large']['cop_sh'][i] == round(float(cop(0.0, tp['MFH-large']['eta_sh'], 45.0)), 3)
    schema = json.load(open(p('swiss/datasets/swiss_district_2023/schema.json')))
    for r in f['hp_sizing']['rows']:
        assert r['nominal_sh_kw'] == schema['buildings'][r['building']]['heating_device']['attributes']['nominal_power']
        assert r['nominal_sh_kw'] == pytest.approx(round(r['peak_sh_elec_kwh'] * 1.1, 4))       # TR-009 rule as coded
    tv = f['tanks']['variants']
    for a, b in zip(tv['swiss_district_2023'], tv['swiss_sens_tank2']):
        assert b['heating_tank_kwh_th'] == pytest.approx(2 * a['heating_tank_kwh_th'], abs=2e-3)
    assert {x['tank_efficiency'] for x in tv['swiss_sens_eff0.99']} == {0.99}
    cd = f['carbon_daily']
    assert sum(cd['hours']) == 8760
    can = __import__('pandas').read_csv(p('data/canonical/carbon_ch_2023_hourly.csv'))
    assert np.nansum([x for x in cd['mwh']['import_france_mwh'] if x is not None]) == pytest.approx(can.import_france_mwh.sum(), rel=1e-6)
    env = f['env_interface']
    assert set(env['actions_active']) == {'heating_storage', 'dhw_storage'}
    assert env['v1_max_abs_err_kwh'] < 1e-5


# ---------------------------------------------------------------- run traces (milestone 5, plan §6)

TRACE_DIR = p('swiss/experiments/results/traces')


def _results():
    import pandas as pd
    return pd.read_csv(p('swiss/experiments/results/baselines_2023.csv')).set_index('controller')


@pytest.mark.parametrize('name', ['ALG-001_zero_action', 'ALG-002_business_as_usual', 'ALG-003_basic_rbc',
                                  'ALG-004_hour_rbc_tariff_r0.05', 'ALG-004_hour_rbc_tariff_r0.10', 'ALG-004_hour_rbc_tariff_r0.20'])
def test_trace_sums_reproduce_aggregates(name):
    import numpy as np
    import pandas as pd
    t = pd.read_csv(os.path.join(TRACE_DIR, f'{name}.csv.gz'))
    r = _results().loc[name]
    assert len(t) == r.steps
    nets = [c for c in t.columns if c.startswith('b') and c.endswith('_net_kwh')]
    assert len(nets) == 6
    imp = sum(np.maximum(t[c].to_numpy(), 0).sum() for c in nets)
    assert imp == pytest.approx(r.district_import_kwh, rel=1e-9)
    assert t.district_net_kwh.max() == pytest.approx(r.district_peak_kw, rel=1e-9)
    assert t.reward.sum() == pytest.approx(r.reward_return, rel=1e-9)
    for k in ('cost', 'peak', 'ramp', 'carbon'):
        assert t[f'term_{k}'].sum() == pytest.approx(r[f'term_{k}_sum'], rel=1e-9)
    cost = sum((np.maximum(t[c].to_numpy(), 0) * t.price.to_numpy()).sum() for c in nets)
    assert cost == pytest.approx(r.cost_chf_excl_vat, rel=1e-9)
    assert t.timestamp_utc.iloc[0] == '2022-12-31 23:00:00+00:00'


def test_traces_do_not_change_rollout():
    """Same controller with and without --traces gives the same results row (plan §6: no behaviour change)."""
    from swiss.experiments import run_baselines as rb
    scales = json.load(open(p('swiss/experiments/results/reward_scales.json')))
    name = 'ALG-004_hour_rbc_tariff_r0.10'
    with_trace, _, tr = rb.rollout(name, rb.CONTROLLERS[name], scales, trace=True)
    committed = _results().loc[name]
    for k, v in with_trace.items():
        if k == 'controller':
            continue
        c = committed[k]
        if isinstance(v, float) and v != v:
            assert c != c, k
        else:
            assert v == pytest.approx(float(c), rel=1e-9, abs=1e-9), k
    assert len(tr) == committed.steps


# ---------------------------------------------------------------- results bundle and system map (milestone 6)

def test_results_bundle_equals_results_files():
    import pandas as pd
    r = read_bundle_file(os.path.join(BUNDLE, 'results.json'))
    csv_ = pd.read_csv(p('swiss/experiments/results/baselines_2023.csv'))
    by = {x['controller']: x for x in r['rows']}
    for _, row in csv_.iterrows():
        for c in csv_.columns:
            v = row[c]
            if isinstance(v, float) and v != v:
                assert by[row.controller][c] is None
            else:
                assert by[row.controller][c] == v
    assert round(by['ALG-003_basic_rbc']['cost_chf_excl_vat'], 2) == 35930.58
    assert r['experiment_of']['ALG-004_hour_rbc_tariff_r0.10'] == ['EXP-011']
    assert r['traces']['ALG-002_business_as_usual']['same_as'] == 'ALG-001_zero_action'
    sens = pd.read_csv(p('swiss/experiments/results/sensitivity_2023.csv'))
    assert len(r['sensitivity']) == len(sens)
    assert max(c['rel_diff'] for v in r['trace_checks'].values() for c in v.values()) < 1e-9


def test_system_map_boxes_have_cards(prov):
    import re
    tsx = open(p('web/src/components/overview/flow-diagram.tsx'), encoding='utf-8').read()
    boxes = re.findall(r'\{ ui: "([^"]+)"', tsx)
    assert len(boxes) >= 12
    for b in boxes:
        assert b in prov
    # walkthrough targets (plan §8.8): one click from the map opens these cards with the audit content on them
    carbon = prov['series:carbon_intensity']
    assert 'epfl_table' in carbon['figures'] and any(c['symbol'] == 'intensity' for c in carbon['code'])
    assert 'cop_curves' in prov['card:cop_model']['figures']
    assert prov['card:tanks']['lineage'][-1] == 'D-017a' and 'tank_sizes' in prov['card:tanks']['figures']


def test_district_view_data_matches_sources():
    f = read_bundle_file(os.path.join(BUNDLE, 'figures.json'))['district']
    man = json.load(open(p('swiss/datasets/swiss_district_2023/build_manifest.json')))
    assert [b['building'] for b in f['buildings']] == list(man)
    for b in f['buildings']:
        m = man[b['building']]
        assert (b['role'], b['heating_tank_kwh_th'], b['dhw_tank_kwh_th'], b['hp_sh_nominal_kw']) == \
               (m['role'], m['heating_tank_kwh_th'], m['dhw_tank_kwh_th'], m['hp_sh_nominal_kw'])
    assert [b['units'] for b in f['buildings'] if b['type'] == 'MFH'] == [5, 14, 24]
    t = read_bundle_file(os.path.join(BUNDLE, 'trace_ALG-003_basic_rbc.json'))['arrays']
    assert all(f'b{i}_hp_kwh_el' in t for i in range(1, 7))


def test_dirty_check_ignores_bundle_even_on_first_line():
    assert bb.dirty_lines(' M web/public/bundle/figures.json\n M web/public/bundle/meta.json\n') == []
    assert bb.dirty_lines('?? web/public/bundle/meta.json\n M swiss/dashboard/lint.py\n') == [' M swiss/dashboard/lint.py']


# ---------------------------------------------------------------- web UI sources are linted against ui_map (P5)

def test_web_sources_are_scanned_and_figures_resolve():
    import re
    srcs = dict(lint.web_sources())
    assert any(k.endswith('flow-diagram.tsx') for k in srcs) and any(k.endswith('scene.tsx') for k in srcs)
    keys = set()
    for text in srcs.values():
        keys |= set(re.findall(r'["\']((?:series|card|kpi|panel):[a-z0-9_]+)["\']', text))
    assert {'card:district', 'card:tanks', 'series:carbon_intensity'} <= keys
    registry = open(lint.REGISTRY, encoding='utf-8').read()
    figs = set(re.findall(r'^  (\w+): \{ title:', registry, re.M))
    assert len(figs) >= 22 and 'cop_curves' in figs
    import yaml
    ui = yaml.safe_load(open(bb.UI_MAP, encoding='utf-8'))
    used = {f for k, e in ui.items() if not k.startswith('_') for f in (e.get('figures') or [])}
    assert used <= figs


def test_bundle_files_are_plain_json():
    for name in ('meta', 'provenance', 'figures', 'results', 'series_inputs'):
        with open(os.path.join(BUNDLE, f'{name}.json'), encoding='utf-8') as f:
            assert isinstance(json.load(f), dict)


# ---------------------------------------------------------------- story page content (plain-language layer)

@pytest.fixture(scope='module')
def story():
    return read_bundle_file(os.path.join(BUNDLE, 'story.json'))


def test_story_numbers_equal_source_files(story):
    import pandas as pd
    r = pd.read_csv(p('swiss/experiments/results/baselines_2023.csv')).set_index('controller')
    s = pd.read_csv(p('swiss/experiments/results/sensitivity_2023.csv')).set_index(['variant', 'controller'])
    ref, night = r.loc['ALG-001_zero_action'], r.loc['ALG-003_basic_rbc']
    pct = lambda c: (night[c] - ref[c]) / abs(ref[c]) * 100
    v = story['story']['findings']['verdict']
    assert f"{-pct('district_peak_kw'):.1f} %" in v and f"{pct('district_import_kwh'):.1f} %" in v and f"rises by {pct('cost_chf_excl_vat'):.1f} %" in v
    shift = -s.loc[('reference', 'basic_rbc'), 'high_tariff_share_pts_vs_zero']
    assert f'{shift:.1f} percentage points' in v and '15.05 against 19.05 Rp/kWh' in v
    tiles = {t['node']: t for t in story['story']['findings']['tiles']}
    assert tiles['kpi:cost_chf_excl_vat']['value'] == pytest.approx(night.cost_chf_excl_vat)
    assert tiles['kpi:district_peak_kw']['vs_none_pct'] == pytest.approx(pct('district_peak_kw'))
    assert tiles['kpi:district_import_kwh']['reference'] == pytest.approx(ref.district_import_kwh)
    tariff = r[r.index.str.startswith('ALG-004')]
    lo, hi = ((tariff.cost_chf_excl_vat - ref.cost_chf_excl_vat) / ref.cost_chf_excl_vat * 100).agg(['min', 'max'])
    assert f'{lo:+.1f} to {hi:+.1f} %' in story['story']['findings']['rules_line']


def test_story_validation_count_matches_nodes(story, prov):
    checks = [n for n in prov.values() if n['kind'] == 'validation_check']
    passed = sum(1 for n in checks if n['passed'])
    assert f'{passed} of {len(checks)} validation checks pass' in story['story']['trust']['validation']
    assert passed < len(checks)            # V7 (partial) and V9 (plausibility only) must not be counted as passes


def test_story_phases_come_from_master_plan(story):
    text = open(p('docs/master_plan.md'), encoding='utf-8').read()
    assert [x['letter'] for x in story['phases']] == ['A', 'B', 'C']
    for ph in story['story']['next']['phases']:
        assert ph['objective'] in text
    assert 'Phase A of 3' in story['story']['hero']['status']


def test_winter_day_is_the_coldest_weekday():
    import pandas as pd
    w = pd.read_csv(p('data/canonical/weather_klo_2023_hourly.csv'))
    t = pd.Series(w.temp_c.to_numpy(), index=pd.to_datetime(w.timestamp_utc, utc=True).dt.tz_convert('Europe/Zurich'))
    daily = t.groupby(t.index.date).agg(['mean', 'count'])
    daily = daily[(daily['count'] == 24) & (pd.to_datetime(daily.index).weekday < 5) & (daily.index < pd.Timestamp('2023-12-31').date())]
    story = read_bundle_file(os.path.join(BUNDLE, 'story.json'))
    assert story['derived']['day']['date'] == str(daily['mean'].idxmin())


def test_every_controller_and_building_has_a_display_name(story):
    import pandas as pd
    for c in pd.read_csv(p('swiss/experiments/results/baselines_2023.csv')).controller:
        assert story['controllers'][c]['display_name']
    assert set(story['buildings']) == {'SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large'}
    assert len(story['glossary']) >= 15


def test_prose_rules_catch_violations():
    from swiss.dashboard import story as sm
    ui = {'_settings': {'prose_allowed_tokens': ['2023']}, '_glossary': [{'id': 'peak', 'term': 'Peak', 'definition': 'ok'}],
          '_story': {'hero': {'a': 'costs 58 g in 2023', 'b': 'see D-017a', 'c': 'the [[peak|peak]] and [[x|nope]]', 'd': 'fine {derived.hours:,}'}},
          '_controllers': {'X': {'display_name': ''}}}
    errs = sm.check_prose(ui, lint.prose_digits)
    assert any('"58"' in e for e in errs) and not any('2023' in e for e in errs)
    assert any('registry ID' in e for e in errs) and any('unknown glossary term "nope"' in e for e in errs)
    assert any('no display_name' in e for e in errs) and not any('hero.d' in e for e in errs)


def test_story_prose_has_no_registry_ids(story):
    import re
    from swiss.dashboard.story import ID_PATTERN
    def walk(o):
        if isinstance(o, str): yield o
        elif isinstance(o, list):
            for x in o: yield from walk(x)
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ('node', 'id', 'letter', 'controller'): yield from walk(v)
    for key in ('story', 'glossary', 'pages', 'buildings'):
        for text in walk(story[key]):
            assert not ID_PATTERN.search(text), text
    assert not any(ID_PATTERN.search(c['display_name']) for c in story['controllers'].values())


# ---------------------------------------------------------------- plain building names and relative carbon (outside the carbon card)

def test_carbon_rank_matches_independent_recomputation(series):
    """Percent of valid hours with a lower intensity (mid-rank for ties, clamped 1..99), recomputed from the canonical CSV
    with sorted arrays and searchsorted instead of the pandas rank used by the builder."""
    import numpy as np
    import pandas as pd
    v = pd.read_csv(p('data/canonical/carbon_ch_2023_hourly.csv')).ci_consumption_lifecycle_g_per_kwh.to_numpy(float)
    ok = ~np.isnan(v)
    srt = np.sort(v[ok])
    less, upto = np.searchsorted(srt, v[ok], side='left'), np.searchsorted(srt, v[ok], side='right')
    expect = np.clip(np.rint((less + (upto - less) / 2.0) / ok.sum() * 100.0), 1, 99).astype(int)
    got = series['carbon_rank']['values']
    assert len(got) == 8760 == len(v)
    assert [i for i, x in enumerate(got) if x is None] == list(np.flatnonzero(~ok))        # the 4 missing hours get no rank
    assert np.array_equal(np.array([x for x in got if x is not None]), expect)
    assert series['carbon_rank']['year'] == 2023
    # the ranking is monotone in the intensity and spans the whole scale
    order = np.argsort(v[ok], kind='stable')
    ranked = np.array([x for x in got if x is not None])[order]
    assert (np.diff(ranked) >= 0).all() and ranked[0] == 1 and ranked[-1] == 99
    assert series['series']['carbon']['relative_only'] and series['series']['carbon_domestic']['relative_only']


def test_carbon_card_shows_the_proxy_range_and_epfl_level_from_the_qc_files(prov):
    qc = json.load(open(p('docs/data/data_quality_reports/qc_carbon_2023.json')))
    lo, hi = qc['proxy_sensitivity_mean_g_kwh']['proxies_x0.5'], qc['proxy_sensitivity_mean_g_kwh']['proxies_x1.5']
    n = prov['series:carbon_intensity']
    assert f'{lo:.0f}' in n['summary'] and f'{hi:.0f}' in n['summary']
    assert any(f'{lo:.0f}' in c and f'{hi:.0f}' in c for c in n['caveats'])
    assert any('EPFL' in c and '%' in c for c in n['caveats'])
    for k in ('kpi:term_carbon_sum', 'kpi:kpi_carbon_emissions_total'):
        assert prov[k]['fields']['relative_only'] is True


def test_carbon_and_role_guards_catch_violations():
    bad = 'const a = `${role} space heating`; <b>{role}</b>; { text: q.role }; data: roles, x'
    assert len(lint.ui_source_violations('web/src/components/charts/x.tsx', bad)) >= 4
    assert lint.ui_source_violations('web/src/components/charts/x.tsx', 'name: "SFH-low"')
    assert lint.ui_source_violations('web/src/components/charts/util.ts', 'ROLE_COL = { "SFH-low": 1 }') == []
    assert lint.ui_source_violations('web/src/components/charts/x.tsx', 'key={role} data: roles.map(label) label(role)') == []
    assert lint.ui_source_violations('web/src/components/district/district-view.tsx', '`${S.carbon.values[i]} g CO₂ per kWh`')
    assert lint.ui_source_violations('web/src/components/results/x.tsx', 'unit: "gCO2eq/kWh"')
    assert lint.ui_source_violations('web/src/components/charts/figures-inputs.tsx', 'name: "g/kWh", S.carbon.values') == []
    ui = {'kpi:kpi_carbon_emissions_total': {'summary': 'ok', 'fields': {}}, 'kpi:cost': {'summary': 'Costs 5 g/kWh'}}
    prov_ = {'nodes': {'series:carbon_intensity': {'summary': 'Mean 58 g/kWh', 'caveats': []}}}
    qc = {'proxy_sensitivity_mean_g_kwh': {'proxies_x0.5': 46.8, 'proxies_x1.5': 69.4}}
    errs = lint.carbon_text_violations(ui, prov_, {'x': 'about 60 g/kWh'}, qc)
    assert any('relative_only' in e for e in errs) and any('kpi:cost' in e for e in errs) and any('story.json' in e for e in errs)
    assert any('proxy range' in e for e in errs) and any('EPFL' in e for e in errs)


def test_every_role_in_the_bundle_has_a_plain_name_and_group(story, series):
    assert set(series['buildings']) <= set(story['buildings'])
    assert {r.split('-')[0] for r in series['buildings']} <= set(story['building_groups'])
    lo, hi = story['carbon_relative']['typical_band_pct']
    assert 0 < lo < hi < 100
    for k in ('cleaner', 'dirtier', 'typical', 'missing', 'sub'):
        assert story['carbon_relative'][k]
    assert '{pct}' in story['carbon_relative']['cleaner'] and '{pct}' in story['carbon_relative']['dirtier']
