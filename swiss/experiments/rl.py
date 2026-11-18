"""Reinforcement learning on the Swiss district (decision D-023): SAC (one central agent or one agent per building) and MARLISA.

PROTOCOL (owner decisions 2026-11-18: held-out weeks first, quarter cross-validation later; episode-end fixes 2026-11-18)
  Year: step 0 = local midnight 1 Jan 2023; 52 blocks of 168 steps (one week); the last 23 steps are unused.
  protocol "weeks"   TEST = weeks 3, 10, 16, 23, 29, 36, 42, 49 (start 22 Jan, 12 Mar, 23 Apr, 11 Jun, 23 Jul, 10 Sep, 22 Oct, 10 Dec).
  protocol "quarter" TEST = one 13-week quarter (fold 1..4); the other three quarters train. Rotate the fold to cross-validate.
  TRAINING episodes: random windows of --episode-weeks weeks (default 4, day-aligned) that never touch a test step.
  EVALUATION: for every test window the policy first runs WARM steps before the window from empty tanks (so the window starts in a realistic tank
  state, not empty), deterministic; only the window itself is scored. The same windows are scored for the baselines and the optimum is computed
  elsewhere (oracle.py), so every number is reported against "No control" on identical data (district totals, energy-weighted).
Two artefacts of cutting a year into windows are handled, not ignored (they made "do nothing" look best):
  1. Training: CityLearn flags the end of every window as terminal, so SAC would learn that heat stored for later is worth nothing. The agents here
     bootstrap from the end state instead (a time limit is not a real end: Pardo et al. 2017).
  2. Scoring: heat still stored at the end of a window was paid for but is not credited. It is valued at the electricity it will avoid (stored heat /
     the window's mean COP x price) and reported as a RANGE (price low / mean / high); the raw cost is always reported too.
Reward: "r001" (cost, squared peak and ramp all 1, carbon 0) or "cost" (cost 1, peak and ramp 0.1). One year only, synthetic tanks (D-017a), no comfort.

Usage (repository root):
  PYTHONPATH=. python swiss/experiments/rl.py baselines --reward r001
  PYTHONPATH=. python swiss/experiments/rl.py sac_central --reward r001 --seed 0 --train-steps 150000
  PYTHONPATH=. python swiss/experiments/rl.py sac_central --protocol quarter --fold 2 ...
  kinds: sac_central | sac_decentral | marlisa | baselines
Outputs: swiss/experiments/rl_results/<kind>_<reward>_<protocol>_s<seed>/{config.json, curve.csv, eval_curve.csv, eval_final.json}
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn import __version__ as CL_VERSION  # noqa: E402
from citylearn.agents.marlisa import MARLISA  # noqa: E402
from citylearn.agents.sac import SAC  # noqa: E402
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402

SCHEMA = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'schema.json')
OUT = os.path.join(ROOT, 'swiss', 'experiments', 'rl_results')
PRICE = pd.read_csv(os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'pricing.csv')).electricity_pricing.to_numpy()
HIGH = PRICE > PRICE.min() + 1e-9
WEEK = 168
N_WEEKS = 52
QUARTER = 13 * WEEK
LAST_STEP = 8758
WARM = 96                                          # steps run before an evaluation window so that it starts in a realistic tank state
TEST_WEEKS = [3, 10, 16, 23, 29, 36, 42, 49]
REWARDS = {'r001': {'cost': 1.0, 'peak': 1.0, 'ramp': 1.0, 'carbon': 0.0},
           'cost': {'cost': 1.0, 'peak': 0.1, 'ramp': 0.1, 'carbon': 0.0}}
PRESETS = {'default': {}, 'challenge': dict(hidden_dimension=[256, 256], discount=0.9, lr=0.001, batch_size=512, alpha=1.0)}
KINDS = {'sac_central': True, 'sac_decentral': False, 'marlisa': False}


def window(k):
    """Steps (start, end) of week block k, end inclusive."""
    return (k * WEEK, k * WEEK + WEEK - 1)


def test_windows(protocol='weeks', fold=1):
    if protocol == 'weeks':
        return [window(k) for k in TEST_WEEKS]
    if protocol == 'quarter':
        assert fold in (1, 2, 3, 4), 'fold must be 1..4'
        return [((fold - 1) * QUARTER, fold * QUARTER - 1)]
    raise ValueError(protocol)


def train_windows(tests, episode_weeks=4):
    """Day-aligned windows of episode_weeks weeks that do not contain a single test step."""
    length = episode_weeks * WEEK
    blocked = np.zeros(LAST_STEP + 2, dtype=bool)
    for s, e in tests:
        blocked[s:e + 1] = True
    out = [(s, s + length - 1) for s in range(0, LAST_STEP - length + 2, 24) if not blocked[s:s + length].any()]
    if not out:
        raise ValueError('no training window left')
    return out


def make_env(central, reward, windows, seed=None):
    """windows: one (start, end) tuple = simulation window (evaluation); a list of tuples = random training episodes drawn from these windows."""
    kw = dict(central_agent=central, reward_function=SwissDistrictReward, reward_function_kwargs={'weights': REWARDS[reward]})
    if isinstance(windows, tuple):
        kw.update(simulation_start_time_step=windows[0], simulation_end_time_step=windows[1])
    else:
        kw.update(simulation_start_time_step=0, simulation_end_time_step=LAST_STEP, episode_time_steps=list(windows), random_episode_split=True)
    if seed is not None:
        kw['random_seed'] = seed
    return CityLearnEnv(SCHEMA, **kw)


# ------------------------------------------------------------------------------------------------ agents that bootstrap at window cuts
class SACBootstrap(SAC):
    """SAC whose replay buffer never marks a window cut as terminal (Pardo et al. 2017, "Time Limits in Reinforcement Learning").
    CityLearn flags the last step of every episode `terminated`, and SAC stores that flag to switch the future-value term off."""
    def update(self, observations, actions, reward, next_observations, terminated, truncated):
        super().update(observations, actions, reward, next_observations, terminated=False, truncated=bool(terminated or truncated))


class MARLISABootstrap(MARLISA):
    def update(self, observations, actions, reward, next_observations, terminated, truncated):
        super().update(observations, actions, reward, next_observations, terminated=False, truncated=bool(terminated or truncated))


# ------------------------------------------------------------------------------------------------ scoring
def window_metrics(env, rewards, s0, s, e):
    """District totals of window [s, e] (global steps) from a rollout that started at global step s0 <= s."""
    i0, i1 = s - s0, e - s0
    net_b = [np.asarray(b.net_electricity_consumption, dtype=float)[i0:i1 + 1] for b in env.buildings]
    n = len(net_b[0])
    imp = np.sum([np.maximum(x, 0) for x in net_b], axis=0)
    net = np.sum(net_b, axis=0)
    ci = np.asarray(env.buildings[0].carbon_intensity.carbon_intensity, dtype=float)[i0:i1 + 1]
    price, high = PRICE[s:s + n], HIGH[s:s + n]
    T = np.asarray(env.buildings[0].weather.outdoor_dry_bulb_temperature, dtype=float)
    d_e, value = 0.0, {'low': 0.0, 'mean': 0.0, 'high': 0.0}
    for b in env.buildings:
        for tank, dev in ((b.heating_storage, b.heating_device), (b.dhw_storage, b.dhw_device)):
            cap = float(tank.capacity)
            if cap <= 0:
                continue
            soc = np.asarray(tank.soc, dtype=float)
            e_end = soc[i1] * cap
            e_start = soc[i0 - 1] * cap if i0 > 0 else float(tank.initial_soc) * cap
            cop = float(np.mean([dev.get_cop(t, heating=True) for t in T[i0:i1 + 1]]))
            de = e_end - e_start
            d_e += de
            for k, p in (('low', PRICE.min()), ('mean', float(price.mean())), ('high', PRICE.max())):
                value[k] += de / cop * p                    # electricity the net stored heat will avoid later, at the window's COP and a price
    return {'import_kwh': float(imp.sum()), 'cost_chf': float((imp * price).sum()), 'peak_kw': float(net.max()),
            'high_tariff_import_kwh': float(imp[high].sum()), 'carbon_weighted_import': float((imp * ci).sum()),
            'daily_peaks_kw': [float(net[i:i + 24].max()) for i in range(0, n, 24)], 'steps': int(n),
            'stored_change_kwh_th': float(d_e), 'terminal_value_chf': value, 'reward': float(np.sum(rewards[i0:i1 + 1]))}


def play(make_policy, central, reward, win, warm=WARM):
    """Deterministic rollout of a policy over window `win`, started `warm` steps earlier from empty tanks; only the window is scored."""
    s, e = win
    s0 = max(0, s - warm)
    env = make_env(central, reward, windows=(s0, min(e + 1, LAST_STEP)))
    policy = make_policy(env)
    obs, _ = env.reset()
    rewards = []
    while not env.terminated:
        obs, r, *_ = env.step(policy.predict(obs))
        rewards.append(float(np.sum(r)))
    return window_metrics(env, rewards, s0, s, e)


def aggregate(rows):
    imp = sum(r['import_kwh'] for r in rows)
    daily = [d for r in rows for d in r['daily_peaks_kw']]
    cost = sum(r['cost_chf'] for r in rows)
    v = {k: sum(r['terminal_value_chf'][k] for r in rows) for k in ('low', 'mean', 'high')}
    corrected = [cost - v[k] for k in ('low', 'mean', 'high')]     # the sign of the stored-heat change decides which price gives the lowest cost
    return {'import_kwh': imp, 'cost_chf': cost, 'cost_corrected_chf': cost - v['mean'], 'cost_corrected_chf_min': min(corrected), 'cost_corrected_chf_max': max(corrected),
            'stored_change_kwh_th': sum(r['stored_change_kwh_th'] for r in rows), 'highest_hour_kw': max(r['peak_kw'] for r in rows),
            'mean_weekly_peak_kw': float(np.mean([r['peak_kw'] for r in rows])), 'mean_daily_peak_kw': float(np.mean(daily)),
            'high_tariff_import_share': sum(r['high_tariff_import_kwh'] for r in rows) / imp,
            'carbon_weighted_import': sum(r['carbon_weighted_import'] for r in rows), 'reward_sum': sum(r['reward'] for r in rows), 'windows': len(rows)}


def vs_reference(agg, ref):
    """Percent change against the zero-action aggregate on the same windows (carbon is relative only). The corrected cost credits stored heat."""
    out = {f'{k}_vs_zero_pct': (100.0 * (agg[k] / ref[k] - 1.0) if ref[k] else None)
           for k in ('import_kwh', 'cost_chf', 'highest_hour_kw', 'mean_daily_peak_kw', 'carbon_weighted_import')}
    out['cost_corrected_vs_zero_pct'] = 100.0 * (agg['cost_corrected_chf'] / ref['cost_chf'] - 1.0)
    out['cost_corrected_vs_zero_pct_min'] = 100.0 * (agg['cost_corrected_chf_min'] / ref['cost_chf'] - 1.0)
    out['cost_corrected_vs_zero_pct_max'] = 100.0 * (agg['cost_corrected_chf_max'] / ref['cost_chf'] - 1.0)
    out['high_tariff_share_points_vs_zero'] = 100.0 * (agg['high_tariff_import_share'] - ref['high_tariff_import_share'])
    out['reward_sum_vs_zero'] = agg['reward_sum'] - ref['reward_sum']
    return out


class _Greedy:
    """Wraps a trained agent: deterministic actions, so evaluation never explores or updates."""
    def __init__(self, agent):
        self.agent = agent

    def predict(self, obs):
        return self.agent.predict(obs, deterministic=True)


def evaluate(agent, central, reward, windows):
    rows = [play(lambda env: _Greedy(agent), central, reward, w) for w in windows]
    return {'aggregate': aggregate(rows), 'windows': rows}


def baselines_zero(reward, windows):
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    return aggregate([play(lambda e: ZeroActionBaselineAgent(e), True, reward, w) for w in windows])


def baselines(reward, windows):
    from swiss.experiments.run_baselines import CONTROLLERS
    out = {}
    for name, mk in CONTROLLERS.items():
        rows = [play(mk, True, reward, w) for w in windows]
        out[name] = {'aggregate': aggregate(rows), 'windows': rows}
    ref = out['ALG-001_zero_action']['aggregate']
    for name in out:
        out[name]['vs_zero'] = vs_reference(out[name]['aggregate'], ref)
    return out


# ------------------------------------------------------------------------------------------------ training
def git_commit():
    r = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True)
    return r.stdout.strip() or 'unknown'


def protocol_tag(protocol, fold):
    return 'weeks' if protocol == 'weeks' else f'q{fold}'


def train(kind, reward, seed, train_steps, explore_steps, eval_every, max_hours, preset, out_dir, protocol='weeks', fold=1, episode_weeks=4):
    import torch
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    central = KINDS[kind]
    cls = MARLISABootstrap if kind == 'marlisa' else SACBootstrap
    tests = test_windows(protocol, fold)
    trains = train_windows(tests, episode_weeks)
    os.makedirs(out_dir, exist_ok=True)
    env = make_env(central, reward, windows=trains, seed=seed)
    kwargs = dict(PRESETS[preset], standardize_start_time_step=explore_steps, end_exploration_time_step=explore_steps)
    agent = cls(env, **kwargs)
    config = {'kind': kind, 'reward': reward, 'weights': REWARDS[reward], 'seed': seed, 'train_steps': train_steps, 'explore_steps': explore_steps,
              'eval_every': eval_every, 'max_hours': max_hours, 'preset': preset, 'agent_kwargs': kwargs, 'protocol': protocol, 'fold': fold,
              'test_windows': tests, 'n_train_windows': len(trains), 'episode_steps': episode_weeks * WEEK, 'warm_steps': WARM,
              'bootstrap_at_window_end': True, 'git_commit': git_commit(), 'citylearn': CL_VERSION, 'torch': torch.__version__, 'numpy': np.__version__,
              'pandas': pd.__version__, 'python': sys.version.split()[0], 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    json.dump(config, open(os.path.join(out_dir, 'config.json'), 'w'), indent=1)
    ref = baselines_zero(reward, tests)
    curve, evals, steps_done, t0, next_eval, stopped_by = [], [], 0, time.time(), eval_every, 'steps'
    # MARLISA: mid-training evaluation mutates its internal buffers (HANDOFF section 5), so it is evaluated at the end only.
    mid_eval = kind != 'marlisa' and eval_every > 0
    ep_steps = episode_weeks * WEEK
    while steps_done < train_steps:
        if max_hours and (time.time() - t0) / 3600.0 > max_hours:
            stopped_by = 'time'
            break
        agent.learn(episodes=1)
        start = int(env.episode_tracker.episode_start_time_step)
        steps_done += ep_steps
        rewards = [float(np.sum(x)) for x in env.unwrapped.rewards]
        m = window_metrics(env, rewards, start, start, start + ep_steps - 2)
        curve.append({'episode': len(curve) + 1, 'steps': steps_done, 'window_start_step': start, 'seconds': round(time.time() - t0),
                      'train_reward': m['reward'], 'import_kwh': m['import_kwh'], 'cost_chf': m['cost_chf'], 'peak_kw': m['peak_kw']})
        pd.DataFrame(curve).to_csv(os.path.join(out_dir, 'curve.csv'), index=False)      # rewritten every episode (survives a timeout)
        if mid_eval and steps_done >= next_eval:
            ev = evaluate(agent, central, reward, tests)
            evals.append({'steps': steps_done, 'seconds': round(time.time() - t0), **ev['aggregate'], **vs_reference(ev['aggregate'], ref)})
            pd.DataFrame(evals).to_csv(os.path.join(out_dir, 'eval_curve.csv'), index=False)
            next_eval += eval_every
            z = evals[-1]
            print(f'[{kind} {reward} s{seed}] {steps_done} steps {time.time()-t0:.0f}s  test cost raw {z["cost_chf_vs_zero_pct"]:+.2f}% corrected '
                  f'{z["cost_corrected_vs_zero_pct"]:+.2f}% import {z["import_kwh_vs_zero_pct"]:+.2f}% highest hour {z["highest_hour_kw_vs_zero_pct"]:+.2f}%', flush=True)
        elif len(curve) % 10 == 0:
            print(f'[{kind} {reward} s{seed}] {steps_done} steps {time.time()-t0:.0f}s  last train cost {m["cost_chf"]:.1f} CHF', flush=True)
    final = evaluate(agent, central, reward, tests)
    final['vs_zero'] = vs_reference(final['aggregate'], ref)
    final.update({'stopped_by': stopped_by, 'steps_trained': steps_done, 'seconds': round(time.time() - t0), 'zero_action': ref})
    json.dump(final, open(os.path.join(out_dir, 'eval_final.json'), 'w'), indent=1)
    z = final['vs_zero']
    print(f'[{kind} {reward} s{seed}] DONE ({stopped_by}) {steps_done} steps in {time.time()-t0:.0f}s; test cost raw {z["cost_chf_vs_zero_pct"]:+.2f}% '
          f'corrected {z["cost_corrected_vs_zero_pct"]:+.2f}% import {z["import_kwh_vs_zero_pct"]:+.2f}% highest hour {z["highest_hour_kw_vs_zero_pct"]:+.2f}%', flush=True)
    return final


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=list(KINDS) + ['baselines'])
    ap.add_argument('--reward', choices=list(REWARDS), default='r001')
    ap.add_argument('--protocol', choices=['weeks', 'quarter'], default='weeks')
    ap.add_argument('--fold', type=int, default=1, help='held-out quarter 1..4 (protocol quarter)')
    ap.add_argument('--episode-weeks', type=int, default=4, help='length of a training episode in weeks')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--train-steps', type=int, default=150000, help='total environment steps used for training')
    ap.add_argument('--explore-steps', type=int, default=2000, help='random-action warm-up and start of observation standardisation (cumulative steps)')
    ap.add_argument('--eval-every', type=int, default=25000, help='held-out evaluation every N training steps (0 = final only; ignored for marlisa)')
    ap.add_argument('--max-hours', type=float, default=11.0, help='stop training at the next episode boundary after this wall-clock time, then evaluate')
    ap.add_argument('--preset', choices=list(PRESETS), default='default')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args(argv)
    tests = test_windows(a.protocol, a.fold)
    if a.kind == 'baselines':
        os.makedirs(a.out, exist_ok=True)
        res = baselines(a.reward, tests)
        json.dump(res, open(os.path.join(a.out, f'baselines_{protocol_tag(a.protocol, a.fold)}_{a.reward}.json'), 'w'), indent=1)
        for name, v in res.items():
            z = v['vs_zero']
            print(f'{name:32s} cost raw {z["cost_chf_vs_zero_pct"]:+6.2f}%  corrected {z["cost_corrected_vs_zero_pct"]:+6.2f}% '
                  f'[{z["cost_corrected_vs_zero_pct_min"]:+.2f}, {z["cost_corrected_vs_zero_pct_max"]:+.2f}]  highest hour {z["highest_hour_kw_vs_zero_pct"]:+6.2f}%  '
                  f'reward {v["aggregate"]["reward_sum"]:.0f}')
        return res
    return train(a.kind, a.reward, a.seed, a.train_steps, a.explore_steps, a.eval_every, a.max_hours, a.preset,
                 os.path.join(a.out, f'{a.kind}_{a.reward}_{protocol_tag(a.protocol, a.fold)}_s{a.seed}'), a.protocol, a.fold, a.episode_weeks)


if __name__ == '__main__':
    main()
