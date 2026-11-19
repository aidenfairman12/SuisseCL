"""Climate impact metrics: known-answer tests on small synthetic cases and a closure check on a real CityLearn rollout."""
import numpy as np
import pytest

from swiss.experiments import climate_metrics as cm


def test_allocation_priority_and_balance():
    base = np.array([1.0, 1.0, 1.0, 0.0]); dhw = np.array([0.5, 0.5, 0.0, 0.0]); heat = np.array([0.0, 2.0, 0.0, 0.0]); cool = np.array([0.0, 0.0, 3.0, 0.0])
    pv = np.array([4.0, 2.0, 2.0, 5.0]); batt = np.array([0.0, 0.0, 0.0, 2.0])
    a = cm.allocate(base, dhw, heat, cool, pv, batt)
    # step 1: pv 4 serves base 1, dhw .5, nothing else, export 2.5
    assert a['pv_to_base'][0] == 1.0 and a['pv_to_dhw'][0] == 0.5 and a['export'][0] == pytest.approx(2.5)
    # step 2: pv 2 serves base 1 then dhw .5 then heat .5; grid heat 1.5
    assert a['pv_to_heat'][1] == pytest.approx(0.5) and a['grid_heat'][1] == pytest.approx(1.5)
    # step 3: pv 2 serves base 1 and cool 1; grid cool 2
    assert a['pv_to_cool'][2] == pytest.approx(1.0) and a['grid_cool'][2] == pytest.approx(2.0)
    # step 4: no load, pv 5, battery charges 2 from pv, export 3
    assert a['pv_to_charge'][3] == pytest.approx(2.0) and a['export'][3] == pytest.approx(3.0)
    net = base + dhw + heat + cool + batt - pv
    assert np.allclose(net, a['imp'] - a['export'])


def test_hp_first_priority_gives_cooling_more_pv():
    z = np.zeros(1)
    a = cm.allocate(np.array([1.0]), z, z, np.array([2.0]), np.array([2.0]), z, 'default')
    b = cm.allocate(np.array([1.0]), z, z, np.array([2.0]), np.array([2.0]), z, 'hp_first')
    assert a['pv_to_cool'][0] == pytest.approx(1.0) and b['pv_to_cool'][0] == pytest.approx(2.0)


def test_battery_discharge_serves_remaining_proportionally_and_excess_exported():
    z = np.zeros(2)
    a = cm.allocate(np.array([1.0, 0.0]), z, np.array([1.0, 0.0]), np.array([2.0, 0.0]), z, np.array([-2.0, -1.0]))
    # step 0: remaining loads 1 (base) 1 (heat) 2 (cool); discharge 2 -> half of each
    assert a['batt_to_cool'][0] == pytest.approx(1.0) and a['grid_cool'][0] == pytest.approx(1.0)
    # step 1: no load, discharge 1 exported
    assert a['batt_export'][1] == pytest.approx(1.0)
    net = np.array([1.0, 0.0]) + np.array([1.0, 0.0]) + np.array([2.0, 0.0]) + np.array([-2.0, -1.0])
    assert np.allclose(net, a['imp'] - a['export'])


def test_building_and_district_metrics_and_difference():
    rng = np.random.default_rng(0)
    n = 24 * 366
    months = np.repeat(np.arange(12), n // 12 + 1)[:n] + 1
    def mk(cool_scale):
        return dict(base=rng.uniform(0.2, 1, n), dhw=rng.uniform(0, 0.3, n), heat=rng.uniform(0, 0.5, n), cool=cool_scale * rng.uniform(0, 1, n),
                    pv=rng.uniform(0, 2, n), batt=rng.uniform(-0.5, 0.5, n), temp=rng.uniform(20, 30, n))
    s1, s0 = mk(1.0), mk(0.0)
    d1 = cm.district_metrics([s1, s1], months); d0 = cm.district_metrics([s0, s0], months)
    assert d1['balance_error_kwh'] < 1e-9
    assert d1['annual']['pv_self_consumption'] <= 1.0
    diff = cm.difference(d1, d0)
    assert diff['annual']['cool'] > 0 and diff['annual']['import'] != 0
    b = d1['buildings'][0]['annual']
    assert b['pv_share_of_cooling'] + b['battery_share_of_cooling'] + b['grid_share_of_cooling'] == pytest.approx(1.0)


def test_closure_on_citylearn_rollout():
    import os
    from citylearn.citylearn import CityLearnEnv
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    env = CityLearnEnv(os.path.join(root, 'swiss', 'datasets', 'swiss_pvbat_2023', 'schema.json'), central_agent=True,
                       simulation_start_time_step=0, simulation_end_time_step=24 * 14)
    ag = ZeroActionBaselineAgent(env)
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    ser = cm.series_from_env(env)
    n = len(ser[0]['base'])
    d = cm.district_metrics(ser, np.full(n, 1))
    assert d['balance_error_kwh'] < 1e-6
    for s in ser:
        assert np.allclose(s['base'] + s['dhw'] + s['heat'] + s['cool'] + s['batt'] - s['pv'], s['net'], atol=1e-6)
