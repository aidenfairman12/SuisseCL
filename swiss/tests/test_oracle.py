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


def test_what_if_cases_behave_as_expected():
    result, tanks, env0 = oracle.run([1.0])
    _, imp0 = oracle.zero_action_import()
    cases = [('base', {}), ('ideal', {'ideal': True}), ('spread x2', {'spread': 2.0})]
    base, ideal, wide = oracle.what_if(tanks, imp0, cases)
    assert abs(base['saving_chf'] - result['scales']['1.0']['saving_chf']) < 1e-6
    assert ideal['saving_chf'] > base['saving_chf'] and wide['saving_chf'] > 1.5 * base['saving_chf']
