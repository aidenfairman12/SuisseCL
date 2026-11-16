"""Method check (D-013): run the carbon reconstruction on 2016 and 2017 and compare with the EPFL hourly dataset
(Vuarnoz & Aguacil Moreno 2020, Mendeley m5cd9spsrk, attributional LCA, 'GMT+1' reference; SRC-009).
Alignment: EPFL rows are matched BY POSITION to the 8,784/8,760 hourly slots of the local (CET) year starting 00:00 CET
(= 23:00 UTC previous day), assuming row i is hour i of the year (timestamps are 23:59:59.999 stamps = hour marks).
Output: docs/data/data_quality_reports/carbon_epfl_comparison.json
Run: PYTHONPATH=. cl/bin/python -I swiss/validation/compare_epfl_carbon.py
"""
import importlib.util
import json
import os
import sys

import numpy as np
import openpyxl
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
spec = importlib.util.spec_from_file_location('bc', os.path.join(ROOT, 'swiss', 'pipeline', 'build_carbon.py'))
BC = importlib.util.module_from_spec(spec); spec.loader.exec_module(BC)
XLSX = os.path.join(ROOT, 'data', 'raw', 'epfl', 'Swiss Mix 2016_2017.xlsx')
OUT = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'carbon_epfl_comparison.json')


def epfl(year):
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb[str(year)]
    rows = [r for r in ws.iter_rows(values_only=True)][1:]
    return np.array([r[3] for r in rows], dtype=float) * 1000.0  # kg -> g CO2eq/kWh


def stats(a, b):
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    s = pd.Series
    r = float(np.corrcoef(a, b)[0, 1])
    rs = float(s(a).corr(s(b), method='spearman'))
    slope = float(np.polyfit(b, a, 1)[0])
    return {'n': int(ok.sum()), 'mean_mine': float(a.mean()), 'mean_epfl': float(b.mean()), 'ratio_mean': float(a.mean() / b.mean()),
            'pearson': r, 'spearman': rs, 'slope_mine_per_epfl': slope}


def main():
    res = {}
    for year in (2016, 2017):
        out, _, _ = BC.build(str(year))
        mine = out.ci_consumption_lifecycle_g_per_kwh
        dom = out.ci_domestic_generation_lifecycle_g_per_kwh
        ref = epfl(year)
        n = min(len(mine), len(ref))
        idx = mine.index[:n]
        m, d, e = mine.to_numpy()[:n], dom.to_numpy()[:n], ref[:n]
        loc = idx.tz_convert('Europe/Zurich')
        frame = pd.DataFrame({'mine': m, 'dom': d, 'epfl': e}, index=idx)
        monthly = frame.resample('MS').mean()
        daily = frame.resample('1D').mean()
        diurnal = frame.groupby(loc.hour).mean()
        res[str(year)] = {
            'rows_mine': len(mine), 'rows_epfl': len(ref), 'missing_mine_hours': int(np.isnan(m).sum()),
            'hourly_consumption_vs_epfl': stats(m, e), 'hourly_domestic_vs_epfl': stats(d, e),
            'daily_consumption_vs_epfl': stats(daily.mine.to_numpy(), daily.epfl.to_numpy()),
            'monthly_means': {'mine': monthly.mine.round(1).tolist(), 'epfl': monthly.epfl.round(1).tolist()},
            'monthly_corr': float(np.corrcoef(monthly.mine.dropna(), monthly.epfl[monthly.mine.notna()])[0, 1]),
            'diurnal_means': {'mine': diurnal.mine.round(1).tolist(), 'epfl': diurnal.epfl.round(1).tolist()},
            'diurnal_corr': float(np.corrcoef(diurnal.mine, diurnal.epfl)[0, 1]),
            'diurnal_amplitude': {'mine': float(diurnal.mine.max() - diurnal.mine.min()), 'epfl': float(diurnal.epfl.max() - diurnal.epfl.min())},
            'coefficient_of_variation': {'mine': float(np.nanstd(m) / np.nanmean(m)), 'epfl': float(np.nanstd(e) / np.nanmean(e))},
            'neighbour_fallback_hours': int(out.neighbour_intensity_fallback_flag.sum()) if 'neighbour_intensity_fallback_flag' in out else None}
    json.dump(res, open(OUT, 'w'), indent=1)
    return res


if __name__ == '__main__':
    r = main()
    for y, v in r.items():
        print(y, 'hourly r', round(v['hourly_consumption_vs_epfl']['pearson'], 3), 'spearman', round(v['hourly_consumption_vs_epfl']['spearman'], 3),
              'ratio mean', round(v['hourly_consumption_vs_epfl']['ratio_mean'], 3), 'means', round(v['hourly_consumption_vs_epfl']['mean_mine'], 1), round(v['hourly_consumption_vs_epfl']['mean_epfl'], 1),
              '| monthly r', round(v['monthly_corr'], 3), '| diurnal r', round(v['diurnal_corr'], 3), '| domestic-only r', round(v['hourly_domestic_vs_epfl']['pearson'], 3), '| missing', v['missing_mine_hours'])
