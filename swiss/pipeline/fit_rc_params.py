"""B7 step 1: what the derived heat demand can say about the single-node RC model (equation (1) of Melillo et al. 2021, J. Phys.: Conf. Ser. 2042 012009, as pasted by the owner):
    C_l dT/dt = -H (T - T_amb) + g I + L_emitter + L_internal
Quasi-steady daily regression over heating days (daily mean outdoor temperature < 12 C), where dT/dt averages out and C_l drops out:
    mean heat demand [kW] = a + b T_amb + c GHI    ->  H = -b (W/K), balance temperature = a / -b, effective solar aperture g_eff = -c (W per W/m2)
Only H and g_eff are (partly) identifiable from heat demand and weather; C_l needs indoor temperature dynamics and stays an assumption.
The heat demand is DERIVED (heat pump electricity x modeled COP, SPF-anchored, M-001), so H inherits the SPF assumption (ISS-028).
Output: data/canonical/rc/rc_quasi_steady_fit_2023.json   Run: cl/bin/python -I swiss/pipeline/fit_rc_params.py
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')
AREA = {'SFH-low': 220.0, 'SFH-mid': 166.0, 'SFH-high': 260.0, 'MFH-small': 400.0, 'MFH-medium': 1120.0, 'MFH-large': 1920.0}   # m2; MFH = units x 80 (A-014)
HEATING_DAY_MAX_C = 12.0


def main():
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    out = {}
    for role, area in AREA.items():
        d = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'), parse_dates=['timestamp_utc'])
        df = pd.DataFrame({'t': d.timestamp_utc, 'q': d.heating_demand_kwh.values, 'ta': w.temp_c.values, 'g': w.ghi_wm2.values})
        df['day'] = df.t.dt.tz_convert('Europe/Zurich').dt.date
        D = df.groupby('day').agg(q=('q', 'sum'), ta=('ta', 'mean'), g=('g', 'mean'))
        h = D[D.ta < HEATING_DAY_MAX_C]
        X = np.column_stack([np.ones(len(h)), h.ta, h.g]); y = (h.q / 24.0).to_numpy()
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        pred = X @ b
        r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        # bootstrap over days for the spread of H
        rng = np.random.default_rng(0); Hs = []
        for _ in range(300):
            ix = rng.integers(0, len(y), len(y)); bb = np.linalg.lstsq(X[ix], y[ix], rcond=None)[0]; Hs.append(-bb[1] * 1000)
        out[role] = {'floor_area_m2': area, 'heating_days': int(len(h)), 'H_w_per_k': round(float(-b[1] * 1000), 1), 'H_w_per_k_m2': round(float(-b[1] * 1000 / area), 3),
                     'H_bootstrap_p5_p95': [round(float(np.percentile(Hs, 5)), 1), round(float(np.percentile(Hs, 95)), 1)],
                     'balance_temp_c': round(float(b[0] / -b[1]), 1), 'g_eff_m2': round(float(-b[2] * 1000), 2), 'r2': round(float(r2), 3),
                     'annual_heat_kwh_th': round(float(d.heating_demand_kwh.sum()), 0)}
    meta = {'method': 'daily quasi-steady regression, heating days only', 'heating_day_max_c': HEATING_DAY_MAX_C,
            'note': 'C_l is not identifiable from heat demand; floor areas of MFH are assumed (80 m2 per unit); heat demand is derived (SPF-anchored)', 'fits': out}
    os.makedirs(os.path.join(CAN, 'rc'), exist_ok=True)
    json.dump(meta, open(os.path.join(CAN, 'rc', 'rc_quasi_steady_fit_2023.json'), 'w'), indent=1)
    for r, v in out.items():
        print(r, v)


if __name__ == '__main__':
    main()
