"""Phase C content of the dashboard (WP5b): climate.json, cooling.json, explorer.json, houses.json.

Reads ONLY committed files: the scenario weather and PV files of data/canonical/climate/ (WP1), the generated climate validation report (tables parsed by header name),
swiss/experiments/climate_results/ (matrix, summary, robustness; WP3/WP4), swiss/dashboard/data/climate_weeks.json (hourly heat-wave-week rollouts written by
swiss/dashboard/climate_series.py) and the cooling constants of swiss/models/rc_building.py. Every number the pages show comes from these files; prose numbers go through the
`pc` placeholder namespace (section `_phase_c` of ui_map.yaml). Rules used to derive numbers (all simple and stated on the pages):
  saving % = 100 x (thermostat bill - bill) / thermostat bill (the matrix already stores it);  share of ceiling = saving / exact optimum saving on the same weeks;
  district PV coverage of cooling = cooling-weighted mean of the per-building shares (PV allocation priority: base load, hot water, heat pump, then battery charging;
  sensitivity 'hp_first': heat pump first); added consumption by cooling = cooling electricity of the cell; heating saved by warming = heating electricity of the
  heating-only cell in 2023 weather minus that of the heating-only cell in the scenario weather; spill-over = difference of a cell against the heating-only cell of the same
  scenario (difference method of climate_metrics.py).
ARCHETYPE: every record carries `archetype` ('central' now). The pages build their archetype selector from the set present in the data, so a second archetype (room units)
only needs its records appended with another `archetype` value (see `ARCHETYPES`).
"""
import os
import re

import numpy as np

CS = 'swiss/experiments/climate_results/'
CAN = 'data/canonical/climate/'
WEEKS_FILE = 'swiss/dashboard/data/climate_weeks.json'
REPORT = 'docs/experiments/validation_reports/climate_scenarios.md'
SC_ORDER = ('hist', 'hist_hw99', 'gwl2.0', 'gwl2.0_hw99', 'gwl3.0', 'gwl3.0_hw99')
SC_SENS = ('gwl1.5', 'hist_hw', 'gwl2.0_hw', 'gwl3.0_hw')
SC_LABEL = {'hist': 'Observed 2023', 'gwl2.0': '+2.0 °C typical year', 'gwl3.0': '+3.0 °C typical year', 'gwl1.5': '+1.5 °C typical year',
            'hist_hw99': 'Observed 2023 with a heat wave', 'gwl2.0_hw99': '+2.0 °C with a heat wave', 'gwl3.0_hw99': '+3.0 °C with a heat wave',
            'hist_hw': '2023 with a milder spell (sensitivity)', 'gwl2.0_hw': '+2.0 °C with a milder spell (sensitivity)', 'gwl3.0_hw': '+3.0 °C with a milder spell (sensitivity)'}
ADOPT = ('none', 'low', 'medium', 'high', 'high_alt')
ADOPT_LABEL = {'none': 'Heating only', 'low': 'Low: small apartment building cooled', 'medium': 'Medium: medium apartment building cooled',
               'high': 'High: large apartment building cooled', 'high_alt': 'High, other assignment: medium and small apartment buildings and the three houses cooled'}
ADOPT_SHORT = {'none': 'none', 'low': 'low', 'medium': 'medium', 'high': 'high', 'high_alt': 'high (other)'}
BUILDINGS = ('SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large')
CTRLS = ('thermostat', 'pv_rule', 'mpc', 'mpc_peak0.1')
CTRL_LABEL = {'thermostat': 'Thermostat (reference)', 'pv_rule': 'Hand-set solar rule', 'mpc': 'Planner (MPC)', 'mpc_peak0.1': 'Planner with a small peak weight',
              'optimum': 'Exact optimum (perfect foresight)'}
ARCHETYPES = {'central': 'Central: the whole building is cooled by one system'}
ROBUST_CASES = {
    'scenario': 'Reference run: forecasters trained on the scenario year',
    'trained_hist': 'Forecasters trained on 2023 weather only',
    'T-2': 'Forecast temperature 2 K too low (plus noise)', 'T-1': 'Forecast temperature 1 K too low (plus noise)',
    'T+1': 'Forecast temperature 1 K too high (plus noise)', 'T+2': 'Forecast temperature 2 K too high (plus noise)',
    'T0n1': 'Forecast temperature noise only', 'G30': 'Irradiance forecast noise of a third',
    'T+2G30': 'Temperature 2 K too high and irradiance noise', 'T-2G30': 'Temperature 2 K too low and irradiance noise',
    'T+2corr': 'Temperature 2 K too high with online correction and a small comfort margin'}
HOUR_KEYS = ('base', 'dhw', 'heat', 'cool', 'pv', 'batt', 'net')


def split_cell(cell):
    for a in ('high_alt',) + ADOPT[:4][::-1]:
        if cell.endswith('_' + a):
            return cell[:-(len(a) + 1)], a
    raise ValueError(cell)


def md_tables(text):
    """All markdown tables of a text as lists of dicts keyed by the header cells (cells stripped)."""
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cur is None:
                cur = {'head': cells, 'rows': []}
            elif set(''.join(cells)) <= set('-: '):
                continue
            else:
                cur['rows'].append(dict(zip(cur['head'], cells)))
        else:
            if cur is not None:
                out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return out


def num(s):
    m = re.search(r'-?\d+(?:\.\d+)?', s or '')
    return float(m.group(0)) if m else None


def weighted_cooling_share(b_annual):
    """Cooling-weighted mean over buildings of the PV, battery and grid share of the cooling electricity (None without cooling)."""
    tot = sum(v['cool'] for v in b_annual.values())
    if tot <= 1e-9:
        return None
    return {'pv': sum(v['cool'] * (v['pv_share_of_cooling'] or 0.0) for v in b_annual.values()) / tot,
            'battery': sum(v['cool'] * (v['battery_share_of_cooling'] or 0.0) for v in b_annual.values()) / tot,
            'grid': sum(v['cool'] * (v['grid_share_of_cooling'] or 0.0) for v in b_annual.values()) / tot, 'cooling_kwh': tot}


def build(bb, ui, errors, nodes, pb):
    rj, rdf = bb.read_json, bb.read_df
    import pandas as pd
    from swiss.models import rc_building as rcb
    bb._read_files.add('swiss/models/rc_building.py')
    cfg = ui.get('_phase_c', {})
    pc = {}

    # ------------------------------------------------------------------ climate.json
    scen = {}
    for s in SC_ORDER + SC_SENS:
        path = 'data/canonical/weather_klo_2023_hourly.csv' if s == 'hist' else CAN + f'weather_klo_{s}_hourly.csv'
        w = rdf(path)
        ts = pd.to_datetime(w['timestamp_utc'], utc=True).dt.tz_convert('Europe/Zurich')
        T = w['temp_c'].astype(float)
        day = ts.dt.date
        dmax = T.groupby(day).max()
        pvp = 'data/canonical/pv/pv_ac_w_per_kwp_2023_hourly.csv' if s == 'hist' else CAN + f'pv_ac_w_per_kwp_{s}_hourly.csv'
        pv = rdf(pvp)['pv_ac_w_per_kwp'].astype(float)
        wk = T.iloc[4872:5040]
        scen[s] = {'id': s, 'label': SC_LABEL[s], 'sensitivity': s in SC_SENS, 'annual_mean_c': float(T.mean()), 'days_ge30': int((dmax >= 30).sum()), 'days_ge35': int((dmax >= 35).sum()),
                   'hottest_168h_c': float(T.rolling(168).mean().max()), 'week29_mean_c': float(wk.mean()), 'week29_max_c': float(wk.max()),
                   'ghi_kwh_m2': float(w['ghi_wm2'].astype(float).sum() / 1000.0), 'pv_kwh_kwp': float(pv.sum() / 1000.0),
                   'monthly_mean_c': [float(x) for x in T.groupby(ts.dt.month).mean().values]}
        if s in ('hist', 'hist_hw99', 'gwl2.0_hw99', 'gwl3.0_hw99'):
            scen[s]['week29_hourly_c'] = [round(float(x), 2) for x in wk.values]
    spells_raw = rj(CAN + 'heatwave_spells.json')
    spells = []
    for lvl, key, pct in (('Reference 1991-2020', 'hist', 95), ('+2.0 °C', 'gwl2.0', 95), ('+3.0 °C', 'gwl3.0', 95), ('Reference 1991-2020', 'hist99', 99), ('+2.0 °C', 'gwl2.099', 99),
                          ('+3.0 °C', 'gwl3.099', 99)):
        sp = spells_raw[key]
        spells.append({'level': lvl, 'percentile': pct, 'chain': sp['chain'], 'model_year': sp['model_year'], 'start': sp['start_date_365'], 'severity_c': sp['severity_mean_tasmax'],
                       'tasmax': sp['daily']['tasmax'], 'tasmin': sp['daily']['tasmin']})
    rep = bb.read_text(REPORT)
    tabs = md_tables(rep)
    ens = []
    for t in tabs:
        if 'Days tasmax >= 30 C' in t['head']:
            for r in t['rows']:
                ens.append({'level': r['Level'], 'days_ge30': num(r['Days tasmax >= 30 C']), 'days_ge35': num(r['>= 35 C']), 'hurs_max': num(r['hurs max (share > 100 %)'])})
    m_all = re.search(r'all days with a range of at least 1 K \((\d+) days.*?RMSE ([\d.]+) K', rep, re.S)
    m_hot = re.search(r'hot days \(hourly maximum >= 27 C and range >= 5 K, (\d+) days.*?RMSE ([\d.]+) K', rep, re.S)
    validation = {'recon_all_days': int(m_all.group(1)), 'recon_all_rmse_k': float(m_all.group(2)), 'recon_hot_days': int(m_hot.group(1)), 'recon_hot_rmse_k': float(m_hot.group(2)), 'ensemble': ens}
    climate = {'scenarios': scen, 'order': list(SC_ORDER), 'sensitivity': list(SC_SENS), 'spells': spells, 'validation': validation, 'rule': spells_raw['rule'],
               'inserted_rows': spells_raw['inserted_rows'],
               'citation': 'MeteoSwiss & ETH Zurich (2025): Climate CH2025 - Daily Datasets. Federal Office of Meteorology and Climatology MeteoSwiss, Zurich, https://doi.org/10.18751/climate/scenarios/ch2025/data/1.0/',
               'sources': [CAN, REPORT, 'data/canonical/weather_klo_2023_hourly.csv']}
    pc['climate'] = {'hist_mean': scen['hist']['annual_mean_c'], 'g2_mean': scen['gwl2.0']['annual_mean_c'], 'g3_mean': scen['gwl3.0']['annual_mean_c'],
                     'hist_d30': scen['hist']['days_ge30'], 'g3_d30': scen['gwl3.0']['days_ge30'], 'hist_d35': scen['hist']['days_ge35'], 'g3_d35': scen['gwl3.0']['days_ge35'],
                     'hw_hist': scen['hist_hw99']['week29_mean_c'], 'hw_g3': scen['gwl3.0_hw99']['week29_mean_c'], 'hw_g3_max': scen['gwl3.0_hw99']['week29_max_c'],
                     'obs_w29': scen['hist']['week29_mean_c'], 'rmse_all': validation['recon_all_rmse_k'], 'rmse_hot': validation['recon_hot_rmse_k']}
    pc['rc'] = {'cool_setpoint': rcb.COOL_SETPOINT_C, 'cool_supply': rcb.COOL_SUPPLY_C, 'cool_min_outdoor': rcb.COOLING_MIN_OUTDOOR_C, 'upper_heating': rcb.UPPER_HEATING_SEASON_C}

    # ------------------------------------------------------------------ cooling.json and houses.json
    S = rj(CS + 'climate_summary.json')
    cells, houses = [], {}
    for cell, c in S['cells'].items():
        sc, ad = split_cell(cell)
        th_b = c['thermostat_year']['default']['buildings']
        op_b = c['optimum_year']['default']['buildings']
        th_h = c['thermostat_year']['hp_first']['buildings']
        op_h = c['optimum_year']['hp_first']['buildings']
        rec = {'id': cell, 'archetype': 'central', 'scenario': sc, 'adoption': ad, 'cooled': c['cooled'],
               'ceiling_year_pct': c['ceiling_year_pct'], 'pinned_year_pct': c['pinned_year_pct'], 'mass_value_pts': c['mass_value_pts'], 'ceiling_weeks_pct': c['ceiling_weeks_pct'],
               'zero_bill_chf': c['zero_bill_chf'], 'opt_bill_chf': c['opt_bill_chf'], 'cooling_kwh': c['cooling_kwh'], 'heating_kwh': c['heating_kwh'], 'import_kwh': c['import_kwh'],
               'export_kwh': c['export_kwh'], 'peak_kw': c['peak_kw'], 'dh26': {'baseline': c['degree_hours_above_26']['baseline'], 'optimum': c['degree_hours_above_26']['optimum']},
               'pv_self_consumption': c['pv_self_consumption'], 'emissions_kg': c['emissions_kg'],
               'pv_cooling_share': {'thermostat': weighted_cooling_share({b: v['annual'] for b, v in th_b.items()}), 'optimum': weighted_cooling_share({b: v['annual'] for b, v in op_b.items()}),
                                    'thermostat_hp_first': weighted_cooling_share({b: v['annual'] for b, v in th_h.items()}),
                                    'optimum_hp_first': weighted_cooling_share({b: v['annual'] for b, v in op_h.items()})},
               'controllers': {}, 'difference_vs_none': c.get('difference_vs_none')}
        for k in CTRLS:
            m = c['controllers'][k]
            rec['controllers'][k] = {'saving_pct': m['saving_pct'], 'share_of_ceiling_pct': 100.0 * m['share_of_ceiling'], 'highest_hour_kw': m['highest_hour_kw'], 'weekly_peak_kw': m['mean_weekly_peak_kw'],
                                     'comfort_cold_kh': m['comfort_cold_kh'], 'dh26': m['degree_hours_above_26'], 'cooling_kwh': m['cooling_electricity_kwh'], 'heating_kwh': m['heating_electricity_kwh'],
                                     'import_kwh': m['import_kwh'], 'export_kwh': m['export_kwh'], 'cost_chf': m['cost_chf']}
        cells.append(rec)
        hb = {}
        for ctrl, byb, byh, dist in (('thermostat', th_b, th_h, c['thermostat_year']['default']), ('optimum', op_b, op_h, c['optimum_year']['default'])):
            hb[ctrl] = {'district': {'annual': dist['annual'], 'summer': dist['summer'], 'peak_kw': dist['peak_net_kw'], 'summer_peak_kw': dist['summer_peak_net_kw'],
                                     'dh26': dist['degree_hours_above']},
                        'buildings': {b: {'annual': v['annual'], 'summer': v['summer'], 'peak_kw': v['peak_net_kw'], 'dh26': v['degree_hours_above'],
                                          'pv_share_of_cooling_hp_first': byh[b]['annual']['pv_share_of_cooling']} for b, v in byb.items()}}
        houses[cell] = hb
    by_id = {r['id']: r for r in cells}

    # robustness (high adoption heat-wave cells)
    robust = []
    for cell in ('gwl3.0_hw99_high', 'gwl2.0_hw99_high', 'hist_hw99_high'):
        base = by_id[cell]
        thermo_cost = base['controllers']['thermostat']['cost_chf']
        ceil_w = base['ceiling_weeks_pct']
        for case, label in ROBUST_CASES.items():
            if case == 'scenario':
                m = base['controllers']['mpc']
                row = {'saving_pct': m['saving_pct'], 'comfort_cold_kh': m['comfort_cold_kh'], 'dh26': m['dh26'], 'cooling_kwh': m['cooling_kwh'], 'highest_hour_kw': m['highest_hour_kw']}
            else:
                f = CS + f'robust__{cell}__{case}.json'
                if not os.path.exists(bb._abs(f)):
                    errors.append(f'phase_c: missing robustness file {f}')
                    continue
                a = rj(f)['aggregate']
                row = {'saving_pct': 100.0 * (thermo_cost - a['cost_chf']) / thermo_cost, 'comfort_cold_kh': a['comfort_cold_kh'], 'dh26': a['degree_hours_above_26'],
                       'cooling_kwh': a['cooling_electricity_kwh'], 'highest_hour_kw': a['highest_hour_kw']}
            row.update({'cell': cell, 'case': case, 'label': label, 'share_of_ceiling_pct': 100.0 * row['saving_pct'] / ceil_w, 'synthetic': case not in ('scenario', 'trained_hist')})
            robust.append(row)

    # ---- derived headline numbers (min / max over the stated cell sets)
    def vals(f, ids):
        return [f(by_id[i]) for i in ids if i in by_id]

    central = [r for r in cells if r['adoption'] != 'high_alt']
    cooled = [r for r in central if r['adoption'] != 'none']
    none = [r for r in central if r['adoption'] == 'none']
    pc['mass'] = {'none_min': min(r['mass_value_pts'] for r in none), 'none_max': max(r['mass_value_pts'] for r in none),
                  'cool_min': min(r['mass_value_pts'] for r in cooled), 'cool_max': max(r['mass_value_pts'] for r in cooled),
                  'alt_max': max([r['mass_value_pts'] for r in cells if r['adoption'] == 'high_alt'])}
    h_hist = by_id['hist_none']['heating_kwh']['baseline']
    h_g3 = by_id['gwl3.0_none']['heating_kwh']['baseline']
    h_g2 = by_id['gwl2.0_none']['heating_kwh']['baseline']
    pc['heat'] = {'hist_mwh': h_hist / 1000.0, 'g2_mwh': h_g2 / 1000.0, 'g3_mwh': h_g3 / 1000.0, 'g3_drop_pct': 100.0 * (h_hist - h_g3) / h_hist, 'g2_drop_pct': 100.0 * (h_hist - h_g2) / h_hist}
    cool_vals = [r['cooling_kwh']['baseline'] / 1000.0 for r in cooled]
    pc['cool'] = {'min_mwh': min(cool_vals), 'max_mwh': max(cool_vals), 'g3_high_mwh': by_id['gwl3.0_high']['cooling_kwh']['baseline'] / 1000.0,
                  'hist_high_mwh': by_id['hist_high']['cooling_kwh']['baseline'] / 1000.0, 'alt_max_mwh': max(r['cooling_kwh']['baseline'] for r in cells if r['adoption'] == 'high_alt') / 1000.0,
                  'g3_drop_mwh': (h_hist - h_g3) / 1000.0}
    sh = [r['pv_cooling_share']['thermostat']['pv'] for r in cooled if r['pv_cooling_share']['thermostat']]
    sho = [r['pv_cooling_share']['optimum']['pv'] + r['pv_cooling_share']['optimum']['battery'] for r in cooled if r['pv_cooling_share']['optimum']]
    pc['pvshare'] = {'thermo_min': 100 * min(sh), 'thermo_max': 100 * max(sh), 'opt_min': 100 * min(sho), 'opt_max': 100 * max(sho),
                     'alt_thermo': 100 * min(r['pv_cooling_share']['thermostat']['pv'] for r in cells if r['adoption'] == 'high_alt')}
    dsp = [r['difference_vs_none']['thermostat']['summer_peak_kw'] for r in cooled if r['difference_vs_none']]
    dso = [r['difference_vs_none']['optimum']['summer_peak_kw'] for r in cooled if r['difference_vs_none']]
    pc['summerpeak'] = {'thermo_max': max(dsp), 'opt_max': max(dso), 'opt_min': min(dso)}
    d = by_id['gwl3.0_hw99_high']['difference_vs_none']['thermostat']
    pc['spill'] = {'import_kwh': d['import_kwh'], 'export_kwh': -d['export_kwh'], 'cool_kwh': d['cool_kwh'], 'summer_import_kwh': d['summer_import_kwh']}
    ex = by_id['hist_none']
    pc['summer_peak'] = {'thermo_kw': ex['peak_kw']['summer_baseline'], 'opt_kw': ex['peak_kw']['summer_optimum']}
    pc['mpc'] = {'share_min': min(r['controllers']['mpc']['share_of_ceiling_pct'] for r in central), 'share_max': max(r['controllers']['mpc']['share_of_ceiling_pct'] for r in central),
                 'rule_min': min(r['controllers']['pv_rule']['share_of_ceiling_pct'] for r in central), 'rule_max': max(r['controllers']['pv_rule']['share_of_ceiling_pct'] for r in central),
                 'peak_mpc_min': min(r['controllers']['mpc']['highest_hour_kw'] for r in central), 'peak_mpc_max': max(r['controllers']['mpc']['highest_hour_kw'] for r in central),
                 'peak01_max': max(r['controllers']['mpc_peak0.1']['highest_hour_kw'] for r in central),
                 'thermo_peak_min': min(r['controllers']['thermostat']['highest_hour_kw'] for r in central), 'thermo_peak_max': max(r['controllers']['thermostat']['highest_hour_kw'] for r in central),
                 'peak01_delta_min': min(r['controllers']['mpc_peak0.1']['saving_pct'] - r['controllers']['mpc']['saving_pct'] for r in central), 'mpc_saving_g3hw': by_id['gwl3.0_hw99_high']['controllers']['mpc']['saving_pct']}
    pc['ceil'] = {'hist_none': by_id['hist_none']['ceiling_year_pct'], 'g3_none': by_id['gwl3.0_none']['ceiling_year_pct'], 'g3hw_high': by_id['gwl3.0_hw99_high']['ceiling_year_pct']}
    pc['dh26'] = {'per_uncooled_building_hist': houses['hist_none']['thermostat']['buildings']['SFH-low']['dh26'], 'per_uncooled_building_g3': houses['gwl3.0_none']['thermostat']['buildings']['SFH-low']['dh26']}
    rb = {r['case'] + '|' + r['cell']: r for r in robust}
    g3 = 'gwl3.0_hw99_high'
    pc['robust'] = {'hist_trained_share': rb['trained_hist|' + g3]['share_of_ceiling_pct'], 'scen_share': rb['scenario|' + g3]['share_of_ceiling_pct'],
                    'tm2_share': rb['T-2|' + g3]['share_of_ceiling_pct'], 'tp2_cold': rb['T+2|' + g3]['comfort_cold_kh'], 'tp2corr_cold': rb['T+2corr|' + g3]['comfort_cold_kh'],
                    'g30_share': rb['G30|' + g3]['share_of_ceiling_pct'], 'tp2corr_share': rb['T+2corr|' + g3]['share_of_ceiling_pct'], 'scen_cold': rb['scenario|' + g3]['comfort_cold_kh']}

    heatmap_note = {'test_weeks': S.get('test_weeks'), 'export_price_rp': S['export_price_rp']}
    cooling = {'archetypes': [{'id': k, 'label': v} for k, v in ARCHETYPES.items()], 'scenarios': list(SC_ORDER), 'scenario_labels': {s: SC_LABEL[s] for s in SC_ORDER},
               'adoption': list(ADOPT), 'adoption_labels': ADOPT_LABEL, 'adoption_short': ADOPT_SHORT, 'controllers': list(CTRLS), 'controller_labels': CTRL_LABEL, 'cells': cells,
               'robustness': robust, 'meta': heatmap_note, 'sources': [CS, REPORT]}
    houses_obj = {'buildings': list(BUILDINGS), 'archetypes': cooling['archetypes'], 'scenarios': list(SC_ORDER), 'scenario_labels': cooling['scenario_labels'], 'adoption': list(ADOPT),
                  'adoption_labels': ADOPT_LABEL, 'cells': {k: {'archetype': 'central', **v} for k, v in houses.items()}, 'sources': [CS + 'climate_summary.json']}

    # ------------------------------------------------------------------ explorer.json (hourly heat-wave week)
    wk = {}
    wf = bb._abs(WEEKS_FILE)
    rolled = rj(WEEKS_FILE) if os.path.exists(wf) else None
    if rolled is None:
        errors.append(f'phase_c: {WEEKS_FILE} missing; run swiss/dashboard/climate_series.py')
        rolled = {'cells': {}, 'steps': [4872, 5039]}
    for cell, c in S['cells'].items():
        w29 = c['week29']
        h = {'thermostat': {k: [round(x, 2) for x in w29['thermostat'][k]] for k in HOUR_KEYS}, 'optimum': {k: [round(x, 2) for x in w29['optimum'][k]] for k in HOUR_KEYS}}
        for k, v in (rolled['cells'].get(cell) or {}).items():
            if k != 'error' and isinstance(v, dict):
                h[k] = {kk: [round(x, 2) for x in v[kk]] for kk in HOUR_KEYS}
        wk[cell] = h
    explorer = {'archetypes': cooling['archetypes'], 'scenarios': list(SC_ORDER), 'scenario_labels': cooling['scenario_labels'], 'adoption': list(ADOPT), 'adoption_labels': ADOPT_LABEL,
                'controllers': ['thermostat', 'pv_rule', 'mpc', 'mpc_peak0.1', 'optimum'], 'controller_labels': CTRL_LABEL, 'week': {'steps': rolled['steps'], 'number': 29},
                'hourly': {cell: {'archetype': 'central', **v} for cell, v in wk.items()}, 'hours_note_cells': sorted(rolled['cells'].keys()),
                'house_groups': {'SFH': ['SFH-low', 'SFH-mid', 'SFH-high'], 'MFH': ['MFH-small', 'MFH-medium', 'MFH-large']}, 'sources': [WEEKS_FILE, CS + 'climate_summary.json']}

    # ------------------------------------------------------------------ prose (numbers only through placeholders)
    data_ns = {'pb': pb, 'pc': pc}
    prose = {}
    for page in ('climate', 'cooling', 'explorer', 'houses'):
        sec = cfg.get(page, {})
        filled = {}
        for k, v in sec.items():
            if isinstance(v, str):
                filled[k] = bb.fill(v, data_ns, errors, f'_phase_c.{page}.{k}')
            elif isinstance(v, list) and k != 'limitations':
                if not all(isinstance(x, str) for x in v):
                    errors.append(f'phase_c: _phase_c.{page}.{k} has a list item that is not a string (a colon followed by a space inside plain YAML text makes a mapping; use a folded block)')
                filled[k] = [bb.fill(x, data_ns, errors, f'_phase_c.{page}.{k}') if isinstance(x, str) else x for x in v]
        prose[page] = filled
    lim = []
    for nid in cfg.get('limitations', []):
        n = nodes.get(nid)
        if not n:
            errors.append(f'phase_c: limitation {nid} is not a registry node')
            continue
        lim.append({'id': nid, 'kind': n['kind'], 'title': n.get('title'), 'summary': n.get('summary'), 'status': n.get('status')})
    pending = [{'title': e['title'], 'text': bb.fill(e['text'], data_ns, errors, f'_phase_c.pending.{i}')} for i, e in enumerate(cfg.get('pending_register', []) or [])]
    climate['prose'] = prose.get('climate', {})
    cooling['prose'] = prose.get('cooling', {})
    cooling['limitations'] = lim
    cooling['pending_register'] = pending
    explorer['prose'] = prose.get('explorer', {})
    houses_obj['prose'] = prose.get('houses', {})
    return climate, cooling, explorer, houses_obj, pc
