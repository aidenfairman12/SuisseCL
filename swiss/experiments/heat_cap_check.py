"""Does the thermostat saturate the space-heating heat pump? Per building and climate cell (heating-only, thermostat reference, full year).

For each building: rated electric power of the space-heating heat pump (schema), hours at that cap, hours and K*h below the heating set point and below the comfort lower
bound (rc_params), and the heat the thermostat asked for but the device could not deliver (requested - delivered, kWh thermal; requested = the heat that would hold the set point
in that step, as computed by climate_controllers.ThermostatAgentCool before it clips to the device's maximum output). Also the sizing source: rated = 1.1 x the highest hourly
space-heating electricity of the derived 2023 dataset (swiss/citylearn_build/build_dataset.py), listed as measured_peak_kw.
Run: PYTHONPATH=. cl/bin/python swiss/experiments/heat_cap_check.py      (about 2 minutes per cell). Output: swiss/experiments/heat_peak_results/heat_cap_check.json
"""
import json
import os
import warnings

import numpy as np

warnings.filterwarnings('ignore')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'swiss', 'experiments', 'heat_peak_results', 'heat_cap_check.json')
CELLS = ('hist_none', 'gwl2.0_none', 'gwl3.0_none')
CAP_TOL = 1e-3


def run_cell(cell):
    from swiss.experiments import climate_controllers as cc, climate_matrix as cm, oracle_climate as oc
    from swiss.models.rc_building import heat_for_target
    cm.ensure_datasets([cell])
    inp = oc.ClimateInputs(cell)
    raw = {}

    class Probe(cc.ThermostatAgentCool):
        def building_actions(self, b):
            out = super().building_actions(b)
            t = b.time_step
            w = b.weather
            ghi = float(w.direct_solar_irradiance[t]) + float(w.diffuse_solar_irradiance[t])
            t_out = float(w.outdoor_dry_bulb_temperature[t])
            dt_h = b._dataset_step_hours()
            dyn = b.dynamics
            q = max(heat_for_target(dyn.temperature, dyn.params['setpoint_c'], t_out, ghi, dyn.area_eff, dt_s=3600.0 * dt_h, p=dyn.params), 0.0) * dt_h
            maxout = b.heating_device.get_max_output_power(t_out, heating=True, max_electric_power=b.heating_device.nominal_power * dt_h)
            raw.setdefault(b.name, []).append((q, maxout))
            return out

    env = cm.rollout_year(inp, lambda e: Probe(e))
    res = {}
    for role, b in zip(inp.roles, env.buildings):
        el = np.asarray(b.heating_electricity_consumption, dtype=float)
        nom = float(b.heating_device.nominal_power)
        n = len(el)
        T = np.asarray(b.indoor_dry_bulb_temperature, dtype=float)[:n]
        sp, lo = float(b.dynamics.params['setpoint_c']), float(b.dynamics.params['comfort_lower_c'])
        q, mx = np.array(raw[b.name][:n]).T
        res[role] = {'rated_kw': nom, 'hours_at_cap': int((el >= nom * (1 - CAP_TOL)).sum()), 'peak_kw': float(el.max()),
                     'setpoint_c': sp, 'comfort_lower_c': lo, 'min_indoor_c': float(T.min()),
                     'hours_below_setpoint': int((T < sp - 0.05).sum()), 'kh_below_setpoint': float(np.maximum(sp - T, 0).sum()),
                     'hours_below_comfort_lower': int((T < lo).sum()), 'kh_below_comfort_lower': float(np.maximum(lo - T, 0).sum()),
                     'hours_demand_above_capacity': int((q > mx * (1 + CAP_TOL)).sum()), 'unmet_heat_kwh_th': float(np.maximum(q - mx, 0).sum()),
                     'requested_heat_kwh_th': float(q.sum())}
    return res


def main():
    out = {'cells': {c: run_cell(c) for c in CELLS}, 'rated_rule': 'rated = 1.1 x highest hourly space-heating electricity of the derived 2023 dataset (build_dataset.py)'}
    out['sources'] = ['swiss/citylearn_build/build_dataset.py', 'swiss/datasets/climate/hist_none/schema.json', 'swiss/datasets/climate/hist_none/rc_params.json']
    json.dump(out, open(OUT, 'w'), indent=1)
    for c, r in out['cells'].items():
        for role, v in r.items():
            print(c, role, {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items() if k in ('rated_kw', 'hours_at_cap', 'hours_below_setpoint', 'kh_below_setpoint', 'hours_below_comfort_lower', 'unmet_heat_kwh_th', 'hours_demand_above_capacity')}, flush=True)


if __name__ == '__main__':
    main()
