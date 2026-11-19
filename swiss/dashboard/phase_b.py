"""Phase B content of the dashboard: scenarios.json and controllers.json (WP5a).

Reads ONLY committed result files (oracle results, RL results, MPC results, baselines, registries through the bundle graph) and writes two compact bundle files that
the pages `/scenarios/` and `/controllers/` render. Every number the UI shows comes from these files; prose with numbers is filled from the `pb` namespace through the
placeholder mechanism of build_bundle.fill (section `_phase_b` of ui_map.yaml). Nothing is computed that does not follow from a result file by a stated, simple rule
(percent saving = 100 x (reference bill - bill) / reference bill; mean and standard deviation over seeds as rl_report.py does).

Called from build_bundle.main(); the Phase C pages (WP5b) can add their own `build_*` function next to these and emit another file the same way.
"""
import csv
import json
import os

import numpy as np

SC = ('s1', 's2', 's3')
SC_NAME = {'s1': 'S1', 's2': 'S2', 's3': 'S3'}
RL_KINDS = ('sac_central', 'sac_decentral', 'marlisa')
RL_LABEL = {'sac_central': 'Central SAC (one agent for the district)', 'sac_decentral': 'SAC per building', 'marlisa': 'MARLISA (coordinated agents)'}
OR = 'swiss/experiments/oracle_results/'
RLR = 'swiss/experiments/rl_results/'
MPCR = 'swiss/experiments/mpc_results/'


def pct_saving(ref, x):
    return 100.0 * (ref - x) / ref


def _mpc_label(d):
    mode = d['mode']
    pp = d.get('perfect_parts') or []
    base = {'perfect': 'Perfect forecast', 'naive': 'History-only forecast (same hour last week or yesterday)', 'weather': 'Weather-conditioned forecast',
            'weather_lag': 'Weather-conditioned forecast plus lagged load features', 'noisy': 'Perfect forecast plus synthetic error'}[mode]
    parts = []
    if mode == 'noisy':
        parts.append(f'error {d["level"]:g} x standard deviation')
    if pp:
        parts.append('true ' + ' and '.join({'load': 'household load', 'pv': 'PV', 'dem': 'tank demand'}[p] for p in pp))
    if d.get('peak_w'):
        parts.append(f'peak weight {d["peak_w"]:g}')
    if d.get('rc_perturb', 1.0) != 1.0:
        parts.append(f'planner room model x{d["rc_perturb"]:g}')
    if d.get('rc_margin'):
        parts.append(f'comfort margin {d["rc_margin"]:g} K')
    if d.get('rc_correct'):
        parts.append('online model correction')
    if d.get('scenarios', 1) > 1:
        parts.append(f'{d["scenarios"]} error scenarios')
        if d.get('share', 1) != 1:
            parts.append(f'{d["share"]} steps shared')
        if d.get('err_scale', 1.0) != 1.0:
            parts.append(f'errors scaled x{d["err_scale"]:g}')
    parts.append(f'horizon {d["horizon"]} h')
    return base + ' (' + ', '.join(parts) + ')'


def _mpc_group(d):
    if d.get('scenarios', 1) > 1:
        return 'mpc_stochastic'
    if d.get('rc_perturb', 1.0) != 1.0 or d.get('rc_margin') or d.get('rc_correct'):
        return 'mpc_model_error'
    if d.get('peak_w'):
        return 'mpc_peak'
    if d.get('perfect_parts') or d['mode'] == 'weather_lag':
        return 'mpc_ablation'
    return 'mpc_forecast'


def build(bb, ui, errors, nodes):
    """Returns (scenarios, controllers, pb) with `pb` the placeholder namespace for the `_phase_b` prose."""
    rj = bb.read_json
    pvb, rc, tar, q15 = rj(OR + 'oracle_pvbat.json'), rj(OR + 'oracle_rc.json'), rj(OR + 'oracle_tariffs.json'), rj(OR + 'oracle_q15.json')
    met, evleg, ref = rj(OR + 'phase_b_metrics.json'), rj(OR + 'ev_leg.json'), rj(OR + 'rl_reference.json')
    cfg = ui.get('_phase_b', {})
    pb = {}

    # ------------------------------------------------------------------ scenarios.json
    ceil = {}
    for s in SC:
        r = ref['scenarios'][s]
        ceil[s] = {'week': r['saving_pct'], 'year': r['year_saving_pct'], 'zero_bill_week': r['zero_bill_test_chf'], 'optimum_bill_week': r['optimum_bill_test_chf']}
    hourly = q15['hourly']
    ceil['s0'] = {'week': None, 'year': hourly['S0']['saving_pct']}
    pb['ceil'] = ceil
    pb['gate_pct'] = pvb['gate_pct']
    zero_year = {'s0': hourly['S0']['zero_bill'], 's1': hourly['S1']['zero_bill'], 's2': hourly['S2']['zero_bill'], 's3': hourly['S3 band 21-24']['zero_bill']}
    ladder = []
    for e in cfg.get('scenarios', {}).get('ladder', []):
        k = e['id'].lower()
        row = {'id': e['id'], 'name': e['name'], 'adds': e['adds'], 'classes': e.get('classes', []), 'nodes': e.get('nodes', []),
               'zero_bill_year_chf': zero_year[k], 'saving_year_pct': ceil[k]['year'], 'saving_week_pct': ceil[k]['week']}
        ladder.append(row)
    sweep = {}
    for p in ('0.0', '4.0', '8.0', '12.0'):
        sweep[p] = {'S1': pvb['rungs']['S1'][p]['saving_pct'], 'S2': pvb['rungs']['S2'][p]['saving_pct']}
        sweep[p]['S3'] = rc['bands']['band 21-24']['saving_pct'] if p == '8.0' else rc['export'][p]['saving_pct']
    pb['sweep'] = {f'{k.replace(".0", "")}': v for k, v in sweep.items()}
    pb['bands'] = {'s3_band_20_24': rc['bands']['band 20-24']['saving_pct'], 's3_band_21_24': rc['bands']['band 21-24']['saving_pct'],
                   's3_no_flex': rc['bands']['no thermal flexibility']['saving_pct']}
    pb['mass_points'] = rc['bands']['band 21-24']['saving_pct'] - rc['bands']['no thermal flexibility']['saving_pct']
    tariffs = []
    for k, t in tar['tariffs'].items():
        tariffs.append({'id': k, 'label': t['label'], 'spread_rp': t['spread_rp'], 'mean_rp': t['mean_rp'], 'S0': t['S0']['saving_pct'], 'S1': t['S1']['saving_pct'],
                        'S2': t['S2']['saving_pct'], 'S3': t['S3']['saving_pct']})
    pb['tariff_s2_min'] = min(t['S2'] for t in tariffs)
    pb['tariff_s2_max'] = max(t['S2'] for t in tariffs)
    pb['tariff_s0_max'] = max(t['S0'] for t in tariffs)
    resolution = []
    for name in ('S0', 'S1', 'S2', 'S3 band 21-24', 'S3 band 20-24'):
        resolution.append({'name': name, 'hourly_pct': q15['hourly'][name]['saving_pct'], 'q15_pct': q15['rungs'][name]['saving_pct']})
    pb['q15_gain_s2'] = q15['rungs']['S2']['saving_pct'] - q15['hourly']['S2']['saving_pct']
    ev = evleg['ev']
    ev_rows = [{'name': 'S2 without EV', 'zero_bill': ev['S2_no_ev']['zero_bill'], 'saving_pct': ev['S2_no_ev']['saving_pct']},
               {'name': 'S2 with EV, EV charges as measured', 'zero_bill': ev['S2_ev_uncontrolled_others_optimised']['zero_bill'], 'saving_pct': ev['S2_ev_uncontrolled_others_optimised']['saving_pct']},
               {'name': 'S2 with EV, EV charging optimised', 'zero_bill': ev['S2_ev_flexible']['zero_bill'], 'saving_pct': ev['S2_ev_flexible']['saving_pct']}]
    leg_rows = []
    for d, v in evleg['leg']['S2'].items():
        leg_rows.append({'discount': float(d), 'bill_with_leg': v['bill_with_leg'], 'bill_before_leg_credit': v['bill_before_leg_credit'], 'zero_bill_with_leg': v['zero_bill_with_leg'],
                         'internal_kwh': v['internal_kwh'], 'sharing_share_of_import': v['sharing_share_of_import']})
    pb['ev_value_chf'] = evleg['ev']['ev_flexibility_value_chf']
    pb['ev_value_pct'] = evleg['ev']['ev_flexibility_value_pct_of_zero_bill']
    pb['ev_annual_kwh'] = evleg['ev_info']['annual_kwh_per_ev']
    pb['leg_discount_max'] = max(r['discount'] for r in leg_rows) * 100
    peak_rows = []
    for name, r in met['rows'].items():
        peak_rows.append({'name': name, 'import_kwh': r['import_kwh'], 'peak_kw': r['peak_net_kw_coincident'], 'pv_self_consumption': r['pv_self_consumption'],
                          'self_sufficiency': r.get('self_sufficiency'), 'battery_cycles': r.get('battery_equivalent_cycles'), 'bill_chf': r['bill_chf'],
                          'emissions_index': r.get('emissions_index_vs_s0_zero')})
    mr = met['rows']
    pb['peak'] = {'s2_zero_kw': mr['S2 zero action']['peak_net_kw_coincident'], 's2_opt_kw': mr['S2 optimum']['peak_net_kw_coincident'],
                  's2_rise_pct': 100 * (mr['S2 optimum']['peak_net_kw_coincident'] / mr['S2 zero action']['peak_net_kw_coincident'] - 1),
                  's3_rise_pct': 100 * (mr['S3 optimum (band 21-24)']['peak_net_kw_coincident'] / mr['S3 thermostat']['peak_net_kw_coincident'] - 1),
                  's2_selfcons_zero': mr['S2 zero action']['pv_self_consumption'], 's2_selfcons_opt': mr['S2 optimum']['pv_self_consumption']}
    scenarios = {'ladder': ladder, 'ceilings': ceil, 'export_sweep': sweep, 'bands': pb['bands'], 'tariffs': tariffs, 'resolution': resolution,
                 'ev': ev_rows, 'leg': leg_rows, 'metrics': peak_rows, 'gate_pct': pvb['gate_pct'], 'export_price_rp': pvb['gate_export_rp'],
                 'sources': [OR + n + '.json' for n in ('oracle_pvbat', 'oracle_rc', 'oracle_tariffs', 'oracle_q15', 'phase_b_metrics', 'ev_leg', 'rl_reference')]}

    # ------------------------------------------------------------------ controllers.json
    summary = rj(RLR + 'phase_b_summary.json')
    base = {s: rj(RLR + f'baselines_{s}_weeks_bill.json') for s in SC}
    mp = {}
    for fn in sorted(os.listdir(bb._abs(MPCR))):
        if fn.startswith('mpc_s') and fn.endswith('.json'):
            d = rj(MPCR + fn)
            d['_file'] = fn
            mp.setdefault(d['scenario'], []).append(d)
    ferr = rj(MPCR + 'forecast_error.json')
    tw = rj(MPCR + 'forecast_nrmse_testweeks.json')                # forecaster errors measured on the eight test weeks (mpc_forecast_nrmse.py)
    out = {'scenarios': {}, 'rl_curves': [], 'sources': [RLR + 'phase_b_summary.json', MPCR]}
    comfort_rl = {}
    for s in SC:
        for kind in RL_KINDS:
            vals = []
            for seed in range(3):
                p = RLR + f'{s}_{kind}_bill_weeks_s{seed}/eval_final.json'
                if os.path.exists(bb._abs(p)):
                    f = rj(p)
                    vals.append(f['aggregate']['comfort_cold_kh'])
                    cp = RLR + f'{s}_{kind}_bill_weeks_s{seed}/eval_curve.csv'      # MARLISA is evaluated at the end only (no curve)
                    cv = bb.read_csv_dicts(cp) if os.path.exists(bb._abs(cp)) else []
                    if cv:
                        out['rl_curves'].append({'scenario': s, 'kind': kind, 'seed': seed, 'steps': [int(r['steps']) for r in cv],
                                                 'bill_change_pct': [float(r['cost_chf_vs_zero_pct']) for r in cv]})
            comfort_rl[(s, kind)] = float(np.mean(vals)) if vals else None
    for s in SC:
        b = base[s]
        refk = next(iter(b))
        zero = b[refk]['aggregate']
        rows = []
        rows.append({'id': 'optimum', 'group': 'optimum', 'label': 'Exact optimum with perfect foresight (upper reference)', 'saving_pct': ceil[s]['week'], 'corrected_pct': None,
                     'peak_kw': None, 'peak_vs_zero_pct': None, 'weekly_peak_kw': None, 'comfort_kh': None, 'n': None, 'spread_pct': None})
        for k in sorted(b):
            if k.startswith('pv_rule'):
                a = b[k]['aggregate']
                rows.append({'id': k, 'group': 'pv_rule', 'label': 'PV rule (rate ' + k.split('_r')[-1] + ' of capacity per hour)', 'saving_pct': pct_saving(zero['cost_chf'], a['cost_chf']),
                             'corrected_pct': pct_saving(zero['cost_corrected_chf'], a['cost_corrected_chf']), 'peak_kw': a['highest_hour_kw'],
                             'peak_vs_zero_pct': 100 * (a['highest_hour_kw'] / zero['highest_hour_kw'] - 1), 'weekly_peak_kw': a['mean_weekly_peak_kw'],
                             'comfort_kh': a['comfort_cold_kh'], 'n': None, 'spread_pct': None})
        for kind in RL_KINDS:
            r = summary.get(f'{s}_{kind}')
            if not r:
                rows.append({'id': f'rl_{kind}', 'group': 'rl', 'label': RL_LABEL[kind], 'saving_pct': None, 'n': 0, 'note': 'no finished run'})
                continue
            v = np.array(r['bill raw']); c = np.array(r['bill corrected']); h = np.array(r['highest hour'])
            rows.append({'id': f'rl_{kind}', 'group': 'rl', 'label': RL_LABEL[kind], 'saving_pct': float(-v.mean()), 'spread_pct': float(v.std()),
                         'corrected_pct': float(-c.mean()), 'peak_kw': None, 'peak_vs_zero_pct': float(h.mean()), 'weekly_peak_kw': None, 'comfort_kh': comfort_rl[(s, kind)],
                         'n': int(r['n']), 'steps_trained': int(np.mean(r['steps_trained']))})
        # MPC rows
        for d in sorted(mp.get(s, []), key=lambda x: x['_file']):
            a = d['mpc']
            rows.append({'id': d['_file'][:-5], 'group': _mpc_group(d), 'label': _mpc_label(d), 'mode': d['mode'], 'horizon': d['horizon'], 'level': d.get('level', 0.0),
                         'peak_w': d.get('peak_w', 0.0), 'rc_perturb': d.get('rc_perturb', 1.0), 'rc_margin': d.get('rc_margin', 0.0), 'rc_correct': bool(d.get('rc_correct', False)),
                         'scenarios': d.get('scenarios', 1), 'share': d.get('share', 1), 'err_scale': d.get('err_scale', 1.0), 'perfect_parts': d.get('perfect_parts', []),
                         'saving_pct': pct_saving(zero['cost_chf'], a['cost_chf']), 'corrected_pct': pct_saving(zero['cost_corrected_chf'], a['cost_corrected_chf']),
                         'peak_kw': a['highest_hour_kw'], 'peak_vs_zero_pct': 100 * (a['highest_hour_kw'] / zero['highest_hour_kw'] - 1),
                         'weekly_peak_kw': a['mean_weekly_peak_kw'], 'comfort_kh': a['comfort_cold_kh'], 'n': None, 'spread_pct': None})
        out['scenarios'][s] = {'name': SC_NAME[s], 'ceiling_pct': ceil[s]['week'], 'reference': {'label': 'Zero action' if s != 's3' else 'Thermostat', 'bill_chf': zero['cost_chf'],
                                'peak_kw': zero['highest_hour_kw'], 'weekly_peak_kw': zero['mean_weekly_peak_kw']}, 'rows': rows}

    for s in SC:                                  # share of the exact optimum each row reaches (rows without a saving or the optimum row itself get none)
        c = ceil[s]['week']
        for r in out['scenarios'][s]['rows']:
            r['share_of_ceiling_pct'] = 100.0 * r['saving_pct'] / c if (r.get('saving_pct') is not None and r['group'] != 'optimum') else None

    def find(s, **kw):
        for r in out['scenarios'][s]['rows']:
            if all(r.get(k) == v for k, v in kw.items()):
                return r
        return None

    def mpc(s, mode, horizon=48, **kw):
        base_kw = dict(group=None)
        for r in out['scenarios'][s]['rows']:
            if r['group'] and r['group'].startswith('mpc') and r['mode'] == mode and r['horizon'] == horizon and r['peak_w'] == kw.get('peak_w', 0.0) and \
               r['rc_perturb'] == kw.get('rc_perturb', 1.0) and r['rc_margin'] == kw.get('rc_margin', 0.0) and r['rc_correct'] == kw.get('rc_correct', False) and \
               r['scenarios'] == kw.get('scenarios', 1) and r['level'] == kw.get('level', 0.0) and r['perfect_parts'] == kw.get('perfect_parts', []) and r['share'] == kw.get('share', 1):
                return r
        return None

    # forecast quality (S2): synthetic error sweep, measured history-only error, weather-conditioned point
    pts = []
    for lvl in (0.0, 0.1, 0.3, 0.5):
        r = mpc('s2', 'perfect' if lvl == 0.0 else 'noisy', 48, level=lvl)
        pts.append({'x': lvl, 'saving_pct': r['saving_pct'], 'kind': 'synthetic' if lvl else 'perfect', 'label': 'Perfect forecast' if lvl == 0.0 else f'Perfect forecast plus error {lvl:g}'})
    hist = mpc('s2', 'naive', 48)
    weather = mpc('s2', 'weather', 48)
    out['forecast_quality'] = {'scenario': 's2', 'synthetic': pts,
                               'history_only': {'x': tw['history_only']['load'], 'saving_pct': hist['saving_pct'], 'label': 'History-only forecast (same hour last week)'},
                               'weather_conditioned': {'x': tw['weather']['load'], 'saving_pct': weather['saving_pct'], 'label': 'Weather-conditioned forecast', 'error_stored': True,
                                                       'pv_error': tw['weather']['pv'], 'demand_error': tw['weather']['dem']},
                               'measured_error': tw, 'ceiling_pct': ceil['s2']['week']}
    # peak trade-off
    to = {}
    for s in ('s2', 's3'):
        series = {}
        for mode in ('perfect', 'weather'):
            pts = []
            for w in (0.0, 0.1, 0.3, 1.0, 3.0):
                r = mpc(s, mode, 48, peak_w=w)
                if r:
                    pts.append({'peak_w': w, 'saving_pct': r['saving_pct'], 'peak_kw': r['peak_kw'], 'weekly_peak_kw': r['weekly_peak_kw'], 'comfort_kh': r['comfort_kh']})
            if pts:
                series[mode] = pts
        rule = find(s, id='pv_rule_r0.1')
        to[s] = {'series': series, 'zero_peak_kw': out['scenarios'][s]['reference']['peak_kw'], 'pv_rule': {'saving_pct': rule['saving_pct'], 'peak_kw': rule['peak_kw']}}
    out['peak_tradeoff'] = to
    # S3 model error
    me = []
    for r in out['scenarios']['s3']['rows']:
        if r['group'] == 'mpc_model_error' or (r['group'] == 'mpc_forecast' and r['mode'] == 'weather'):
            me.append({k: r[k] for k in ('label', 'rc_perturb', 'rc_margin', 'rc_correct', 'peak_w', 'saving_pct', 'comfort_kh', 'peak_kw')})
    out['model_error_s3'] = me
    # stochastic
    out['stochastic'] = [{k: r[k] for k in ('label', 'scenarios', 'share', 'err_scale', 'horizon', 'saving_pct', 'peak_kw')} for r in out['scenarios']['s2']['rows'] if r['group'] == 'mpc_stochastic']
    out['deterministic_reference'] = {k: mpc('s2', 'weather', 24)[k] for k in ('saving_pct', 'peak_kw', 'horizon')}

    # namespace for prose
    def sv(s, **kw):
        r = mpc(s, kw.pop('mode'), kw.pop('horizon', 48), **kw)
        return r['saving_pct']
    pb['mpc'] = {
        's1': {'perfect': sv('s1', mode='perfect'), 'weather': sv('s1', mode='weather'), 'rule': find('s1', id='pv_rule_r0.1')['saving_pct']},
        's2': {'perfect': sv('s2', mode='perfect'), 'weather': sv('s2', mode='weather'), 'naive': sv('s2', mode='naive'), 'rule': find('s2', id='pv_rule_r0.1')['saving_pct'],
               'weather_peak01': sv('s2', mode='weather', peak_w=0.1), 'perfect_peak03': sv('s2', mode='perfect', peak_w=0.3),
               'weather_peak01_kw': mpc('s2', 'weather', 48, peak_w=0.1)['peak_kw'], 'weather_kw': mpc('s2', 'weather', 48)['peak_kw'], 'zero_kw': out['scenarios']['s2']['reference']['peak_kw'],
               'true_load': sv('s2', mode='weather', perfect_parts=['load'])},
        's3': {'perfect': sv('s3', mode='perfect'), 'weather': sv('s3', mode='weather'), 'rule': find('s3', id='pv_rule_r0.1')['saving_pct'],
               'x08_cold': mpc('s3', 'weather', 48, rc_perturb=0.8)['comfort_kh'],
               'x08_corr_m02_cold': mpc('s3', 'weather', 48, rc_perturb=0.8, rc_margin=0.2, rc_correct=True)['comfort_kh'],
               'x08_corr_m02': sv('s3', mode='weather', rc_perturb=0.8, rc_margin=0.2, rc_correct=True)}}
    pb['rl'] = {s: {k: (find(s, id=f'rl_{k}') or {}).get('saving_pct') for k in RL_KINDS} for s in SC}
    pb['rl_n'] = sum(1 for _ in out['rl_curves'])
    full = [r for r in out['stochastic'] if r['err_scale'] == 1.0]          # errors at the measured size; scaled-down errors are a diagnostic
    pb['stoch'] = {'min': min(r['saving_pct'] for r in full), 'max': max(r['saving_pct'] for r in full), 'det': out['deterministic_reference']['saving_pct']}
    pb['forecast'] = {'history_load': tw['history_only']['load'], 'history_pv': tw['history_only']['pv'], 'history_dem': tw['history_only']['dem'],
                      'weather_load': tw['weather']['load'], 'weather_pv': tw['weather']['pv'], 'weather_dem': tw['weather']['dem']}
    pb['share_of_ceiling_s2'] = 100 * pb['mpc']['s2']['weather'] / ceil['s2']['week']
    pb['share_of_ceiling_s3'] = 100 * pb['mpc']['s3']['weather'] / ceil['s3']['week']

    # limitations pulled from the registry nodes (ids chosen in ui_map `_phase_b.limitations`)
    lim = []
    for nid in cfg.get('limitations', []):
        n = nodes.get(nid)
        if not n:
            errors.append(f'phase_b: limitation {nid} is not a registry node')
            continue
        lim.append({'id': nid, 'kind': n['kind'], 'title': n.get('title'), 'summary': n.get('summary'), 'status': n.get('status')})
    out['limitations'] = lim

    # prose filled from ui_map (numbers only through placeholders)
    data_ns = {'pb': pb}
    prose = {}
    for page in ('scenarios', 'controllers'):
        sec = cfg.get(page, {})
        filled = {}
        for k, v in sec.items():
            if isinstance(v, str):
                filled[k] = bb.fill(v, data_ns, errors, f'_phase_b.{page}.{k}')
            elif isinstance(v, list) and k != 'ladder':
                filled[k] = [bb.fill(x, data_ns, errors, f'_phase_b.{page}.{k}') if isinstance(x, str) else x for x in v]
        prose[page] = filled
    for e in ladder:
        e['adds'] = bb.fill(e['adds'], data_ns, errors, f'_phase_b.ladder.{e["id"]}')
    scenarios['prose'] = prose.get('scenarios', {})
    out['prose'] = prose.get('controllers', {})
    return scenarios, out, pb
