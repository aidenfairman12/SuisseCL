"""Run baseline controllers on a full CityLearn dataset and compare district scores.
Usage: cl/bin/python my_data/run.py [dataset_name ...]   (default: 2023 phase_3_1..3)
"""
import sys, os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
from citylearn.citylearn import CityLearnEnv
from citylearn.agents.baseline import ZeroActionBaselineAgent, RBCSmartPolicy
from citylearn.agents.rbc import BasicBatteryRBC

ROOT = os.environ.get('CITYLEARN_DATA', '/Users/Aiden/Projects/citylearn/CityLearn/data/datasets')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
DEFAULT = [f'citylearn_challenge_2023_phase_3_{i}' for i in (1, 2, 3)]

def make_env(name):
    return CityLearnEnv(f'{ROOT}/{name}/schema.json', central_agent=True)

def run_agent(name, cls):
    env = make_env(name)
    agent = cls(env)
    obs, _ = env.reset()
    while not env.terminated:
        env.step(agent.predict(obs))  # keep obs updated below
        break
    env = make_env(name); agent = cls(env)
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(agent.predict(obs))
    return env

def run_hour_rule(name, scale=1.0):
    """User's rule: charge battery 9-15h, discharge 17-22h; everything else 0."""
    env = make_env(name); env.reset()
    names = env.action_names[0]
    t = 0
    while not env.terminated:
        hr = t % 24
        v = scale if 9 <= hr < 15 else (-scale if 17 <= hr < 22 else 0.0)
        a = [v if n.startswith('electrical_storage') else 0.0 for n in names]
        env.step([a]); t += 1
    return env

def district(env):
    df = env.evaluate()
    d = df[df.level == 'district'].set_index('cost_function')['value']
    return d

if __name__ == '__main__':
    datasets = sys.argv[1:] or DEFAULT
    os.makedirs(OUT, exist_ok=True)
    for ds in datasets:
        runs = {
            'do_nothing': lambda: run_agent(ds, ZeroActionBaselineAgent),
            'hour_rule': lambda: run_hour_rule(ds),
            'BasicBatteryRBC': lambda: run_agent(ds, BasicBatteryRBC),
            'RBCSmartPolicy': lambda: run_agent(ds, RBCSmartPolicy),
        }
        res = {}
        for k, f in runs.items():
            try:
                res[k] = district(f())
            except Exception as e:
                print(f'[{ds}] {k} FAILED: {type(e).__name__}: {e}')
        tbl = pd.DataFrame(res).dropna(how='all')
        tbl.to_csv(f'{OUT}/{ds}.csv')
        print(f'\n=== {ds} ===')
        print(tbl.round(3).to_string())
