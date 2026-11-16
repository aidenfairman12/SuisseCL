"""Backtest of gap-fill candidates for the HEAPO 24 h gap (UTC day 2023-10-29).

For every complete UTC day D in 2023-09-15..2023-12-15 (all required neighbour days complete),
predict D's 24 hourly values from neighbours and compare to the measured values:
  A = mean(D-1, D+1)   neighbouring calendar days
  B = mean(D-7, D+7)   same weekday, neighbouring weeks
Metrics per method/variable: mean absolute error of hourly kWh and mean absolute % error of daily kWh.
Also reported separately for Sundays (the gap day is a Sunday).

Run: cl/bin/python -I swiss/pipeline/backtest_gap_fill.py   -> prints + writes JSON to docs/data/data_quality_reports/
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'backtest_gap_fill.json')
GAP_DAY = pd.Timestamp('2023-10-29', tz='UTC')


def day_matrix(s):
    """Series indexed by UTC hour -> DataFrame rows = UTC dates, cols = hour 0..23."""
    d = s.to_frame('v')
    d['date'] = d.index.floor('1D')
    d['hour'] = d.index.hour
    return d.pivot(index='date', columns='hour', values='v')


def run():
    res = {}
    for role in ['SFH-low', 'SFH-mid', 'SFH-high']:
        h = pd.read_csv(os.path.join(ROOT, 'data', 'canonical', 'hourly', f'{role}_2023_hourly.csv'),
                        index_col='timestamp_utc', parse_dates=True)
        for var in ['kwh_hp', 'kwh_other']:
            M = day_matrix(h[var])
            rows = []
            for D in M.index:
                if not (pd.Timestamp('2023-09-15', tz='UTC') <= D <= pd.Timestamp('2023-12-15', tz='UTC')):
                    continue
                need = [D, D - pd.Timedelta(days=1), D + pd.Timedelta(days=1), D - pd.Timedelta(days=7), D + pd.Timedelta(days=7)]
                if any(n not in M.index or M.loc[n].isna().any() for n in need):
                    continue
                act = M.loc[D].to_numpy()
                a = (M.loc[need[1]].to_numpy() + M.loc[need[2]].to_numpy()) / 2
                b = (M.loc[need[3]].to_numpy() + M.loc[need[4]].to_numpy()) / 2
                rows.append({'date': D, 'sunday': D.dayofweek == 6,
                             'mae_A': np.abs(a - act).mean(), 'mae_B': np.abs(b - act).mean(),
                             'dpe_A': abs(a.sum() - act.sum()) / max(act.sum(), 1e-9),
                             'dpe_B': abs(b.sum() - act.sum()) / max(act.sum(), 1e-9)})
            r = pd.DataFrame(rows)
            for name, sub in (('all_days', r), ('sundays', r[r.sunday])):
                res[f'{role}|{var}|{name}'] = {'n_days': len(sub), 'hourly_MAE_kWh_A_neighbour_days': round(sub.mae_A.mean(), 4),
                                               'hourly_MAE_kWh_B_same_weekday': round(sub.mae_B.mean(), 4),
                                               'daily_MAPE_A': round(sub.dpe_A.mean(), 4), 'daily_MAPE_B': round(sub.dpe_B.mean(), 4)}
    json.dump(res, open(OUT, 'w'), indent=1)
    return res


if __name__ == '__main__':
    for k, v in run().items():
        print(k, v)
