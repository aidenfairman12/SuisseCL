"""B4 battery (assumed, per building): CityLearn 3.3.0 electrical storage with constant round-trip efficiency, no degradation.
Checks: SoC bounds, power limit, energy conservation with losses, no self-discharge, net consumption identity."""
import os

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DS = os.path.join(ROOT, 'swiss', 'datasets')
N = 240
RT = 0.90          # round-trip efficiency in the dataset (A-016); CityLearn applies sqrt(RT) in each direction
DOD = 0.9


def _run(name, battery_schedule):
    from citylearn.citylearn import CityLearnEnv
    env = CityLearnEnv(os.path.join(DS, name, 'schema.json'), central_agent=True)
    env.reset()
    for t in range(N):
        a = []
        for b in env.buildings:
            for nm in b.active_actions:
                a.append(battery_schedule(t) if nm == 'electrical_storage' else 0.0)
        env.step([a])
    return env


def _schedule(t):                       # charge 12 h, rest 4 h, discharge 8 h, repeat; full-power requests then half
    h = t % 24
    return 1.0 if h < 12 else (0.0 if h < 16 else -0.7)


@pytest.fixture(scope='module')
def envs():
    if not os.path.isdir(os.path.join(DS, 'swiss_pvbat_2023')):
        pytest.skip('swiss_pvbat_2023 not built (build_dataset.py --pv-ratio 1.0 --battery-kwh-per-kwp 1.0 --out-name swiss_pvbat_2023)')
    return _run('swiss_pvbat_2023', _schedule), _run('swiss_pvbat_2023', lambda t: 0.0), _run('swiss_pv_2023', lambda t: 0.0)


def test_soc_bounds_power_limit_and_no_self_discharge(envs):
    env, idle, _ = envs
    for b in env.buildings:
        bat = b.electrical_storage
        soc = np.asarray(bat.soc)[:N]
        e = np.asarray(bat.electricity_consumption)[:N]
        assert soc.min() >= (1 - DOD) - 1e-6 and soc.max() <= 1.0 + 1e-6
        assert np.abs(e).max() <= bat.nominal_power + 1e-5                       # kWh per 1 h step = kW
        rest = np.array([(t % 24) in range(12, 16) for t in range(N)])
        d = np.diff(soc, prepend=1 - DOD)
        assert np.abs(d[rest & (np.arange(N) > 0)]).max() < 1e-6                 # nothing leaks while idle
    for b in idle.buildings:
        assert np.allclose(np.asarray(b.electrical_storage.soc)[:N], 1 - DOD, atol=1e-6)


def test_energy_conservation_with_losses(envs):
    env, _, _ = envs
    eta1 = np.sqrt(RT)
    for b in env.buildings:
        bat = b.electrical_storage
        cap = bat.capacity
        soc = np.asarray(bat.soc)[:N]
        e = np.asarray(bat.electricity_consumption)[:N]                          # grid side, + charge, - discharge
        stored = np.diff(np.concatenate([[1 - DOD], soc])) * cap                 # change of stored energy per step
        ch, dis = np.clip(e, 0, None), np.clip(-e, 0, None)
        np.testing.assert_allclose(stored[ch > 1e-9], eta1 * ch[ch > 1e-9], rtol=2e-3, atol=1e-4)
        np.testing.assert_allclose(stored[dis > 1e-9], -dis[dis > 1e-9] / eta1, rtol=2e-3, atol=1e-4)
        loss = e.sum() - (soc[-1] - (1 - DOD)) * cap                             # grid energy in minus stored energy gained
        assert loss > 0                                                          # losses are positive, never a gain
        assert loss <= (ch.sum() + dis.sum()) * (1 - eta1) / eta1 + 1e-6          # and bounded by the efficiency in each direction


def test_net_consumption_identity(envs):
    env, idle, pv_only = envs
    for i, b in enumerate(env.buildings):
        diff = np.asarray(b.net_electricity_consumption)[:N] - np.asarray(pv_only.buildings[i].net_electricity_consumption)[:N]
        np.testing.assert_allclose(diff, np.asarray(b.electrical_storage.electricity_consumption)[:N], atol=1e-4)
        # idle battery does not change anything
        np.testing.assert_allclose(np.asarray(idle.buildings[i].net_electricity_consumption)[:N],
                                   np.asarray(pv_only.buildings[i].net_electricity_consumption)[:N], atol=1e-5)


def test_sizing_rule_in_manifest():
    import json
    p = os.path.join(DS, 'swiss_pvbat_2023', 'build_manifest.json')
    if not os.path.exists(p):
        pytest.skip('dataset not built')
    m = json.load(open(p))
    for v in m.values():
        assert v['battery_kwh'] == pytest.approx(v['pv_kwp'], abs=1e-3)           # 1 kWh per kWp
