"""Train SAC / MARLISA on the first part of a dataset and score on held-out later weeks.

Usage: cl/bin/python my_data/rl.py <kind> [--episodes 30] [--reward composite] [--seed 0] [--weights comfort=1,cost=1,...]
  kind: sac_central | sac_decentral | marlisa | baselines | scales
  --reward composite : use rewards.CompositeReward (default: the schema's own comfort-only reward)
  scales : compute reward normalisation scales -> results/reward_scales.json (run once before composite runs)
Results -> my_data/results/rl_<kind>[_<reward>]_s<seed>.csv (district KPIs on the TEST window)
"""
import sys, os, time, warnings, functools
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as base
import json, argparse
from rewards import CompositeReward, TERMS
from citylearn.citylearn import CityLearnEnv
from citylearn.agents.sac import SAC
from citylearn.agents.marlisa import MARLISA
from citylearn.agents.baseline import ZeroActionBaselineAgent, RBCSmartPolicy
from citylearn.agents.rbc import BasicBatteryRBC

DS = 'citylearn_challenge_2023_phase_3_1'
TRAIN = (0, 1535)      # first 64 days
TEST = (1536, 2207)    # last 28 days, never seen in training
OUT = base.OUT

def env_for(window, central, reward=None, seed=None, weights=None):
    kw = dict(central_agent=central, simulation_start_time_step=window[0], simulation_end_time_step=window[1])
    if reward == 'composite':
        kw['reward_function'] = CompositeReward
        if weights: kw['reward_function_kwargs'] = {'weights': weights}
    elif reward:
        kw['reward_function'] = reward
    if seed is not None: kw['random_seed'] = seed
    return CityLearnEnv(f'{base.ROOT}/{DS}/schema.json', **kw)

def compute_scales():
    """Mean per-step value of each reward term under a reference rollout (BasicBatteryRBC, train window)."""
    import numpy as np
    log = {t: [] for t in TERMS}
    class Probe(CompositeReward):
        def __init__(self, *a, **k):
            k['scales'] = {t: 1.0 for t in TERMS}; super().__init__(*a, **k)
        def calculate(self, observations):
            r = self.raw_terms(observations)
            log['comfort'].append(r['comfort'].sum()); log['cost'].append(r['cost'].sum()); log['carbon'].append(r['carbon'].sum())
            log['peak'].append(r['peak']); log['ramp'].append(r['ramp'])
            return [0.0]
    env = CityLearnEnv(f'{base.ROOT}/{DS}/schema.json', central_agent=True, simulation_start_time_step=TRAIN[0],
                       simulation_end_time_step=TRAIN[1], reward_function=Probe)
    agent = BasicBatteryRBC(env); obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(agent.predict(obs))
    scales = {t: float(np.mean(v)) for t, v in log.items()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(scales, open(f'{OUT}/reward_scales.json', 'w'), indent=2)
    print('scales', scales)

def evaluate(agent, env):
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(agent.predict(obs, deterministic=True))
    return base.district(env)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['sac_central', 'sac_decentral', 'marlisa', 'baselines', 'scales'])
    ap.add_argument('--episodes', type=int, default=30)
    ap.add_argument('--reward', default=None, help="'composite' or a CityLearn reward class name")
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--weights', default=None, help='e.g. comfort=1,cost=1,carbon=1,peak=1,ramp=1')
    a = ap.parse_args()
    weights = {k: float(v) for k, v in (kv.split('=') for kv in a.weights.split(','))} if a.weights else None
    os.makedirs(OUT, exist_ok=True)

    if a.kind == 'scales':
        return compute_scales()
    if a.kind == 'baselines':
        base.make_env = lambda name: env_for(TEST, True)
        res = {
            'do_nothing': base.district(base.run_agent(DS, ZeroActionBaselineAgent)),
            'hour_rule': base.district(base.run_hour_rule(DS)),
            'BasicBatteryRBC': base.district(base.run_agent(DS, BasicBatteryRBC)),
            'RBCSmartPolicy': base.district(base.run_agent(DS, RBCSmartPolicy)),
        }
        pd.DataFrame(res).to_csv(f'{OUT}/rl_baselines.csv'); print('wrote baselines'); return

    cls, central = {'sac_central': (SAC, True), 'sac_decentral': (SAC, False), 'marlisa': (MARLISA, False)}[a.kind]
    train_env = env_for(TRAIN, central, a.reward, a.seed, weights)
    agent = cls(train_env)
    t = time.time()
    for ep in range(a.episodes):   # one call per episode so we can see progress
        agent.learn(episodes=1)
        print(f'[{a.kind} s{a.seed}] episode {ep+1}/{a.episodes}  {time.time()-t:.0f}s', flush=True)
    score = evaluate(agent, env_for(TEST, central, a.reward, a.seed, weights))
    tag = a.kind + (f'_{a.reward}' if a.reward else '') + f'_s{a.seed}'
    score.to_csv(f'{OUT}/rl_{tag}.csv', header=[tag])
    print(f'[{tag}] done in {time.time()-t:.0f}s -> rl_{tag}.csv')

if __name__ == '__main__':
    main()
