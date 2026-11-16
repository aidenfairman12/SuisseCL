"""A8 tests: reward and baseline controllers (short episodes)."""
import os

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCHEMA = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'schema.json')
pytestmark = pytest.mark.skipif(not os.path.exists(SCHEMA), reason='dataset not built')


def _run(make_agent, steps=719):
    from citylearn.citylearn import CityLearnEnv
    from swiss.experiments.rewards import SwissDistrictReward
    env = CityLearnEnv(SCHEMA, central_agent=True, simulation_end_time_step=steps, reward_function=SwissDistrictReward)
    agent = make_agent(env)
    obs, _ = env.reset()
    ret = 0.0
    while not env.terminated:
        obs, r, term, trunc, _ = env.step(agent.predict(obs))
        ret += float(np.sum(r))
        if term or trunc:
            break
    imp = sum(np.maximum(np.asarray(b.net_electricity_consumption, dtype=float), 0) for b in env.buildings)
    return ret, imp


def test_bau_identical_to_zero_action_without_ev_appliance_battery():
    from citylearn.agents.baseline import BusinessAsUsualAgent, ZeroActionBaselineAgent
    r0, i0 = _run(lambda e: ZeroActionBaselineAgent(e))
    r1, i1 = _run(lambda e: BusinessAsUsualAgent(e))
    assert np.allclose(i0, i1) and abs(r0 - r1) < 1e-9


def test_tariff_map_matches_documented_hours():
    from swiss.experiments.run_baselines import tariff_map
    m = tariff_map(0.1)['heating_storage']
    assert m[1] == 0.1 and m[7] == 0.1 and m[8] == 0.0 and m[9] == -0.1 and m[20] == -0.1 and m[21] == 0.1 and m[24] == 0.1
    assert set(tariff_map(0.1)) == {'heating_storage', 'dhw_storage'}


def test_rbc_moves_energy_and_reward_is_finite_negative():
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    from citylearn.agents.rbc import BasicRBC
    r0, i0 = _run(lambda e: ZeroActionBaselineAgent(e))
    r1, i1 = _run(lambda e: BasicRBC(e))
    assert np.isfinite(r0) and r0 < 0 and np.isfinite(r1)
    assert not np.allclose(i0, i1)          # storage actions change the load shape
    assert i1.sum() >= i0.sum() * 0.99      # storage losses cannot create energy
