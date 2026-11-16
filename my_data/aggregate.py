"""Mean +/- std of held-out district KPIs across seeds, next to the baselines.
Usage: cl/bin/python my_data/aggregate.py [prefix]   e.g. rl_sac_central_composite  (default: every rl_*_s<seed>.csv group)
Writes results/summary.csv
"""
import glob, os, re, sys
import pandas as pd
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
KEYS = ['cost_total', 'carbon_emissions_total', 'electricity_consumption_total', 'all_time_peak_average', 'daily_peak_average',
        'ramping_average', 'daily_one_minus_load_factor_average', 'discomfort_proportion', 'discomfort_hot_proportion', 'discomfort_cold_proportion']
groups = {}
for f in sorted(glob.glob(f'{R}/rl_*_s[0-9]*.csv')):
    m = re.match(r'rl_(.+)_s(\d+)\.csv', os.path.basename(f))
    if m and (len(sys.argv) < 2 or m.group(1).startswith(sys.argv[1].removeprefix('rl_'))):
        groups.setdefault(m.group(1), []).append(pd.read_csv(f, index_col=0).iloc[:, 0])
rows = {}
for g, series in groups.items():
    d = pd.concat(series, axis=1).loc[KEYS]
    rows[f'{g} (n={d.shape[1]})'] = d.mean(axis=1).round(3).astype(str) + ' ± ' + d.std(axis=1).fillna(0).round(3).astype(str)
out = pd.DataFrame(rows)
base = pd.read_csv(f'{R}/rl_baselines.csv', index_col=0).loc[KEYS].round(3).astype(str)
out = base.join(out)
out.to_csv(f'{R}/summary.csv'); pd.set_option('display.width', 250); print(out.to_string())
