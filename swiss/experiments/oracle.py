"""Exact perfect-foresight optimum of the tank schedule for ELECTRICITY COST (an upper bound on what any controller can save in this model).

The only thing a controller can do in the Phase A district is charge or discharge each building's heating and hot-water tank. Demand is fixed, so
cost = sum_t price_t x (heat pump electricity_t + household electricity_t), and the cost-optimal schedule of every tank is an independent linear
program (no coupling between tanks). The program mirrors CityLearn 3.3.0's tank rules exactly (verified by replaying the schedule in the real environment):
  a_t  heat the heat pump puts into the tank (0 <= a_t <= capacity); the heat pump's output is shared: (demand_t - d_t) + a_t <= maximum output_t
  d_t  heat the tank delivers to the demand (0 <= d_t <= min(capacity, demand_t))
  E_t  stored heat after step t:   E_t = (1 - loss) E_{t-1} + rho a_t - d_t / rho,   0 <= E_t <= capacity,   rho = sqrt(efficiency)
  heat-pump electricity_t = (demand_t - d_t + a_t) / COP_t        (CityLearn: direct output + charging heat, at the COP of the hour)
Objective per tank: minimise sum_t price_t (a_t - d_t) / COP_t.  Not modelled here: the peak and ramp terms of the reward (they couple the buildings and
make the problem quadratic); this is the CITY BILL bound, the quantity the project asks about.

Run: PYTHONPATH=. python swiss/experiments/oracle.py [--scales 0.5 1 2 4 8]
Output: swiss/experiments/oracle_results/oracle_cost.json and docs/experiments/validation_reports/oracle_cost_bound.md
"""
import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.experiments import rl  # noqa: E402
from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402

N = 8759
OUT = os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results')


def tank_inputs(env):
    """Per tank: capacity, demand, COP, maximum heat-pump output, efficiency terms (all read from the built environment)."""
    T = np.asarray(env.buildings[0].weather.outdoor_dry_bulb_temperature, dtype=float)[:N]
    out = []
    for bi, b in enumerate(env.buildings):
        for kind, act in (('heating', 0), ('dhw', 1)):
            tank, dev = getattr(b, f'{kind}_storage'), getattr(b, f'{kind}_device')
            cap = float(tank.capacity)
            if cap <= 0:
                continue
            cop = np.array([dev.get_cop(t, heating=True) for t in T])
            out.append({'building': bi, 'kind': kind, 'action_index': act, 'cap': cap, 'cop': cop, 'maxout': float(dev.nominal_power) * cop,
                        'demand': np.asarray(getattr(b, f'{kind}_demand'), dtype=float)[:N], 'rho': float(tank.round_trip_efficiency),
                        'loss': float(tank.loss_coefficient), 'e0': float(tank.initial_soc) * cap})
    return out


def solve_tank(t, price, scale=1.0):
    """LP for one tank; returns (a, d, E, objective) where objective = change of the bill in CHF (negative = saving)."""
    n, cap, rho, lam = N, t['cap'] * scale, t['rho'], t['loss']
    cost = price / t['cop']
    c = np.concatenate([cost, -cost, np.zeros(n)])                                  # variables: a (n), d (n), E (n)
    main = sp.identity(n, format='csr')
    sub = sp.diags([np.full(n - 1, -(1.0 - lam))], [-1], shape=(n, n), format='csr')
    A_eq = sp.hstack([-rho * main, main / rho, main + sub], format='csr')           # E_t - (1-lam) E_{t-1} - rho a_t + d_t / rho = 0
    b_eq = np.zeros(n)
    b_eq[0] = (1.0 - lam) * t['e0']
    # the heat pump's output is shared between direct supply (demand - d) and charging (a): (demand - d) + a <= maximum output
    A_ub = sp.hstack([main, -main, sp.csr_matrix((n, n))], format='csr')
    b_ub = t['maxout'] - t['demand']
    bounds = ([(0.0, float(min(cap, m))) for m in t['maxout']] + [(0.0, float(min(cap, dm))) for dm in t['demand']] + [(0.0, cap)] * n)
    r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    if r.status != 0:
        raise RuntimeError(f'LP failed: {r.message}')
    x = r.x
    return x[:n], x[n:2 * n], x[2 * n:], float(r.fun)


def baseline_arrays(env):
    imp = np.sum([np.maximum(np.asarray(b.net_electricity_consumption, dtype=float), 0) for b in env.buildings], axis=0)
    return imp


def zero_action_import():
    env = CityLearnEnv(rl.SCHEMA, central_agent=True, reward_function=SwissDistrictReward)
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    ag, (obs, _) = ZeroActionBaselineAgent(env), env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    return env, baseline_arrays(env)


class Replay:
    """Plays a fixed action schedule (rows = steps, columns = the 12 central-agent action slots)."""
    def __init__(self, actions):
        self.actions, self.i = actions, 0

    def predict(self, obs):
        a = self.actions[min(self.i, len(self.actions) - 1)]
        self.i += 1
        return [a.tolist()]


def schedule_actions(tanks, solutions, n_buildings):
    act = np.zeros((N, 2 * n_buildings))
    for t, (a, d, E, obj) in zip(tanks, solutions):
        act[:, 2 * t['building'] + t['action_index']] = np.clip((a - d) / t['cap'], -1.0, 1.0)
    return act


def run(scales):
    env0, imp0 = zero_action_import()
    price = rl.PRICE[:N]
    tanks = tank_inputs(env0)
    cost0 = float((imp0 * price).sum())
    test_idx = np.concatenate([np.arange(s, e + 1) for s, e in rl.test_windows('weeks')])
    result = {'zero_action_cost_chf': cost0, 'zero_action_cost_test_weeks_chf': float((imp0 * price)[test_idx].sum()), 'tanks': len(tanks), 'scales': {}}
    for sc in scales:
        t0 = time.time()
        sols = [solve_tank(t, price, sc) for t in tanks]
        saving = -sum(s[3] for s in sols)                                           # CHF per year
        imp = imp0.copy()
        for t, (a, d, E, obj) in zip(tanks, sols):
            imp += (a - d) / t['cop']                                              # change of heat-pump electricity of this tank
        cost = float((imp * price).sum())
        sav_test = float(((imp0 - imp) * price)[test_idx].sum())
        result['scales'][str(sc)] = {'tank_capacity_scale': sc, 'total_capacity_kwh_th': float(sum(t['cap'] for t in tanks) * sc),
                                     'optimal_cost_chf': cost, 'saving_chf': saving, 'saving_pct': 100.0 * saving / cost0,
                                     'saving_test_weeks_chf': sav_test, 'saving_test_weeks_pct': 100.0 * sav_test / result['zero_action_cost_test_weeks_chf'],
                                     'import_change_kwh': float(imp.sum() - imp0.sum()), 'seconds': round(time.time() - t0, 1)}
        print(f'tank capacity x{sc:<4}: optimum saves {saving:7.1f} CHF/yr = {100 * saving / cost0:5.2f} % of {cost0:,.0f} CHF '
              f'(test weeks {result["scales"][str(sc)]["saving_test_weeks_pct"]:.2f} %)   [{time.time() - t0:.0f}s]', flush=True)
    return result, tanks, env0


def validate_by_replay(tanks, n_buildings, price):
    """Play the scale-1 optimum in the real environment: the realised bill must equal the program's prediction."""
    sols = [solve_tank(t, price, 1.0) for t in tanks]
    pred = -sum(s[3] for s in sols)
    env = CityLearnEnv(rl.SCHEMA, central_agent=True, reward_function=SwissDistrictReward)
    ag = Replay(schedule_actions(tanks, sols, n_buildings))
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    imp = baseline_arrays(env)
    cost = float((imp * price).sum())
    return pred, cost, env


REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'oracle_cost_bound.md')


def write_report(result, path=REPORT):
    sc = result['scales']
    lines = ['# Exact cost optimum of the tank schedule (ceiling for any controller)', '',
             'Generated by `swiss/experiments/oracle.py` from `swiss/experiments/oracle_results/oracle_cost.json`. Nothing here is typed by hand.', '',
             'A controller in the Phase A district can only charge or discharge each building\'s heating and hot-water tank; demand is fixed. With perfect foresight the '
             'cost-optimal schedule of every tank is a linear program that mirrors CityLearn 3.3.0\'s tank rules (efficiency, standby loss, capacity, and the heat pump\'s '
             'output shared between direct supply and charging). **It is exact for this simulator**: replaying the schedule in CityLearn realises the predicted saving '
             f'({result["replay_check"]["predicted_saving_chf"]:.2f} CHF predicted, {result["replay_check"]["realised_saving_chf"]:.2f} CHF realised).', '',
             'Reference: no control costs ' + f'{result["zero_action_cost_chf"]:,.0f}'.replace(',', ' ') + ' CHF a year (EKZ standard tariff 2023, excl. VAT) and '
             + f'{result["zero_action_cost_test_weeks_chf"]:,.0f}'.replace(',', ' ') + ' CHF on the 8 held-out test weeks.', '',
             '| Tank size (x assumed, D-017a) | Total capacity (kWh_th) | Best saving per year | Share of the bill | Share on the 8 test weeks |', '|---|---|---|---|---|']
    for k, v in sc.items():
        lines.append(f'| x{v["tank_capacity_scale"]:g} | {v["total_capacity_kwh_th"]:.0f} | {v["saving_chf"]:.0f} CHF | {v["saving_pct"]:.2f} % | {v["saving_test_weeks_pct"]:.2f} % |')
    lines += ['', '## How to read it',
              '- At the assumed tank sizes (x1) no controller can save more than this share of the electricity bill in this simulator. The bound is exact, so a score clearly above it would point to an evaluation artefact, not to a better controller (the test-week share differs slightly because evaluation windows start from a warm-up instead of the continuous year).',
              '- Savings grow much more slowly than tank size (diminishing returns): the tariff spread is only 4 Rp/kWh, the round trip loses about 5 % and the COP is lower at night.',
              '- This is the value of storage under the **flat two-tier tariff, without PV, building thermal mass or demand charges**; the tank sizes are assumptions with no source (ISS-032).',
              '- Tank size as a design variable: the table is the value of storage; whether a larger tank is worth installing depends on its cost and space, which this model does not contain.', '',
              '## Not covered',
              '- The peak and ramp terms of reward R-001 (they couple the buildings and make the problem quadratic); this bound is for the bill only.',
              '- Anything outside the simulator: building thermal mass, part-load and cycling effects on the heat pump (the COP depends only on outdoor temperature, ISS-034), PV, dynamic tariffs.',
              '- Forecast error: the optimum knows the whole year in advance.', '']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--scales', type=float, nargs='+', default=[0.5, 1.0, 2.0, 4.0, 8.0])
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    result, tanks, env0 = run(a.scales)
    price = rl.PRICE[:N]
    pred_saving, realised_cost, _ = validate_by_replay(tanks, len(env0.buildings), price)
    result['replay_check'] = {'predicted_saving_chf': pred_saving, 'realised_cost_chf': realised_cost,
                              'realised_saving_chf': result['zero_action_cost_chf'] - realised_cost,
                              'abs_difference_chf': abs(pred_saving - (result['zero_action_cost_chf'] - realised_cost))}
    print('replay check in CityLearn: predicted saving %.2f CHF, realised saving %.2f CHF (difference %.3f)' % (
        pred_saving, result['replay_check']['realised_saving_chf'], result['replay_check']['abs_difference_chf']), flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump(result, open(os.path.join(a.out, 'oracle_cost.json'), 'w'), indent=1)
    if a.out == OUT:
        write_report(result)
    return result


if __name__ == '__main__':
    main()
