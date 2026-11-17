"""Record one controller's full-year rollout of the Swiss district (contract v1, roadmap step 3 groundwork).

Uses the same environment, reward and controller factories as swiss/experiments/run_baselines.py and only READS CityLearn
properties after the episode, so the rollout (and every KPI in baselines_2023.csv) is unchanged. All arrays have one value
per simulated step (8,759 hourly steps; CityLearn does not simulate the final hour). Units: kWh per step (el = electrical,
th = thermal), CityLearn tank state of charge in 0..1.

Heat-flow semantics (CityLearn 3.3.0, verified by test_contract.py):
  heat pump output = energy_from_*_device (direct to demand) + positive tank energy_balance (into the tank)
  tank output to demand = negative tank energy_balance
  heat-pump electricity = heat pump output / COP(T_out)
  tank loss (efficiency + standby) = into tank - out of tank - change in stored energy   (exact by energy conservation)
"""
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.citylearn import CityLearnEnv  # noqa: E402

from swiss.experiments.rewards import SwissDistrictReward  # noqa: E402
from swiss.experiments.run_baselines import CONTROLLERS, SCHEMA  # noqa: E402

TANKS = ('heating', 'dhw')   # CityLearn names; exported as sh (space heating) and hw (hot water and other base load)


def _f(x):
    return np.asarray(x, dtype=float)


def record(controller):
    """Run one episode of `controller` (a key of run_baselines.CONTROLLERS). Returns a dict of numpy arrays."""
    env = CityLearnEnv(SCHEMA, central_agent=True, reward_function=SwissDistrictReward)
    agent = CONTROLLERS[controller](env)
    obs, _ = env.reset()
    rf = env.unwrapped.reward_function if hasattr(env, 'unwrapped') else env.reward_function
    acts, reward, parts = [], [], []
    while not env.terminated:
        a = agent.predict(obs)
        acts.append(np.ravel(np.asarray(a, dtype=float)))
        obs, r, terminated, truncated, _ = env.step(a)
        reward.append(float(np.sum(r)))
        t = rf.last_terms
        parts.append([-rf.weights[k] * t[k] / rf.scales[k] for k in ('cost', 'peak', 'ramp')])
        if terminated or truncated:
            break
    acts = np.array(acts)
    n = len(reward)
    out = {'n': n, 'reward': np.array(reward), 'reward_parts': np.array(parts),
           'reward_weights': dict(rf.weights), 'reward_scales': dict(rf.scales),
           'carbon_intensity_internal': _f(env.buildings[0].carbon_intensity.carbon_intensity)[:n],
           'buildings': []}
    k = 0
    for b in env.buildings:
        d = {}
        T = _f(b.weather.outdoor_dry_bulb_temperature)[:n]
        d['hp_sh_kwh_el'] = _f(b.heating_electricity_consumption)[:n]
        d['hp_hw_kwh_el'] = _f(b.dhw_electricity_consumption)[:n]
        d['household_kwh_el'] = _f(b.non_shiftable_load)[:n]
        d['net_kwh_el'] = _f(b.net_electricity_consumption)[:n]
        d['sh_demand_kwh_th'] = _f(b.heating_demand)[:n]
        d['hw_demand_kwh_th'] = _f(b.dhw_demand)[:n]
        d['cop_sh'] = np.array([b.heating_device.get_cop(t, heating=True) for t in T])
        d['cop_hw'] = np.array([b.dhw_device.get_cop(t, heating=True) for t in T])
        for cl, pre in (('heating', 'sh'), ('dhw', 'hw')):
            dev_out = _f(getattr(b, f'energy_from_{cl}_device'))[:n]
            to_tank = _f(getattr(b, f'energy_from_{cl}_device_to_{cl}_storage'))[:n]
            from_tank = _f(getattr(b, f'energy_from_{cl}_storage'))[:n]
            tank = getattr(b, f'{cl}_storage')
            soc = _f(tank.soc)[:n]
            cap = float(tank.capacity)
            stored = soc * cap
            prev = np.r_[float(tank.initial_soc) * cap, stored[:-1]]
            d[f'hp_{pre}_direct_kwh_th'] = dev_out
            d[f'hp_{pre}_to_tank_kwh_th'] = to_tank
            d[f'{pre}_tank_to_demand_kwh_th'] = from_tank
            d[f'{pre}_tank_loss_kwh_th'] = np.maximum(to_tank - from_tank - (stored - prev), 0.0)
            d[f'{pre}_tank_soc'] = soc
            d[f'{pre}_tank_capacity_kwh_th'] = cap
            d[f'{pre}_tank_action'] = np.full(n, np.nan)
        for a in b.active_actions:
            pre = {'heating_storage': 'sh', 'dhw_storage': 'hw'}[a]
            d[f'{pre}_tank_action'] = acts[:n, k]
            k += 1
        d['hp_sh_nominal_kw_el'] = float(b.heating_device.nominal_power)
        d['hp_hw_nominal_kw_el'] = float(b.dhw_device.nominal_power)
        out['buildings'].append(d)
    return out
