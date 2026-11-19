"""Hourly heat-wave-week series for the scenario explorer (Phase C, WP5b).

Rolls out week 29 (the week that holds the inserted heat wave, steps 4872 to 5039) of the heat-wave cells for the PV rule, the MPC and the MPC with peak weight 0.1, with
the same controllers, datasets, forecasters (weather-conditioned, weather taken as known, A-028) and warm-up (96 steps from empty tanks, as rl.play) as the matrix of
swiss/experiments/climate_matrix.py, and writes district hourly series (kWh per hour) to swiss/dashboard/data/climate_weeks.json. The thermostat and the exact optimum
series of the same week come from the full-year replays already stored in swiss/experiments/climate_results/climate_summary.json (week29), so they are not repeated here.
Cells: hist_hw99, gwl2.0_hw99, gwl3.0_hw99 x adoption none and high (central archetype). One thread per worker, at most six workers.
Note on comparability: the optimum series continues the year-long replay (carried-in storage state), the controllers here start the week from empty tanks after a 96 step
warm-up, so the first hours of the week can differ a little between the two groups.

Archetype B (room units, WP5c): `--arch ru` rolls out the heat-wave week of the cells hist_hw99, gwl2.0_hw99 and gwl3.0_hw99 with adoption high at the default cooled fraction
(cell names `<scenario>_high_ru`; the adoption `none` cells are shared with archetype A) and writes swiss/dashboard/data/climate_weeks_ru.json; archetype A's file is not touched.

Run: cl/bin/python -I swiss/dashboard/climate_series.py [--workers 6] [--arch central|ru]
"""
import os

for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'

import argparse  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402

import numpy as np  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, 'swiss', 'dashboard', 'data', 'climate_weeks.json')
OUT_RU = os.path.join(ROOT, 'swiss', 'dashboard', 'data', 'climate_weeks_ru.json')
CELLS = [f'{s}_{a}' for s in ('hist_hw99', 'gwl2.0_hw99', 'gwl3.0_hw99') for a in ('none', 'high')]
CELLS_RU = [f'{s}_high_ru' for s in ('hist_hw99', 'gwl2.0_hw99', 'gwl3.0_hw99')]
CTRLS = ('pv_rule', 'mpc', 'mpc_peak0.1')
WEEK = 29


def district(ser):
    keys = ('base', 'dhw', 'heat', 'cool', 'pv', 'batt', 'net')
    return {k: [round(float(v), 3) for v in np.sum([s[k] for s in ser], axis=0)] for k in keys}


def run_cell(cell):
    """All three controllers on one cell (the forecaster is trained once per cell). Returns {ctrl: {district arrays, summary}}."""
    from swiss.experiments import climate_controllers as cc, climate_matrix as cmx, climate_metrics as cm, oracle_climate as oc, rl
    rl.use_scenario('s3')
    inp = oc.ClimateInputs(cell)
    fc = cc.ClimateForecaster(inp, 'weather')
    out = {}
    for ctrl in CTRLS:
        t0 = time.time()
        mk = cmx.make_controller(ctrl, inp, fc)
        s, e = rl.window(WEEK)
        s0 = max(0, s - rl.WARM)
        rl.SCHEMA = os.path.join(inp.dir, 'schema.json')
        env = rl.make_env(True, 'bill', windows=(s0, min(e + 1, rl.LAST_STEP)))
        agent = mk(env, s0)
        obs, _ = env.reset()
        rewards = []
        while not env.terminated:
            obs, r, *_ = env.step(agent.predict(obs))
            rewards.append(float(np.sum(r)))
        i0, i1 = s - s0, e - s0
        ser = cm.series_from_env(env, i0, i1)
        d = district(ser)
        d['seconds'] = round(time.time() - t0, 1)
        out[ctrl] = d
    return cell, out


def worker(cell):
    try:
        return run_cell(cell)
    except Exception:
        return cell, {'error': traceback.format_exc()[-800:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--arch', default='central', choices=['central', 'ru'])
    a = ap.parse_args()
    from swiss.pipeline import build_climate_datasets as bcd
    cells, out_path = (CELLS_RU, OUT_RU) if a.arch == 'ru' else (CELLS, OUT)
    for c in cells:
        if a.arch == 'ru':
            sc, ad = c[:-len('_high_ru')], 'high'
            d, fr = bcd.cell_dir(sc, ad, bcd.RU_FRACTION), bcd.RU_FRACTION
        else:
            sc, ad = c.rsplit('_', 1)
            d, fr = bcd.cell_dir(sc, ad), None
        if not os.path.exists(os.path.join(d, 'schema.json')):
            bcd.build_cell(sc, ad, fraction=fr)
    res = {}
    ctx = mp.get_context('spawn')
    t0 = time.time()
    with ctx.Pool(min(a.workers, 6), maxtasksperchild=1) as pool:
        for cell, out in pool.imap_unordered(worker, cells):
            res[cell] = out
            print(f'[{time.time() - t0:5.0f}s] {cell}', 'ERROR' if 'error' in out else 'ok', flush=True)
            if 'error' in out:
                print(out['error'], flush=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({'week': WEEK, 'steps': [4872, 5039], 'unit': 'kWh per hour, district sum of six buildings', 'warm_steps': 96, 'archetype': 'room_units' if a.arch == 'ru' else 'central',
               'controllers': list(CTRLS), 'cells': res}, open(out_path, 'w'), separators=(',', ':'))
    print('written', out_path, f'{os.path.getsize(out_path) / 1e3:.0f} kB')


if __name__ == '__main__':
    main()
