"""Phase C WP1: climate scenarios for Kloten (swiss/pipeline/build_climate.py). Construction tests run on small synthetic inputs or on the 2023 weather;
tests of the written files need `cl/bin/python -I swiss/pipeline/build_climate.py` to have run (they skip with that message otherwise); tests that read the
CH2025 files need data/raw/ch2025_klo/ (git-ignored)."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from swiss.experiments import rl
from swiss.pipeline import build_climate as bc
from swiss.pipeline.build_pv import pv_ac_w_per_kwp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')
OUT = os.path.join(CAN, 'climate')
SCEN = ['gwl1.5', 'gwl2.0', 'gwl3.0', 'hist_hw', 'gwl2.0_hw', 'gwl3.0_hw', 'hist_hw99', 'gwl2.0_hw99', 'gwl3.0_hw99']
needs_raw = pytest.mark.skipif(not os.path.isdir(bc.RAW), reason='data/raw/ch2025_klo not present (git-ignored download)')
needs_out = pytest.mark.skipif(not os.path.exists(os.path.join(OUT, 'heatwave_spells.json')), reason='run cl/bin/python -I swiss/pipeline/build_climate.py first')


@pytest.fixture(scope='module')
def w0():
    return bc.load_2023()


@pytest.fixture(scope='module')
def cs(w0):
    return bc.clearsky_hourly(w0.timestamp_utc)


def _read(name):
    return pd.read_csv(os.path.join(OUT, f'weather_klo_{name}_hourly.csv'), parse_dates=['timestamp_utc'])


# ------------------------------------------------------------------------------------------------ construction (no data files needed beyond 2023)
def test_week29_rows_equal_the_rl_window():
    assert bc.WEEK29 == rl.window(29)


def test_zero_delta_identity(w0, cs):
    d = {'tas': np.zeros(12), 'tasmin': np.zeros(12), 'tasmax': np.zeros(12), 'rsds': np.ones(12), 'hurs': np.ones(12)}
    out, capped = bc.apply_deltas(w0, d, cs)
    for c in ('temp_c', 'rh_pct', 'ghi_wm2', 'diffuse_wm2', 'beam_horizontal_wm2'):
        np.testing.assert_allclose(out[c].to_numpy(float), w0[c].to_numpy(float), atol=0.051, equal_nan=True, err_msg=c)
    assert capped == 0


def test_additive_delta_gives_the_monthly_mean_warming(w0, cs):
    dtas = np.linspace(1.0, 2.2, 12)
    d = {'tas': dtas, 'tasmin': dtas + 0.3, 'tasmax': dtas + 0.9, 'rsds': np.ones(12), 'hurs': np.ones(12)}
    out, _ = bc.apply_deltas(w0, d, cs)
    month = bc.local_index(w0).month
    got = (out.temp_c - w0.temp_c).groupby(month).mean().to_numpy()
    np.testing.assert_allclose(got, dtas, atol=2e-3)       # temperatures are rounded to 0.01 K


def test_radiation_and_humidity_bounds_after_scaling(w0, cs):
    d = {'tas': np.ones(12), 'tasmin': np.ones(12), 'tasmax': np.ones(12), 'rsds': np.full(12, 1.2), 'hurs': np.full(12, 1.3)}
    out, capped = bc.apply_deltas(w0, d, cs)
    assert out.rh_pct.max() <= 100.0 and out.rh_pct.min() >= 0.0
    cap = np.maximum(cs, w0.ghi_wm2.to_numpy(float))
    assert (out.ghi_wm2.to_numpy() <= cap + 0.06).all()
    assert capped > 0                                  # a 20 % increase must hit the cap on clear hours
    tot = out.beam_horizontal_wm2.to_numpy(float) + out.diffuse_wm2.to_numpy(float)
    ok = ~np.isnan(tot)                                  # the 2023 file has one missing diffuse and beam value
    np.testing.assert_allclose(tot[ok], out.ghi_wm2.to_numpy(float)[ok], atol=0.2)


def test_day_temperature_matches_minimum_maximum_and_mean():
    shape = np.sin((np.arange(24) - 9) / 24.0 * np.pi * 2 * 0.5) ** 2
    shape = (shape - shape.min()) / (shape.max() - shape.min())
    for tmin, tmax, tas in ((12.0, 31.0, 21.5), (15.0, 36.0, 26.0), (18.0, 27.0, 22.0)):
        T = bc.day_temperature(tmin, tmax, tas, shape, np.arange(24))
        assert abs(T.min() - tmin) < 1e-3 and abs(T.max() - tmax) < 1e-3 and abs(T.mean() - tas) < 0.02


def test_day_humidity_matches_daily_mean_and_bounds():
    T = 18 + 8 * np.sin(np.arange(24) / 24 * 2 * np.pi - 2)
    rh = bc.day_humidity(T, 60.0)
    assert abs(rh.mean() - 60.0) < 0.1 and rh.max() <= 100.0 and rh.min() >= 0.0


def test_reconstruction_validation_of_2023(w0):
    shape, n_hot = bc.hot_day_shape(w0)
    assert shape.min() == 0.0 and shape.max() == 1.0 and n_hot >= 20
    r = bc.reconstruction_validation(w0, shape)
    # reported in the validation report; thresholds are loose guards, not claims
    assert r['rmse_all_days_K'] < 2.0 and r['rmse_hot_days_K'] < 1.8 and r['n_days_all'] > 300
    assert all(abs(v) < 0.5 for v in r['monthly_bias_K'].values())


# ------------------------------------------------------------------------------------------------ CH2025 reading and selection
@needs_raw
def test_read_ch2025_shape_and_missing_values():
    for var in bc.VARS:
        Y, chains = bc.read_ch2025(var, 'gwl2.0')
        assert Y.shape == (30, 365, len(chains)) and len(chains) >= 20
        assert np.isnan(Y).sum() > 0 and np.nanmin(Y) > -60
    Y, _ = bc.read_ch2025('hurs', 'ref91-20')
    assert np.nanmin(Y) >= 0 and np.nanmax(Y) <= 110.0           # CH2025 hurs exceeds 100 % in places (model output, max 106.1 in the reference file): capped at 100 when used


@needs_raw
def test_ensemble_statistics_and_delta_signs():
    ref, g2, g3 = (bc.ensemble(lv) for lv in (bc.REF, 'gwl2.0', 'gwl3.0'))
    d2, d3 = bc.monthly_deltas(g2, ref), bc.monthly_deltas(g3, ref)
    assert (d2['tas'] > 0).all() and (d3['tas'] > d2['tas']).all()                      # more warming at the higher level, every month
    assert d3['tas'].mean() > 2.0 and d2['tas'].mean() > 1.0
    assert (d3['tasmax'] >= d3['tasmin'] - 0.5).all()
    assert 0.8 < d3['rsds'].min() and d3['rsds'].max() < 1.2 and 0.85 < d3['hurs'].min()


@needs_raw
def test_spell_selection_is_deterministic_and_inside_summer():
    ens = bc.ensemble('gwl2.0')
    a, b = bc.select_spell(ens, 95.0), bc.select_spell(ens, 95.0)
    assert a == b
    assert bc.SUMMER_START <= a['start_day_index'] <= bc.SUMMER_LAST_START
    assert abs(a['severity_mean_tasmax'] - a['target_severity']) < 0.1
    d = a['daily']
    assert all(len(v) == 7 and not np.isnan(v).any() for v in d.values())
    assert all(d['tasmin'][i] < d['tas'][i] < d['tasmax'][i] for i in range(7))
    assert bc.select_spell(ens, 99.0)['severity_mean_tasmax'] > a['severity_mean_tasmax']


# ------------------------------------------------------------------------------------------------ written files
@needs_out
@pytest.mark.parametrize('name', SCEN)
def test_files_columns_length_and_ranges(name, w0):
    w = _read(name)
    assert list(w.columns) == list(w0.columns) and len(w) == len(w0) == 8760
    assert (w.timestamp_utc == w0.timestamp_utc).all()
    assert w.rh_pct.between(0, 100).all() and w.temp_c.between(-30, 50).all()
    assert w.ghi_wm2.min() >= 0 and w.diffuse_wm2.dropna().min() >= -1e-9
    pv = pd.read_csv(os.path.join(OUT, f'pv_ac_w_per_kwp_{name}_hourly.csv'), parse_dates=['timestamp_utc'])
    assert list(pv.columns) == ['timestamp_utc', 'pv_ac_w_per_kwp'] and len(pv) == 8760 and (pv.timestamp_utc == w0.timestamp_utc).all()
    assert pv.pv_ac_w_per_kwp.min() >= 0 and 900 < pv.pv_ac_w_per_kwp.sum() / 1000.0 < 1300       # kWh per kWp, plausibility only


@needs_out
@pytest.mark.parametrize('name', ['gwl1.5', 'gwl2.0', 'gwl3.0'])
def test_typical_year_warms_and_stays_below_clear_sky(name, w0, cs):
    w = _read(name)
    assert w.temp_c.mean() - w0.temp_c.mean() > 0.4
    month = bc.local_index(w0).month
    d = (w.temp_c - w0.temp_c).groupby(month).mean()
    assert (d > 0).all()
    cap = np.maximum(cs, w0.ghi_wm2.to_numpy(float))
    assert (w.ghi_wm2.to_numpy() <= cap + 0.06).all()
    assert w.rh_pct.max() <= 100.0


@needs_out
@pytest.mark.parametrize('name,base', [('hist_hw', None), ('gwl2.0_hw', 'gwl2.0'), ('gwl3.0_hw', 'gwl3.0'), ('hist_hw99', None), ('gwl2.0_hw99', 'gwl2.0'), ('gwl3.0_hw99', 'gwl3.0')])
def test_heat_wave_replaces_exactly_week_29(name, base, w0, cs):
    w = _read(name)
    b = w0 if base is None else _read(base)
    a, e = bc.WEEK29
    outside = np.ones(len(w), dtype=bool)
    outside[a:e + 1] = False
    for c in ('temp_c', 'rh_pct', 'ghi_wm2', 'diffuse_wm2', 'beam_horizontal_wm2'):
        np.testing.assert_allclose(w[c].to_numpy(float)[outside], b[c].to_numpy(float)[outside], atol=0.051, equal_nan=True, err_msg=c)
    inside = slice(a + bc.RAMP, e + 1 - bc.RAMP)
    assert np.abs(w.temp_c.to_numpy()[inside] - b.temp_c.to_numpy()[inside]).max() > 1.0        # the week is not the base week
    assert w.temp_c.iloc[a:e + 1].max() > b.temp_c.iloc[a:e + 1].max() or name.startswith('hist')
    ghi = w.ghi_wm2.to_numpy()[a:e + 1]
    assert (ghi <= 1.15 * cs[a:e + 1] + 1e-6).all()                       # not above clear sky (kmax is the 99.9th percentile of the 2023 ratio, about 1.05 to 1.1)


@needs_out
@pytest.mark.parametrize('key,name', [('hist', 'hist_hw'), ('gwl2.0', 'gwl2.0_hw'), ('gwl3.0', 'gwl3.0_hw'), ('gwl3.099', 'gwl3.0_hw99')])
def test_inserted_spell_matches_daily_values(key, name):
    sp = json.load(open(os.path.join(OUT, 'heatwave_spells.json')))[key]
    w = _read(name)
    a, _ = bc.WEEK29
    for i in range(1, 6):                                                   # interior days (the first and last day carry the blending ramps)
        blk = w.iloc[a + 24 * i: a + 24 * i + 24]
        d = sp['daily']
        assert abs(blk.temp_c.min() - d['tasmin'][i]) < 0.15 and abs(blk.temp_c.max() - d['tasmax'][i]) < 0.15 and abs(blk.temp_c.mean() - d['tas'][i]) < 0.15
        assert abs(blk.rh_pct.mean() - d['hurs'][i]) < 1.0
        assert abs(blk.ghi_wm2.mean() - d['rsds'][i]) < 1.0 or sp['daily']['rsds'][i] * 24 > blk.ghi_wm2.sum()


@needs_out
def test_spell_severity_orders_with_warming():
    s = json.load(open(os.path.join(OUT, 'heatwave_spells.json')))
    assert s['hist']['severity_mean_tasmax'] < s['gwl2.0']['severity_mean_tasmax'] < s['gwl3.0']['severity_mean_tasmax']
    assert s['hist99']['severity_mean_tasmax'] > s['hist']['severity_mean_tasmax']
    assert s['inserted_rows'] == list(rl.window(29))


@needs_out
def test_2023_pv_is_reproduced_exactly_by_the_refactored_function(w0):
    pv_df, _ = pv_ac_w_per_kwp(w0)
    ref = pd.read_csv(os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    assert (pv_df.timestamp_utc.to_numpy() == ref.timestamp_utc.to_numpy()).all()
    np.testing.assert_array_equal(pv_df.pv_ac_w_per_kwp.to_numpy(), ref.pv_ac_w_per_kwp.to_numpy())
