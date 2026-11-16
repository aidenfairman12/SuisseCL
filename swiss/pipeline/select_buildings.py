"""Task A3: deterministic, rule-based selection of the six candidate buildings.

Rules were fixed BEFORE looking at individual IDs (see docs/data/building_selection_design.md).
Reads data/interim/{heapo_candidates,ekz_meters}.csv, writes data/interim/selected_buildings.csv.

Run:  cl/bin/python -I swiss/pipeline/select_buildings.py
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INT = os.path.join(ROOT, 'data', 'interim')
MIN_COV = 0.95


def nearest_to_median(df, col):
    med = df[col].median()
    return df.loc[(df[col] - med).abs().idxmin()]


def single_family():
    h = pd.read_csv(os.path.join(INT, 'heapo_candidates.csv'))
    pool = h[h.has_hp_submeter & (h.cov_2023 >= MIN_COV) & (h.cov_hp_2023 >= MIN_COV)
             & (h.Survey_HeatPump_Installation_Type == 'air-source')
             & (h.Survey_Building_Type == 'house') & h.Survey_Building_LivingArea.notna()
             & (h.n_dup_ts == 0)].copy()
    # three strata by terciles of 2023 heat-pump electricity
    q = pool.kwh_hp_2023.quantile([1 / 3, 2 / 3]).values
    pool['stratum'] = np.where(pool.kwh_hp_2023 <= q[0], 'low', np.where(pool.kwh_hp_2023 <= q[1], 'mid', 'high'))
    rows = []
    for s in ['low', 'mid', 'high']:
        r = nearest_to_median(pool[pool.stratum == s], 'kwh_hp_2023')
        rows.append({'role': f'SFH-{s}', 'source': 'HEAPO', 'id': int(r.Household_ID), 'stratum': s,
                     'n_pool': int((pool.stratum == s).sum()), 'kwh_total_2023': r.kwh_total_2023,
                     'kwh_hp_2023': r.kwh_hp_2023, 'area_m2': r.Survey_Building_LivingArea,
                     'residents': r.Survey_Building_Residents, 'pv_flag': r.Installation_HasPVSystem,
                     'units': 1})
    return rows, len(pool)


def multi_family():
    m = pd.read_csv(os.path.join(INT, 'ekz_meters.csv'))
    pool = m[(m['0_installation_type'] == 'Heat pump') & (m['0_object_type'] == 'Apartment building')
             & (m.cov_2023 >= MIN_COV) & (m.cov_2024 >= MIN_COV) & (m.n_dup_ts == 0)
             & (m['0_num_housing_units'] >= 4)].copy()
    bins = {'small': (4, 6), 'medium': (7, 14), 'large': (24, 10 ** 6)}
    rows = []
    for s, (lo, hi) in bins.items():
        sub = pool[(pool['0_num_housing_units'] >= lo) & (pool['0_num_housing_units'] <= hi)].copy()
        sub['kwh_per_unit'] = sub.kwh_import_2023 / sub['0_num_housing_units']
        r = nearest_to_median(sub, 'kwh_per_unit')
        rows.append({'role': f'MFH-{s}', 'source': 'EKZ', 'id': int(r['0_meter_id']), 'stratum': s,
                     'n_pool': len(sub), 'kwh_total_2023': np.nan, 'kwh_hp_2023': r.kwh_import_2023,
                     'area_m2': np.nan, 'residents': np.nan, 'pv_flag': np.nan,
                     'units': int(r['0_num_housing_units']), 'object_id': int(r['0_object_id'])})
    return rows, len(pool)


if __name__ == '__main__':
    a, na = single_family()
    b, nb = multi_family()
    out = pd.DataFrame(a + b)
    out.to_csv(os.path.join(INT, 'selected_buildings.csv'), index=False)
    pd.set_option('display.width', 220, 'display.max_columns', 30)
    print('SFH pool', na, 'MFH pool', nb)
    print(out.to_string())
