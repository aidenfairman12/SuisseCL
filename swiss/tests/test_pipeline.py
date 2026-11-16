"""Tests for the Phase A data pipeline (A4). Run: cl/bin/python -m pytest swiss/tests -q

Unit tests need no data. Data tests read data/canonical and data/raw and skip if absent.
"""
import hashlib
import importlib.util
import json
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')
RAW = os.path.join(ROOT, 'data', 'raw')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'swiss', 'pipeline', f'{name}.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = _load('build_buildings_hourly')
need_canonical = pytest.mark.skipif(not os.path.isdir(os.path.join(CAN, 'hourly')), reason='canonical data not built')
need_raw = pytest.mark.skipif(not os.path.isdir(os.path.join(RAW, 'heapo', 'extracted')), reason='raw data not present')


def hourly(role):
    return pd.read_csv(os.path.join(CAN, 'hourly', f'{role}_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)


def quarter(role):
    return pd.read_csv(os.path.join(CAN, 'quarter_hourly', f'{role}_2023_15min.csv'), index_col='timestamp_utc', parse_dates=True)


# ------------------------------------------------------------------ unit tests
def test_hourly_sum_requires_all_four_quarters():
    idx = pd.date_range(P.START, periods=8, freq='15min')
    q = pd.Series([1, 1, 1, 1, 1, np.nan, 1, 1], index=idx, dtype=float)
    # sum over quarters in each hour: first complete -> 4, second has a NaN -> NaN
    full = pd.Series(np.nan, index=P.Q_INDEX); full.loc[idx] = q.values
    s, nmiss = P.hourly_sum(full)
    assert s.iloc[0] == 4.0 and nmiss.iloc[0] == 0
    assert np.isnan(s.iloc[1]) and nmiss.iloc[1] == 1


def test_zero_runs_threshold_and_nan_breaks_run():
    s = pd.Series([0, 0, 0, 1, 0, 0, np.nan, 0, 0, 0], dtype=float)
    assert P.zero_runs(s, 3).tolist() == [True, True, True, False, False, False, False, True, True, True]
    assert not P.zero_runs(s, 4).any()


def test_fill_gap_days_uses_mean_of_neighbour_days_and_only_full_days():
    idx = pd.date_range('2023-01-01', periods=72, freq='1h', tz='UTC')
    s = pd.Series(np.r_[np.full(24, 2.0), np.full(24, np.nan), np.full(24, 4.0)], index=idx)
    out, mask = P.fill_gap_days(s)
    assert (out.iloc[24:48] == 3.0).all() and mask.iloc[24:48].all() and not mask.iloc[:24].any()
    # partially missing day is NOT filled; neighbour incomplete -> NOT filled
    s2 = s.copy(); s2.iloc[30] = 9.0
    out2, mask2 = P.fill_gap_days(s2)
    assert not mask2.any()
    s3 = s.copy(); s3.iloc[0] = np.nan
    assert not P.fill_gap_days(s3)[1].any()


def test_window_is_exactly_one_local_year_8760_hours():
    assert len(P.H_INDEX) == 8760 and len(P.Q_INDEX) == 8760 * 4
    assert P.H_INDEX.is_unique and P.H_INDEX.is_monotonic_increasing
    loc = P.H_INDEX.tz_convert('Europe/Zurich')
    assert loc[0] == pd.Timestamp('2023-01-01 00:00', tz='Europe/Zurich')
    assert loc[-1] == pd.Timestamp('2023-12-31 23:00', tz='Europe/Zurich')


def test_local_fields_dst_transitions():
    f = P.local_fields(P.H_INDEX)
    spring = f[f.local_time.str.startswith('2023-03-26')].local_time.str[-5:].tolist()
    assert '02:00' not in spring and len(spring) == 23          # 02:00 skipped
    autumn = f[f.local_time.str.startswith('2023-10-29')].local_time.str[-5:].tolist()
    assert autumn.count('02:00') == 2 and len(autumn) == 25      # 02:00 repeated
    assert f.dst_active.iloc[0] == 0 and f.dst_active.iloc[-1] == 0
    assert f.dst_active.sum() == 5208                            # 217 days * 24 h


# ------------------------------------------------------------------ data tests
@need_canonical
@pytest.mark.parametrize('role', ROLES)
def test_hourly_index_complete_unique_and_labelled(role):
    h = hourly(role)
    assert len(h) == 8760 and h.index.is_unique and h.index.is_monotonic_increasing
    assert h.index[0] == P.START and h.index[-1] == P.END - pd.Timedelta('1h')
    assert set(h.dst_active.unique()) == {0, 1}


@need_canonical
@pytest.mark.parametrize('role', ROLES)
def test_no_negative_values_in_energy_columns(role):
    h = hourly(role)
    for c in [c for c in h.columns if c.startswith('kwh_')]:
        assert (h[c].dropna() >= 0).all(), c


@need_canonical
@pytest.mark.parametrize('role', ROLES)
def test_hourly_energy_equals_quarter_hour_energy(role):
    """Energy conservation: hourly values equal the sum of their (complete) quarter-hours."""
    h, q = hourly(role), quarter(role)
    col = 'kwh_hp'
    hh = q[col].groupby(q.index.floor('1h')).sum(min_count=4).reindex(h.index)
    pd.testing.assert_series_equal(h[col], hh, check_names=False, check_freq=False, rtol=1e-9, atol=1e-9)
    assert abs(h[col].sum() - q[col].sum()) < 1e-6 or h[col].isna().any()


@need_canonical
@pytest.mark.parametrize('role', ['SFH-low', 'SFH-mid', 'SFH-high'])
def test_heapo_total_is_hp_plus_other_no_double_counting(role):
    h = hourly(role).dropna(subset=['kwh_total'])
    assert np.allclose(h.kwh_total, h.kwh_hp + h.kwh_other, atol=1e-9)


@need_canonical
@pytest.mark.parametrize('role', ['SFH-low', 'SFH-mid', 'SFH-high'])
def test_gap_fill_only_the_dst_day_and_flagged(role):
    h = hourly(role)
    flagged = h[h.gap_filled_flag == 1]
    assert len(flagged) == 24 and set(flagged.index.strftime('%Y-%m-%d')) == {'2023-10-29'}
    assert h.kwh_total_f.notna().all()
    # raw columns untouched (still NaN), measured hours identical to raw
    assert h.loc[flagged.index, 'kwh_total'].isna().all()
    ok = h.gap_filled_flag == 0
    assert np.allclose(h.loc[ok, 'kwh_total_f'], h.loc[ok, 'kwh_total'], equal_nan=False)
    # UTC day 29 filled with mean of UTC days 28 and 30
    d28 = h[h.index.strftime('%Y-%m-%d') == '2023-10-28'].kwh_hp.to_numpy()
    d30 = h[h.index.strftime('%Y-%m-%d') == '2023-10-30'].kwh_hp.to_numpy()
    assert np.allclose(h.loc[flagged.index, 'kwh_hp_f'], (d28 + d30) / 2)


@need_canonical
def test_known_annual_totals_regression():
    """Pinned values (measured data; changes mean the pipeline or source changed)."""
    exp = {'SFH-low': 4720.8, 'SFH-mid': 6037.9, 'SFH-high': 11493.2, 'MFH-small': 12715.2,
           'MFH-medium': 25716.0, 'MFH-large': 21103.0}
    for role, v in exp.items():
        assert abs(hourly(role).kwh_hp.sum() - v) < 0.2, role


@need_canonical
def test_mfh_composites_use_distinct_apartment_meters_and_correct_count():
    qc = json.load(open(os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_2023_buildings.json')))
    seen = []
    for role in ['MFH-small', 'MFH-medium', 'MFH-large']:
        ids = qc[role]['apartment_composite_meter_ids']
        assert len(ids) == qc[role]['housing_units'] == len(set(ids))
        seen += ids
        assert hourly(role).n_apartments_in_composite.iloc[0] == len(ids)
        assert 'SYNTHETIC' in qc[role]['apartment_composite_note']
    assert len(seen) == len(set(seen))  # no meter reused across buildings


@need_canonical
def test_weather_relabel_end_to_start_and_values():
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    assert len(w) == 8760 and w.index.is_unique
    raw = os.path.join(RAW, 'meteoswiss', 'ogd-smn_klo_h_historical_2020-2029.csv')
    if not os.path.exists(raw):
        pytest.skip('raw MeteoSwiss file absent')
    r = pd.read_csv(raw, sep=';', usecols=['reference_timestamp', 'tre200h0', 'gre000h0'])
    r['end'] = pd.to_datetime(r.reference_timestamp, format='%d.%m.%Y %H:%M').dt.tz_localize('UTC')
    r = r.set_index('end')
    for t in [pd.Timestamp('2023-07-15 10:00', tz='UTC'), pd.Timestamp('2023-01-01 00:00', tz='UTC'), pd.Timestamp('2023-12-31 22:00', tz='UTC')]:
        assert w.loc[t, 'temp_c'] == r.loc[t + pd.Timedelta('1h'), 'tre200h0']
        assert w.loc[t, 'ghi_wm2'] == r.loc[t + pd.Timedelta('1h'), 'gre000h0']
    assert (w.ghi_wm2.dropna() >= 0).all()
    assert w.temp_c.between(-30, 45).all() and w.rh_pct.between(0, 100).all()
    # derived column consistency
    assert np.allclose(w.beam_horizontal_wm2.dropna(), (w.ghi_wm2 - w.diffuse_wm2).dropna())


@need_canonical
def test_manifest_hashes_match_files():
    man = os.path.join(CAN, 'MANIFEST.sha256')
    for line in open(man):
        digest, rel = line.strip().split('  ', 1)
        with open(os.path.join(CAN, rel), 'rb') as f:
            assert hashlib.sha256(f.read()).hexdigest() == digest, rel


@need_raw
def test_raw_source_checksums_match_registry():
    expect = {os.path.join('heapo', 'heapo_data.zip'): '2b92b0d52487e1a733c35ee59860450d',
              os.path.join('ekz', 'dataset.zip'): 'dd40d5e24aee2a3563bc36285b463dbd'}
    for rel, md5 in expect.items():
        path = os.path.join(RAW, rel)
        if not os.path.exists(path):
            pytest.skip(f'{rel} missing')
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        assert h.hexdigest() == md5


@need_canonical
def test_tariff_structure_matches_documented_two_tier_schedule():
    """EKZ standard tariff 2023: high price 07:00-20:00 local on weekdays, else low (paper Sec 2.4)."""
    t = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    assert len(t) == 8760 and t.index.is_unique and t.total_rp_kwh.notna().all()
    loc = t.index.tz_convert('Europe/Zurich')
    window = (loc.dayofweek < 5) & (loc.hour >= 7) & (loc.hour < 20)
    assert ((t.tier == 'high').to_numpy() == window).all()
    assert set(t.total_rp_kwh.round(2)) == {15.05, 19.05}
    assert np.allclose(t.total_rp_kwh, t.energy_rp_kwh + t.grid_rp_kwh)
    assert np.allclose(t.total_chf_kwh * 100, t.total_rp_kwh)
