"""RL block (D-044): the bill reward, scenario switch and PV rule, hand-computed or structural checks that need no training."""
import os

import numpy as np
import pytest

from swiss.experiments import rl
from swiss.experiments.rewards import SwissBillReward


def _reward(**kw):
    r = SwissBillReward({'central_agent': True}, weights={'cost': 1.0, 'peak': 0.0, 'ramp': 0.0, 'carbon': 0.0, 'comfort': 1.0}, scales={'cost': 1.0, 'peak': 1.0, 'ramp': 1.0, 'carbon': 1.0}, **kw)
    return r


def test_bill_reward_terms_hand_computed():
    r = _reward(export_price=0.08, setpoint=21.0)
    obs = [{'net_electricity_consumption': 2.0, 'electricity_pricing': 0.2, 'indoor_dry_bulb_temperature': 20.0},
           {'net_electricity_consumption': -1.0, 'electricity_pricing': 0.2, 'indoor_dry_bulb_temperature': 22.0}]
    t = r.terms(obs)
    assert t['cost'] == pytest.approx(2.0 * 0.2 - 0.08 * 1.0)            # import cost minus export revenue
    assert t['peak'] == pytest.approx(1.0) and t['comfort'] == pytest.approx(1.0)      # only the cold side counts
    assert r.calculate(obs) == [pytest.approx(-(0.32 + 1.0))]


def test_bill_reward_without_indoor_temperature_has_no_comfort_term():
    r = _reward()
    obs = [{'net_electricity_consumption': 1.0, 'electricity_pricing': 0.1}]
    assert r.terms(obs)['comfort'] == 0.0


@pytest.mark.skipif(not os.path.exists(os.path.join(rl.ROOT, 'swiss', 'datasets', 'swiss_rc_2023', 'schema.json')), reason='datasets not built')
def test_scenario_switch_and_reference_agent():
    try:
        for name, ds in rl.SCENARIOS.items():
            rl.use_scenario(name)
            assert rl.SCHEMA.endswith(os.path.join(ds, 'schema.json')) and len(rl.PRICE) == 8760
        rl.use_scenario('s3')
        env = rl.make_env(True, 'bill', windows=(0, 200))
        ag = rl.reference_agent(env)
        obs, _ = env.reset()
        for _ in range(30):
            obs, *_ = env.step(ag.predict(obs))
        assert abs(float(env.buildings[0].energy_simulation.indoor_dry_bulb_temperature[10]) - 21.0) < 0.1       # thermostat holds the setpoint
        rule = rl.PVRule(env, 0.2)
        act = rule.predict(obs)[0]
        assert len(act) == len(env.action_space[0].low)
    finally:
        rl.use_scenario('s0')
