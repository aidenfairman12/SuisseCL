"""Phase C WP2: cooling in the RC model and CityLearn, the dataset builder options and the climate exact optimum (oracle_climate).
Fast tests by default; the long replay needs RUN_SLOW=1 (it plays 5,100 hourly steps, a few minutes)."""
import json
import os
import shutil
import sys
import warnings

import numpy as np
import pytest

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from swiss.models import rc_building as rcb  # noqa: E402

DS = os.path.join(ROOT, 'swiss', 'datasets')
needs_data = pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, 'data', 'canonical', 'weather_klo_2023_hourly.csv')), reason='canonical data not built')


# --------------------------------------------------------------------------------------------------------------- model helpers
def test_cooling_cop_equals_citylearn():
    from citylearn.energy_model import HeatPump
    dev = HeatPump(nominal_power=10.0, efficiency=0.356, target_heating_temperature=35.0, target_cooling_temperature=8.0)
    t = np.array([-5.0, 0.0, 8.0, 9.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0])
    ref = np.array([dev.get_cop(float(x), heating=False) for x in t])
    assert np.allclose(rcb.cooling_cop(t, 0.356), ref)


def test_cooling_capacity_zero_below_threshold_and_scales():
    t = np.array([10.0, 14.9, 15.0, 30.0])
    cap = rcb.cooling_capacity_kwh(t, 10.0, 0.356, dt_h=1.0)
    assert cap[0] == 0 and cap[1] == 0 and cap[2] > 0
    assert np.isclose(cap[3], 10.0 * rcb.cooling_cop(30.0, 0.356))
    assert np.allclose(rcb.cooling_capacity_kwh(t, 10.0, 0.356, dt_h=0.25), cap * 0.25)


def test_thermostat_without_cooling_is_simulate_ideal():
    rng = np.random.default_rng(1)
    ta = 10 + 12 * np.sin(np.linspace(0, 6, 500)) + rng.normal(0, 1, 500)
    ghi = np.clip(300 * np.sin(np.linspace(0, 60, 500)), 0, None)
    q0, T0 = rcb.simulate_ideal(300.0, ta, ghi)
    q, qc, T = rcb.simulate_thermostat(300.0, ta, ghi)
    assert np.allclose(q, q0) and np.allclose(T, T0) and qc.max() == 0


def test_thermostat_cooling_holds_the_set_point_and_balances():
    n = 240
    ta = np.full(n, 34.0); ghi = np.full(n, 600.0)
    cap = np.full(n, 1e3)                                                  # ample capacity (kW thermal)
    q, qc, T = rcb.simulate_thermostat(300.0, ta, ghi, q_cool_max=cap)
    assert qc[24:].min() > 0 and np.all(T[24:] <= rcb.COOL_SETPOINT_C + 1e-6) and np.allclose(T[24:], rcb.COOL_SETPOINT_C, atol=1e-6)
    t1 = rcb.step_temperature(T[10], ta[11], ghi[11], q[11] - qc[11], 300.0)
    assert np.isclose(t1, T[11])
    free = rcb.simulate_thermostat(300.0, ta, ghi, q_cool_max=np.full(n, 1.0))[2]       # undersized device: temperature above the set point
    assert free[-1] > rcb.COOL_SETPOINT_C


# --------------------------------------------------------------------------------------------------------------- dataset builder
@needs_data
def test_default_rc_build_is_unchanged():
    """The Phase C options must not change a Phase B build: rebuild S3 under a scratch name and compare with swiss_rc_2023."""
    from swiss.citylearn_build import build_dataset
    ref = os.path.join(DS, 'swiss_rc_2023')
    if not os.path.exists(os.path.join(ref, 'schema.json')):
        pytest.skip('swiss_rc_2023 not built')
    name = '_test_rc_regress'
    out = os.path.join(DS, name)
    try:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            build_dataset.main(out_name=name, carbon_file=os.path.join(ROOT, 'data', 'canonical', 'carbon_intensity_citylearn_2023.csv'), pv_ratio=1.0, battery_kwh_per_kwp=1.0, rc=True)
        for f in ('schema.json', 'weather.csv', 'pricing.csv', 'Building_1.csv', 'Building_6.csv', 'build_manifest.json'):
            assert open(os.path.join(out, f), 'rb').read() == open(os.path.join(ref, f), 'rb').read(), f
        assert not os.path.exists(os.path.join(out, 'build_meta.json'))
    finally:
        shutil.rmtree(out, ignore_errors=True)


@pytest.fixture(scope='module')
def cells():
    from swiss.pipeline import build_climate_datasets as bc
    if not os.path.exists(os.path.join(ROOT, 'data', 'canonical', 'weather_klo_2023_hourly.csv')):
        pytest.skip('canonical data not built')
    return {a: bc.build_cell('hist', a) for a in ('none', 'low', 'high')}


def test_cooled_cell_structure(cells):
    from swiss.pipeline import build_climate_datasets as bc
    sch = json.load(open(os.path.join(cells['high'], 'schema.json')))
    man = json.load(open(os.path.join(cells['high'], 'build_manifest.json')))
    meta = json.load(open(os.path.join(cells['high'], 'build_meta.json')))
    b = sch['buildings']
    assert meta['cooled_buildings'] == ['MFH-large'] and meta['climate_scenario'] == 'hist'
    assert 'cooling_device' in b['Building_6'] and b['Building_6']['inactive_actions'] == ['heating_device']
    assert all('cooling_device' not in b[f'Building_{i}'] and b[f'Building_{i}']['inactive_actions'] == ['cooling_or_heating_device'] for i in range(1, 6))
    assert man['Building_6']['cooled'] and not man['Building_1']['cooled']
    assert b['Building_6']['cooling_device']['attributes'] == b['Building_6']['heating_device']['attributes']        # reversible device assumption
    assert abs(bc.unit_share('low') - 5 / 46) < 1e-12 and abs(bc.unit_share('high') - 24 / 46) < 1e-12 and abs(bc.unit_share('medium') - 14 / 46) < 1e-12
    none = json.load(open(os.path.join(cells['none'], 'schema.json')))
    assert none['actions']['cooling_or_heating_device']['active'] is False                                         # heating-only district: Phase B action layout


def test_cooling_step_in_citylearn_balances(cells):
    """One hot step: cooling demand = action x nominal power x COPc, electricity = action x nominal power, indoor temperature from the RC step with heat -Qc."""
    from citylearn.citylearn import CityLearnEnv
    from swiss.experiments.rewards import SwissDistrictReward
    start = 4872 + 60                                                      # mid July 2023
    env = CityLearnEnv(os.path.join(cells['high'], 'schema.json'), central_agent=True, reward_function=SwissDistrictReward,
                       simulation_start_time_step=start, simulation_end_time_step=start + 6)
    env.reset()
    cols = [(i, nm) for i, x in enumerate(env.buildings) for nm in x.active_actions]
    b = env.buildings[5]
    a = np.zeros(len(cols))
    a[cols.index((5, 'cooling_or_heating_device'))] = -0.5
    t_before = b.dynamics.temperature
    env.step([a.tolist()])
    t_out = float(b.weather.outdoor_dry_bulb_temperature[0])
    ghi = float(b.weather.direct_solar_irradiance[0] + b.weather.diffuse_solar_irradiance[0])
    cop = rcb.cooling_cop(t_out, float(b.cooling_device.efficiency))
    assert t_out > rcb.COOLING_MIN_OUTDOOR_C
    assert np.isclose(float(b.energy_simulation.cooling_demand[0]), 0.5 * b.cooling_device.nominal_power * cop)
    assert np.isclose(float(b.cooling_electricity_consumption[0]), 0.5 * b.cooling_device.nominal_power)
    t_exp = rcb.step_temperature(t_before, t_out, ghi, -float(b.energy_simulation.cooling_demand[0]), float(b.dynamics.area_eff))
    assert np.isclose(b.dynamics.temperature, t_exp)
    assert np.all([float(x.energy_simulation.cooling_demand[0]) == 0.0 for i, x in enumerate(env.buildings) if i != 5])      # heating-only buildings do not cool


# --------------------------------------------------------------------------------------------------------------- climate exact optimum
def test_uncooled_program_equals_oracle_rc(cells):
    """Heating-only cell, 300 steps: the climate program reproduces oracle_rc (small gap from the rounded building areas stored in the dataset)."""
    from swiss.experiments import oracle_climate as oc, oracle_rc as orc
    inp = oc.ClimateInputs(cells['none'])
    base_ref = orc.RCInputs()
    for bi in range(6):
        ref = base_ref.net_s0[bi] - base_ref.derived_heat[bi] / base_ref.heat_tank[bi]['cop']
        assert np.abs(ref[:2000] - inp.base[bi][:2000]).max() < 1e-4
    ref_tot = orc.scenario(base_ref, {}, 'band 21-24', 8.0, n=300)
    tot, _ = oc.solve_cell(inp, 'band', 8.0, 300)
    assert abs(tot['opt_bill_chf'] - ref_tot['opt_bill']) / ref_tot['zero_bill'] < 5e-4
    assert abs(tot['zero_bill_chf'] - ref_tot['zero_bill']) / ref_tot['zero_bill'] < 5e-4


def test_cooled_program_is_consistent_and_never_worse(cells):
    from swiss.experiments import oracle_climate as oc
    inp = oc.ClimateInputs(cells['high'])
    n = 4200                                                               # to the end of June 2023
    tot, sols = oc.solve_cell(inp, 'band', 8.0, n)
    assert tot['saving_chf'] > 0 and tot['cooling_electricity_kwh']['baseline'] > 0
    s = sols[5]
    assert s['T'].max() <= 26.0 + 1e-6 or s['T'].max() <= s['T_th'].max() + 1e-6          # band upper limit (or the thermostat path where that is higher)
    assert np.all(s['Qc'] <= inp.qc_max[5][:n] + 1e-9) and s['Qc'].min() >= -1e-9
    pinned, sp_ = oc.solve_cell(inp, 'pinned', 8.0, n)
    assert pinned['saving_chf'] <= tot['saving_chf'] + 1e-6                # flexibility cannot hurt
    assert np.allclose(sp_[5]['T'], sp_[5]['T_th'], atol=1e-6)


@pytest.mark.skipif(not os.environ.get('RUN_SLOW'), reason='long CityLearn replay; set RUN_SLOW=1')
def test_replay_cooled_cell_hot_weeks(cells):
    from swiss.experiments import oracle_climate as oc
    inp = oc.ClimateInputs(cells['high'])
    r = oc.replay(inp, 'band', 8.0, 5100)                                  # through the July 2023 test week
    assert r['rel_diff_saving_pct'] < 0.5
    assert r['cooling_electricity_kwh_predicted'] > 0
