"""Phase C scenario matrix (WP3) and robustness runs (WP4): climate scenario x cooling adoption cells.

Cells: scenarios hist, hist_hw99, gwl2.0, gwl2.0_hw99, gwl3.0, gwl3.0_hw99 x adoption none, low, medium, high (24) + high_alt for gwl3.0 and gwl3.0_hw99 (26).
Per cell, as separate tasks (multiprocessing, results in swiss/experiments/climate_results/<cell>__<task>.json):
  year            exact optimum of the year (bands 'band' and 'pinned'; mass value = saving(band) - saving(pinned)), the ceiling on the eight held-out weeks, full-year CityLearn
                  rollouts of the thermostat reference and of the replayed band optimum with climate_metrics (added consumption, PV coverage of cooling, import/export, peaks,
                  degree-hours above 26 C, emissions), hourly district series of week 29
  weeks:<ctrl>    controller study on the eight held-out weeks (rl.TEST_WEEKS; week 29 holds the inserted spell in the *_hw99 scenarios), ctrl in thermostat, pv_rule, mpc, mpc_peak0.1
Aggregation (`aggregate`): docs/experiments/validation_reports/climate_matrix.md and swiss/experiments/climate_results/climate_summary.json.
Robustness (`robust`): MPC on the heat-wave cells with high adoption, forecasters trained on 2023 only against trained on the scenario, and synthetic weather forecast error.

Run: PYTHONPATH=. cl/bin/python swiss/experiments/climate_matrix.py run [--workers 11] [--cells a b]   |   aggregate   |   robust [--workers 11]
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
import warnings

for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):       # one thread per worker (the WP3 run showed a load average of 35 on 12 cores)
    os.environ[_v] = '1'
ARCH = sys.argv[sys.argv.index('--arch') + 1] if '--arch' in sys.argv else os.environ.get('CLIMATE_ARCH', 'central')    # 'central' = archetype A, 'ru' = archetype B (room units)
os.environ['CLIMATE_ARCH'] = ARCH                                                 # inherited by the spawned workers

import numpy as np

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

RES_A = os.path.join(ROOT, 'swiss', 'experiments', 'climate_results')
RES = os.path.join(ROOT, 'swiss', 'experiments', 'climate_results_ru') if ARCH == 'ru' else RES_A
SUMMARY = os.path.join(RES, 'climate_summary_ru.json' if ARCH == 'ru' else 'climate_summary.json')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'climate_matrix_ru.md' if ARCH == 'ru' else 'climate_matrix.md')
SCENARIOS = ('hist', 'hist_hw99', 'gwl2.0', 'gwl2.0_hw99', 'gwl3.0', 'gwl3.0_hw99')
ADOPTION = ('none', 'low', 'medium', 'high')
CTRLS = ('thermostat', 'pv_rule', 'mpc', 'mpc_peak0.1')
EXPORT_RP = 8.0
WEEK29 = (4872, 5040)


def all_cells():
    if ARCH == 'ru':                                            # archetype B: low, medium, high x six scenarios at the default cooled fraction + the two sensitivities
        from swiss.pipeline import build_climate_datasets as bcd
        return [bcd.cell_name(s, a, fr) for s, a, fr in bcd.ru_cells()]
    cells = [f'{s}_{a}' for s in SCENARIOS for a in ADOPTION]
    cells += ['gwl3.0_high_alt', 'gwl3.0_hw99_high_alt']
    return cells


def parse_cell(cell):
    """(scenario, adoption, cooled fraction or None) of a cell name; archetype B cells end in _ru (default fraction), _ru0.2, _ru0.6."""
    from swiss.pipeline import build_climate_datasets as bcd
    frac = None
    if '_ru' in cell:
        cell, suffix = cell.rsplit('_ru', 1)
        frac = bcd.RU_FRACTION if suffix == '' else float(suffix)
    for a in ('high_alt',) + ADOPTION[::-1]:
        if cell.endswith('_' + a):
            return cell[:-(len(a) + 1)], a, frac
    raise ValueError(cell)


def split_cell(cell):
    sc, ad, _ = parse_cell(cell)
    return sc, ad


def ensure_datasets(cells):
    from swiss.pipeline import build_climate_datasets as bcd
    for c in cells:
        sc, ad, fr = parse_cell(c)
        d = bcd.cell_dir(sc, ad, fr)
        if not (os.path.exists(os.path.join(d, 'schema.json')) and os.path.exists(os.path.join(d, 'build_manifest.json'))):
            print('building cell dataset', c, flush=True)
            bcd.build_cell(sc, ad, fraction=fr)


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return [jsonable(v) for v in x.tolist()]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def test_index():
    from swiss.experiments import rl
    return np.concatenate([np.arange(s, e + 1) for s, e in rl.test_windows('weeks')])


def rollout_year(inp, make_agent):
    from citylearn.citylearn import CityLearnEnv
    from swiss.experiments.rewards import SwissDistrictReward
    env = CityLearnEnv(os.path.join(inp.dir, 'schema.json'), central_agent=True, reward_function=SwissDistrictReward)
    ag = make_agent(env)
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    return env


def year_metrics(inp, env):
    """climate_metrics of a full-year rollout, compact (JSON-ready), plus emissions and the hourly district series of week 29."""
    from swiss.experiments import climate_metrics as cm
    ser = cm.series_from_env(env)
    n = len(ser[0]['base'])
    months = inp.month[:n]
    out = {'steps': int(n)}
    for prio in ('default', 'hp_first'):
        d = cm.district_metrics(ser, months, prio)
        d.pop('net_kwh_per_step')
        out[prio] = {k: v for k, v in d.items() if k != 'buildings'}
        out[prio]['buildings'] = {r: {k: b[k] for k in ('annual', 'summer', 'degree_hours_above', 'peak_net_kw')} for r, b in zip(inp.roles, d['buildings'])}
    ci = inp.carbon[:n]
    imp = sum(np.maximum(s['net'], 0) for s in ser)
    out['emissions_kg'] = float((imp * ci).sum())
    out['import_building_level_kwh'] = float(imp.sum())
    sl = slice(WEEK29[0], WEEK29[1])
    w = {k: np.sum([s[k][sl] for s in ser], axis=0) for k in ('base', 'dhw', 'heat', 'cool', 'pv', 'batt', 'net')}
    out['week29_district'] = {k: np.round(v, 3).tolist() for k, v in w.items()}
    out['week29_temp_by_building'] = {r: np.round(s['temp'][sl], 2).tolist() for r, s in zip(inp.roles, ser)}
    return out


def task_year(cell):
    from swiss.experiments import climate_controllers as cc, oracle, oracle_climate as oc
    inp = oc.ClimateInputs(cell)
    n = inp.N
    res = {'cell': cell, 'cooled': [r for r, c in zip(inp.roles, inp.cooled) if c], 'cooled_fraction': next((f for f, c in zip(inp.frac, inp.cooled) if c), None)}
    sols_band = None
    t0 = time.time()
    for band in ('band', 'pinned'):
        tot, sols = oc.solve_cell(inp, band, EXPORT_RP, n)
        res[band] = tot
        if band == 'band':
            sols_band = sols
        idx = test_index()
        price = inp.price
        zero = sum(float((price[idx] * np.maximum(s['net_base'][idx], 0)).sum() - 0.08 * np.maximum(-s['net_base'][idx], 0).sum()) for s in sols)
        opt = sum(float((price[idx] * s['imp'][idx]).sum() - 0.08 * s['exp'][idx].sum()) for s in sols)
        res[band]['test_weeks'] = {'zero_bill_chf': zero, 'opt_bill_chf': opt, 'saving_pct': 100.0 * (zero - opt) / zero}
    res['mass_value_pts'] = res['band']['saving_pct'] - res['pinned']['saving_pct']
    res['lp_seconds'] = time.time() - t0
    t0 = time.time()
    env_th = rollout_year(inp, lambda env: cc.ThermostatAgentCool(env))
    res['thermostat_year'] = year_metrics(inp, env_th)
    sched = oc.schedule(env_th, inp, sols_band, inp.N)
    env_op = rollout_year(inp, lambda env: oracle.Replay(sched))
    res['optimum_year'] = year_metrics(inp, env_op)
    res['rollout_seconds'] = time.time() - t0
    return res


def make_controller(ctrl, inp, fc=None, view=None, margin=0.0, correct=False):
    from swiss.experiments import climate_controllers as cc
    if ctrl == 'thermostat':
        return lambda env, s0: cc.ThermostatAgentCool(env)
    if ctrl == 'pv_rule':
        return lambda env, s0: cc.PVRuleCool(env, 0.1)
    fc = fc or cc.ClimateForecaster(inp, 'weather')
    pw = 0.1 if ctrl == 'mpc_peak0.1' else 0.0
    return lambda env, s0: cc.MPCClimate(env, s0, inp, fc, 48, peak_w=pw, margin=margin, correct=correct, view=view)


def task_weeks(cell, ctrl, fc=None, view=None, margin=0.0, correct=False, weeks=None):
    from swiss.experiments import climate_controllers as cc, oracle_climate as oc, rl
    rl.use_scenario('s3')
    inp = oc.ClimateInputs(cell)
    mk = make_controller(ctrl, inp, fc, view, margin, correct)
    rows = []
    t0 = time.time()
    for k in (weeks or rl.TEST_WEEKS):
        m = cc.play_window(inp.dir, mk, rl.window(k))
        m['week'] = k
        rows.append(m)
    agg = cc.aggregate_windows(rows)
    return {'cell': cell, 'ctrl': ctrl, 'aggregate': agg, 'windows': rows, 'seconds': time.time() - t0}


def worker(args):
    cell, task = args
    fn = os.path.join(RES, f'{cell}__{task.replace(":", "_")}.json')
    if os.path.exists(fn):
        return cell, task, 'cached'
    t0 = time.time()
    try:
        out = task_year(cell) if task == 'year' else task_weeks(cell, task.split(':')[1])
        out['wall_seconds'] = time.time() - t0
        json.dump(jsonable(out), open(fn, 'w'))
        return cell, task, f'ok {time.time() - t0:.0f}s'
    except Exception:
        return cell, task, 'ERROR ' + traceback.format_exc()[-600:]


def run(workers=11, cells=None):
    os.makedirs(RES, exist_ok=True)
    cells = cells or all_cells()
    ensure_datasets(cells)
    tasks = [(c, f'weeks:{k}') for c in cells for k in ('mpc_peak0.1', 'mpc')] + [(c, 'year') for c in cells] + [(c, f'weeks:{k}') for c in cells for k in ('pv_rule', 'thermostat')]
    ctx = mp.get_context('spawn')
    t0 = time.time()
    with ctx.Pool(workers, maxtasksperchild=1) as pool:
        for cell, task, status in pool.imap_unordered(worker, tasks):
            print(f'[{time.time() - t0:6.0f}s] {cell:22s} {task:16s} {status}', flush=True)


# ------------------------------------------------------------------------------------------------------------------------------ aggregation
def load(cell, task):
    fn = os.path.join(RES, f'{cell}__{task.replace(":", "_")}.json')
    return json.load(open(fn)) if os.path.exists(fn) else None


def week_share(ctrl_agg, ceiling_pct, thermo_cost):
    sav = 100.0 * (thermo_cost - ctrl_agg['cost_chf']) / abs(thermo_cost) if thermo_cost else None
    return sav


def aggregate():
    cells = all_cells()
    S = {'cells': {}, 'export_price_rp': EXPORT_RP, 'test_weeks': None}
    for c in cells:
        yr = load(c, 'year')
        if yr is None:
            continue
        rec = {'cooled': yr['cooled'], 'cooled_fraction': yr.get('cooled_fraction'), 'ceiling_year_pct': yr['band']['saving_pct'], 'pinned_year_pct': yr['pinned']['saving_pct'], 'mass_value_pts': yr['mass_value_pts'],
               'ceiling_weeks_pct': yr['band']['test_weeks']['saving_pct'], 'pinned_weeks_pct': yr['pinned']['test_weeks']['saving_pct'],
               'zero_bill_chf': yr['band']['zero_bill_chf'], 'opt_bill_chf': yr['band']['opt_bill_chf'],
               'cooling_kwh': yr['band']['cooling_electricity_kwh'], 'heating_kwh': yr['band']['heating_electricity_kwh'],
               'import_kwh': yr['band']['import_kwh'], 'export_kwh': yr['band']['export_kwh'], 'peak_kw': yr['band']['peak_kw'],
               'degree_hours_above_26': yr['band']['degree_hours_above_26'], 'emissions_kg': yr['band']['emissions_kg'], 'pv_self_consumption': yr['band']['pv_self_consumption'],
               'thermostat_year': {k: yr['thermostat_year'][k] for k in ('default', 'hp_first', 'emissions_kg')}, 'optimum_year': {k: yr['optimum_year'][k] for k in ('default', 'hp_first', 'emissions_kg')},
               'week29': {'thermostat': yr['thermostat_year']['week29_district'], 'optimum': yr['optimum_year']['week29_district']}, 'controllers': {}}
        th = load(c, 'weeks:thermostat')
        for k in CTRLS:
            w = load(c, f'weeks:{k}')
            if w is None:
                continue
            a = w['aggregate']
            e = {'cost_chf': a['cost_chf'], 'cost_corrected_chf': a['cost_corrected_chf'], 'comfort_cold_kh': a['comfort_cold_kh'], 'degree_hours_above_26': a['degree_hours_above_26'],
                 'highest_hour_kw': a['highest_hour_kw'], 'mean_weekly_peak_kw': a['mean_weekly_peak_kw'], 'cooling_electricity_kwh': a['cooling_electricity_kwh'],
                 'heating_electricity_kwh': a['heating_electricity_kwh'], 'import_kwh': a['import_kwh'], 'export_kwh': a['export_kwh'], 'solve_seconds': a['solve_seconds']}
            if th:
                tc = th['aggregate']['cost_chf']
                e['saving_pct'] = 100.0 * (tc - a['cost_chf']) / abs(tc)
                e['saving_corrected_pct'] = 100.0 * (th['aggregate']['cost_corrected_chf'] - a['cost_corrected_chf']) / abs(th['aggregate']['cost_corrected_chf'])
                ceil = rec['ceiling_weeks_pct']
                e['share_of_ceiling'] = e['saving_pct'] / ceil if ceil > 1e-9 else None
            rec['controllers'][k] = e
        S['cells'][c] = rec
    # difference-method pairs against the 'none' cell of the same scenario (archetype B: the heating-only cell of archetype A, read-only: the heating-only district is identical)
    base_cells = S['cells']
    if ARCH == 'ru':
        base_cells = json.load(open(os.path.join(RES_A, 'climate_summary.json')))['cells']
    for c, rec in S['cells'].items():
        sc, ad = split_cell(c)
        base = base_cells.get(f'{sc}_none')
        if base is None or ad == 'none':
            continue
        d = {}
        for tag, key in (('thermostat', 'thermostat_year'), ('optimum', 'optimum_year')):
            a, b = rec[key]['default'], base[key]['default']
            d[tag] = {'cool_kwh': a['annual']['cool'] - b['annual']['cool'], 'heat_kwh': a['annual']['heat'] - b['annual']['heat'],
                      'import_kwh': a['annual']['import'] - b['annual']['import'], 'export_kwh': a['annual']['export'] - b['annual']['export'],
                      'summer_import_kwh': a['summer']['import'] - b['summer']['import'], 'summer_peak_kw': (a['summer_peak_net_kw'] or 0) - (b['summer_peak_net_kw'] or 0),
                      'peak_kw': a['peak_net_kw'] - b['peak_net_kw'], 'degree_hours_above_26': a['degree_hours_above'] - b['degree_hours_above'],
                      'emissions_kg': rec[key]['emissions_kg'] - base[key]['emissions_kg']}
        rec['difference_vs_none'] = d
    json.dump(jsonable(S), open(SUMMARY, 'w'))
    write_report(S)
    return S


def f1(x, nd=1):
    return '-' if x is None else f'{x:.{nd}f}'


def write_report(S):
    C = S['cells']
    L = ['# Phase C scenario matrix: climate x cooling adoption (WP3)' if ARCH != 'ru' else '# Phase C scenario matrix, archetype B (room units): climate x cooling adoption (WP2b)', '',
         ('' if ARCH != 'ru' else 'ARCHETYPE B: in a cooled building only a fraction of the floor area (default 0.4, assumption A-058, no source) is cooled by room units (two independent zones, capacity proportional); '
          'the rest of the building floats. Cell names end in `_ru` (`_ru0.2`, `_ru0.6` sensitivities). The difference-method rows compare with the heating-only cell of archetype A. ')
         + 'Generated by `swiss/experiments/climate_matrix.py aggregate' + (' --arch ru' if ARCH == 'ru' else '') + '` from `' + os.path.relpath(RES, ROOT) + '/`. Nothing here is typed by hand. Every cell is an S3 district '
         '(assumed PV, battery, RC building; export 8 Rp/kWh) with cooling in the cooled buildings; climate scenarios are CH2025 delta-change years built on observed 2023 weather '
         '(`climate_scenarios.md`); `*_hw99` = the 99th-percentile heat-wave week inserted in week 29. Cooling demand, COP, device and adoption are modelled or assumed (see the registry '
         'drafts), none is measured. Reference = thermostat (heat to 21 C, cool to 26 C where a cooling device exists). Year ceilings are perfect-foresight exact optima (comfort band 21 to 24 '
         'C, 26 C in the cooling season for cooled buildings); the held-out-week ceilings evaluate the same optimum on the eight test weeks.', '']
    L += ['## 1. Ceilings (year, perfect foresight)', '',
          '| Cell | Cooled | Ceiling year | Ceiling test weeks | Mass value (pts) | Cooling el. thermostat / optimum (kWh) | Heating el. thermostat / optimum (kWh) | Peak kW thermostat / optimum | Summer peak kW thermostat / optimum | Degree-hours > 26 C (all buildings, thermostat) |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for c, r in C.items():
        L.append(f'| {c} | {", ".join(r["cooled"]) or "-"} | {f1(r["ceiling_year_pct"], 2)} % | {f1(r["ceiling_weeks_pct"], 2)} % | {f1(r["mass_value_pts"], 2)} | '
                 f'{f1(r["cooling_kwh"]["baseline"], 0)} / {f1(r["cooling_kwh"]["optimum"], 0)} | {f1(r["heating_kwh"]["baseline"], 0)} / {f1(r["heating_kwh"]["optimum"], 0)} | '
                 f'{f1(r["peak_kw"]["baseline"])} / {f1(r["peak_kw"]["optimum"])} | {f1(r["peak_kw"]["summer_baseline"])} / {f1(r["peak_kw"]["summer_optimum"])} | {f1(r["degree_hours_above_26"]["baseline"], 0)} |')
    L += ['', '## 2. Controllers on the eight held-out weeks (saving against the thermostat on the same weeks, share of the held-out-week ceiling)', '',
          '| Cell | Ceiling weeks | PV rule | MPC | MPC peak 0.1 | Highest hour kW: thermostat / PV rule / MPC / MPC peak 0.1 | Cold K h (MPC) | Degree-hours > 26 C (thermostat / MPC) | Cooling el. kWh (thermostat / MPC) |',
          '|---|---|---|---|---|---|---|---|---|']
    for c, r in C.items():
        k = r['controllers']
        if not k:
            continue
        g = lambda n, key: k.get(n, {}).get(key)   # noqa: E731
        sh = lambda n: '-' if g(n, 'saving_pct') is None else f'{g(n, "saving_pct"):.2f} % ({100 * (g(n, "share_of_ceiling") or 0):.0f} %)'   # noqa: E731
        L.append(f'| {c} | {f1(r["ceiling_weeks_pct"], 2)} % | {sh("pv_rule")} | {sh("mpc")} | {sh("mpc_peak0.1")} | '
                 f'{f1(g("thermostat", "highest_hour_kw"))} / {f1(g("pv_rule", "highest_hour_kw"))} / {f1(g("mpc", "highest_hour_kw"))} / {f1(g("mpc_peak0.1", "highest_hour_kw"))} | '
                 f'{f1(g("mpc", "comfort_cold_kh"))} | {f1(g("thermostat", "degree_hours_above_26"), 0)} / {f1(g("mpc", "degree_hours_above_26"), 0)} | '
                 f'{f1(g("thermostat", "cooling_electricity_kwh"), 0)} / {f1(g("mpc", "cooling_electricity_kwh"), 0)} |')
    L += ['', '## 3. Difference method: every cooled cell against the heating-only cell of the same climate (thermostat reference and year optimum)', '',
          '| Cell | Added cooling el. (kWh) | Heating el. change (kWh) | Annual import change (kWh) | Annual export change (kWh) | Summer import change (kWh) | Summer peak change (kW) | Peak change (kW) | Degree-hours > 26 C change | Emissions change (kg) |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for c, r in C.items():
        d = r.get('difference_vs_none')
        if not d:
            continue
        for tag in ('thermostat', 'optimum'):
            x = d[tag]
            L.append(f'| {c} ({tag}) | {f1(x["cool_kwh"], 0)} | {f1(x["heat_kwh"], 0)} | {f1(x["import_kwh"], 0)} | {f1(x["export_kwh"], 0)} | {f1(x["summer_import_kwh"], 0)} | '
                     f'{f1(x["summer_peak_kw"])} | {f1(x["peak_kw"])} | {f1(x["degree_hours_above_26"], 0)} | {f1(x["emissions_kg"], 0)} |')
    L += ['', '## 4. PV and battery coverage of cooling electricity (year, thermostat reference | optimum; PV priority rule `default`: base, DHW, heat pump, battery; `hp_first`: heat pump first)', '',
          '| Cell | PV directly | Battery | Grid | PV directly (hp_first) | Cooling el. (kWh) |', '|---|---|---|---|---|---|']
    for c, r in C.items():
        if not r['cooled']:
            continue
        def share(key, prio='default'):
            a = r[key][prio]['buildings']
            cool = sum(a[b]['annual']['cool'] for b in a)
            if cool <= 1e-9:
                return None, None, None, cool
            pv = sum(a[b]['annual']['pv_share_of_cooling'] * a[b]['annual']['cool'] for b in a if a[b]['annual']['pv_share_of_cooling'] is not None) / cool
            ba = sum(a[b]['annual']['battery_share_of_cooling'] * a[b]['annual']['cool'] for b in a if a[b]['annual']['battery_share_of_cooling'] is not None) / cool
            gr = sum(a[b]['annual']['grid_share_of_cooling'] * a[b]['annual']['cool'] for b in a if a[b]['annual']['grid_share_of_cooling'] is not None) / cool
            return pv, ba, gr, cool
        t, o_ = share('thermostat_year'), share('optimum_year')
        th_ = share('thermostat_year', 'hp_first'); oh_ = share('optimum_year', 'hp_first')
        pc = lambda x: '-' if x is None else f'{100 * x:.0f} %'   # noqa: E731
        L.append(f'| {c} | {pc(t[0])} / {pc(o_[0])} | {pc(t[1])} / {pc(o_[1])} | {pc(t[2])} / {pc(o_[2])} | {pc(th_[0])} / {pc(oh_[0])} | {f1(t[3], 0)} / {f1(o_[3], 0)} |')
    rob = os.path.join(RES, 'robustness.json')
    if os.path.exists(rob):
        L += ['', open(os.path.join(RES, 'robustness_section.md')).read()] if os.path.exists(os.path.join(RES, 'robustness_section.md')) else []
    L += ['', '## Limits', '- Cooling is modelled (A-040 to A-047): reversible heat pump, cooling off below 15 C outdoors, 26 C cooling season set point; adoption levels are labelled defaults '
          '(whole buildings by dwelling-unit share); one station (Kloten) and 2023 weather; heat waves come from model chains made hourly (`climate_scenarios.md`).',
          '- The household load is a synthetic composite (ISS-040); the MPC uses known weather (A-028) and forecasts of load, DHW demand and PV trained outside the test weeks.',
          '- Exact optima are perfect-foresight upper bounds; PV allocation shares are a bookkeeping rule (`climate_metrics.py`), not a physical attribution.', '']
    open(REPORT, 'w', encoding='utf-8').write('\n'.join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'aggregate', 'robust', 'build', 'cells', 'one'])
    ap.add_argument('--cell', default=None, help='one: the cell')
    ap.add_argument('--task', default=None, help='one: year | weeks:thermostat | weeks:pv_rule | weeks:mpc | weeks:mpc_peak0.1')
    ap.add_argument('--arch', choices=['central', 'ru'], default='central', help='central = archetype A (results in climate_results/), ru = archetype B room units (climate_results_ru/)')
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--cells', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'cells':                                         # for swiss/hpc/submit_climate_matrix.sh: the cell list of the architecture, one per line
        print('\n'.join(all_cells()))
    elif a.cmd == 'build':                                       # build the cell datasets of the architecture (cluster prerequisite job)
        ensure_datasets(all_cells())
    elif a.cmd == 'one':                                         # one (cell, task), cached like the pool workers (cluster task job)
        os.makedirs(RES, exist_ok=True)
        ensure_datasets([a.cell])
        print(worker((a.cell, a.task)), flush=True)
    elif a.cmd == 'run':
        run(a.workers, a.cells)
    elif a.cmd == 'aggregate':
        aggregate()
    else:
        from swiss.experiments import climate_robust
        climate_robust.run(a.workers)


if __name__ == '__main__':
    main()
