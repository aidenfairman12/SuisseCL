"""Exact cost optimum (oracle.py): replaying its schedule in the real CityLearn environment must realise exactly the predicted saving.

Run: PYTHONPATH=. cl/bin/python -m pytest swiss/tests/test_oracle.py -q
"""
import os

import pytest

from swiss.experiments import oracle, rl

pytestmark = pytest.mark.skipif(not os.path.exists(rl.SCHEMA), reason='dataset not built')


def test_optimum_replayed_in_citylearn_matches_the_program_exactly():
    result, tanks, env0 = oracle.run([0.5, 1.0])
    pred, realised_cost, _ = oracle.validate_by_replay(tanks, len(env0.buildings), rl.PRICE[:oracle.N])
    realised = result['zero_action_cost_chf'] - realised_cost
    assert abs(pred - realised) < 1e-3, f'program and environment disagree: {pred:.3f} vs {realised:.3f} CHF'
    s1, s05 = result['scales']['1.0'], result['scales']['0.5']
    assert 0.2 < s1['saving_pct'] < 2.0, 'the ceiling on tariff savings at the assumed tank sizes is below 2 % of the bill'
    assert s05['saving_chf'] < s1['saving_chf'], 'a bigger tank can only help'
    assert abs(s1['saving_chf'] - pred) < 1e-6
