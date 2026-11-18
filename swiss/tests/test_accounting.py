"""B5 accounting: own cost/bill equals the CityLearn environment on a full-year S1 rollout; export revenue is separate."""
import os

import numpy as np
import pytest

from swiss.experiments.accounting import replay_check, rollout_arrays, scenario_metrics
from swiss.models.export_price import DEFAULT_EXPORT_RP, EXPORT_SWEEP_RP, export_price_chf_per_kwh

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def test_export_price_series():
    p = export_price_chf_per_kwh(5, 8.0)
    assert p.shape == (5,) and (p == 0.08).all()
    assert DEFAULT_EXPORT_RP in EXPORT_SWEEP_RP and 0.0 in EXPORT_SWEEP_RP


@pytest.fixture(scope='module')
def s1_env():
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    from citylearn.citylearn import CityLearnEnv
    schema = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_pv_2023', 'schema.json')
    if not os.path.exists(schema):
        pytest.skip('swiss_pv_2023 not built')
    env = CityLearnEnv(schema, central_agent=True)
    ag = ZeroActionBaselineAgent(env); obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    return env


def test_replay_import_cost_equals_environment(s1_env):
    own, theirs, rel = replay_check(s1_env)
    assert rel < 1e-4 and own > 0


def test_environment_gives_no_export_credit(s1_env):
    net, pv, cost, price = rollout_arrays(s1_env)
    assert (net < 0).any(), 'S1 should export in some hours'
    assert (cost >= -1e-9).all()                      # environment never credits exports
    m0 = scenario_metrics(s1_env, export_rp=0.0)
    assert m0['export_kwh'] > 0 and m0['export_revenue_chf'] == 0.0
    assert m0['bill_chf'] == pytest.approx(m0['import_cost_chf'])


def test_bill_identity_and_sweep_is_monotone(s1_env):
    bills = []
    for rp in EXPORT_SWEEP_RP:
        m = scenario_metrics(s1_env, export_rp=rp)
        assert m['export_revenue_chf'] == pytest.approx(m['export_kwh'] * rp / 100.0, rel=1e-9)
        assert m['bill_chf'] == pytest.approx(m['import_cost_chf'] - m['export_revenue_chf'], rel=1e-12)
        bills.append(m['bill_chf'])
    assert all(a >= b for a, b in zip(bills, bills[1:]))
    assert scenario_metrics(s1_env)['export_revenue_chf'] is None          # absent, never 0


def test_pv_energy_matches_capacity(s1_env):
    import json
    meta = json.load(open(os.path.join(ROOT, 'data', 'canonical', 'pv', 'pv_capacity_2023.json')))
    kwp = sum(b['ratios']['1.0']['kwp'] for b in meta['buildings'].values())
    _, pv, _, _ = rollout_arrays(s1_env)
    n = len(pv)
    expected = kwp * meta['annual_specific_yield_kwh_per_kwp'] * n / 8760
    assert pv.sum() == pytest.approx(expected, rel=0.01)
