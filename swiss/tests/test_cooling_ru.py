"""Archetype B (room units, WP2b): two-zone model, thermostat, LP and CityLearn dynamics; and the regression that archetype A is reproduced exactly (cooled fraction 1).
The cell datasets are git-ignored; the tests build the cells they need (a few seconds each). The slow replay needs RUN_SLOW=1."""
import json
import os

import numpy as np
import pytest

from swiss.models.rc_building import PRIORS, simulate_thermostat, simulate_thermostat_zones, step_temperature

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# golden values of archetype A recorded BEFORE the two-zone code was added (hist_high, building 5 = MFH-large cooled; first 5,100 steps; export 8 Rp/kWh)
GOLD_A = {'lp_bill_5100_bi5': 2233.8243253320347, 'lp_zero_5100_bi5': 3077.623485833322, 'qc_sum': 6850.959340750305, 'T_sum': 114566.00454556334, 'th_qc_sum': 5756.392617697149,
          'lp_bill_400_bi0': 82.04937171686477, 'thermo_cost': 67.44935869889699, 'thermo_cooling_kwh': 19.102297857403755, 'thermo_dh26': 484.81067657470703,
          'thermo_import': 1627.4753481596708}


def weather(n=24 * 60):
    k = np.arange(n)
    t = np.where(k < n // 2, 5.0, 30.0) + 3 * np.sin(k / 3.8)
    return t, np.clip(400 * np.sin(k / 3.8), 0, None)


def test_zone_thermostat_with_full_fraction_equals_single_node():
    t, ghi = weather()
    n = len(t)
    qh, qcm = np.full(n, 20.0), np.full(n, 12.0)
    q, qc, T = simulate_thermostat(80.0, t, ghi, None, 3600.0, qh, qcm)
    q1, qc1, t1, t2, tm = simulate_thermostat_zones(80.0, 1.0, t, ghi, None, 3600.0, qh, qcm)
    assert np.array_equal(q, q1) and np.array_equal(qc, qc1) and np.array_equal(T, tm)


def test_mean_temperature_follows_single_node_with_net_heat():
    """Two independent zones with heat Q split by area and cooling Qc on the cooled zone: the area-weighted mean obeys the single-node equation with net heat Q - Qc."""
    t, ghi = weather(24 * 10)
    rng = np.random.default_rng(3)
    A, f = 120.0, 0.4
    q = rng.uniform(0, 8, len(t)); qc = rng.uniform(0, 3, len(t))
    T1 = T2 = Tm = 21.0
    for k in range(len(t)):
        T1 = step_temperature(T1, t[k], ghi[k], f * q[k] - qc[k], f * A)
        T2 = step_temperature(T2, t[k], ghi[k], (1 - f) * q[k], (1 - f) * A)
        Tm = step_temperature(Tm, t[k], ghi[k], q[k] - qc[k], A)
        assert abs(f * T1 + (1 - f) * T2 - Tm) < 1e-9


def test_cooled_zone_held_at_setpoint_uncooled_zone_floats():
    t, ghi = weather()
    n = len(t)
    q, qc, t1, t2, tm = simulate_thermostat_zones(80.0, 0.4, t, ghi, None, 3600.0, np.full(n, 20.0), np.full(n, 0.4 * 30.0))
    assert t1.max() <= 26.0 + 1e-9 and t2.max() > 28.0
    assert (qc[q > 0] == 0).all()                      # never heating and cooling in the same step
    assert abs(tm - (0.4 * t1 + 0.6 * t2)).max() < 1e-12


def test_degree_hours_zone_weighting():
    from swiss.experiments import climate_metrics as cm
    s = {'temp': np.full(10, 27.0), 'temp_cooled': np.full(10, 26.0), 'temp_uncooled': np.full(10, 28.0), 'frac': 0.4}
    b, c, u = cm.degree_hours(s)
    assert (c, u) == (0.0, 20.0) and abs(b - 0.6 * 20.0) < 1e-12
    assert cm.degree_hours({'temp': np.full(10, 27.0)}) == (10.0, None, None)


def _cell(scenario, adoption, fraction=None):
    from swiss.pipeline import build_climate_datasets as bcd
    d = bcd.cell_dir(scenario, adoption, fraction)
    if not (os.path.exists(os.path.join(d, 'schema.json')) and os.path.exists(os.path.join(d, 'build_manifest.json'))):
        bcd.build_cell(scenario, adoption, fraction=fraction)
    return os.path.basename(d)


def test_cell_names_and_dataset_attributes():
    from swiss.pipeline import build_climate_datasets as bcd
    assert bcd.cell_name('gwl3.0', 'high', 0.4) == 'gwl3.0_high_ru' and bcd.cell_name('gwl3.0', 'high', 0.2) == 'gwl3.0_high_ru0.2' and bcd.cell_name('gwl3.0', 'high') == 'gwl3.0_high'
    assert len(bcd.ru_cells()) == 20
    name = _cell('hist', 'high', 0.4)
    d = os.path.join(bcd.ROOT, 'swiss', 'datasets', 'climate', name)
    man = json.load(open(os.path.join(d, 'build_manifest.json')))
    big = man['Building_6']
    assert big['cooled'] and big['cooled_fraction'] == 0.4 and abs(big['cooling_device_nominal_kw'] / big['hp_sh_nominal_kw'] - 0.4) < 1e-4
    sch = json.load(open(os.path.join(d, 'schema.json')))
    assert sch['buildings']['Building_6']['dynamics']['attributes']['cooled_fraction'] == 0.4
    assert 'cooled_fraction' not in sch['buildings']['Building_1']['dynamics']['attributes']
    a = json.load(open(os.path.join(bcd.ROOT, 'swiss', 'datasets', 'climate', _cell('hist', 'high'), 'schema.json')))
    assert 'cooled_fraction' not in a['buildings']['Building_6']['dynamics']['attributes']          # archetype A datasets carry no new attribute


def test_archetype_a_reproduced_exactly_lp_and_thermostat():
    """Regression: cooled fraction 1 (archetype A) gives the same LP bills and the same CityLearn thermostat window as before the two-zone code."""
    from swiss.experiments import climate_controllers as cc, oracle_climate as oc, rl
    name = _cell('hist', 'high')
    inp = oc.ClimateInputs(name)
    assert not any(inp.two_zone) and inp.frac == [1.0] * 6
    s = oc.solve_building(inp, 5, 0.08, 'band', 5100)
    assert abs(s['bill'] - GOLD_A['lp_bill_5100_bi5']) < 1e-6 and abs(s['zero_bill'] - GOLD_A['lp_zero_5100_bi5']) < 1e-6
    assert abs(s['Qc'].sum() - GOLD_A['qc_sum']) < 1e-6 and abs(s['T'].sum() - GOLD_A['T_sum']) < 1e-6 and abs(s['qc_th'].sum() - GOLD_A['th_qc_sum']) < 1e-6
    assert abs(oc.solve_building(inp, 0, 0.08, 'band', 400)['bill'] - GOLD_A['lp_bill_400_bi0']) < 1e-6
    rl.use_scenario('s3')
    m = cc.play_window(inp.dir, lambda env, s0: cc.ThermostatAgentCool(env), (4900, 5100))
    assert abs(m['cost_chf'] - GOLD_A['thermo_cost']) < 1e-6 and abs(m['cooling_electricity_kwh'] - GOLD_A['thermo_cooling_kwh']) < 1e-6
    assert abs(m['degree_hours_above_26'] - GOLD_A['thermo_dh26']) < 1e-6 and abs(m['import_kwh'] - GOLD_A['thermo_import']) < 1e-6


def test_pinned_two_zone_lp_reproduces_the_thermostat():
    from swiss.experiments import oracle_climate as oc
    inp = oc.ClimateInputs(_cell('hist', 'high', 0.4))
    assert inp.two_zone[5] and inp.frac[5] == 0.4 and not any(inp.two_zone[:5])
    n = 4500                                                           # includes cooling days of June
    s = oc.solve_building(inp, 5, 0.08, 'pinned', n)
    assert s['qc_th'].sum() > 0
    assert np.allclose(s['Q'], s['q_th'], atol=1e-6) and np.allclose(s['Qc'], s['qc_th'], atol=1e-6)
    assert np.allclose(s['T1'], s['T1_th'], atol=1e-6) and np.allclose(s['T2'], s['T2_th'], atol=1e-6)
    assert np.allclose(s['T'], 0.4 * s['T1'] + 0.6 * s['T2'])


def test_citylearn_two_zone_dynamics_match_the_thermostat_simulation():
    from swiss.experiments import climate_controllers as cc, oracle_climate as oc, rl
    from swiss.experiments import climate_metrics as cm
    rl.use_scenario('s3')
    inp = oc.ClimateInputs(_cell('hist_hw99', 'high', 0.4))
    rl.SCHEMA = os.path.join(inp.dir, 'schema.json')                  # the cell dataset (rl.use_scenario points at the Phase B S3 dataset)
    s0, e = 4780, 4900
    env = rl.make_env(True, 'bill', windows=(s0, e))
    ag = cc.ThermostatAgentCool(env)
    obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    ser = cm.series_from_env(env)
    big = ser[5]
    assert 'temp_cooled' in big and abs(big['frac'] - 0.4) < 1e-12
    c, u = big['temp_cooled'][:-1], big['temp_uncooled'][:-1]
    assert np.nanmax(c) <= 26.0 + 1e-6 and np.nanmax(u) > 27.0
    assert np.allclose(big['temp'][:-1], 0.4 * c + 0.6 * u, atol=1e-9)
    assert big['cool'].sum() > 0
    for k in range(5):
        assert 'temp_cooled' not in ser[k]


@pytest.mark.skipif(not os.environ.get('RUN_SLOW'), reason='slow: LP plus CityLearn replay over 5,100 steps (about 2 minutes); set RUN_SLOW=1')
def test_two_zone_replay_matches_program():
    from swiss.experiments import oracle_climate as oc
    inp = oc.ClimateInputs(_cell('hist_hw99', 'high', 0.4))
    r = oc.replay(inp, 'band', 8.0, 5100)
    assert r['rel_diff_saving_pct'] < 0.5 and r['max_temperature_difference_k'] < 1e-6
    assert abs(r['cooling_electricity_kwh_predicted'] - r['cooling_electricity_kwh_realised']) < 1e-3
