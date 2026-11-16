"""Train SAC / MARLISA on the first part of a dataset and score on held-out later weeks.

Usage: cl/bin/python my_data/rl.py <kind> [episodes] [reward]
  kind: sac_central | sac_decentral | marlisa | baselines
  reward: optional citylearn reward class name (default: the schema's own reward)
Results -> my_data/results/rl_<kind>[_<reward>].csv (district metrics on the TEST window)
"""
import sys, os, time, warnings, functools
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as base
from citylearn.citylearn import CityLearnEnv
from citylearn.agents.sac import SAC
from citylearn.agents.marlisa import MARLISA
from citylearn.agents.baseline import ZeroActionBaselineAgent, RBCSmartPolicy
from citylearn.agents.rbc import BasicBatteryRBC

DS = 'citylearn_challenge_2023_phase_3_1'
TRAIN = (0, 1535)      # first 64 days
TEST = (1536, 2207)    # last 28 days, never seen in training
OUT = base.OUT

def env_for(window, central, reward=None):
    kw = dict(central_agent=central, simulation_start_time_step=window[0], simulation_end_time_step=window[1])
    if reward: kw['reward_function'] = reward
    return CityLearnEnv(f'{base.ROOT}/{DS}/schema.json', **kw)

def evaluate(agent, env):
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(agent.predict(obs, deterministic=True))
    return base.district(env)

def main():
    kind = sys.argv[1]
    episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    reward = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(OUT, exist_ok=True)

    if kind == 'baselines':
        base.make_env = lambda name: env_for(TEST, True)
        res = {
            'do_nothing': base.district(base.run_agent(DS, ZeroActionBaselineAgent)),
            'hour_rule': base.district(base.run_hour_rule(DS)),
            'BasicBatteryRBC': base.district(base.run_agent(DS, BasicBatteryRBC)),
            'RBCSmartPolicy': base.district(base.run_agent(DS, RBCSmartPolicy)),
        }
        pd.DataFrame(res).to_csv(f'{OUT}/rl_baselines.csv'); print('wrote baselines'); return

    cls, central = {'sac_central': (SAC, True), 'sac_decentral': (SAC, False), 'marlisa': (MARLISA, False)}[kind]
    train_env = env_for(TRAIN, central, reward)
    agent = cls(train_env)
    t = time.time()
    for ep in range(episodes):   # one call per episode so we can see progress
        agent.learn(episodes=1)
        print(f'[{kind}] episode {ep+1}/{episodes}  {time.time()-t:.0f}s', flush=True)
    score = evaluate(agent, env_for(TEST, central, reward))
    tag = kind + (f'_{reward}' if reward else '')
    score.to_csv(f'{OUT}/rl_{tag}.csv', header=[tag])
    print(f'[{kind}] done in {time.time()-t:.0f}s -> rl_{tag}.csv')

if __name__ == '__main__':
    main()
