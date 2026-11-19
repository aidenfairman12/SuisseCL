"""M-005 in CityLearn 3.3.0: a DynamicsBuilding whose indoor temperature follows the single-node RC model (swiss/models/rc_building.py).

Extension by subclassing (CityLearn itself is not edited). Mapping of CityLearn semantics:
  heating_demand[t]            = heat delivered to the room in step t (kWh_th per step = kW at 3600 s); set by the `heating_device` action as
                                 action x nominal electric power x COP(T_out), exactly as CityLearn's LSTM building does for its own demand.
  tank discharge                serves part of that demand (stock logic); the device supplies the rest plus tank charging.
  indoor_dry_bulb_temperature[t] = temperature at the END of step t after the heat of step t (RC exact step).
Solar input of the RC equation is global horizontal irradiance = direct (beam horizontal) + diffuse of the weather file.
"""
import numpy as np
from citylearn.building import DynamicsBuilding
from citylearn.dynamics import Dynamics

from swiss.models.rc_building import COOLING_MIN_OUTDOOR_C, PRIORS, step_temperature


class RCDynamics(Dynamics):
    def __init__(self, area_eff, filepath=None, **params):
        super().__init__()
        self.filepath = filepath                            # CityLearn's loader always passes a file path (LSTM weights); here it only documents the parameters
        self.area_eff = float(area_eff)
        self.params = {**PRIORS, **{k: v for k, v in params.items() if k in PRIORS}}
        self.temperature = self.params['setpoint_c']

    def reset(self):
        self.temperature = self.params['setpoint_c']


class RCDynamicsBuilding(DynamicsBuilding):
    @property
    def simulate_dynamics(self):
        return not self.ignore_dynamics

    def get_dynamics_input(self):
        return None

    def _update_dynamics_input(self):
        pass

    def update_cooling_demand(self, action):
        """Phase C cooling (M-006): a cooled building has the `cooling_or_heating_device` action (negative = cooling, CityLearn splits it into a cooling and a heating
        action in the same step); the cooling demand is the heat removed from the room, action x nominal power x cooling COP. Other buildings: no cooling (as in Phase B)."""
        if 'cooling_or_heating_device' in self.active_actions and self.simulate_dynamics:
            if self.energy_simulation.hvac_mode[self.time_step] in [1, 3]:
                t_out = float(self.weather.outdoor_dry_bulb_temperature[self.time_step])
                if t_out >= COOLING_MIN_OUTDOOR_C:
                    electric_power = float(action) * self.cooling_device.nominal_power * self._dataset_step_hours()
                    demand = self.cooling_device.get_max_output_power(t_out, heating=False, max_electric_power=electric_power)
                else:
                    demand = 0.0
            else:
                demand = 0.0
            self.energy_simulation.cooling_demand[self.time_step] = demand

    def update_heating_demand(self, action):
        if ('heating_device' in self.active_actions or 'cooling_or_heating_device' in self.active_actions) and self.simulate_dynamics:
            if self.energy_simulation.hvac_mode[self.time_step] in [2, 3]:
                electric_power = float(action) * self.heating_device.nominal_power * self._dataset_step_hours()
                demand = self.heating_device.get_max_output_power(self.weather.outdoor_dry_bulb_temperature[self.time_step],
                                                                  heating=True, max_electric_power=electric_power)
            else:
                demand = 0.0
            self.energy_simulation.heating_demand[self.time_step] = demand

    def update_indoor_dry_bulb_temperature(self):
        t = self.time_step
        w = self.weather
        ghi = float(w.direct_solar_irradiance[t]) + float(w.diffuse_solar_irradiance[t])
        q_kw = (float(self.energy_simulation.heating_demand[t]) - float(self.energy_simulation.cooling_demand[t])) / self._dataset_step_hours()    # cooling removes heat (zero in Phase B datasets)
        dyn = self.dynamics
        T = step_temperature(dyn.temperature, float(w.outdoor_dry_bulb_temperature[t]), ghi, q_kw, dyn.area_eff,
                             dt_s=3600.0 * self._dataset_step_hours(), p=dyn.params)
        dyn.temperature = float(T)
        series = self.energy_simulation.indoor_dry_bulb_temperature
        series[t] = T
        if t + 1 < series.shape[0]:
            series[t + 1] = T                                  # what the agent observes next, as CityLearn's LSTM building does
