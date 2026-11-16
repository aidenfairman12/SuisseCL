"""Reward-term diagnostic: per-step raw value of each composite-reward term under reference behaviours (train window).

Why: with equal weights the composite reward must rank "cool to setpoint" better than "cooling off". Currently it does not:
the comfort term is nearly insensitive (cooling off ~570 vs cooling-to-setpoint ~494 per step) while peak/ramp/cost react strongly.
Use this script to check any redesigned comfort term. Acceptance test: comfort(conventional) << comfort(cooling_off).
Usage: cl/bin/python my_data/reward_diagnostics.py      (about 2 minutes)
"""
import os, sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import rl, tuned_rule as T
from rewards import CompositeReward, TERMS
from citylearn.agents.rbc import BasicBatteryRBC
from citylearn.citylearn import CityLearnEnv

def run(make_step):
    log = {t: [] for t in TERMS}
    class Probe(CompositeReward):
        def __init__(self, *a, **k):
            k['scales'] = {t: 1.0 for t in TERMS}; super().__init__(*a, **k)
        def calculate(self, observations):
            r = self.raw_terms(observations)
            log['comfort'].append(r['comfort'].sum()); log['cost'].append(r['cost'].sum()); log['carbon'].append(r['carbon'].sum())
            log['peak'].append(r['peak']); log['ramp'].append(r['ramp']); return [0.0]
    env = CityLearnEnv(f'{rl.base.ROOT}/{rl.DS}/schema.json', central_agent=True, simulation_start_time_step=rl.TRAIN[0],
                       simulation_end_time_step=rl.TRAIN[1], reward_function=Probe)
    env.reset(); step = make_step(env)
    while not env.terminated:
        env.step(step())
    return {t: float(np.mean(v)) for t, v in log.items()}, float(rl.base.district(env)['discomfort_proportion'])

def tuned(params):
    return lambda env: T.TunedRule(env, params).act

def bbr(env):
    agent = BasicBatteryRBC(env)
    return lambda: agent.predict(env.observations)

if __name__ == '__main__':
    zero = {n: 0.0 for n in T.SPACE}; zero['cool_cap_hi_price'] = 1.0
    conv = dict(zero, cool_gain=2.0, cool_offset_base=0.0)          # cool to setpoint, storage idle
    mid = {n: (lo + hi) / 2 for n, (lo, hi) in T.SPACE.items()}
    runs = {'cooling_off': lambda env: (lambda: [[0.0] * len(env.action_names[0])]),
            'conventional (cool to setpoint, no storage)': tuned(conv), 'mid_params': tuned(mid), 'BasicBatteryRBC': bbr}
    scales = json.load(open(f'{rl.OUT}/reward_scales.json'))
    print('current reward scales:', {k: round(v, 2) for k, v in scales.items()})
    for name, mk in runs.items():
        terms, disc = run(mk)
        print(f'{name:46s} discomfort={disc:.3f}  per-step raw terms:', {k: round(v, 2) for k, v in terms.items()})
