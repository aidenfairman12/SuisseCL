"""S3 (RC thermal model): CityLearn building class, thermostat baseline, and the exact optimum replayed in the environment."""
import os

import numpy as np
import pytest

from swiss.experiments import oracle_rc as o
from swiss.experiments.thermostat import ThermostatAgent

pytestmark = pytest.mark.skipif(not os.path.isdir(os.path.join(o.DS, 'swiss_rc_2023')), reason='swiss_rc_2023 not built (build_dataset.py --pv-ratio 1.0 --battery-kwh-per-kwp 1.0 --rc --out-name swiss_rc_2023)')
N = 1500


@pytest.fixture(scope='module')
def inp():
    return o.RCInputs()


def test_thermostat_in_citylearn_matches_the_model_baseline(inp):
    from citylearn.citylearn import CityLearnEnv
    env = CityLearnEnv(os.path.join(o.DS, 'swiss_rc_2023', 'schema.json'), central_agent=True)
    ag = ThermostatAgent(env); obs, _ = env.reset()
    for _ in range(N):
        obs, *_ = env.step(ag.predict(obs))
    for bi, b in enumerate(env.buildings):
        A = inp.area(bi, o.PRIORS)
        q, T = o.thermostat(inp, bi, A, o.PRIORS, N)
        # steps 0 and 1 show a start-up transient of the CityLearn episode (0.4 kWh at most, temperature back at 21 C at step 1); compare from step 2
        np.testing.assert_allclose(np.asarray(b.heating_demand)[2:N], q[2:], rtol=2e-3, atol=2e-3)   # float32 in CityLearn
        np.testing.assert_allclose(np.asarray(b.energy_simulation.indoor_dry_bulb_temperature)[2:N], T[2:], atol=2e-2)
    net = np.stack([np.asarray(b.net_electricity_consumption, dtype=float)[:N] for b in env.buildings], axis=1)
    price = inp.price[:N]
    bill = float((np.maximum(net, 0) * price[:, None]).sum() - 0.08 * np.maximum(-net, 0).sum())
    tot = o.scenario(inp, {}, 'band 21-24', 8.0, n=N)
    assert bill == pytest.approx(tot['zero_bill'], rel=5e-3)


@pytest.mark.parametrize('band', ['band 20-24', 'band 21-24'])
def test_replay_matches_program_and_respects_comfort(inp, band):
    r = o.replay(inp, {}, band, 8.0, n=N)
    assert r['rel_diff_saving_pct'] < 0.5, r                    # plan stop condition
    assert r['max_temperature_difference_k'] < 0.05, r
    tot, sols = o.scenario(inp, {}, band, 8.0, n=N, with_solution=True)
    lower = o.BANDS[band]
    for s in sols:
        assert s['T'].min() >= lower - 1e-6
        assert (s['T'] <= np.maximum(o.UPPER_BY[band], s['T_thermostat']) + 1e-6).all()
    assert tot['saving_chf'] > 0


def test_pure_shifting_saves_less_than_wider_band(inp):
    a = o.scenario(inp, {}, 'band 20-24', 8.0, n=800)
    b = o.scenario(inp, {}, 'band 21-24', 8.0, n=800)
    assert a['saving_chf'] >= b['saving_chf'] - 1e-6            # a wider feasible set cannot be worse


def test_thermal_mass_adds_value_on_top_of_tanks_and_battery(inp):
    none = o.scenario(inp, {}, 'no thermal flexibility', 8.0, n=800, with_solution=True)
    with_mass = o.scenario(inp, {}, 'band 21-24', 8.0, n=800)
    assert with_mass['saving_chf'] >= none[0]['saving_chf'] - 1e-6
    for s in none[1]:
        assert np.abs(s['T'] - s['T_thermostat']).max() < 0.05          # the house stays on the thermostat path
