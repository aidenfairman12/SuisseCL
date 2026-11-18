"""RL protocol tests (D-023): window partitions, training episodes drawn only from training windows, scoring checked against the independent
full-year trace, the end-of-window bootstrapping fix, and an end-to-end tiny training run that writes its result files.

Run: PYTHONPATH=. cl/bin/python -m pytest swiss/tests/test_rl.py -q
"""
import json
import os

import numpy as np
import pandas as pd
import pytest
from citylearn.agents.sac import SAC

from swiss.experiments import rl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
pytestmark = pytest.mark.skipif(not os.path.exists(rl.SCHEMA), reason='dataset not built')


def test_week_windows_are_disjoint_and_inside_the_year():
    tests = rl.test_windows('weeks')
    assert len(tests) == 8 and len({w[0] for w in tests}) == 8
    for s, e in tests:
        assert e - s + 1 == 168 and 0 <= s and e <= rl.LAST_STEP and s % 168 == 0
    assert 4 <= sum(k < 13 or k >= 40 for k in rl.TEST_WEEKS) <= 5, 'test weeks must cover both heating season and mild weeks'


def test_quarter_folds_partition_the_year():
    covered = np.zeros(4 * rl.QUARTER, dtype=bool)
    for f in (1, 2, 3, 4):
        (s, e), = rl.test_windows('quarter', f)
        assert e - s + 1 == rl.QUARTER and not covered[s:e + 1].any()
        covered[s:e + 1] = True
    assert covered.all()


@pytest.mark.parametrize('protocol,fold', [('weeks', 1), ('quarter', 1), ('quarter', 3), ('quarter', 4)])
def test_training_windows_never_touch_a_test_step(protocol, fold):
    tests = rl.test_windows(protocol, fold)
    blocked = np.zeros(rl.LAST_STEP + 2, dtype=bool)
    for s, e in tests:
        blocked[s:e + 1] = True
    for weeks in (1, 4):
        wins = rl.train_windows(tests, weeks)
        assert len(wins) > 20
        for s, e in wins:
            assert e - s + 1 == weeks * 168 and s % 24 == 0 and e <= rl.LAST_STEP and not blocked[s:e + 1].any()


def test_training_environment_draws_only_allowed_windows():
    wins = rl.train_windows(rl.test_windows('weeks'), 4)
    env = rl.make_env(True, 'r001', windows=wins, seed=1)
    allowed, seen = {w[0] for w in wins}, set()
    for _ in range(15):
        env.reset()
        s = int(env.episode_tracker.episode_start_time_step)
        seen.add(s)
        assert s in allowed
    assert len(seen) > 6, 'episodes must vary'


def test_reward_presets_reach_the_reward_function():
    for name, w in rl.REWARDS.items():
        env = rl.make_env(True, name, windows=rl.test_windows('weeks')[0])
        assert env.unwrapped.reward_function.weights == w
    assert rl.REWARDS['r001'] == {'cost': 1.0, 'peak': 1.0, 'ramp': 1.0, 'carbon': 0.0}


def test_zero_action_scoring_equals_the_independent_full_year_trace():
    """Doing nothing does not depend on where a window starts or on the warm-up, so the score must equal slicing the full-year trace."""
    t = pd.read_csv(os.path.join(ROOT, 'swiss', 'experiments', 'results', 'traces', 'ALG-001_zero_action.csv.gz'))
    tests = rl.test_windows('weeks')
    got = rl.baselines_zero('r001', tests)
    imp = cost = peak = 0.0
    for s, e in tests:
        sl = t.iloc[s:e + 1]                                   # 168 scored steps
        i = sum(np.maximum(sl[f'b{b}_net_kwh'].to_numpy(), 0) for b in range(1, 7))
        imp += i.sum()
        cost += float((i * sl.price.to_numpy()).sum())
        peak = max(peak, float(sl.district_net_kwh.max()))
    assert abs(got['import_kwh'] - imp) < 1e-6 * imp and abs(got['cost_chf'] - cost) < 1e-6 * cost and abs(got['highest_hour_kw'] - peak) < 1e-6 * peak
    assert abs(got['stored_change_kwh_th']) < 1e-9 and abs(got['cost_corrected_chf'] - got['cost_chf']) < 1e-9


def test_vs_reference_of_the_reference_is_zero():
    agg = rl.baselines_zero('r001', rl.test_windows('weeks'))
    assert all(abs(v) < 1e-9 for v in rl.vs_reference(agg, agg).values())


def test_stored_heat_correction_is_a_consistent_range():
    from swiss.experiments.run_baselines import CONTROLLERS
    tests = rl.test_windows('weeks')[:2]
    rows = [rl.play(CONTROLLERS['ALG-003_basic_rbc'], True, 'r001', w) for w in tests]
    agg = rl.aggregate(rows)
    assert agg['cost_corrected_chf_min'] <= agg['cost_corrected_chf'] <= agg['cost_corrected_chf_max']
    assert abs(agg['stored_change_kwh_th']) > 0.1, 'the night rule ends windows with a different stored amount than it starts with'
    for r in rows:
        assert r['terminal_value_chf']['low'] <= r['terminal_value_chf']['mean'] <= r['terminal_value_chf']['high'] or r['stored_change_kwh_th'] < 0


def _done_flags(agent):
    return [x[4] for x in agent.replay_buffer[0].buffer]


def test_bootstrapping_never_marks_a_window_cut_as_terminal():
    """Plain SAC stores CityLearn's end-of-episode flag as 'done' (the future-value term is then switched off); the bootstrapping agent must not."""
    kw = dict(standardize_start_time_step=40, end_exploration_time_step=40)
    plain = SAC(rl.make_env(True, 'r001', windows=[(0, 167)], seed=0), **kw)
    plain.learn(episodes=1)
    boot = rl.SACBootstrap(rl.make_env(True, 'r001', windows=[(0, 167)], seed=0), **kw)
    boot.learn(episodes=1)
    assert any(_done_flags(plain)), 'control: plain SAC marks the last step of the window as done'
    assert not any(_done_flags(boot)) and len(_done_flags(boot)) == len(_done_flags(plain))


def test_tiny_training_run_writes_all_outputs(tmp_path):
    final = rl.main(['sac_central', '--reward', 'r001', '--seed', '0', '--train-steps', '336', '--episode-weeks', '1', '--explore-steps', '168',
                     '--eval-every', '0', '--out', str(tmp_path)])
    d = tmp_path / 'sac_central_r001_weeks_s0'
    for f in ('config.json', 'curve.csv', 'eval_final.json'):
        assert (d / f).exists(), f
    cfg = json.loads((d / 'config.json').read_text())
    assert cfg['protocol'] == 'weeks' and cfg['bootstrap_at_window_end'] is True and cfg['seed'] == 0 and cfg['citylearn'] == '3.3.0' and cfg['warm_steps'] == 96
    curve = pd.read_csv(d / 'curve.csv')
    allowed = {w[0] for w in rl.train_windows(rl.test_windows('weeks'), 1)}
    assert list(curve.steps) == [168, 336] and set(curve.window_start_step) <= allowed
    assert final['stopped_by'] == 'steps' and final['steps_trained'] == 336 and len(final['windows']) == 8
    assert final['aggregate']['windows'] == 8 and np.isfinite(final['vs_zero']['cost_corrected_vs_zero_pct'])
