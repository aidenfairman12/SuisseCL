"""Tuned parametric rule-based controller for the 2023 CityLearn buildings (actions: dhw_storage, electrical_storage, cooling_device).

A rule with 10 numbers; differential evolution searches them on the TRAIN window to maximise the total CompositeReward
(the same objective the SAC/MARLISA agents optimise), then the best setting is scored on the held-out TEST window.
(An equal-weight mean of KPI ratios was rejected as the objective: switching cooling off scores better than a sensible rule.)
Usage: cl/bin/python my_data/tuned_rule.py [--workers 4] [--maxiter 8] [--popsize 4]
"""
import os, sys, json, time, argparse, warnings
os.environ.setdefault('OMP_NUM_THREADS', '1'); os.environ.setdefault('MKL_NUM_THREADS', '1')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rl

# name: (low, high)
SPACE = {
    'pv_charge_rate':     (0.0, 1.0),   # battery charge action when PV surplus
    'discharge_rate':     (0.0, 1.0),   # battery discharge action when needed
    'discharge_thr_kw':   (0.0, 3.0),   # discharge when last-step net demand exceeds this (kW) ...
    'discharge_hi_price': (0.0, 1.0),   # ... or during high price, scaled by this (0 = ignore price)
    'precharge_rate':     (0.0, 0.5),   # charge from grid in low-price hours
    'cool_gain':          (0.0, 2.0),   # cooling action per degC above target
    'cool_offset_base':   (-1.0, 3.0),  # target = setpoint - offset (degC); negative lets it drift above setpoint
    'cool_offset_solar':  (0.0, 3.0),   # extra pre-cooling during PV hours (degC)
    'cool_cap_hi_price':  (0.2, 1.0),   # cap on cooling action in high-price hours
    'dhw_charge_solar':   (0.0, 1.0),   # hot-water storage charge action during PV hours
}
NAMES = list(SPACE)

class TunedRule:
    def __init__(self, env, params):
        self.env, self.p = env.unwrapped, params
        price = np.asarray(self.env.buildings[0].pricing.electricity_pricing, dtype=float)
        self.price_mid = 0.5 * (price.min() + price.max())

    def act(self):
        p, out = self.p, []
        for b in self.env.buildings:
            o = b.observations()
            high = o['electricity_pricing'] > self.price_mid
            sun = o['solar_generation'] > 0.05
            surplus = o['solar_generation'] - o['non_shiftable_load']
            net = o['net_electricity_consumption']
            soc = o['electrical_storage_soc']
            batt = 0.0
            if sun and surplus > 0.05 and soc < 0.95:
                batt = p['pv_charge_rate']
            elif soc > 0.15 and (net > p['discharge_thr_kw'] or (high and p['discharge_hi_price'] > 0.5)):
                batt = -p['discharge_rate']
            elif (not high) and (not sun) and soc < 0.6:
                batt = p['precharge_rate']
            target = o['indoor_dry_bulb_temperature_cooling_set_point'] - p['cool_offset_base'] - (p['cool_offset_solar'] if sun else 0.0)
            cool = float(np.clip(p['cool_gain'] * (o['indoor_dry_bulb_temperature'] - target), 0.0, 1.0))
            if high:
                cool = min(cool, p['cool_cap_hi_price'])
            dhw = p['dhw_charge_solar'] if (sun and o['dhw_storage_soc'] < 0.95) else 0.0
            acts = {'dhw_storage': dhw, 'electrical_storage': batt, 'cooling_device': cool}
            out.extend(acts[n] for n in b.active_actions)
        return [out]

def rollout(params, window, seed=0):
    """Returns (district KPIs, total composite reward over the window)."""
    env = rl.env_for(window, True, 'composite', seed)
    env.reset(); ctl = TunedRule(env, params); total = 0.0
    while not env.terminated:
        _, r, *_ = env.step(ctl.act()); total += float(np.sum(r))
    return rl.base.district(env), total

def objective(x):
    params = dict(zip(NAMES, map(float, x)))
    try:
        return -rollout(params, rl.TRAIN)[1]      # minimise negative total reward
    except Exception as e:      # an infeasible setting should not kill the search
        print('eval failed', repr(e), flush=True); return 10.0

if __name__ == '__main__':
    from scipy.optimize import differential_evolution
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--maxiter', type=int, default=8)
    ap.add_argument('--popsize', type=int, default=4); ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    t0 = time.time(); hist = []
    def cb(xk, convergence=None):
        hist.append(dict(generation=len(hist) + 1, seconds=round(time.time() - t0), best_train_reward=-objective(xk)))
        print(hist[-1], flush=True)
    res = differential_evolution(objective, [SPACE[n] for n in NAMES], maxiter=a.maxiter, popsize=a.popsize, seed=a.seed,
                                 workers=a.workers, updating='deferred', init='sobol', polish=False, tol=0, callback=cb)
    best = dict(zip(NAMES, map(float, res.x)))
    os.makedirs(rl.OUT, exist_ok=True)
    json.dump(dict(params=best, train_score=float(res.fun), evaluations=int(res.nfev)), open(f'{rl.OUT}/tuned_rule_params.json', 'w'), indent=2)
    pd.DataFrame(hist).to_csv(f'{rl.OUT}/tuned_rule_search.csv', index=False)
    test, test_reward = rollout(best, rl.TEST)
    test.to_csv(f'{rl.OUT}/rl_tuned_rule_s0.csv', header=['tuned_rule_s0'])
    print('BEST PARAMS', json.dumps(best, indent=1))
    print('TRAIN total reward', round(-float(res.fun), 1), '| TEST total reward', round(test_reward, 1))
    print(test[['cost_total', 'carbon_emissions_total', 'daily_peak_average', 'all_time_peak_average', 'ramping_average', 'discomfort_proportion']].round(3).to_dict())
    print(f'{res.nfev} evaluations in {time.time()-t0:.0f}s')
