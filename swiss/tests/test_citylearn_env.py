"""Integration tests for the generated CityLearn dataset (A7). Skip if the dataset or CityLearn data is absent."""
import json
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCHEMA = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'schema.json')
pytestmark = pytest.mark.skipif(not os.path.exists(SCHEMA), reason='dataset not built')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']


def test_dataset_files_shape_and_values():
    d = os.path.dirname(SCHEMA)
    for i in range(1, 7):
        b = pd.read_csv(os.path.join(d, f'Building_{i}.csv'))
        assert len(b) == 8760 and b.notna().all().all()
        assert (b[['non_shiftable_load', 'dhw_demand', 'heating_demand']] >= 0).all().all()
        assert b.hour.between(1, 24).all() and b.day_type.between(1, 7).all()
        assert (b.solar_generation == 0).all() and (b.cooling_demand == 0).all()
    w = pd.read_csv(os.path.join(d, 'weather.csv')); p = pd.read_csv(os.path.join(d, 'pricing.csv'))
    assert len(w) == 8760 == len(p) and w.notna().all().all() and (w.direct_solar_irradiance >= 0).all()
    assert set(p.electricity_pricing.round(4)) == {0.1505, 0.1905}
    # predicted price is the exact future price except the last 3 steps
    assert np.allclose(p.electricity_pricing_predicted_1.iloc[:-1], p.electricity_pricing.iloc[1:])


def test_full_year_episode_runs_and_reproduces_measured_hp_electricity():
    """Zero-action run: simulated HP electricity equals measured (implementation consistency, tautological by design)."""
    from citylearn.citylearn import CityLearnEnv
    env = CityLearnEnv(SCHEMA, central_agent=True)
    assert len(env.buildings) == 6 and env.time_steps == 8760
    env.reset()
    na = len(env.action_names[0])
    while not env.terminated:
        env.step([[0.0] * na])
    thermal = {r: pd.read_csv(os.path.join(ROOT, 'data', 'canonical', 'thermal', f'{r}_2023_thermal_hourly.csv')) for r in ROLES}
    for b, role in zip(env.buildings, ROLES):
        sim = b.heating_device.electricity_consumption.sum() + b.dhw_device.electricity_consumption.sum()
        meas = thermal[role].e_hp_kwh.sum()
        assert abs(sim - meas) / meas < 0.01, (role, sim, meas)
        assert abs(b.non_shiftable_load.sum() - thermal[role].non_shiftable_load_kwh.iloc[:8759].sum()) / thermal[role].non_shiftable_load_kwh.sum() < 0.01


def test_storage_charging_costs_energy_not_creates_it():
    from citylearn.citylearn import CityLearnEnv
    schema = json.load(open(SCHEMA))
    env = CityLearnEnv(SCHEMA, central_agent=True, simulation_end_time_step=719)
    env.reset(); na = len(env.action_names[0])
    while not env.terminated:
        env.step([[0.5] * na])
    charged = sum(b.heating_device.electricity_consumption.sum() + b.dhw_device.electricity_consumption.sum() for b in env.buildings)
    env0 = CityLearnEnv(SCHEMA, central_agent=True, simulation_end_time_step=719)
    env0.reset()
    while not env0.terminated:
        env0.step([[0.0] * na])
    base = sum(b.heating_device.electricity_consumption.sum() + b.dhw_device.electricity_consumption.sum() for b in env0.buildings)
    assert charged >= base * 0.99  # extra charging cannot reduce total HP electricity materially (losses >= 0)
