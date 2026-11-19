"""WP3 controllers on a short window of one cell (gwl3.0_hw99_high: heat-wave week 29, MFH-large cooled) and the cell result schema."""
import json
import os

import numpy as np
import pytest

from swiss.experiments import climate_controllers as cc, oracle_climate as oc, rl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CELL = 'gwl3.0_hw99_high'
WIN = (4872 + 24, 4872 + 24 + 71)          # three days inside the inserted heat wave


@pytest.fixture(scope='module')
def inp():
    from swiss.pipeline import build_climate_datasets as bcd
    d = bcd.cell_dir('gwl3.0_hw99', 'high')
    if not os.path.exists(os.path.join(d, 'schema.json')):
        bcd.build_cell('gwl3.0_hw99', 'high')
    rl.use_scenario('s3')
    return oc.ClimateInputs(CELL)


@pytest.fixture(scope='module')
def runs(inp):
    out = {}
    out['thermostat'] = cc.play_window(inp.dir, lambda env, s0: cc.ThermostatAgentCool(env), WIN)
    out['pv_rule'] = cc.play_window(inp.dir, lambda env, s0: cc.PVRuleCool(env, 0.1), WIN)
    fc = cc.ClimateForecaster(inp, 'perfect')
    out['mpc'] = cc.play_window(inp.dir, lambda env, s0: cc.MPCClimate(env, s0, inp, fc, 24), WIN)
    return out


def test_thermostat_cools_in_the_heat_wave_and_no_cold(runs):
    t = runs['thermostat']
    assert t['cooling_electricity_kwh'] > 50.0
    assert t['comfort_cold_kh'] < 1.0


def test_pv_rule_runs_and_is_finite(runs):
    assert np.isfinite(runs['pv_rule']['cost_chf'])
    assert runs['pv_rule']['cooling_electricity_kwh'] > 0.0


def test_mpc_perfect_forecast_beats_thermostat_without_discomfort(runs):
    t, m = runs['thermostat'], runs['mpc']
    assert m['cost_chf'] <= t['cost_chf'] + 0.5
    assert m['comfort_cold_kh'] < 1.0
    assert m['cooling_electricity_kwh'] > 0.0                                      # cooling is used in the hot week
    # the cooled building stays at or below about 26 C (soft constraint): degree hours of the district differ from the thermostat by little
    assert m['degree_hours_above_26'] <= t['degree_hours_above_26'] + 50.0


def test_thermostat_agent_matches_the_baseline_path_of_the_program(inp):
    """The rollout thermostat reproduces the thermostat path used as reference by oracle_climate (same temperatures)."""
    from citylearn.citylearn import CityLearnEnv
    from swiss.experiments.rewards import SwissDistrictReward
    env = CityLearnEnv(os.path.join(inp.dir, 'schema.json'), central_agent=True, reward_function=SwissDistrictReward, simulation_start_time_step=0, simulation_end_time_step=4872 + 100)
    ag = cc.ThermostatAgentCool(env)
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    for bi, b in enumerate(env.buildings):
        T = np.asarray(b.energy_simulation.indoor_dry_bulb_temperature, dtype=float)[4800:4872]
        T_prog = oc.thermostat(inp, bi, inp.N)[2][4800:4872]
        assert np.abs(T - T_prog).max() < 0.05


def test_weather_view_true_equals_inputs(inp):
    v = cc.WeatherView(inp)
    assert v.ta is inp.ta and np.allclose(v.cop_h[0], inp.heat_tank[0]['cop'])
    ta_f, dif, dire = cc.synthetic_weather_error(inp, bias_k=2.0, noise_k=0.0)
    assert np.allclose(ta_f - inp.ta, 2.0)
    v2 = cc.WeatherView(inp, ta_f, dif + dire)
    assert not np.allclose(v2.cop_h[0], v.cop_h[0])


def test_year_result_schema():
    fn = os.path.join(ROOT, 'swiss', 'experiments', 'climate_results', f'{CELL}__year.json')
    if not os.path.exists(fn):
        pytest.skip('matrix not run')
    y = json.load(open(fn))
    for k in ('band', 'pinned', 'mass_value_pts', 'thermostat_year', 'optimum_year', 'cooled'):
        assert k in y
    assert y['band']['saving_pct'] >= y['pinned']['saving_pct'] - 1e-6              # mass flexibility cannot lower the optimum saving
    for key in ('thermostat_year', 'optimum_year'):
        assert y[key]['default']['balance_error_kwh'] < 1e-6
        assert len(y[key]['week29_district']['net']) == 168
