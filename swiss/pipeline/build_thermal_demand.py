"""Task A5: derive heating and DHW thermal demand (model M-001, D-014) for the six buildings.

Inputs : data/canonical/hourly/<role>_2023_hourly.csv (DER-005), weather_klo_2023_hourly.csv (DER-007)
Outputs: data/canonical/thermal/<role>_2023_thermal_hourly.csv (DER-009), thermal_params.json,
         docs/data/data_quality_reports/qc_thermal_2023.json

All thermal quantities are DERIVED (electricity x modeled COP), not measured.
Parameters (D-014d): supply T: SH 35 C (SFH floor heating) / 45 C (MFH assumption), DHW 55 C;
SPF targets (Arpagaus et al. 2023, IEA HPC paper 478, Table 1): SFH SH-only 3.7; MFH combined 3.1 (renovation
class); DHW-mode SPF 2.8 for all.  eta calibrated per building (annual).

Run: cl/bin/python -I swiss/pipeline/build_thermal_demand.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.models.heat_pump import calibrate_eta, cop, split_baseline  # noqa: E402

CAN = os.path.join(ROOT, 'data', 'canonical')
QC = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_thermal_2023.json')
AREA = {'SFH-low': 220.0, 'SFH-mid': 166.0, 'SFH-high': 260.0}  # HEAPO survey living area (m2)
T_SH = {'SFH': 35.0, 'MFH': 45.0}
T_DHW = 55.0
SPF_DHW = 2.8
SPF_TARGET = {'SFH': ('SH', 3.7), 'MFH': ('SH+DHW', 3.1)}
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']


def r2_linear(x, y):
    X = np.c_[np.ones(len(x)), x]
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    res = y - X @ b
    return float(1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum())


def solve_eta_sh_combined(e_sh, e_dhw, t, t_sh, eta_dhw, target):
    tot = e_sh.sum() + e_dhw.sum()
    q_dhw = (e_dhw * cop(t, eta_dhw, T_DHW)).sum()
    lo, hi = 0.05, 1.0
    f = lambda eta: ((e_sh * cop(t, eta, t_sh)).sum() + q_dhw) / tot - target
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


def run(spf_scale=1.0, write=True, out_subdir='thermal', t_sh=None):
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    t_sh_map = t_sh or T_SH
    out, qc = {}, {}
    for role in ROLES:
        kind = role[:3]
        h = pd.read_csv(os.path.join(CAN, 'hourly', f'{role}_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
        e = h['kwh_hp_f'] if 'kwh_hp_f' in h else h['kwh_hp']
        t = w.temp_c.reindex(e.index)
        base, sh, B = split_baseline(e, None, t)
        e_d, e_s = base.to_numpy(), sh.to_numpy()
        mode, target = SPF_TARGET[kind]
        target = target * spf_scale
        eta_dhw = calibrate_eta(e_d, t.to_numpy(), T_DHW, SPF_DHW * spf_scale)
        if mode == 'SH':
            eta_sh = calibrate_eta(e_s, t.to_numpy(), t_sh_map[kind], target)
        else:
            eta_sh = solve_eta_sh_combined(e_s, e_d, t.to_numpy(), t_sh_map[kind], eta_dhw, target)
        cop_sh = cop(t.to_numpy(), eta_sh, t_sh_map[kind])
        cop_dhw = cop(t.to_numpy(), eta_dhw, T_DHW)
        q_sh, q_dhw = e_s * cop_sh, e_d * cop_dhw
        if kind == 'SFH':
            nonshift = h['kwh_other_f']
            nonshift_class = 'measured (HEAPO Other; includes EWH DHW electricity where present (D-014a); SFH-low may include EV charging); 24 h synthetic fill on 2023-10-29 (D-011)'
        else:
            nonshift = h['kwh_common_areas_measured'] + h['kwh_apartments_synthetic']
            nonshift_class = 'measured common areas + SYNTHETIC apartment composite (D-006, D-015)'
        d = pd.DataFrame({'e_hp_kwh': e.to_numpy(), 'e_hp_baseline_kwh': e_d, 'e_hp_space_heating_kwh': e_s,
                          'outdoor_temp_c': t.to_numpy(), 'cop_space_heating': cop_sh, 'cop_baseline_dhw': cop_dhw,
                          'heating_demand_kwh': q_sh, 'dhw_demand_kwh': q_dhw,
                          'non_shiftable_load_kwh': nonshift.to_numpy(),
                          'gap_filled_flag': h['gap_filled_flag'].to_numpy() if 'gap_filled_flag' in h else 0}, index=e.index)
        out[role] = d
        # checks
        day = d.resample('1D').agg({'e_hp_kwh': 'sum', 'heating_demand_kwh': 'sum', 'dhw_demand_kwh': 'sum', 'outdoor_temp_c': 'mean'})
        cold = day[day.outdoor_temp_c < 12]
        hdd = np.maximum(15.0 - cold.outdoor_temp_c.to_numpy(), 0)
        qtot = (cold.heating_demand_kwh + cold.dhw_demand_kwh).to_numpy()
        qc[role] = {'mode_target': mode, 'spf_target': target, 'eta_sh': eta_sh, 'eta_dhw': eta_dhw, 'T_sup_sh_c': t_sh_map[kind],
                    'baseline_kwh_per_day_B': B, 'baseline_share_of_hp_electricity': float(e_d.sum() / np.nansum(e)),
                    'annual_hp_electricity_kwh': float(np.nansum(e)), 'annual_heating_demand_kwh': float(q_sh.sum()),
                    'annual_dhw_demand_kwh': float(q_dhw.sum()),
                    'implied_spf_sh': float(q_sh.sum() / e_s.sum()), 'implied_spf_dhw': float(q_dhw.sum() / e_d.sum()),
                    'implied_spf_combined': float((q_sh.sum() + q_dhw.sum()) / np.nansum(e)),
                    'cop_sh_range': [float(np.nanmin(cop_sh[e_s > 0])), float(np.nanmax(cop_sh[e_s > 0]))] if (e_s > 0).any() else None,
                    'negative_values': int((d[['heating_demand_kwh', 'dhw_demand_kwh']] < 0).sum().sum()),
                    'nan_values': int(d.isna().sum().sum()),
                    'r2_daily_electricity_vs_hdd_cold_days': r2_linear(hdd, cold.e_hp_kwh.to_numpy()),
                    'r2_daily_derived_heat_vs_hdd_cold_days': r2_linear(hdd, qtot),
                    'cold_days_n': int(len(cold))}
        if role in AREA:
            qc[role]['annual_space_heating_kwh_per_m2'] = float(q_sh.sum() / AREA[role])
            qc[role]['annual_total_heat_kwh_per_m2'] = float((q_sh.sum() + q_dhw.sum()) / AREA[role])
        qc[role]['nonshiftable_classification'] = nonshift_class
    if write:
        os.makedirs(os.path.join(CAN, out_subdir), exist_ok=True)
        for role, d in out.items():
            d.to_csv(os.path.join(CAN, out_subdir, f'{role}_2023_thermal_hourly.csv'), index_label='timestamp_utc')
        json.dump({r: {k: v for k, v in q.items() if k in ('eta_sh', 'eta_dhw', 'T_sup_sh_c', 'mode_target', 'spf_target')}
                   | {'T_sup_dhw_c': T_DHW, 'spf_dhw': SPF_DHW} for r, q in qc.items()},
                  open(os.path.join(CAN, out_subdir, 'thermal_params.json'), 'w'), indent=1)
    return out, qc


if __name__ == '__main__':
    _, qc = run()
    sens = {}
    for name, scale in (('spf_x0.81 (~3.0 on 3.7)', 3.0 / 3.7), ('spf_x1.08 (~4.0 on 3.7)', 4.0 / 3.7)):
        _, q2 = run(spf_scale=scale, write=False)
        sens[name] = {r: round(q2[r]['annual_heating_demand_kwh'] + q2[r]['annual_dhw_demand_kwh']) for r in ROLES}
    qc['sensitivity_total_heat_kwh'] = sens
    qc['reference_total_heat_kwh'] = {r: round(qc[r]['annual_heating_demand_kwh'] + qc[r]['annual_dhw_demand_kwh']) for r in ROLES}
    json.dump(qc, open(QC, 'w'), indent=1)
    for r in ROLES:
        q = qc[r]
        print(r, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in q.items() if k not in ('nonshiftable_classification',)})
    print(json.dumps({k: qc[k] for k in ('reference_total_heat_kwh', 'sensitivity_total_heat_kwh')}, indent=1))
