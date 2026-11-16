"""Tests for the carbon reconstruction (D-013)."""
import importlib.util
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
spec = importlib.util.spec_from_file_location('bc', os.path.join(ROOT, 'swiss', 'pipeline', 'build_carbon.py'))
BC = importlib.util.module_from_spec(spec); spec.loader.exec_module(BC)
CSV = os.path.join(ROOT, 'data', 'canonical', 'carbon_ch_2023_hourly.csv')


def test_intensity_weighted_average_exact():
    idx = pd.date_range('2023-01-01', periods=3, freq='1h', tz='UTC')
    df = pd.DataFrame({'Nuclear': [100.0, 0, 50], 'Fossil gas': [0.0, 100, 50]}, index=idx)
    i, tot, emis = BC.intensity(df, 41.0)
    assert np.allclose(i.to_numpy(), [12.0, 490.0, (50 * 12 + 50 * 490) / 100])
    assert np.allclose(tot.to_numpy(), [100, 100, 100])


def test_pumped_storage_and_non_generation_columns_excluded():
    idx = pd.date_range('2023-01-01', periods=2, freq='1h', tz='UTC')
    df = pd.DataFrame({'Nuclear': [100.0, 100], 'Hydro pumped storage': [500.0, 500], 'Load': [1000.0, 1000],
                       'Cross border electricity trading': [-50.0, -50]}, index=idx)
    i, tot, _ = BC.intensity(df, 41.0)
    assert np.allclose(i, 12.0) and np.allclose(tot, 100.0)


def test_structural_zero_runs_vs_isolated_gaps():
    idx = pd.date_range('2023-01-01', periods=200, freq='1h', tz='UTC')
    s = pd.Series(1.0, index=idx); s.iloc[10:70] = np.nan; s.iloc[100:103] = np.nan
    out = BC.structural_zero(s)
    assert (out.iloc[10:70] == 0).all()        # 60 h run -> structural zero
    assert out.iloc[100:103].isna().all()      # 3 h gap stays missing


def test_emission_factors_are_the_verified_ipcc_medians():
    assert BC.EF_IPCC == {'Nuclear': 12.0, 'Hydro Run-of-River': 24.0, 'Hydro water reservoir': 24.0, 'Biomass': 230.0,
                          'Geothermal': 38.0, 'Wind onshore': 11.0, 'Wind offshore': 12.0, 'Fossil hard coal': 820.0, 'Fossil gas': 490.0}
    assert BC.SOLAR_CH == 41.0 and BC.SOLAR_OTHER == 48.0


@pytest.mark.skipif(not os.path.exists(CSV), reason='carbon series not built')
def test_series_complete_flagged_and_plausible():
    c = pd.read_csv(CSV, index_col=0, parse_dates=True)
    assert len(c) == 8760 and c.index.is_unique
    assert c.carbon_intensity_kg_per_kwh.notna().all() and (c.carbon_intensity_kg_per_kwh > 0).all()
    assert c.gap_interpolated_flag.sum() <= 6
    assert 0.02 < c.carbon_intensity_kg_per_kwh.mean() < 0.2
    assert np.allclose(c.carbon_intensity_kg_per_kwh.to_numpy()[c.gap_interpolated_flag == 0],
                       c.ci_consumption_lifecycle_g_per_kwh[c.gap_interpolated_flag == 0] / 1000)
    # consumption intensity >= domestic when imports are dirtier on average (Swiss domestic mix is hydro+nuclear)
    assert c.ci_consumption_lifecycle_g_per_kwh.mean() > c.ci_domestic_generation_lifecycle_g_per_kwh.mean()
