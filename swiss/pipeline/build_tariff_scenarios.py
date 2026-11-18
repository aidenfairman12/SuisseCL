"""Task B5 (step 9): LABELLED scenario tariffs ("what if prices varied more"), never a claim about current Swiss prices (plan section 3).
S0 stays the realistic baseline (EKZ standard 2023). Scenario tariffs, hourly 2023 local year, CHF/kWh excl. VAT, all built from the EKZ file (SRC-002, CC BY 4.0):
  tou_q4_2023     energy_standard 2023 (two-tier) + EKZ time-of-use GRID fee as published for Q4 2023 (the only 2023 months of the pilot),
                  applied by hour of day and day type to every day of 2023
  tou_2024        energy_standard 2023 + EKZ time-of-use grid fee of the 2024 structure (seasonal, three or four levels) by month, day type and hour,
                  applied to the same months of 2023
  dyn_2024        energy_standard 2023 + EKZ dynamic grid fee of 2024 on the SAME CALENDAR DATE of 2023 (29 February dropped). The dynamic fee follows grid
                  conditions of 2024, which do not match the 2023 weather: a stylised use
  spread2/spread5 the S0 price stretched around its mean by 2 and 5 (Phase A what-ifs; stylised)
The pilot tariffs apply to pilot participants only and ran from 1 October 2023; 2024 energy prices were much higher than 2023 and are not used.
Output: data/canonical/tariff_scenarios_2023_hourly.csv, docs/data/data_quality_reports/qc_tariff_scenarios_2023.json
Run: cl/bin/python -I swiss/pipeline/build_tariff_scenarios.py
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'data', 'raw', 'ekz', 'extracted', 'tariff_data.csv')
CAN = os.path.join(ROOT, 'data', 'canonical')
OUT = os.path.join(CAN, 'tariff_scenarios_2023_hourly.csv')
QC = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_tariff_scenarios_2023.json')


def mode_table(df, col, keys):
    """Modal value per key cell and the share of quarter-hours that agree with it (purity)."""
    g = df.dropna(subset=[col]).groupby(keys)[col]
    mode = g.agg(lambda x: x.round(3).mode().iloc[0])
    purity = g.agg(lambda x: float((x.round(3) == x.round(3).mode().iloc[0]).mean()))
    return mode, purity


def main():
    t = pd.read_csv(SRC, sep=';', parse_dates=['timestamp_utc']).set_index('timestamp_utc')
    loc = t.index.tz_convert('Europe/Zurich')
    t['y'], t['m'], t['d'], t['h'] = loc.year, loc.month, loc.day, loc.hour
    t['dt'] = np.where(loc.dayofweek < 5, 'weekday', np.where(loc.dayofweek == 5, 'sat', 'sun'))
    base = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), parse_dates=['timestamp_utc']).set_index('timestamp_utc')
    bl = base.index.tz_convert('Europe/Zurich')
    frame = pd.DataFrame({'m': bl.month, 'd': bl.day, 'h': bl.hour, 'dt': np.where(bl.dayofweek < 5, 'weekday', np.where(bl.dayofweek == 5, 'sat', 'sun'))}, index=base.index)
    energy = base.energy_rp_kwh
    out = pd.DataFrame(index=base.index)
    out['standard_s0'] = base.total_chf_kwh
    qc = {}
    # tou Q4 2023: by hour and day type
    q4 = t[(t.y == 2023) & (t.m >= 10)]
    mode, pur = mode_table(q4, 'grid_tou', ['dt', 'h'])
    qc['tou_q4_2023_purity_min'] = float(pur.min())
    qc['tou_q4_2023_table'] = {f'{k[0]}-{k[1]:02d}': float(v) for k, v in mode.items()}
    key = list(zip(frame.dt, frame.h))
    grid = pd.Series([mode[k] for k in key], index=base.index)
    out['tou_q4_2023'] = (energy + grid) / 100.0
    # tou 2024 structure: by month, day type, hour
    y24 = t[t.y == 2024]
    mode, pur = mode_table(y24, 'grid_tou', ['m', 'dt', 'h'])
    qc['tou_2024_purity_min'] = float(pur.min()); qc['tou_2024_purity_mean'] = float(pur.mean())
    grid = pd.Series([mode[k] for k in zip(frame.m, frame.dt, frame.h)], index=base.index)
    out['tou_2024'] = (energy + grid) / 100.0
    # dynamic grid fee 2024 on the same calendar date (hourly mean of quarter-hours)
    dyn = y24.dropna(subset=['grid_dyn']).groupby(['m', 'd', 'h']).grid_dyn.mean()
    grid = pd.Series([dyn.get(k, np.nan) for k in zip(frame.m, frame.d, frame.h)], index=base.index)
    qc['dyn_missing_hours'] = int(grid.isna().sum())
    grid = grid.interpolate(limit_direction='both')
    out['dyn_2024'] = (energy + grid) / 100.0
    # stylised spreads
    mean = base.total_chf_kwh.mean()
    out['spread2'] = mean + 2.0 * (base.total_chf_kwh - mean)
    out['spread5'] = mean + 5.0 * (base.total_chf_kwh - mean)
    out.to_csv(OUT, index_label='timestamp_utc', float_format='%.6f')
    qc['summary_rp_per_kwh'] = {c: {'mean': round(float(out[c].mean() * 100), 3), 'min': round(float(out[c].min() * 100), 3), 'max': round(float(out[c].max() * 100), 3),
                                    'p05': round(float(out[c].quantile(0.05) * 100), 3), 'p95': round(float(out[c].quantile(0.95) * 100), 3), 'std': round(float(out[c].std() * 100), 3)}
                                for c in out.columns}
    json.dump(qc, open(QC, 'w'), indent=1)
    print(json.dumps({k: v for k, v in qc.items() if k != 'tou_q4_2023_table'}, indent=1)[:2500])
    print(qc['tou_q4_2023_table'])


if __name__ == '__main__':
    main()
