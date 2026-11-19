"""Task B3: assumed-PV scenario inputs (M-003). Writes, under data/canonical/pv/:
  pv_ac_w_per_kwp_2023_hourly.csv   inverter AC output per kWp in W/kW (CityLearn solar_generation convention), 8,760 hours
  pv_capacity_2023.json             per building and yield-to-demand ratio (0.5, 1.0, 1.5): kWp, cap, binding flag, annual yield
Classification: modeled (irradiance measured, conversion modeled) + assumed-parameter badge (D-021). No building has known PV
except by survey (SFH-low: no); SFH-mid and SFH-high are unknown (ISS-021), so every building gets the SCENARIO PV and the scenario
is "with assumed PV". Annual demand = non-shiftable load + heat-pump electricity under no control (ALG-001), from DER-009.
Run: cl/bin/python -I swiss/pipeline/build_pv.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.models.pv import PARAMS, SIZING, capacity_kwp, rooftop_cap_kwp, specific_yield_kwh_per_kwp  # noqa: E402

CAN = os.path.join(ROOT, 'data', 'canonical')
OUT = os.path.join(CAN, 'pv')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
LIVING_AREA_M2 = {'SFH-low': 220.0, 'SFH-mid': 166.0, 'SFH-high': 260.0}     # HEAPO survey, completion report section 3
UNITS = {'MFH-small': 5, 'MFH-medium': 14, 'MFH-large': 24}
RATIOS = (0.5, 1.0, 1.5)
PLAUSIBLE_YIELD = (900.0, 1250.0)   # kWh/kWp/a, assumed plausibility range for Swiss Mittelland, tilt 30 south; not verified against a source


def pv_ac_w_per_kwp(w):
    """AC output per kWp in W/kW for a weather frame with the columns of weather_klo_2023_hourly.csv (timestamp_utc, temp_c, ghi_wm2, diffuse_wm2).
    Phase C (WP1) calls this with scenario weather; the 2023 output is unchanged (regression test in swiss/tests/test_climate.py)."""
    y = specific_yield_kwh_per_kwp(w.timestamp_utc, w.ghi_wm2, w.diffuse_wm2, w.temp_c)
    return pd.DataFrame({'timestamp_utc': w.timestamp_utc, 'pv_ac_w_per_kwp': np.round(y * 1000.0, 4)}), y


def main():
    os.makedirs(OUT, exist_ok=True)
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    pv_df, y = pv_ac_w_per_kwp(w)
    annual = float(y.sum())
    pv_df.to_csv(os.path.join(OUT, 'pv_ac_w_per_kwp_2023_hourly.csv'), index=False)
    caps = {}
    for role in ROLES:
        d = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'))
        demand = float((d.non_shiftable_load_kwh + d.e_hp_kwh).sum())
        mfh = role.startswith('MFH')
        area = UNITS[role] * SIZING['floor_area_per_mfh_unit_m2'] if mfh else LIVING_AREA_M2[role]
        cap = rooftop_cap_kwp(area, mfh)
        caps[role] = {'annual_import_no_control_kwh': round(demand, 1), 'floor_area_m2': area, 'rooftop_cap_kwp': round(cap, 2), 'ratios': {}}
        for r in RATIOS:
            kwp, bind = capacity_kwp(demand, annual, r, cap)
            caps[role]['ratios'][str(r)] = {'kwp': round(kwp, 3), 'cap_binding': bind,
                                            'annual_pv_kwh': round(kwp * annual, 1), 'yield_to_demand_actual': round(kwp * annual / demand, 3)}
    meta = {'annual_specific_yield_kwh_per_kwp': round(annual, 1), 'plausible_range': PLAUSIBLE_YIELD,
            'in_plausible_range': bool(PLAUSIBLE_YIELD[0] <= annual <= PLAUSIBLE_YIELD[1]),
            'ghi_kwh_per_m2': round(float(w.ghi_wm2.sum()) / 1000.0, 1), 'model_params': PARAMS, 'sizing_params': SIZING,
            'classification': 'modeled + assumed-parameter badge', 'buildings': caps}
    json.dump(meta, open(os.path.join(OUT, 'pv_capacity_2023.json'), 'w'), indent=1)
    print(json.dumps({k: meta[k] for k in ('annual_specific_yield_kwh_per_kwp', 'ghi_kwh_per_m2', 'in_plausible_range')}))
    for role, c in caps.items():
        print(role, c['annual_import_no_control_kwh'], 'cap', c['rooftop_cap_kwp'], {r: (v['kwp'], v['cap_binding']) for r, v in c['ratios'].items()})


if __name__ == '__main__':
    main()
