"""WP4 robustness of the MPC on the heat-wave cells with high cooling adoption (gwl3.0_hw99_high, gwl2.0_hw99_high, hist_hw99_high), eight held-out weeks.

Cases (all with weather taken as known by the planner unless the case says otherwise; synthetic errors are fixed-seed and LABELLED SYNTHETIC, A-031 style):
  scenario        forecasters (load, DHW demand, PV) trained on the scenario's own year (the matrix `mpc` run)
  trained_hist    forecasters trained on the 2023 historical year only (cell hist_high), applied to the scenario's weather features
  T-2, T-1, T+1, T+2   forecast temperature = truth + bias (K) + 1 K Gaussian noise: planner uses it for the room model, heat pump and cooling COP and capacity, and the PV
                       forecast features; the plant sees the true weather
  T0n1            temperature noise 1 K only
  G30             irradiance noise 30 % (multiplicative Gaussian, applied to beam and diffuse) in the room model solar gain and PV forecast features
  T+2G30, T-2G30  both
  T+2corr         bias +2 K with the online room-model correction and a 0.2 C comfort margin
Output: swiss/experiments/climate_results/robust__<cell>__<case>.json, robustness.json, robustness_section.md (included by climate_matrix.py aggregate).
Run: PYTHONPATH=. cl/bin/python swiss/experiments/climate_robust.py [--workers 11]
"""
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
import warnings

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

CELLS = ('gwl3.0_hw99_high', 'gwl2.0_hw99_high', 'hist_hw99_high')
CASES = {'trained_hist': {}, 'T-2': dict(bias_k=-2.0, noise_k=1.0), 'T-1': dict(bias_k=-1.0, noise_k=1.0), 'T+1': dict(bias_k=1.0, noise_k=1.0),
         'T+2': dict(bias_k=2.0, noise_k=1.0), 'T0n1': dict(noise_k=1.0), 'G30': dict(ghi_noise=0.3), 'T+2G30': dict(bias_k=2.0, noise_k=1.0, ghi_noise=0.3),
         'T-2G30': dict(bias_k=-2.0, noise_k=1.0, ghi_noise=0.3), 'T+2corr': dict(bias_k=2.0, noise_k=1.0, correct=True, margin=0.2)}
RES = os.path.join(ROOT, 'swiss', 'experiments', 'climate_results')


def run_case(cell, case):
    from swiss.experiments import climate_controllers as cc, climate_matrix as cmx, oracle_climate as oc
    inp = oc.ClimateInputs(cell)
    spec = dict(CASES[case])
    correct, margin = spec.pop('correct', False), spec.pop('margin', 0.0)
    if case == 'trained_hist':
        fc = cc.ClimateForecaster(inp, 'weather', train_inp=oc.ClimateInputs('hist_high'))
        view = None
    else:
        ta_f, dif_f, dire_f = cc.synthetic_weather_error(inp, seed=7, **spec)
        fc = cc.ClimateForecaster(inp, 'weather', wf=(ta_f, dif_f, dire_f))
        view = cc.WeatherView(inp, ta_f, dif_f + dire_f)
    return cmx.task_weeks(cell, 'mpc', fc=fc, view=view, margin=margin, correct=correct)


def worker(args):
    cell, case = args
    fn = os.path.join(RES, f'robust__{cell}__{case}.json')
    if os.path.exists(fn):
        return cell, case, 'cached'
    t0 = time.time()
    try:
        from swiss.experiments import climate_matrix as cmx
        out = run_case(cell, case)
        out['case'] = case
        json.dump(cmx.jsonable(out), open(fn, 'w'))
        return cell, case, f'ok {time.time() - t0:.0f}s'
    except Exception:
        return cell, case, 'ERROR ' + traceback.format_exc()[-600:]


def summarise():
    rows, L = {}, ['## 5. Robustness of the MPC on the heat-wave cells (high adoption, WP4)', '',
                   'Eight held-out weeks (week 29 holds the p99 heat-wave week); saving against the thermostat on the same weeks; share of the held-out-week ceiling of the same cell. '
                   '`scenario` = forecasters trained on the scenario year (the matrix MPC run); `trained_hist` = trained on 2023 only; T and G cases are SYNTHETIC forecast-weather errors '
                   '(temperature bias in K plus 1 K noise; irradiance noise 30 %), fixed seeds; the plant always sees the true weather.', '',
                   '| Cell | Case | Saving | Share of ceiling | Cold K h | Degree-hours > 26 C | Cooling el. (kWh) | Highest hour kW |', '|---|---|---|---|---|---|---|---|']
    for cell in CELLS:
        yr = json.load(open(os.path.join(RES, f'{cell}__year.json'))) if os.path.exists(os.path.join(RES, f'{cell}__year.json')) else None
        th = json.load(open(os.path.join(RES, f'{cell}__weeks_thermostat.json'))) if os.path.exists(os.path.join(RES, f'{cell}__weeks_thermostat.json')) else None
        if not yr or not th:
            continue
        ceil, tc = yr['band']['test_weeks']['saving_pct'], th['aggregate']['cost_chf']
        cases = [('scenario', os.path.join(RES, f'{cell}__weeks_mpc.json'))] + [(c, os.path.join(RES, f'robust__{cell}__{c}.json')) for c in CASES]
        for case, fn in cases:
            if not os.path.exists(fn):
                continue
            a = json.load(open(fn))['aggregate']
            sav = 100.0 * (tc - a['cost_chf']) / abs(tc)
            rows[f'{cell}|{case}'] = {'saving_pct': sav, 'share_of_ceiling': sav / ceil, 'comfort_cold_kh': a['comfort_cold_kh'], 'degree_hours_above_26': a['degree_hours_above_26'],
                                      'cooling_electricity_kwh': a['cooling_electricity_kwh'], 'highest_hour_kw': a['highest_hour_kw']}
            L.append(f'| {cell} | {case} | {sav:.2f} % | {100 * sav / ceil:.0f} % | {a["comfort_cold_kh"]:.1f} | {a["degree_hours_above_26"]:.0f} | {a["cooling_electricity_kwh"]:.0f} | {a["highest_hour_kw"]:.1f} |')
    json.dump(rows, open(os.path.join(RES, 'robustness.json'), 'w'), indent=1)
    open(os.path.join(RES, 'robustness_section.md'), 'w').write('\n'.join(L) + '\n')
    return rows


def run(workers=11):
    os.makedirs(RES, exist_ok=True)
    from swiss.experiments import climate_matrix as cmx
    cmx.ensure_datasets(list(CELLS) + ['hist_high'])
    tasks = [(c, k) for c in CELLS for k in CASES]
    ctx = mp.get_context('spawn')
    t0 = time.time()
    with ctx.Pool(workers, maxtasksperchild=1) as pool:
        for cell, case, status in pool.imap_unordered(worker, tasks):
            print(f'[{time.time() - t0:6.0f}s] {cell:20s} {case:14s} {status}', flush=True)
    summarise()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    run(a.workers)
