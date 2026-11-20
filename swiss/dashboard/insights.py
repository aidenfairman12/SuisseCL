"""Extra dashboard content: heat_peaks.json (peak heat demand and load-duration curves) and pipeline.json (data pipeline for the Data & methods page).

Both are built from committed files only: swiss/experiments/heat_peak_results/heat_peaks.json (written by swiss/experiments/heat_peaks.py)
and docs/data/data_source_registry.csv. Names and licences are copied from the registry rows, never typed here.
"""
HP = 'swiss/experiments/heat_peak_results/heat_peaks.json'
CAP = 'swiss/experiments/heat_peak_results/heat_cap_check.json'
SRC_REG = 'docs/data/data_source_registry.csv'
WARM = ('gwl2.0_none', 'gwl3.0_none')
LABELS = {'hist_none': 'Observed 2023', 'gwl2.0_none': '+2.0 °C typical year', 'gwl3.0_none': '+3.0 °C typical year'}

# Pipeline stages. The registry ids below are references; the names, publishers and licences shown come from the registry.
STAGES = [
    {'id': 'raw', 'title': 'Raw sources', 'text': 'Open data as downloaded, with the licence recorded in the source registry.',
     'datasets': ['SRC-001', 'SRC-002', 'SRC-004', 'SRC-009', 'SRC-011', 'SRC-012', 'SRC-014']},
    {'id': 'canonical', 'title': 'Canonical datasets', 'text': 'Cleaned hourly series for six buildings, weather, tariff, carbon intensity and PV, each with a quality-control report.',
     'datasets': ['DER-005', 'DER-007', 'DER-008', 'DER-011', 'DER-012', 'DER-023']},
    {'id': 'model', 'title': 'Building and heat-pump model', 'text': 'Heat demand is calculated from heat-pump electricity and outdoor temperature; a simple RC model gives indoor temperature.',
     'datasets': ['DER-009', 'DER-015']},
    {'id': 'env', 'title': 'CityLearn environment', 'text': 'Schema and building files that CityLearn 3.3.0 runs, extended step by step with PV, a battery, the RC model and climate cells.',
     'datasets': ['DER-010', 'DER-013', 'DER-014', 'DER-016', 'DER-027']},
    {'id': 'controllers', 'title': 'Controllers', 'text': 'Thermostat reference, hand-set rules, a planner (MPC), learning controllers and the exact optimum, judged on the same weeks.', 'datasets': []},
    {'id': 'audit', 'title': 'Audit bundle and dashboard', 'text': 'Every number is traced to its source in a provenance bundle that this site reads; a lint checks that the site and the bundle agree.', 'datasets': []},
]


def build_pipeline(bb):
    rows = {r['dataset_id']: r for r in bb.read_csv_dicts(SRC_REG)}
    stages = []
    for s in STAGES:
        ds = []
        for i in s['datasets']:
            r = rows[i]
            ds.append({'id': i, 'name': r['name'], 'publisher': r['publisher'] if i.startswith('SRC') else '', 'licence': r['licence'], 'kind': 'source' if i.startswith('SRC') else 'derived'})
        stages.append({**s, 'datasets': ds})
    return {'stages': stages, 'source': SRC_REG}


def _change(a, b):
    return 100.0 * (b - a) / a


def build_heat_peaks(bb):
    d = bb.read_json(HP)
    roles = d['roles'] + ['district']
    changes = {}
    for warm in WARM:
        changes[warm] = {r: {k: {'annual_pct': _change(d['cells']['hist_none'][r][k]['annual_kwh'], d['cells'][warm][r][k]['annual_kwh']),
                                 'peak_pct': _change(d['cells']['hist_none'][r][k]['peak_kw'], d['cells'][warm][r][k]['peak_kw'])} for k in ('heat_el', 'heat_th')} for r in roles}
    cap = bb.read_json(CAP)['cells']
    capped = {r: {c: {k: cap[c][r][k] for k in ('rated_kw', 'hours_at_cap', 'kh_below_setpoint', 'hours_below_comfort_lower')} for c in cap} for r in d['roles'] if cap['gwl3.0_none'][r]['hours_at_cap']}
    from swiss.experiments import hp_sizing_ratio as hs
    for f in ('swiss/datasets/climate/hist_none/schema.json', 'swiss/datasets/climate/hist_none/weather.csv', 'swiss/experiments/heat_peak_results/hp_sizing_ratio.json', *(f'data/canonical/thermal/{r}_2023_thermal_hourly.csv' for r in hs.ROLES)):
        bb._read_files.add(f)
    m, real = hs.model_side(), bb.read_json('swiss/experiments/heat_peak_results/hp_sizing_ratio.json')
    sl = next(x for x in real['rows'] if x['household'] == hs.SFH_LOW)
    capacity_check = {'sfh_low_model_over_real': m['SFH-low']['cap_a2_w35_kw_th'] / sl['capacity_kw'], 'sfh_low_real_kw_th': sl['capacity_kw'], 'sfh_low_model_kw_th': m['SFH-low']['cap_a2_w35_kw_th'],
                      'sfh_low_derived_peak_kw_th': m['SFH-low']['peak_demand_derived_kw_th'], 'sfh_low_delivered_peak_kw_th': m['SFH-low']['peak_delivered_kw_th'], 'source': 'swiss/experiments/hp_sizing_ratio.py'}
    return {'capacity_check': capacity_check, 'capped': capped, 'roles': d['roles'], 'cells': d['cells'], 'cell_order': ['hist_none', *WARM], 'labels': LABELS, 'changes': changes, 'n_points': d['n_points'],
            'controller': d['controller'], 'source': d['source'], 'sources': [HP, CAP]}
