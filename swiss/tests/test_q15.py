"""B2 15-minute pipeline: hourly series are exact aggregates of the 15-minute ones, DST behaviour, dataset at 900 s, environment agreement with hourly."""
import json
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')
Q = os.path.join(CAN, 'q15')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
pytestmark = pytest.mark.skipif(not os.path.isdir(Q), reason='15-minute data not built (swiss/pipeline/build_15min.py)')


@pytest.mark.parametrize('role', ROLES)
def test_hourly_series_are_exact_aggregates(role):
    q = pd.read_csv(os.path.join(Q, 'thermal', f'{role}_2023_thermal_15min.csv'), index_col='timestamp_utc', parse_dates=True)
    h = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    assert len(q) == 35040 and q.index[0] == pd.Timestamp('2022-12-31 23:00', tz='UTC') and q.index[-1] == pd.Timestamp('2023-12-31 22:45', tz='UTC')
    agg = q[['e_hp_kwh', 'heating_demand_kwh', 'dhw_demand_kwh', 'non_shiftable_load_kwh']].groupby(q.index.floor('1h')).sum(min_count=4)
    for c in agg.columns:
        np.testing.assert_allclose(agg[c].to_numpy(), h[c].to_numpy(), rtol=1e-9, atol=1e-9, err_msg=c)
    assert q.isna().sum().sum() == 0
    # electricity-heat relation: heat = HP electricity x COP, quarter by quarter (double-counting and units check)
    np.testing.assert_allclose(q.heating_demand_kwh, q.e_hp_space_heating_kwh * q.cop_space_heating, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(q.e_hp_kwh, q.e_hp_baseline_kwh + q.e_hp_space_heating_kwh, atol=1e-12)
    assert (q.e_hp_space_heating_kwh >= -1e-12).all() and (q.e_hp_baseline_kwh >= -1e-12).all()


def test_weather_hourly_means_preserved_and_pv_consistent():
    w = pd.read_csv(os.path.join(Q, 'weather_klo_2023_15min.csv'), index_col='timestamp_utc', parse_dates=True)
    wh = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    np.testing.assert_allclose(w.ghi_wm2.groupby(w.index.floor('1h')).mean().to_numpy(), wh.ghi_wm2.fillna(0).to_numpy(), atol=1e-9)
    assert (w.temp_c.groupby(w.index.floor('1h')).nunique() == 1).all()                      # temperature constant inside the hour
    pv = pd.read_csv(os.path.join(Q, 'pv_ac_w_per_kwp_2023_15min.csv'))
    assert (pv.pv_ac_w_per_kwp >= 0).all() and len(pv) == 35040
    annual = pv.pv_ac_w_per_kwp.sum() / 4000.0
    meta = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))
    assert annual == pytest.approx(meta['annual_specific_yield_kwh_per_kwp'], rel=0.01)


def test_tariff_native_15min_and_dst_local_time():
    t = pd.read_csv(os.path.join(Q, 'tariff_ekz_standard_2023_15min.csv'), index_col='timestamp_utc', parse_dates=True)
    th = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    np.testing.assert_allclose(t.total_chf_kwh.groupby(t.index.floor('1h')).mean().to_numpy(), th.total_chf_kwh.to_numpy(), atol=1e-12)
    loc = t.index.tz_convert('Europe/Zurich')
    spring = loc[(loc.month == 3) & (loc.day == 26)]; autumn = loc[(loc.month == 10) & (loc.day == 29)]
    assert len(spring) == 92 and len(autumn) == 100                                           # DST days have 23 and 25 hours, UTC index has no gap or duplicate
    assert t.index.is_unique and t.index.is_monotonic_increasing


def test_dataset_at_900_seconds_and_environment_agrees_with_hourly():
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    from citylearn.citylearn import CityLearnEnv
    ds = os.path.join(ROOT, 'swiss', 'datasets')
    if not os.path.isdir(os.path.join(ds, 'swiss_district_2023_q15')):
        pytest.skip('q15 datasets not built')
    schema = json.load(open(os.path.join(ds, 'swiss_district_2023_q15', 'schema.json')))
    assert schema['seconds_per_time_step'] == 900.0 and schema['simulation_end_time_step'] == 35039
    imps = {}
    for name, n in (('swiss_district_2023', 1000), ('swiss_district_2023_q15', 4000)):
        env = CityLearnEnv(os.path.join(ds, name, 'schema.json'), central_agent=True)
        ag = ZeroActionBaselineAgent(env); obs, _ = env.reset()
        for _ in range(n):
            obs, *_ = env.step(ag.predict(obs))
        imps[name] = sum(float(np.maximum(np.asarray(b.net_electricity_consumption, dtype=float)[:n], 0).sum()) for b in env.buildings)
    assert imps['swiss_district_2023_q15'] == pytest.approx(imps['swiss_district_2023'], rel=2e-3)
