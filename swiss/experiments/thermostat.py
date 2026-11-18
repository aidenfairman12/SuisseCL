"""Thermostat baseline for the RC scenarios (S3): heat pump heats to the setpoint every step, limited by its nominal output; tanks and battery idle.
The S3 counterpart of the zero-action baseline (with a thermal model, zero heating action would let the house cool down)."""
import numpy as np

from swiss.models.rc_building import heat_for_target


class ThermostatAgent:
    def __init__(self, env):
        self.env = env

    def predict(self, observations):
        env = self.env
        acts = []
        for b in env.buildings:
            for nm in b.active_actions:
                if nm != 'heating_device':
                    acts.append(0.0)
                    continue
                t = b.time_step
                w = b.weather
                ghi = float(w.direct_solar_irradiance[t]) + float(w.diffuse_solar_irradiance[t])
                dyn = b.dynamics
                q = heat_for_target(dyn.temperature, dyn.params['setpoint_c'], float(w.outdoor_dry_bulb_temperature[t]), ghi, dyn.area_eff, p=dyn.params)
                maxout = b.heating_device.get_max_output_power(float(w.outdoor_dry_bulb_temperature[t]), heating=True,
                                                               max_electric_power=b.heating_device.nominal_power)
                acts.append(float(np.clip(q / max(maxout, 1e-9), 0.0, 1.0)))
        return [acts]
