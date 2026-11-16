"""Task A4: QC + hourly canonical datasets for the six selected buildings (year 2023).

Inputs : data/raw/{heapo,ekz}/extracted (read-only), data/interim/selected_buildings.csv
Outputs: data/canonical/quarter_hourly/<role>_2023_15min.csv   (original resolution, UTC, no imputation)
         data/canonical/hourly/<role>_2023_hourly.csv          (derived hourly; see columns.json)
         data/canonical/hourly/columns.json                    (variable classification)
         data/canonical/weather_heapo_2023_hourly.csv          (measured, HEAPO-supplied MeteoSwiss subset)
         docs/data/data_quality_reports/qc_2023_buildings.json (+ .md rendered by report step)

Time convention (decision D-007): the simulation year is the Swiss local year 2023,
= UTC window [2022-12-31 23:00, 2023-12-31 23:00) = exactly 8760 hourly slots, so no
duplicate/missing hours arise at DST changes. Local clock fields are derived from
Europe/Zurich; the hourly index itself stays UTC.

Hourly aggregation: sum of 4 quarter-hours, only if all 4 are present; otherwise NaN
(count of missing quarters kept). No interpolation or imputation anywhere.

Run: cl/bin/python -I swiss/pipeline/build_buildings_hourly.py
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW = os.path.join(ROOT, 'data', 'raw')
INT = os.path.join(ROOT, 'data', 'interim')
CAN = os.path.join(ROOT, 'data', 'canonical')
QCDIR = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports')
START = pd.Timestamp('2022-12-31 23:00', tz='UTC')
END = pd.Timestamp('2023-12-31 23:00', tz='UTC')  # exclusive
Q_INDEX = pd.date_range(START, END, freq='15min', inclusive='left')
H_INDEX = pd.date_range(START, END, freq='1h', inclusive='left')
SEED = 20230101
ZERO_RUN_HOURS = 24


def read_q(path, ts_col, cols, sep=';'):
    d = pd.read_csv(path, sep=sep, usecols=[ts_col] + cols)
    d[ts_col] = pd.to_datetime(d[ts_col], utc=True)
    dup = int(d[ts_col].duplicated().sum())
    d = d.drop_duplicates(ts_col).set_index(ts_col).sort_index()
    return d.reindex(Q_INDEX), dup


def hourly_sum(q):
    """Sum 4 quarters if complete; returns (hourly value, n_missing_quarters)."""
    g = q.groupby(q.index.floor('1h'))
    s = g.sum(min_count=4)
    n_missing = g.apply(lambda x: x.isna().sum())
    return s.reindex(H_INDEX), n_missing.reindex(H_INDEX)


def zero_runs(series, min_len):
    """Boolean mask of hours inside runs of >= min_len consecutive zeros (NaN breaks a run)."""
    z = (series == 0).to_numpy()
    mask = np.zeros(len(z), dtype=bool)
    i = 0
    while i < len(z):
        if z[i]:
            j = i
            while j < len(z) and z[j]:
                j += 1
            if j - i >= min_len:
                mask[i:j] = True
            i = j
        else:
            i += 1
    return pd.Series(mask, index=series.index)


def fill_gap_days(series):
    """Fill hours of fully-missing UTC days by the mean of the same hour on day-1 and day+1.

    Only applied when BOTH neighbour days are complete (decision D-011, chosen by backtest
    swiss/pipeline/backtest_gap_fill.py: neighbouring days beat same-weekday-neighbouring-weeks
    on most metrics). Returns (filled series, boolean mask of filled hours). Raw column untouched.
    """
    out = series.copy()
    mask = pd.Series(False, index=series.index)
    days = series.index.floor('1D')
    for day in pd.unique(days):
        sl = days == day
        if series[sl].isna().all():
            prev = series[days == day - pd.Timedelta(days=1)]
            nxt = series[days == day + pd.Timedelta(days=1)]
            if len(prev) == 24 and len(nxt) == 24 and prev.notna().all() and nxt.notna().all():
                out[sl] = (prev.to_numpy() + nxt.to_numpy()) / 2
                mask[sl] = True
    return out, mask


def stats(h, name):
    v = h.dropna()
    return {'column': name, 'coverage_hours': int(h.notna().sum()), 'missing_hours': int(h.isna().sum()),
            'negative_hours': int((v < 0).sum()), 'zero_hours': int((v == 0).sum()),
            'zero_run_hours_ge24': int(zero_runs(h, ZERO_RUN_HOURS).sum()),
            'sum_kwh': float(v.sum()), 'max_hourly_kwh': float(v.max()) if len(v) else None,
            'p99_hourly_kwh': float(v.quantile(.99)) if len(v) else None,
            'hours_gt_5x_p99': int((v > 5 * v.quantile(.99)).sum()) if len(v) else 0}


def local_fields(index):
    loc = index.tz_convert('Europe/Zurich')
    return pd.DataFrame({'local_time': loc.strftime('%Y-%m-%d %H:%M'),
                         'dst_active': (loc.map(lambda t: t.dst().total_seconds() > 0)).astype(int)}, index=index)


def build_sfh(row, qc):
    hid = int(row['id'])
    base = os.path.join(RAW, 'heapo', 'extracted', 'heapo_data', 'smart_meter_data')
    cols = ['kWh_received_Total', 'kWh_received_HeatPump', 'kWh_received_Other']
    q, dup = read_q(os.path.join(base, '15min', f'{hid}.csv'), 'Timestamp', cols)
    q.columns = ['kwh_total', 'kwh_hp', 'kwh_other']
    hd = {}
    for c in q.columns:
        hd[c], hd[c + '_nmiss_q'] = hourly_sum(q[c])
    h = pd.DataFrame({'kwh_hp': hd['kwh_hp'], 'kwh_other': hd['kwh_other'], 'kwh_total': hd['kwh_total'],
                      'nmiss_q_hp': hd['kwh_hp_nmiss_q'], 'nmiss_q_other': hd['kwh_other_nmiss_q'],
                      'nmiss_q_total': hd['kwh_total_nmiss_q']})
    hp_f, m1 = fill_gap_days(h['kwh_hp'])
    ot_f, m2 = fill_gap_days(h['kwh_other'])
    h['kwh_hp_f'] = hp_f
    h['kwh_other_f'] = ot_f
    h['kwh_total_f'] = hp_f + ot_f
    h['gap_filled_flag'] = (m1 | m2).astype(int)
    # double-counting check: Total vs HP + Other on quarter-hours where all three exist
    ok = q.dropna()
    diff = (ok['kwh_total'] - ok['kwh_hp'] - ok['kwh_other'])
    chk = {'n_quarters_all_three': int(len(ok)), 'max_abs_diff_kwh': float(diff.abs().max()),
           'share_abs_diff_gt_0.01': float((diff.abs() > 0.01).mean()),
           'sum_total': float(ok['kwh_total'].sum()), 'sum_hp_plus_other': float((ok['kwh_hp'] + ok['kwh_other']).sum())}
    # returned energy (PV indicator) from daily file
    dd = pd.read_csv(os.path.join(base, 'daily', f'{hid}.csv'), sep=';', usecols=['Timestamp', 'kWh_returned_Total', 'AffectsTimePoint'])
    dd['Timestamp'] = pd.to_datetime(dd['Timestamp'], utc=True)
    d23 = dd[(dd.Timestamp >= START) & (dd.Timestamp <= END + pd.Timedelta(days=1))]
    pv = {'daily_rows_2023': int(len(d23)), 'returned_kwh_2023_sum': float(d23['kWh_returned_Total'].sum(min_count=1)) if len(d23) else None,
          'returned_nonnull_days': int(d23['kWh_returned_Total'].notna().sum()),
          'affects_time_point_values_2023': d23['AffectsTimePoint'].value_counts(dropna=False).to_dict()}
    q.to_csv(os.path.join(CAN, 'quarter_hourly', f"{row['role']}_2023_15min.csv"), index_label='timestamp_utc')
    qc[row['role']] = {'source': 'HEAPO', 'id': hid, 'duplicate_timestamps_dropped': dup,
                       'columns': [stats(h['kwh_hp'], 'kwh_hp'), stats(h['kwh_other'], 'kwh_other'), stats(h['kwh_total'], 'kwh_total')],
                       'gap_filled_hours': int((m1 | m2).sum()),
                       'total_vs_hp_plus_other': chk, 'pv_indicator_daily_returned_energy': pv}
    return h


def build_mfh(row, qc, apt_pool):
    mid = int(row['id']); oid = int(row['object_id']); units = int(row['units'])
    base = os.path.join(RAW, 'ekz', 'extracted')
    q, dup = read_q(os.path.join(base, 'smart_meter_data', f'{mid}.csv'), 'timestamp_utc', ['kWh_to_installation', 'kWh_to_grid'], sep=';')
    qhp = q['kWh_to_installation'].rename('kwh_hp')
    export = float(q['kWh_to_grid'].sum())
    hp, hp_n = hourly_sum(qhp)
    meta = pd.read_csv(os.path.join(base, 'metadata.csv'), sep=';', encoding='utf-8-sig')
    same = meta[meta['0_object_id'] == oid]
    other_meters = same[same['0_meter_id'] != mid][['0_meter_id', '0_installation_type']]
    # measured common-area meters of the same object (if any)
    commons = []
    for _, r in other_meters[other_meters['0_installation_type'] == 'Common areas'].iterrows():
        qc_, _ = read_q(os.path.join(base, 'smart_meter_data', f"{int(r['0_meter_id'])}.csv"), 'timestamp_utc', ['kWh_to_installation'])
        commons.append(hourly_sum(qc_['kWh_to_installation'])[0].rename(int(r['0_meter_id'])))
    common = pd.concat(commons, axis=1) if commons else None
    # synthetic apartment composite: seeded draw of `units` distinct qualifying apartment meters
    rng = np.random.default_rng(SEED + mid)
    avail = [m for m in apt_pool['ids'] if m not in apt_pool['used']]
    pick = list(rng.choice(avail, size=units, replace=False))
    apt_pool['used'].update(pick)
    series = []
    for m in pick:
        a, _ = read_q(os.path.join(base, 'smart_meter_data', f'{int(m)}.csv'), 'timestamp_utc', ['kWh_to_installation'])
        series.append(hourly_sum(a['kWh_to_installation'])[0].rename(int(m)))
    apt = pd.concat(series, axis=1)
    # D-015: composite = units x mean of the drawn apartments that are present, if >= 80 % of them are present;
    # otherwise NaN (no further filling here). Replaces the earlier 'any missing -> NaN' rule.
    n_avail = apt.notna().sum(axis=1)
    comp = (apt.mean(axis=1) * units).where(n_avail >= int(np.ceil(0.8 * units)))
    h = pd.DataFrame({'kwh_hp': hp, 'nmiss_q_hp': hp_n,
                      'kwh_common_areas_measured': (common.sum(axis=1, min_count=common.shape[1]) if common is not None else np.nan),
                      'kwh_apartments_synthetic': comp,
                      'n_apartments_in_composite': units, 'n_apartments_available': n_avail})
    q.rename(columns={'kWh_to_installation': 'kwh_hp', 'kWh_to_grid': 'kwh_to_grid'}).to_csv(
        os.path.join(CAN, 'quarter_hourly', f"{row['role']}_2023_15min.csv"), index_label='timestamp_utc')
    cols = [stats(h['kwh_hp'], 'kwh_hp'), stats(h['kwh_apartments_synthetic'], 'kwh_apartments_synthetic')]
    if common is not None:
        cols.append(stats(h['kwh_common_areas_measured'], 'kwh_common_areas_measured'))
    qc[row['role']] = {'source': 'EKZ', 'id': mid, 'object_id': oid, 'housing_units': units,
                       'duplicate_timestamps_dropped': dup, 'columns': cols,
                       'hp_meter_energy_to_grid_kwh_2023': export,
                       'other_meters_in_object': other_meters.astype({'0_meter_id': int}).to_dict('records'),
                       'apartment_composite_meter_ids': [int(x) for x in pick],
                       'apartment_composite_note': 'SYNTHETIC: drawn at random (seeded) from EKZ apartment meters; not this building'}
    return h


def apartment_pool():
    m = pd.read_csv(os.path.join(INT, 'ekz_meters.csv'))
    a = m[(m['0_installation_type'] == 'Apartment') & (m.cov_2023 >= 0.95) & (m.n_dup_ts == 0)
          & (m.kwh_export_2023 <= 1.0)
          & ~(m[['1_ewh', '1_hp', '1_hp-add', '1_hp-wh', '1_ev', '1_storage_heating', '1_direct_heating']].fillna(False).astype(bool).any(axis=1))]
    return {'ids': sorted(a['0_meter_id'].astype(int).tolist()), 'used': set(), 'n': len(a)}


def weather():
    base = os.path.join(RAW, 'heapo', 'extracted', 'heapo_data', 'weather_data', 'hourly')
    out = {}
    for st in ['Hg', '8jB']:
        w = pd.read_csv(os.path.join(base, f'{st}.csv'), sep=';')
        w['Timestamp'] = pd.to_datetime(w['Timestamp'], utc=True)
        w = w.drop_duplicates('Timestamp').set_index('Timestamp').reindex(H_INDEX)
        w = w[['Temperature_avg_hourly', 'Humidity_avg_hourly', 'Sunshine_duration_hourly', 'Precipitation_total_hourly', 'WindSpeed_hourly']]
        w.columns = [f'{c}__{st}' for c in w.columns]
        out[st] = w
    wd = pd.concat(out.values(), axis=1)
    wd.to_csv(os.path.join(CAN, 'weather_heapo_2023_hourly.csv'), index_label='timestamp_utc')
    return {c: {'coverage_hours': int(wd[c].notna().sum()), 'min': float(wd[c].min()), 'max': float(wd[c].max())} for c in wd.columns}


if __name__ == '__main__':
    for d in ('quarter_hourly', 'hourly'):
        os.makedirs(os.path.join(CAN, d), exist_ok=True)
    os.makedirs(QCDIR, exist_ok=True)
    sel = pd.read_csv(os.path.join(INT, 'selected_buildings.csv'))
    qc = {'window_utc': [str(START), str(END)], 'hours_expected': len(H_INDEX), 'seed': SEED}
    pool = apartment_pool()
    qc['apartment_pool_size'] = pool['n']
    loc = local_fields(H_INDEX)
    for _, r in sel.iterrows():
        h = build_sfh(r, qc) if r['source'] == 'HEAPO' else build_mfh(r, qc, pool)
        out = pd.concat([loc, h], axis=1)
        out.to_csv(os.path.join(CAN, 'hourly', f"{r['role']}_2023_hourly.csv"), index_label='timestamp_utc')
        print(r['role'], 'ok', flush=True)
    qc['weather_heapo'] = weather()
    classes = {'kwh_hp_f/kwh_other_f/kwh_total_f': 'measured where gap_filled_flag==0; SYNTHETIC where gap_filled_flag==1 (mean of day-1 and day+1, D-011)',
               'kwh_hp': 'measured (HP sub-meter, 15-min summed to hourly)', 'kwh_other': 'measured',
               'kwh_total': 'measured', 'kwh_common_areas_measured': 'measured (linked common-area meters of same object)',
               'kwh_apartments_synthetic': 'synthetic (seeded sample of unrelated EKZ apartment meters)',
               'local_time/dst_active': 'derived from UTC index (Europe/Zurich)', 'nmiss_q_*': 'derived QC count'}
    json.dump(classes, open(os.path.join(CAN, 'hourly', 'columns.json'), 'w'), indent=2)
    json.dump(qc, open(os.path.join(QCDIR, 'qc_2023_buildings.json'), 'w'), indent=2, default=str)
    print('done')
