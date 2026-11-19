"""Task B2: 15-minute data pipeline for the Swiss district (2023 local year, UTC window [2022-12-31 23:00, 2023-12-31 23:00), 35,040 quarter-hours).

Everything at 15 minutes is derived from the ORIGINAL 15-minute smart-meter data wherever it exists, with the same rules as the hourly pipeline so that the
hourly series are exact aggregates of the 15-minute series (checked in qc_15min_2023.json and swiss/tests/test_q15.py):
  electricity   SFH (HEAPO): HP and other load as measured, the 24 h gap of 2023-10-29 filled from day-1 and day+1 at quarter-hour resolution (D-011, synthetic);
                MFH (EKZ): HP meter and measured common-area meters as measured, apartment composite = units x mean of the SAME seeded meters (qc_2023_buildings.json)
                at quarter-hour resolution (D-015, synthetic)
  weather       MeteoSwiss KLO is HOURLY only: temperature is held constant within the hour; global and diffuse irradiance are redistributed inside the hour with the
                shape of a Haurwitz clear-sky curve, normalised so that each hourly mean is preserved exactly (assumption A-022; no real 15-minute weather exists)
  tariff        EKZ standard tariff at its native 15-minute resolution
  carbon        modeled hourly carbon intensity held constant within the hour
  PV            same pvlib chain as hourly (M-003) with 15-minute sun positions and the redistributed irradiance
  thermal       M-001 with the hourly calibration (eta, supply temperatures from thermal_params.json) applied to quarter-hour HP electricity. A first version split the
                baseline with a quarter-hour profile; it changed the space-heating / hot-water split by up to 26 % because the split rule (minimum of electricity and a
                baseline profile) is not linear. Final rule (A-023): the hourly baseline of M-001 is distributed over the four quarters in proportion to the quarter's HP
                electricity, so every 15-minute thermal series aggregates EXACTLY to the hourly one. All thermal quantities are DERIVED.
Outputs: data/canonical/q15/ (see below) and docs/data/data_quality_reports/qc_15min_2023.json
Run: cl/bin/python -I swiss/pipeline/build_15min.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from pvlib import irradiance, location  # noqa: E402

from swiss.models.heat_pump import cop  # noqa: E402
from swiss.models.pv import specific_yield_kwh_per_kwp, PARAMS  # noqa: E402
from swiss.pipeline.build_buildings_hourly import Q_INDEX, read_q  # noqa: E402

CAN = os.path.join(ROOT, 'data', 'canonical')
RAW = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(CAN, 'q15')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
SLOTS = 96


def fill_gap_days_q(series):
    """Quarter-hour version of the D-011 rule: a fully missing UTC day is replaced by the mean of day-1 and day+1 (both complete)."""
    out = series.copy(); mask = pd.Series(False, index=series.index)
    days = series.index.floor('1D')
    for day in pd.unique(days):
        sl = days == day
        if series[sl].isna().all():
            prev = series[days == day - pd.Timedelta(days=1)]; nxt = series[days == day + pd.Timedelta(days=1)]
            if len(prev) == SLOTS and len(nxt) == SLOTS and prev.notna().all() and nxt.notna().all():
                out[sl] = (prev.to_numpy() + nxt.to_numpy()) / 2; mask[sl] = True
    return out, mask


def split_baseline_q(e, temp_c, warm=16.0):
    """M-001 baseline split at 15 minutes: daily baseline B (mean daily energy on complete warm days), profile by local quarter-hour of day."""
    days = e.index.tz_convert('Europe/Zurich').floor('1D')
    tmean = pd.Series(np.asarray(temp_c, float), index=e.index).groupby(days).transform('mean')
    full = e.groupby(days).transform(lambda x: x.notna().all()).to_numpy().astype(bool)
    ok = (tmean >= warm).to_numpy() & full
    B = float(e[ok].groupby(days[ok]).sum().mean())
    loc = e.index.tz_convert('Europe/Zurich')
    slot = loc.hour * 4 + loc.minute // 15
    prof = e[ok].groupby(slot[ok]).mean()
    prof = prof / prof.sum()
    base = np.minimum(e.to_numpy(), B * prof.reindex(slot).to_numpy())
    base = pd.Series(base, index=e.index)
    return base, e - base, B


def build_weather():
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    idx15 = Q_INDEX
    w15 = w.reindex(idx15, method='ffill')[['temp_c', 'rh_pct']]
    loc = location.Location(PARAMS['latitude_deg'], PARAMS['longitude_deg'], altitude=PARAMS['altitude_m'])
    mid = idx15 + pd.Timedelta(minutes=7.5)
    cs = loc.get_clearsky(mid, model='haurwitz')['ghi'].to_numpy()
    cs = pd.Series(cs, index=idx15)
    hour = idx15.floor('1h')
    mean_h = cs.groupby(hour).transform('mean')
    factor = np.where(mean_h > 1e-6, cs / mean_h.replace(0, np.nan), 1.0)
    factor = pd.Series(factor, index=idx15).fillna(1.0)
    for c, name in (('ghi_wm2', 'ghi_wm2'), ('diffuse_wm2', 'diffuse_wm2'), ('beam_horizontal_wm2', 'beam_horizontal_wm2')):
        base = w[c].fillna(0.0).reindex(idx15, method='ffill')
        w15[name] = base.to_numpy() * factor.to_numpy()
    # exact preservation of the hourly means (the factor mean is 1 inside every hour with sun; for hours without a clear-sky signal the value is repeated)
    err = (w15.ghi_wm2.groupby(hour).mean() - w.ghi_wm2.fillna(0.0)).abs().max()
    w15.to_csv(os.path.join(OUT, 'weather_klo_2023_15min.csv'), index_label='timestamp_utc')
    return w15, float(err)


def build_pv(w15):
    y = specific_yield_kwh_per_kwp(w15.index, w15.ghi_wm2, w15.diffuse_wm2, w15.temp_c, step_minutes=15)   # kW per kWp
    pd.DataFrame({'timestamp_utc': w15.index, 'pv_ac_w_per_kwp': np.round(y * 1000.0, 4)}).to_csv(os.path.join(OUT, 'pv_ac_w_per_kwp_2023_15min.csv'), index=False)
    return y


def build_tariff():
    t = pd.read_csv(os.path.join(RAW, 'ekz', 'extracted', 'tariff_data.csv'), sep=';', usecols=['timestamp_utc', 'energy_standard', 'grid_standard'])
    t['timestamp_utc'] = pd.to_datetime(t['timestamp_utc'], utc=True)
    t = t.drop_duplicates('timestamp_utc').set_index('timestamp_utc').reindex(Q_INDEX)
    t['total_chf_kwh'] = (t.energy_standard + t.grid_standard) / 100.0
    t.to_csv(os.path.join(OUT, 'tariff_ekz_standard_2023_15min.csv'), index_label='timestamp_utc')
    return t


def build_building(role, w15, params, qc):
    kind = role[:3]
    sel = json.load(open(os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_2023_buildings.json')))[role]
    if kind == 'SFH':
        q = pd.read_csv(os.path.join(CAN, 'quarter_hourly', f'{role}_2023_15min.csv'), index_col='timestamp_utc', parse_dates=True)
        hp, m1 = fill_gap_days_q(q['kwh_hp']); other, m2 = fill_gap_days_q(q['kwh_other'])
        nonshift = other; flag = (m1 | m2).astype(int)
    else:
        base = os.path.join(RAW, 'ekz', 'extracted', 'smart_meter_data')
        hp = read_q(os.path.join(base, f"{sel['id']}.csv"), 'timestamp_utc', ['kWh_to_installation'], sep=';')[0]['kWh_to_installation']
        commons = [read_q(os.path.join(base, f"{m['0_meter_id']}.csv"), 'timestamp_utc', ['kWh_to_installation'], sep=';')[0]['kWh_to_installation']
                   for m in sel['other_meters_in_object'] if m['0_installation_type'] == 'Common areas']
        common = pd.concat(commons, axis=1).sum(axis=1, min_count=len(commons)) if commons else pd.Series(0.0, index=Q_INDEX)
        units = sel['housing_units']
        apt = pd.concat([read_q(os.path.join(base, f'{m}.csv'), 'timestamp_utc', ['kWh_to_installation'], sep=';')[0]['kWh_to_installation'].rename(m)
                         for m in sel['apartment_composite_meter_ids']], axis=1)
        comp = (apt.mean(axis=1) * units).where(apt.notna().sum(axis=1) >= int(np.ceil(0.8 * units)))
        nonshift = common + comp; flag = pd.Series(0, index=Q_INDEX)
    t = w15.temp_c
    hh = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    hour = Q_INDEX.floor('1h')
    e_h = hp.groupby(hour).transform('sum')
    share = (hp / e_h).where(e_h > 0, 0.25)
    base_e = hh.e_hp_baseline_kwh.reindex(hour).to_numpy() * share.to_numpy()
    base_e = pd.Series(base_e, index=Q_INDEX); sh = hp - base_e; B = float('nan')
    if kind == 'MFH':      # level from the hourly composite, shape from the quarter-hour meters
        x = (common + apt.mean(axis=1) * units)
        xs = x.groupby(hour).transform('sum')
        shape = (x / xs).where(xs > 0, 0.25).fillna(0.25)
        nonshift = pd.Series(hh.non_shiftable_load_kwh.reindex(hour).to_numpy() * shape.to_numpy(), index=Q_INDEX)
    pr = params[role]
    T_dhw = pr['T_sup_dhw_c']
    cop_sh = cop(t.to_numpy(), pr['eta_sh'], pr['T_sup_sh_c']); cop_dhw = cop(t.to_numpy(), pr['eta_dhw'], T_dhw)
    d = pd.DataFrame({'e_hp_kwh': hp.to_numpy(), 'e_hp_baseline_kwh': base_e.to_numpy(), 'e_hp_space_heating_kwh': sh.to_numpy(), 'outdoor_temp_c': t.to_numpy(),
                      'cop_space_heating': cop_sh, 'cop_baseline_dhw': cop_dhw, 'heating_demand_kwh': sh.to_numpy() * cop_sh, 'dhw_demand_kwh': base_e.to_numpy() * cop_dhw,
                      'non_shiftable_load_kwh': nonshift.to_numpy(), 'gap_filled_flag': flag.to_numpy()}, index=Q_INDEX)
    os.makedirs(os.path.join(OUT, 'thermal'), exist_ok=True)
    d.to_csv(os.path.join(OUT, 'thermal', f'{role}_2023_thermal_15min.csv'), index_label='timestamp_utc')
    # consistency with the hourly pipeline
    h = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    agg = d.groupby(d.index.floor('1h')).sum(min_count=4)
    qc[role] = {'hp_electricity_kwh_15min': float(d.e_hp_kwh.sum()), 'hp_electricity_kwh_hourly': float(h.e_hp_kwh.sum()),
                'max_abs_hourly_diff_hp': float((agg.e_hp_kwh - h.e_hp_kwh).abs().max()),
                'max_abs_hourly_diff_nonshiftable': float((agg.non_shiftable_load_kwh - h.non_shiftable_load_kwh).abs().max()),
                'heating_demand_kwh_15min': float(d.heating_demand_kwh.sum()), 'heating_demand_kwh_hourly': float(h.heating_demand_kwh.sum()),
                'heating_demand_rel_diff_pct': float(100 * (d.heating_demand_kwh.sum() / h.heating_demand_kwh.sum() - 1)),
                'dhw_demand_kwh_15min': float(d.dhw_demand_kwh.sum()), 'dhw_demand_kwh_hourly': float(h.dhw_demand_kwh.sum()),
                'dhw_demand_rel_diff_pct': float(100 * (d.dhw_demand_kwh.sum() / h.dhw_demand_kwh.sum() - 1)),
                'nan_values': int(d.isna().sum().sum()), 'gap_filled_quarter_hours': int(flag.sum()),
                'peak_heating_kw_15min': float(d.heating_demand_kwh.max() * 4), 'peak_heating_kw_hourly': float(h.heating_demand_kwh.max()),
                'peak_hp_electricity_kw_15min': float(d.e_hp_kwh.max() * 4), 'peak_hp_electricity_kw_hourly': float(h.e_hp_kwh.max())}
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    params = json.load(open(os.path.join(CAN, 'thermal', 'thermal_params.json')))
    qc = {'quarter_hours': len(Q_INDEX)}
    w15, err = build_weather(); qc['weather_ghi_hourly_mean_max_abs_error_wm2'] = err
    y = build_pv(w15)
    h = pd.read_csv(os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    qc['pv_annual_specific_yield_15min'] = float(y.sum() / 4.0); qc['pv_annual_specific_yield_hourly'] = float(h.pv_ac_w_per_kwp.sum() / 1000.0)
    t = build_tariff(); qc['tariff_missing_quarter_hours'] = int(t.total_chf_kwh.isna().sum())
    c = pd.read_csv(os.path.join(CAN, 'carbon_intensity_citylearn_2023.csv')).carbon_intensity.to_numpy()
    pd.DataFrame({'carbon_intensity': np.repeat(c, 4)}).to_csv(os.path.join(OUT, 'carbon_intensity_citylearn_2023_15min.csv'), index=False)
    for role in ROLES:
        build_building(role, w15, params, qc); print(role, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in qc[role].items() if 'diff' in k}, flush=True)
    json.dump(qc, open(os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_15min_2023.json'), 'w'), indent=1)
    print({k: v for k, v in qc.items() if k not in ROLES})


if __name__ == '__main__':
    main()
