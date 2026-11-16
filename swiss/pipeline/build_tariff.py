"""Task A6: EKZ standard tariff for the simulation year 2023 -> hourly price series.

Input : data/raw/ekz/extracted/tariff_data.csv (SRC-002; Rp./kWh excl. VAT, 15-min, UTC start-of-interval)
Output: data/canonical/tariff_ekz_standard_2023_hourly.csv (DER-008)

Standard products only: energy_standard (EKZ Mixstrom) + grid_standard (EKZ Netz 400F).
Paper (arXiv:2607.19294, Sec 2.4): both two-tier ToU, higher price 07:00-20:00 on weekdays in 2023.
NOT included: VAT, federal levies/Netzzuschlag, metering, other surcharges (not in the file).
Pilot tariffs (unit/ToU/dynamic) are ignored: they apply to pilot participants only.
Hourly price = mean of the four 15-min prices (reported if prices vary inside an hour).

Run: cl/bin/python -I swiss/pipeline/build_tariff.py
"""
import json
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'data', 'raw', 'ekz', 'extracted', 'tariff_data.csv')
OUT = os.path.join(ROOT, 'data', 'canonical', 'tariff_ekz_standard_2023_hourly.csv')
QC = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_tariff_2023.json')
START = pd.Timestamp('2022-12-31 23:00', tz='UTC')
END = pd.Timestamp('2023-12-31 23:00', tz='UTC')

t = pd.read_csv(SRC, sep=';', usecols=['timestamp_utc', 'energy_standard', 'grid_standard'])
t['timestamp_utc'] = pd.to_datetime(t['timestamp_utc'], utc=True)
dup = int(t.timestamp_utc.duplicated().sum())
t = t.drop_duplicates('timestamp_utc').set_index('timestamp_utc')
t = t[(t.index >= START) & (t.index < END)].reindex(pd.date_range(START, END, freq='15min', inclusive='left'))
g = t.groupby(t.index.floor('1h'))
h = g.mean()
within = int((g.nunique(dropna=True) > 1).any(axis=1).sum())
h['n_missing_q'] = g.apply(lambda x: x['energy_standard'].isna().sum())
h = h.rename(columns={'energy_standard': 'energy_rp_kwh', 'grid_standard': 'grid_rp_kwh'})
h['total_rp_kwh'] = h.energy_rp_kwh + h.grid_rp_kwh
h['total_chf_kwh'] = h.total_rp_kwh / 100.0
h['tier'] = (h.total_rp_kwh >= h.total_rp_kwh.max() - 1e-9).map({True: 'high', False: 'low'})
h.to_csv(OUT, index_label='timestamp_utc')
qc = {'rows': len(h), 'duplicates_dropped': dup, 'missing_hours': int(h.total_rp_kwh.isna().sum()),
      'hours_with_price_change_inside_hour': within,
      'distinct_total_rp': sorted(h.total_rp_kwh.dropna().unique().round(3).tolist()),
      'distinct_energy_rp': sorted(h.energy_rp_kwh.dropna().unique().round(3).tolist()),
      'distinct_grid_rp': sorted(h.grid_rp_kwh.dropna().unique().round(3).tolist()),
      'mean_total_rp': float(h.total_rp_kwh.mean())}
json.dump(qc, open(QC, 'w'), indent=1)
print(json.dumps(qc, indent=1))
