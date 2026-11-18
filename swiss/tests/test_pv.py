"""B3 PV model: physical sanity, capacity rule, and the CityLearn 3.3.0 sign/unit convention (verified on the source and by rollout)."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from swiss.models.pv import capacity_kwp, rooftop_cap_kwp, specific_yield_kwh_per_kwp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')


def _weather():
    return pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), parse_dates=['timestamp_utc'])


def test_pvlib_version_pinned():
    import pvlib
    assert pvlib.__version__ == '0.16.1'


def test_zero_at_night_and_no_negative_and_bounds():
    w = _weather()
    y = specific_yield_kwh_per_kwp(w.timestamp_utc, w.ghi_wm2, w.diffuse_wm2, w.temp_c)
    assert (y >= 0).all() and y.max() <= 1.0 / 1.2 * 0.97   # inverter clips at 1/1.2 of the nameplate times efficiency
    assert (y[(w.ghi_wm2 == 0).to_numpy()] == 0).all()
    local = pd.DatetimeIndex(w.timestamp_utc).tz_convert('Europe/Zurich')
    assert y[np.asarray(local.hour == 0)].sum() == 0.0     # midnight


def test_annual_specific_yield_in_documented_range():
    meta = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))
    assert meta['in_plausible_range'] and 900 <= meta['annual_specific_yield_kwh_per_kwp'] <= 1250
    w = _weather()
    y = specific_yield_kwh_per_kwp(w.timestamp_utc, w.ghi_wm2, w.diffuse_wm2, w.temp_c)
    assert y.sum() == pytest.approx(meta['annual_specific_yield_kwh_per_kwp'], abs=0.1)
    csv = pd.read_csv(os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv'))
    assert len(csv) == 8760 and csv.pv_ac_w_per_kwp.sum() / 1000 == pytest.approx(y.sum(), abs=0.5)


def test_diffuse_only_sky_gives_positive_yield_and_more_beam_gives_more():
    ts = pd.DatetimeIndex(['2023-06-21 10:00'])
    lo = specific_yield_kwh_per_kwp(ts, [400.0], [400.0], [20.0])[0]
    hi = specific_yield_kwh_per_kwp(ts, [800.0], [100.0], [20.0])[0]
    assert 0 < lo < hi


def test_capacity_rule_and_cap():
    assert capacity_kwp(10000, 1000, 1.0, 100) == (10.0, False)
    assert capacity_kwp(10000, 1000, 1.5, 12) == (12.0, True)
    assert rooftop_cap_kwp(260, multi_family=False) == pytest.approx(260 / 2 * 0.5 * 0.2)
    meta = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))
    for role, b in meta['buildings'].items():
        for r, v in b['ratios'].items():
            assert v['kwp'] <= b['rooftop_cap_kwp'] + 1e-9
            if not v['cap_binding']:
                assert v['yield_to_demand_actual'] == pytest.approx(float(r), abs=0.01)


def test_citylearn_sign_and_units():
    """CityLearn 3.3.0: schema value in W/kW, building.solar_generation negative kWh/step, net = net_without_pv + solar_generation."""
    from citylearn.agents.baseline import ZeroActionBaselineAgent
    from citylearn.citylearn import CityLearnEnv
    ds = os.path.join(ROOT, 'swiss', 'datasets')
    if not os.path.isdir(os.path.join(ds, 'swiss_pv_2023')):
        pytest.skip('swiss_pv_2023 not built (build_dataset.py --pv-ratio 1.0 --out-name swiss_pv_2023)')
    envs = {}
    for nm in ('swiss_district_2023', 'swiss_pv_2023'):
        env = CityLearnEnv(os.path.join(ds, nm, 'schema.json'), central_agent=True)
        ag = ZeroActionBaselineAgent(env); obs, _ = env.reset()
        for _ in range(300):
            obs, *_ = env.step(ag.predict(obs))
        envs[nm] = env
    meta = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))
    pvcsv = pd.read_csv(os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv')).pv_ac_w_per_kwp.to_numpy()[:300]
    roles = list(meta['buildings'])
    for i, role in enumerate(roles):
        a, b = envs['swiss_district_2023'].buildings[i], envs['swiss_pv_2023'].buildings[i]
        sg = np.asarray(b.solar_generation)[:300]
        kwp = meta['buildings'][role]['ratios']['1.0']['kwp']
        assert (sg <= 1e-9).all()
        np.testing.assert_allclose(-sg, kwp * pvcsv / 1000.0, rtol=1e-3, atol=1e-5)
        diff = np.asarray(b.net_electricity_consumption)[:300] - np.asarray(a.net_electricity_consumption)[:300]
        np.testing.assert_allclose(diff, sg, atol=1e-4)
