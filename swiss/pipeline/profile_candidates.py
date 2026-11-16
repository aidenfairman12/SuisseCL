"""Task A3 support: per-household / per-meter / per-object summary statistics for
building selection. Reads raw data read-only, writes small derived summary CSVs.

Run:  cl/bin/python -I swiss/pipeline/profile_candidates.py

Outputs (data/interim/, classification: DERIVED from measured data):
  heapo_candidates.csv  one row per HEAPO household
  ekz_meters.csv        one row per EKZ meter
  ekz_objects.csv       one row per EKZ object_id (building) with meter counts

No imputation. Coverage = share of expected 15-min slots that are non-null and the
row exists; zero-runs/negatives are NOT removed here (that is Task A4 QC).
Timestamps are UTC in both sources; calendar-year windows are in UTC.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(ROOT, 'data', 'interim')
YEARS = (2022, 2023)  # HEAPO full calendar years
EKZ_YEARS = (2023, 2024)
SLOTS = {2022: 365 * 96, 2023: 365 * 96, 2024: 366 * 96}


def heapo():
    base = os.path.join(RAW, 'heapo', 'extracted', 'heapo_data')
    hh = pd.read_csv(os.path.join(base, 'meta_data', 'households.csv'), sep=';')
    md = pd.read_csv(os.path.join(base, 'meta_data', 'meta_data.csv'), sep=';')
    rows = []
    for f in sorted(glob.glob(os.path.join(base, 'smart_meter_data', '15min', '*.csv'))):
        d = pd.read_csv(f, sep=';', usecols=['Household_ID', 'Timestamp', 'kWh_received_Total',
                                             'kWh_received_HeatPump', 'kWh_received_Other'])
        ts = pd.to_datetime(d['Timestamp'], utc=True)
        r = {'Household_ID': int(d['Household_ID'].iloc[0]), 'first_ts': ts.min(), 'last_ts': ts.max(),
             'n_rows': len(d), 'n_dup_ts': int(ts.duplicated().sum()),
             'has_hp_submeter': bool(d['kWh_received_HeatPump'].notna().any())}
        for y in YEARS:
            m = ts.dt.year == y
            tot = d.loc[m, 'kWh_received_Total']
            r[f'cov_{y}'] = tot.notna().sum() / SLOTS[y]
            r[f'kwh_total_{y}'] = tot.sum()
            r[f'zero_share_{y}'] = (tot[tot.notna()] == 0).mean() if tot.notna().any() else np.nan
            hp = d.loc[m, 'kWh_received_HeatPump']
            r[f'cov_hp_{y}'] = hp.notna().sum() / SLOTS[y]
            r[f'kwh_hp_{y}'] = hp.sum()
        rows.append(r)
    out = pd.DataFrame(rows).merge(hh, on='Household_ID', how='left').merge(md, on='Household_ID', how='left')
    out.to_csv(os.path.join(OUT, 'heapo_candidates.csv'), index=False)
    return out


def ekz():
    base = os.path.join(RAW, 'ekz', 'extracted')
    meta = pd.read_csv(os.path.join(base, 'metadata.csv'), sep=';', encoding='utf-8-sig')
    rows = []
    for f in sorted(glob.glob(os.path.join(base, 'smart_meter_data', '*.csv'))):
        d = pd.read_csv(f, sep=';', usecols=['timestamp_utc', 'kWh_to_installation', 'kWh_to_grid'])
        ts = pd.to_datetime(d['timestamp_utc'], utc=True)
        r = {'0_meter_id': int(os.path.basename(f)[:-4]), 'n_rows': len(d), 'n_dup_ts': int(ts.duplicated().sum())}
        for y in EKZ_YEARS:
            m = ts.dt.year == y
            imp = d.loc[m, 'kWh_to_installation']
            r[f'cov_{y}'] = imp.notna().sum() / SLOTS[y]
            r[f'kwh_import_{y}'] = imp.sum()
            r[f'kwh_export_{y}'] = d.loc[m, 'kWh_to_grid'].sum()
        rows.append(r)
    mt = pd.DataFrame(rows).merge(meta, on='0_meter_id', how='left')
    mt.to_csv(os.path.join(OUT, 'ekz_meters.csv'), index=False)
    ap = mt[mt['0_object_type'] == 'Apartment building']
    g = ap.groupby('0_object_id').agg(
        n_meters=('0_meter_id', 'size'),
        n_apartment_meters=('0_installation_type', lambda s: (s == 'Apartment').sum()),
        n_common=('0_installation_type', lambda s: (s == 'Common areas').sum()),
        n_hp_meter=('0_installation_type', lambda s: (s == 'Heat pump').sum()),
        any_hp_flag=('1_hp', 'any'), any_ewh_flag=('1_ewh', 'any'),
        housing_units=('0_num_housing_units', 'max'),
        min_cov_2023=('cov_2023', 'min'), kwh_import_2023=('kwh_import_2023', 'sum'),
        kwh_export_2023=('kwh_export_2023', 'sum')).reset_index()
    g.to_csv(os.path.join(OUT, 'ekz_objects.csv'), index=False)
    return mt, g


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if which in ('all', 'heapo'):
        heapo(); print('heapo done', flush=True)
    if which in ('all', 'ekz'):
        ekz(); print('ekz done', flush=True)
