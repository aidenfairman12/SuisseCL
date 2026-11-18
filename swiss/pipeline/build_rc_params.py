"""B7: pooled per-m2 RC parameters (M-005) and per-building effective area (energy closure with the derived heat, D-038).
Output: data/canonical/rc/rc_params_2023.json   Run: cl/bin/python -I swiss/pipeline/build_rc_params.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.models.rc_building import PRIORS, SWEEP, calibrate_area, tau_seconds  # noqa: E402

CAN = os.path.join(ROOT, 'data', 'canonical')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
FLOOR = {'SFH-low': 220.0, 'SFH-mid': 166.0, 'SFH-high': 260.0, 'MFH-small': 400.0, 'MFH-medium': 1120.0, 'MFH-large': 1920.0}   # MFH: 80 m2 per unit (A-014)


def main():
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'))
    out = {'priors': PRIORS, 'sweep': SWEEP, 'time_constant_h': round(tau_seconds() / 3600.0, 1), 'buildings': {}}
    for role in ROLES:
        d = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'))
        heat = float(d.heating_demand_kwh.sum())
        a = calibrate_area(heat, w.temp_c.to_numpy(), w.ghi_wm2.fillna(0).to_numpy())
        out['buildings'][role] = {'annual_derived_heat_kwh_th': round(heat, 1), 'floor_area_m2': FLOOR[role], 'effective_area_m2': round(a, 1),
                                  'effective_over_floor': round(a / FLOOR[role], 2), 'H_w_per_k': round(PRIORS['H_w_per_k_m2'] * a, 1),
                                  'C_mj_per_k': round(PRIORS['C_j_per_k_m2'] * a / 1e6, 1)}
        print(role, out['buildings'][role])
    json.dump(out, open(os.path.join(CAN, 'rc', 'rc_params_2023.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
