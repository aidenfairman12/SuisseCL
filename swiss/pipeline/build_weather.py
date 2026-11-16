"""Task A4/A6: hourly 2023 weather for Zurich/Kloten (KLO) from MeteoSwiss OGD.

Input : data/raw/meteoswiss/ogd-smn_klo_h_historical_2020-2029.csv  (SRC-004)
Output: data/canonical/weather_klo_2023_hourly.csv                   (DER-007)
        docs/data/data_quality_reports/qc_weather_klo_2023.json

Timestamp convention (D-009, determined empirically, see EL-0018): MeteoSwiss hourly
`reference_timestamp` (UTC) labels the END of the averaging hour. The value for the
hour that STARTS at UTC t is therefore the row labelled t+1h. Evidence: July mean global
radiation peaks at label 12:00 UTC while local solar noon at Kloten is ~11:26 UTC
(interval [11,12] centred 11:30).

Variables (all measured except the one derived column):
  temp_c (tre200h0), rh_pct (ure200h0), ghi_wm2 (gre000h0), diffuse_wm2 (ods000h0),
  sunshine_min (sre000h0), beam_horizontal_wm2 = ghi - diffuse   [DERIVED, horizontal
  beam component, NOT direct-normal irradiance].
No cleaning: night-time radiation of ~1-2 W/m2 (sensor offset) is kept as measured.

Run: cl/bin/python -I swiss/pipeline/build_weather.py
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'data', 'raw', 'meteoswiss', 'ogd-smn_klo_h_historical_2020-2029.csv')
OUT = os.path.join(ROOT, 'data', 'canonical', 'weather_klo_2023_hourly.csv')
QC = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_weather_klo_2023.json')
H_INDEX = pd.date_range(pd.Timestamp('2022-12-31 23:00', tz='UTC'), pd.Timestamp('2023-12-31 23:00', tz='UTC'), freq='1h', inclusive='left')

d = pd.read_csv(SRC, sep=';', usecols=['reference_timestamp', 'tre200h0', 'ure200h0', 'gre000h0', 'ods000h0', 'sre000h0'])
d['end'] = pd.to_datetime(d['reference_timestamp'], format='%d.%m.%Y %H:%M').dt.tz_localize('UTC')
dup = int(d['end'].duplicated().sum())
d['start'] = d['end'] - pd.Timedelta('1h')
d = d.drop_duplicates('start').set_index('start').reindex(H_INDEX)
w = pd.DataFrame({'temp_c': d.tre200h0, 'rh_pct': d.ure200h0, 'ghi_wm2': d.gre000h0, 'diffuse_wm2': d.ods000h0,
                  'sunshine_min': d.sre000h0})
w['beam_horizontal_wm2'] = w.ghi_wm2 - w.diffuse_wm2
w.to_csv(OUT, index_label='timestamp_utc')
qc = {'rows': len(w), 'duplicates_dropped': dup, 'missing': w.isna().sum().to_dict(),
      'min': w.min().round(2).to_dict(), 'max': w.max().round(2).to_dict(),
      'annual_ghi_kwh_m2': float(w.ghi_wm2.sum() / 1000), 'annual_mean_temp_c': float(w.temp_c.mean()),
      'hours_beam_negative': int((w.beam_horizontal_wm2 < 0).sum()),
      'hours_night_ghi_positive_le_5': int(((w.ghi_wm2 > 0) & (w.ghi_wm2 <= 5)).sum()),
      'ghi_gt_diffuse_violations_gt_10': int(((w.diffuse_wm2 - w.ghi_wm2) > 10).sum())}
json.dump(qc, open(QC, 'w'), indent=2, default=str)
print(json.dumps(qc, indent=1, default=str))
