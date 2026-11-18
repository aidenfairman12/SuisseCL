"""Task A7: build the CityLearn 3.3.0 dataset (schema.json + CSVs) for the six-building Swiss district, year 2023.

Inputs : data/canonical/thermal/*_2023_thermal_hourly.csv (DER-009), thermal_params.json,
         weather_klo_2023_hourly.csv (DER-007), tariff_ekz_standard_2023_hourly.csv (DER-008),
         optional carbon series (not yet available -> carbon_intensity null).
Output : swiss/datasets/swiss_district_2023/  (DER-010)
Conventions: D-007, D-014*, D-017a, D-018 (see docs/decisions/decision_log.md). CityLearn is not modified.

Run: cl/bin/python -I swiss/citylearn_build/build_dataset.py [--tank-scale 1.0]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']
UNITS = {'MFH-small': 5, 'MFH-medium': 14, 'MFH-large': 24}
WH_PER_L_K = 1.163
SETPOINT_C = 21.0
LOSS_COEFF = 0.003
TANK_EFF = 0.95
BATTERY = {'efficiency': 0.90, 'depth_of_discharge': 0.9, 'c_rate': 0.5}   # B4 assumptions A-016: ROUND-TRIP efficiency (CityLearn applies its square root in each direction, verified), usable share, power per kWh
DHW_MIN_KWH_DAY = 3.0


def buffer_kwh(role):
    litres = 300.0 if role.startswith('SFH') else 50.0 * UNITS[role]
    return litres * WH_PER_L_K * 10.0 / 1000.0


def main(tank_scale=1.0, out_name='swiss_district_2023', carbon_file=None, tank_eff=TANK_EFF, thermal_subdir='thermal', pv_ratio=None, battery_kwh_per_kwp=None):
    out_dir = os.path.join(ROOT, 'swiss', 'datasets', out_name)
    os.makedirs(out_dir, exist_ok=True)
    params = json.load(open(os.path.join(CAN, thermal_subdir, 'thermal_params.json')))
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    tar = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    idx = w.index
    loc = idx.tz_convert('Europe/Zurich')
    cal = pd.DataFrame({'month': loc.month, 'hour': loc.hour + 1, 'day_type': loc.dayofweek + 1,
                        'daylight_savings_status': np.array([int(t.dst().total_seconds() > 0) for t in loc])}, index=idx)

    def ahead(s, k):  # exact future value (perfect foresight); last k hours repeat the final value
        return s.shift(-k).ffill()

    weather = pd.DataFrame({
        'outdoor_dry_bulb_temperature': w.temp_c, 'outdoor_relative_humidity': w.rh_pct,
        'diffuse_solar_irradiance': w.diffuse_wm2.fillna(0.0).clip(lower=0),
        'direct_solar_irradiance': w.beam_horizontal_wm2.fillna(0.0).clip(lower=0)})
    for c in list(weather.columns):
        for k in (1, 2, 3):
            weather[f'{c}_predicted_{k}'] = ahead(weather[c], k)
    weather.to_csv(os.path.join(out_dir, 'weather.csv'), index=False)

    price = pd.DataFrame({'electricity_pricing': tar.total_chf_kwh})
    for k in (1, 2, 3):
        price[f'electricity_pricing_predicted_{k}'] = ahead(price['electricity_pricing'], k)
    price.to_csv(os.path.join(out_dir, 'pricing.csv'), index=False)

    carbon_ref = None
    if carbon_file:
        pd.read_csv(carbon_file).to_csv(os.path.join(out_dir, 'carbon_intensity.csv'), index=False)
        carbon_ref = 'carbon_intensity.csv'

    pv_w = pv_caps = None
    if pv_ratio is not None:   # B3: assumed-PV scenario (M-003); default build is unchanged
        pv_w = pd.read_csv(os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True).pv_ac_w_per_kwp
        assert (pv_w.index == idx).all()
        pv_caps = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))['buildings']

    if battery_kwh_per_kwp is not None:
        assert pv_ratio is not None, 'the battery rule is defined per kWp of PV (B4): pass --pv-ratio too'
    buildings, manifest = {}, {}
    for i, role in enumerate(ROLES, 1):
        d = pd.read_csv(os.path.join(CAN, thermal_subdir, f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
        assert (d.index == idx).all()
        name = f'Building_{i}'
        es = pd.DataFrame({
            'month': cal.month, 'hour': cal.hour, 'day_type': cal.day_type,
            'daylight_savings_status': cal.daylight_savings_status,
            'indoor_dry_bulb_temperature': SETPOINT_C,
            'non_shiftable_load': d.non_shiftable_load_kwh, 'dhw_demand': d.dhw_demand_kwh,
            'cooling_demand': 0.0, 'heating_demand': d.heating_demand_kwh, 'solar_generation': 0.0 if pv_w is None else pv_w.to_numpy(),
            'indoor_dry_bulb_temperature_cooling_set_point': 26.0,
            'indoor_dry_bulb_temperature_heating_set_point': SETPOINT_C, 'hvac_mode': 2})
        es.to_csv(os.path.join(out_dir, f'{name}.csv'), index=False)
        p = params[role]
        peak_sh = float(d.e_hp_space_heating_kwh.max()); peak_dhw = float(d.e_hp_baseline_kwh.max())
        sh_cap = buffer_kwh(role) * tank_scale
        mean_dhw_day = float(d.dhw_demand_kwh.sum() / 365.0)
        b = {'type': 'citylearn.building.Building', 'include': True, 'energy_simulation': f'{name}.csv',
             'weather': 'weather.csv', 'carbon_intensity': carbon_ref, 'pricing': 'pricing.csv',
             'inactive_observations': [], 'inactive_actions': [],
             'heating_device': {'type': 'citylearn.energy_model.HeatPump', 'autosize': False,
                                'attributes': {'nominal_power': round(peak_sh * 1.1, 4), 'efficiency': round(p['eta_sh'], 6),
                                               'target_heating_temperature': p['T_sup_sh_c'], 'target_cooling_temperature': 8.0}},
             'dhw_device': {'type': 'citylearn.energy_model.HeatPump', 'autosize': False,
                            'attributes': {'nominal_power': round(max(peak_dhw * 1.1, 0.01), 4), 'efficiency': round(p['eta_dhw'], 6),
                                           'target_heating_temperature': p['T_sup_dhw_c'], 'target_cooling_temperature': 8.0}},
             'heating_storage': {'type': 'citylearn.energy_model.StorageTank', 'autosize': False,
                                 'attributes': {'capacity': round(sh_cap, 4), 'efficiency': tank_eff, 'loss_coefficient': LOSS_COEFF}}}
        if pv_w is not None:
            kwp = pv_caps[role]['ratios'][str(float(pv_ratio))]['kwp']
            b['pv'] = {'type': 'citylearn.energy_model.PV', 'autosize': False, 'attributes': {'nominal_power': kwp}}
        bat_kwh = 0.0
        if battery_kwh_per_kwp is not None:   # B4: assumed battery per building (M-004), constant efficiency, no degradation
            bat_kwh = round(b['pv']['attributes']['nominal_power'] * battery_kwh_per_kwp, 4)
            eta = BATTERY['efficiency']
            b['electrical_storage'] = {'type': 'citylearn.energy_model.Battery', 'autosize': False,
                                       'attributes': {'capacity': bat_kwh, 'nominal_power': round(bat_kwh * BATTERY['c_rate'], 4),
                                                      'depth_of_discharge': BATTERY['depth_of_discharge'], 'efficiency': eta,
                                                      'loss_coefficient': 0.0, 'capacity_loss_coefficient': 0.0,
                                                      'power_efficiency_curve': [[0.0, eta], [1.0, eta]],
                                                      'capacity_power_curve': [[0.0, 1.0], [1.0, 1.0]]}}
        dhw_cap = 0.0
        if mean_dhw_day >= DHW_MIN_KWH_DAY:
            dhw_cap = mean_dhw_day * tank_scale
            b['dhw_storage'] = {'type': 'citylearn.energy_model.StorageTank', 'autosize': False,
                                'attributes': {'capacity': round(dhw_cap, 4), 'efficiency': tank_eff, 'loss_coefficient': LOSS_COEFF}}
        buildings[name] = b
        manifest[name] = {'role': role, 'heating_tank_kwh_th': round(sh_cap, 3), 'dhw_tank_kwh_th': round(dhw_cap, 3),
                          'hp_sh_nominal_kw': b['heating_device']['attributes']['nominal_power'],
                          'hp_dhw_nominal_kw': b['dhw_device']['attributes']['nominal_power']}
        if pv_w is not None:
            manifest[name]['pv_kwp'] = b['pv']['attributes']['nominal_power']
        if battery_kwh_per_kwp is not None:
            manifest[name]['battery_kwh'] = bat_kwh
    observations = {k: {'active': k in ('day_type', 'hour', 'outdoor_dry_bulb_temperature', 'net_electricity_consumption',
                                         'electricity_pricing', 'electricity_pricing_predicted_1', 'electricity_pricing_predicted_2',
                                         'electricity_pricing_predicted_3', 'heating_storage_soc', 'dhw_storage_soc') or (k == 'electrical_storage_soc' and battery_kwh_per_kwp is not None),
                    'shared_in_central_agent': k in ('day_type', 'hour', 'outdoor_dry_bulb_temperature', 'electricity_pricing',
                                                      'electricity_pricing_predicted_1', 'electricity_pricing_predicted_2',
                                                      'electricity_pricing_predicted_3')}
                    for k in ['day_type', 'hour', 'outdoor_dry_bulb_temperature', 'net_electricity_consumption', 'electricity_pricing',
                              'electricity_pricing_predicted_1', 'electricity_pricing_predicted_2', 'electricity_pricing_predicted_3',
                              'heating_storage_soc', 'dhw_storage_soc', 'electrical_storage_soc']}
    actions = {'heating_storage': {'active': True}, 'dhw_storage': {'active': True}, 'electrical_storage': {'active': battery_kwh_per_kwp is not None},
               'cooling_storage': {'active': False}, 'cooling_device': {'active': False}, 'heating_device': {'active': False},
               'cooling_or_heating_device': {'active': False}}
    schema = {'random_seed': 0, 'central_agent': True, 'simulation_start_time_step': 0, 'simulation_end_time_step': 8759,
              'episode_time_steps': None, 'rolling_episode_split': False, 'random_episode_split': False,
              'seconds_per_time_step': 3600.0, 'observations': observations, 'actions': actions,
              'reward_function': {'type': 'citylearn.reward_function.RewardFunction', 'attributes': {}},
              'buildings': buildings, 'root_directory': '.'}   # '.' = the schema's own folder (CityLearn 3.3.0 resolves it relative to schema.json), so the dataset is portable
    json.dump(schema, open(os.path.join(out_dir, 'schema.json'), 'w'), indent=1)
    json.dump(manifest, open(os.path.join(out_dir, 'build_manifest.json'), 'w'), indent=1)
    print(json.dumps(manifest, indent=1))
    return out_dir


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tank-scale', type=float, default=1.0)
    ap.add_argument('--out-name', default='swiss_district_2023')
    ap.add_argument('--carbon-file', default=None)
    ap.add_argument('--tank-eff', type=float, default=TANK_EFF)
    ap.add_argument('--thermal-subdir', default='thermal')
    ap.add_argument('--battery-kwh-per-kwp', type=float, default=None, help='B4: add an assumed battery of this many kWh per kWp of PV (needs --pv-ratio)')
    ap.add_argument('--pv-ratio', type=float, default=None, help='B3: add assumed PV with this yield-to-demand ratio (0.5, 1.0, 1.5)')
    a = ap.parse_args()
    main(a.tank_scale, a.out_name, a.carbon_file, a.tank_eff, a.thermal_subdir, a.pv_ratio, a.battery_kwh_per_kwp)
