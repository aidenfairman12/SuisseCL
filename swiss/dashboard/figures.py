"""Series and precomputed figure data for the audit dashboard (read-only; pandas/numpy only).

build_inputs(rd)  -> (series bundle dict, figure-data dict)
`rd` is build_bundle's CSV reader (it records every file read for the freshness check).
Every array is taken from the canonical files without modification except rounding; nothing is filled here.
"""
import numpy as np
import pandas as pd

ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']


def arr(s, nd):
    """Rounded list; NaN -> None (JSON null) so missing hours stay visible as gaps."""
    a = np.round(np.asarray(s, dtype=float), nd)
    return [None if np.isnan(x) else (int(x) if nd == 0 else float(x)) for x in a]


def flags(s):
    return [int(x) for x in np.asarray(s).astype(int)]


def carbon_rank(values):
    """Percentile rank of every hour inside the year's own series: the share (0-100, integer) of valid hours with a LOWER
    intensity, mid-rank for ties (pandas average rank minus one half). NaN hours stay None. Clamped to 1..99 so the
    wording never claims "100 % of hours". The absolute level of the modeled series is not reliable (about 62 % of the
    EPFL reference, and it moves with the proxy emission factors); the ordering of the hours is (hourly r about 0.98)."""
    v = pd.Series(np.asarray(values, dtype=float))
    r = (v.rank(method='average') - 0.5) / v.notna().sum() * 100.0
    return [None if np.isnan(x) else int(min(99, max(1, round(x)))) for x in r]


def build_inputs(rd):
    w = rd('data/canonical/weather_klo_2023_hourly.csv')
    t = rd('data/canonical/tariff_ekz_standard_2023_hourly.csv')
    c = rd('data/canonical/carbon_ch_2023_hourly.csv')
    idx = pd.to_datetime(w.timestamp_utc, utc=True)
    for other, name in ((t, 'tariff'), (c, 'carbon')):
        if not (pd.to_datetime(other.timestamp_utc, utc=True).values == idx.values).all():
            raise ValueError(f'{name} index differs from weather index')
    loc = idx.dt.tz_convert('Europe/Zurich')
    off = ((loc.dt.tz_localize(None) - idx.dt.tz_localize(None)) / pd.Timedelta(hours=1)).astype(int)
    S = {
        'start_utc': idx.iloc[0].strftime('%Y-%m-%dT%H:%M:%SZ'), 'step_s': 3600, 'n': int(len(idx)),
        'index_note': 'UTC, start of hour (DER-007 / D-007 / D-009); local time = Europe/Zurich',
        'utc_offset_h': [int(x) for x in off], 'local_hour': [int(x) for x in loc.dt.hour],
        'weekday': [int(x) for x in loc.dt.weekday],
        'series': {}, 'buildings': {},
    }

    def put(key, values, nd, label, unit, file, column, classification, ui, flags_=None):
        S['series'][key] = {'label': label, 'unit': unit, 'file': file, 'column': column,
                            'classification': classification, 'ui': ui, 'values': arr(values, nd),
                            'flags': flags_ or []}

    wf = 'data/canonical/weather_klo_2023_hourly.csv'
    put('temp_c', w.temp_c, 1, 'Outdoor temperature', '°C', wf, 'temp_c', 'measured', 'series:outdoor_temperature')
    put('ghi', w.ghi_wm2, 0, 'Global horizontal irradiance', 'W/m²', wf, 'ghi_wm2', 'measured', 'series:ghi')
    put('diffuse', w.diffuse_wm2, 0, 'Diffuse horizontal irradiance', 'W/m²', wf, 'diffuse_wm2', 'measured', 'series:diffuse')
    put('beam', w.beam_horizontal_wm2, 0, 'Beam horizontal irradiance', 'W/m²', wf, 'beam_horizontal_wm2', 'derived', 'series:beam')
    tf = 'data/canonical/tariff_ekz_standard_2023_hourly.csv'
    put('price', t.total_rp_kwh, 2, 'Electricity price (energy + grid)', 'Rp/kWh', tf, 'total_rp_kwh', 'measured', 'series:price')
    S['tier_high'] = flags(t.tier.eq('high'))
    cf = 'data/canonical/carbon_ch_2023_hourly.csv'
    put('carbon', c.ci_consumption_lifecycle_g_per_kwh, 2, 'Carbon intensity (consumption-based)', 'gCO2eq/kWh', cf,
        'ci_consumption_lifecycle_g_per_kwh', 'modeled', 'series:carbon_intensity',
        ['neighbour_intensity_fallback_flag', 'gap_interpolated_flag'])
    put('carbon_domestic', c.ci_domestic_generation_lifecycle_g_per_kwh, 2, 'Carbon intensity (domestic generation only)',
        'gCO2eq/kWh', cf, 'ci_domestic_generation_lifecycle_g_per_kwh', 'modeled', 'series:carbon_intensity')
    for k in ('carbon', 'carbon_domestic'):
        S['series'][k]['relative_only'] = True   # outside the carbon audit card the level is shown only as a rank
    S['carbon_rank'] = {
        'values': carbon_rank(c.ci_consumption_lifecycle_g_per_kwh), 'year': int(loc.dt.year.mode().iloc[0]),
        'file': cf, 'column': 'ci_consumption_lifecycle_g_per_kwh', 'ui': 'series:carbon_intensity',
        'definition': 'percent of the year\'s valid hours with a lower modeled intensity (mid-rank for ties, clamped to 1..99)'}
    S['flags'] = {
        'neighbour_intensity_fallback_flag': {'label': 'carbon: neighbour fallback', 'values': flags(c.neighbour_intensity_fallback_flag),
                                              'file': cf, 'ui': 'series:carbon_intensity'},
        'gap_interpolated_flag': {'label': 'carbon: interpolated', 'values': flags(c.gap_interpolated_flag),
                                  'file': cf, 'ui': 'series:carbon_intensity'},
        'weather_missing': {'label': 'weather: missing value', 'values': flags(w[['temp_c', 'ghi_wm2', 'diffuse_wm2']].isna().any(axis=1)),
                            'file': wf, 'ui': 'series:diffuse'},
        'beam_negative': {'label': 'beam < 0 (clipped to 0 in TR-009)', 'values': flags(w.beam_horizontal_wm2.lt(0)),
                          'file': wf, 'ui': 'series:beam'},
    }
    # carbon interpolated hours: the canonical consumption column is NaN there (the CityLearn file is filled, TR-009)
    for role in ROLES:
        f = f'data/canonical/hourly/{role}_2023_hourly.csv'
        b = rd(f)
        if not (pd.to_datetime(b.timestamp_utc, utc=True).values == idx.values).all():
            raise ValueError(f'{role} index differs')
        comps = []
        if role.startswith('SFH'):
            comps.append({'key': 'hp', 'label': 'heat pump', 'column': 'kwh_hp_f', 'classification': 'measured', 'values': arr(b.kwh_hp_f, 3)})
            comps.append({'key': 'other', 'label': 'other (household)', 'column': 'kwh_other_f', 'classification': 'measured', 'values': arr(b.kwh_other_f, 3)})
            gap = flags(b.gap_filled_flag)
        else:
            comps.append({'key': 'hp', 'label': 'heat pump', 'column': 'kwh_hp', 'classification': 'measured', 'values': arr(b.kwh_hp, 3)})
            comps.append({'key': 'common', 'label': 'common areas', 'column': 'kwh_common_areas_measured', 'classification': 'measured',
                          'values': arr(b.kwh_common_areas_measured, 3)})
            comps.append({'key': 'apartments', 'label': 'apartments (SYNTHETIC composite)', 'column': 'kwh_apartments_synthetic',
                          'classification': 'synthetic', 'values': arr(b.kwh_apartments_synthetic, 3)})
            gap = [0] * len(b)
        S['buildings'][role] = {'file': f, 'components': comps, 'gap_filled_flag': gap, 'ui': 'series:building_electricity'}
    return S


def build_figures(rd):
    F = {}
    # --- KLO vs HEAPO station 8jB (D-009/D-010 check): exact equality after the one-hour relabel
    k = rd('data/canonical/weather_klo_2023_hourly.csv')
    h = rd('data/canonical/weather_heapo_2023_hourly.csv')
    rows = []
    for lag in (-1, 0, 1):
        d = (k.temp_c - h.Temperature_avg_hourly__8jB.shift(lag)).abs()
        rows.append({'shift_h': lag, 'max_abs_diff_c': float(d.max()), 'share_identical': float((d < 1e-9).sum() / d.notna().sum()),
                     'n': int(d.notna().sum())})
    F['klo_vs_heapo_8jb'] = {'rows': rows, 'files': ['data/canonical/weather_klo_2023_hourly.csv', 'data/canonical/weather_heapo_2023_hourly.csv'],
                             'note': 'HEAPO weather file is end-labelled (ISS-022 update); shift -1 h aligns it with DER-007.'}
    # --- building selection: candidate pools with the six picks (same filters as swiss/pipeline/select_buildings.py)
    from swiss.pipeline import select_buildings as sb
    hc = rd('data/interim/heapo_candidates.csv')
    pool = hc[hc.has_hp_submeter & (hc.cov_2023 >= sb.MIN_COV) & (hc.cov_hp_2023 >= sb.MIN_COV)
              & (hc.Survey_HeatPump_Installation_Type == 'air-source') & (hc.Survey_Building_Type == 'house')
              & hc.Survey_Building_LivingArea.notna() & (hc.n_dup_ts == 0)]
    m = rd('data/interim/ekz_meters.csv')
    mpool = m[(m['0_installation_type'] == 'Heat pump') & (m['0_object_type'] == 'Apartment building')
              & (m.cov_2023 >= sb.MIN_COV) & (m.cov_2024 >= sb.MIN_COV) & (m.n_dup_ts == 0) & (m['0_num_housing_units'] >= 4)].copy()
    mpool['kwh_per_unit'] = mpool.kwh_import_2023 / mpool['0_num_housing_units']
    sel = rd('data/interim/selected_buildings.csv')
    # guard: the re-applied filters must reproduce the pool sizes and picks recorded by select_buildings.py
    rows_a, na = sb.single_family()
    rows_b, nb = sb.multi_family()
    if na != len(pool) or nb != len(mpool):
        raise ValueError(f'selection pool mismatch: SFH {len(pool)} vs {na}, MFH {len(mpool)} vs {nb}')
    picks = {r['role']: r for r in rows_a + rows_b}
    for _, r in sel.iterrows():
        if int(picks[r.role]['id']) != int(r['id']):
            raise ValueError(f'selection pick mismatch for {r.role}')
    F['building_selection'] = {
        'sfh': {'kwh_hp_2023': [round(float(x), 1) for x in pool.kwh_hp_2023], 'ids': [int(x) for x in pool.Household_ID]},
        'mfh': {'kwh_per_unit_2023': [round(float(x), 1) for x in mpool.kwh_per_unit],
                'units': [int(x) for x in mpool['0_num_housing_units']], 'ids': [int(x) for x in mpool['0_meter_id']]},
        'picks': [{'role': r.role, 'id': int(r['id']), 'n_pool': int(r.n_pool), 'kwh_hp_2023': float(r.kwh_hp_2023),
                   'units': int(r.units)} for _, r in sel.iterrows()],
        'pool_sizes': {'sfh': int(len(pool)), 'mfh': int(len(mpool))},
        'files': ['data/interim/heapo_candidates.csv', 'data/interim/ekz_meters.csv', 'data/interim/selected_buildings.csv'],
        'rule': 'Filters re-applied from swiss/pipeline/select_buildings.py; build fails if pool sizes or picks differ.',
    }
    return F


def build_model_figures(rd, rj):
    """Figure data for models and environment (milestone 4). rd: CSV reader, rj: JSON reader (both record inputs)."""
    from swiss.models import heat_pump
    F = {}
    tp = rj('data/canonical/thermal/thermal_params.json')
    w = rd('data/canonical/weather_klo_2023_hourly.csv')
    tgrid = np.round(np.arange(np.floor(w.temp_c.min()), np.ceil(w.temp_c.max()) + 0.5, 0.5), 1)
    # --- COP curves computed with the repo's own M-001 implementation (swiss/models/heat_pump.py::cop)
    cop = {'t_out_c': [float(x) for x in tgrid], 'buildings': {}}
    split = {'months': [f'2023-{m:02d}' for m in range(1, 13)], 'buildings': {}}
    for role in ROLES:
        p = tp[role]
        th = rd(f'data/canonical/thermal/{role}_2023_thermal_hourly.csv')
        capped = int((th.cop_space_heating >= 20.0).sum())
        cop['buildings'][role] = {
            'eta_sh': p['eta_sh'], 'T_sup_sh_c': p['T_sup_sh_c'], 'eta_dhw': p['eta_dhw'], 'T_sup_dhw_c': p['T_sup_dhw_c'],
            'cop_sh': arr(heat_pump.cop(tgrid, p['eta_sh'], p['T_sup_sh_c']), 3),
            'cop_dhw': arr(heat_pump.cop(tgrid, p['eta_dhw'], p['T_sup_dhw_c']), 3),
            'hours_cop_sh_capped_at_20': capped,
            'file': f'data/canonical/thermal/{role}_2023_thermal_hourly.csv'}
        loc = pd.to_datetime(th.timestamp_utc, utc=True).dt.tz_convert('Europe/Zurich')
        g = th.groupby(loc.dt.month)
        split['buildings'][role] = {'e_hp_baseline_kwh': arr(g.e_hp_baseline_kwh.sum(), 1),
                                    'e_hp_space_heating_kwh': arr(g.e_hp_space_heating_kwh.sum(), 1),
                                    'heating_demand_kwh': arr(g.heating_demand_kwh.sum(), 1),
                                    'dhw_demand_kwh': arr(g.dhw_demand_kwh.sum(), 1)}
    F['cop_curves'] = cop
    F['hp_split_monthly'] = split
    # --- HP nominal power vs peak electricity (TR-009: nominal = 1.1 x peak of the mode's HP electricity)
    schema = rj('swiss/datasets/swiss_district_2023/schema.json')
    man = rj('swiss/datasets/swiss_district_2023/build_manifest.json')
    hp = []
    for name, m in man.items():
        th = rd(f"data/canonical/thermal/{m['role']}_2023_thermal_hourly.csv")
        b = schema['buildings'][name]
        hp.append({'building': name, 'role': m['role'],
                   'peak_sh_elec_kwh': float(th.e_hp_space_heating_kwh.max()), 'nominal_sh_kw': b['heating_device']['attributes']['nominal_power'],
                   'peak_baseline_elec_kwh': float(th.e_hp_baseline_kwh.max()), 'nominal_dhw_kw': b['dhw_device']['attributes']['nominal_power'],
                   'peak_measured_hp_kwh': float(th.e_hp_kwh.max())})
    F['hp_sizing'] = {'rows': hp, 'files': ['swiss/datasets/swiss_district_2023/schema.json', 'data/canonical/thermal/<role>_2023_thermal_hourly.csv']}
    # --- tanks: main dataset and sensitivity variants (build_manifest.json of each)
    variants = {}
    for v in ('swiss_district_2023', 'swiss_sens_tank0.5', 'swiss_sens_tank2', 'swiss_sens_eff0.99', 'swiss_sens_flatcop'):
        mf = rj(f'swiss/datasets/{v}/build_manifest.json')
        sc = rj(f'swiss/datasets/{v}/schema.json')
        variants[v] = [{'building': k, 'role': x['role'], 'heating_tank_kwh_th': x['heating_tank_kwh_th'], 'dhw_tank_kwh_th': x['dhw_tank_kwh_th'],
                        'tank_efficiency': sc['buildings'][k]['heating_storage']['attributes']['efficiency'],
                        'loss_coefficient': sc['buildings'][k]['heating_storage']['attributes']['loss_coefficient']} for k, x in mf.items()]
    F['tanks'] = {'variants': variants}
    # --- CityLearn interface as configured in schema.json (DER-010)
    F['env_interface'] = {
        'observations_active': [k for k, v in schema['observations'].items() if v.get('active')],
        'observations_inactive': [k for k, v in schema['observations'].items() if not v.get('active')],
        'shared_in_central_agent': [k for k, v in schema['observations'].items() if v.get('shared_in_central_agent')],
        'actions_active': [k for k, v in schema['actions'].items() if v.get('active')],
        'actions_inactive': [k for k, v in schema['actions'].items() if not v.get('active')],
        'central_agent': schema.get('central_agent'), 'seconds_per_time_step': schema.get('seconds_per_time_step'),
        'simulation_end_time_step': schema.get('simulation_end_time_step'),
        'building_classes': sorted({b['type'] for b in schema['buildings'].values()}),
        'device_classes': sorted({b[k]['type'] for b in schema['buildings'].values() for k in ('heating_device', 'dhw_device', 'heating_storage', 'dhw_storage') if k in b}),
        'file': 'swiss/datasets/swiss_district_2023/schema.json'}
    v1 = rj('docs/experiments/validation_reports/validation_phase_a.json')['V1_electricity_closure']
    F['env_interface']['v1_max_abs_err_kwh'] = max(x['max_abs_err_kwh'] for x in v1.values())
    F['env_interface']['v1_cases'] = len(v1)
    # --- carbon: daily generation and imports by neighbour (DER-011 columns)
    c = rd('data/canonical/carbon_ch_2023_hourly.csv')
    day = pd.to_datetime(c.timestamp_utc, utc=True).dt.tz_convert('Europe/Zurich').dt.date.astype(str)
    cols = ['domestic_generation_excl_pumped_mwh', 'import_france_mwh', 'import_germany_mwh', 'import_austria_mwh', 'import_italy_mwh']
    g = c.groupby(day)
    F['carbon_daily'] = {'days': list(g.size().index), 'hours': [int(x) for x in g.size()],
                         'mwh': {k: arr(g[k].sum(min_count=1), 1) for k in cols},
                         'missing_hours': {k: [int(x) for x in g[k].apply(lambda s: s.isna().sum())] for k in cols},
                         'mean_ci_consumption': arr(g.ci_consumption_lifecycle_g_per_kwh.mean(), 2),
                         'file': 'data/canonical/carbon_ch_2023_hourly.csv',
                         'note': 'Local (Europe/Zurich) days; the first and last day hold fewer than 24 hours of the 2023 local year window.'}
    return F


TRACE_DIR = 'swiss/experiments/results/traces'


def build_results(rd, rj, exp_rows):
    """Results table, reward scales, sensitivity, controller -> experiment mapping, and trace checks."""
    import os
    res = rd('swiss/experiments/results/baselines_2023.csv')
    meta = rj('swiss/experiments/results/baselines_2023_meta.json')
    sens = rd('swiss/experiments/results/sensitivity_2023.csv')
    R = {'columns': list(res.columns), 'rows': [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()}
                                                 for r in res.to_dict('records')],
         'meta': meta, 'reward_scales': rj('swiss/experiments/results/reward_scales.json'),
         'sensitivity': [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()} for r in sens.to_dict('records')],
         'files': ['swiss/experiments/results/baselines_2023.csv', 'swiss/experiments/results/baselines_2023_meta.json',
                   'swiss/experiments/results/sensitivity_2023.csv']}
    # controller -> experiment: same algorithm ID, registry git commit = commit recorded in the results meta,
    # and the registry's rounded import (metrics column) equal to the results value. Shown on cards with this rule.
    exp_of = {}
    for r in R['rows']:
        alg = r['controller'].split('_')[0]
        hits = []
        for e in exp_rows:
            if alg not in e['algorithm_ids'] or not e['git_commit'].startswith(str(meta.get('git_head', '-'))[:7]):
                continue
            m = __import__('re').search(r'import (\d+) kWh', e['metrics'])
            if m and int(m.group(1)) == int(round(r['district_import_kwh'])):
                hits.append(e['experiment_id'])
        exp_of[r['controller']] = hits
    R['experiment_of'] = exp_of
    R['experiment_rule'] = ('same ALG ID, experiment git_commit starts with the git_head in baselines_2023_meta.json, and the '
                            'registry metrics "import N kWh" equal to the rounded district_import_kwh')
    # traces
    traces, checks = {}, {}
    first = {}
    for r in R['rows']:
        name = r['controller']
        f = f'{TRACE_DIR}/{name}.csv.gz'
        if not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', f)):
            continue
        t = rd(f)
        sums = {'district_import_kwh': float(sum(np.maximum(t[c], 0).sum() for c in t.columns if c.endswith('_net_kwh') and c.startswith('b'))),
                'district_peak_kw': float(t.district_net_kwh.max()), 'reward_return': float(t.reward.sum()),
                'term_cost_sum': float(t.term_cost.sum()), 'term_peak_sum': float(t.term_peak.sum()),
                'term_ramp_sum': float(t.term_ramp.sum()), 'term_carbon_sum': float(t.term_carbon.sum()),
                'steps': int(len(t))}
        checks[name] = {k: {'trace': v, 'results': float(r[k]), 'rel_diff': (abs(v - float(r[k])) / abs(float(r[k])) if float(r[k]) else abs(v))}
                        for k, v in sums.items()}
        nb = len([c for c in t.columns if c.endswith('_net_kwh') and c.startswith('b')])
        arrs = {'district_net_kwh': arr(t.district_net_kwh, 3), 'reward': arr(t.reward, 5),
                'term_cost': arr(t.term_cost, 5), 'term_peak': arr(t.term_peak, 2), 'term_ramp': arr(t.term_ramp, 3),
                'term_carbon': arr(t.term_carbon, 2)}
        for i in range(1, nb + 1):
            arrs[f'b{i}_net_kwh'] = arr(t[f'b{i}_net_kwh'], 3)
            arrs[f'b{i}_heating_storage_soc'] = arr(t[f'b{i}_heating_storage_soc'], 3)
            arrs[f'b{i}_dhw_storage_soc'] = arr(t[f'b{i}_dhw_storage_soc'], 3)
            arrs[f'b{i}_hp_kwh_el'] = arr(t[f'b{i}_heating_device_kwh_el'] + t[f'b{i}_dhw_device_kwh_el'], 3)
            for a in ('heating_storage', 'dhw_storage'):
                if f'b{i}_action_{a}' in t:
                    arrs[f'b{i}_action_{a}'] = arr(t[f'b{i}_action_{a}'], 4)
        key = json_key(arrs)
        same = first.get(key)
        first.setdefault(key, name)
        traces[name] = {'file': f, 'n': int(len(t)), 'start_utc': str(t.timestamp_utc.iloc[0]), 'same_as': same,
                        'arrays': None if same else arrs}
    R['trace_checks'] = checks
    return R, traces


def json_key(d):
    import hashlib
    import json
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def action_maps():
    """ALG-004 24-hour action maps, evaluated with run_baselines.tariff_map itself."""
    import importlib
    rb = importlib.import_module('swiss.experiments.run_baselines')
    out = {}
    for name in rb.CONTROLLERS:
        if 'tariff_r' in name:
            r = float(name.split('_r')[-1])
            m = rb.tariff_map(r)['heating_storage']
            out[name] = {'citylearn_hour': list(range(1, 25)), 'local_hour': [h - 1 for h in range(1, 25)],
                         'action': [m[h] for h in range(1, 25)], 'rate': r}
    return out


def district(rd, rj):
    """Per-building facts for the district illustration (all read from repo files)."""
    man = rj('swiss/datasets/swiss_district_2023/build_manifest.json')
    sel = rd('data/interim/selected_buildings.csv').set_index('role')
    qb = rj('docs/data/data_quality_reports/qc_2023_buildings.json')
    tp = rj('data/canonical/thermal/thermal_params.json')
    out = []
    for i, (name, m) in enumerate(man.items(), start=1):
        role = m['role']
        s = sel.loc[role]
        q = qb[role]
        out.append({'index': i, 'building': name, 'role': role, 'type': 'SFH' if role.startswith('SFH') else 'MFH',
                    'source': q['source'], 'source_id': q['id'], 'units': int(s.units),
                    'area_m2': None if pd.isna(s.area_m2) else float(s.area_m2),
                    'residents': None if pd.isna(s.residents) else float(s.residents),
                    'heating_tank_kwh_th': m['heating_tank_kwh_th'], 'dhw_tank_kwh_th': m['dhw_tank_kwh_th'],
                    'hp_sh_nominal_kw': m['hp_sh_nominal_kw'], 'hp_dhw_nominal_kw': m['hp_dhw_nominal_kw'],
                    'T_sup_sh_c': tp[role]['T_sup_sh_c'], 'eta_sh': tp[role]['eta_sh'],
                    'apartments_synthetic': role.startswith('MFH'), 'gap_filled_hours': q.get('gap_filled_hours', 0)})
    return {'buildings': out, 'files': ['swiss/datasets/swiss_district_2023/build_manifest.json', 'data/interim/selected_buildings.csv',
                                        'docs/data/data_quality_reports/qc_2023_buildings.json', 'data/canonical/thermal/thermal_params.json']}
