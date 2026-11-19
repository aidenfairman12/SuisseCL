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
sys.path.insert(0, ROOT)
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


def main(tank_scale=1.0, out_name='swiss_district_2023', carbon_file=None, tank_eff=TANK_EFF, thermal_subdir='thermal', pv_ratio=None, battery_kwh_per_kwp=None, rc=False, q15=False,
         weather_file=None, pv_file=None, cooled_buildings=(), climate_scenario=None):
    out_dir = os.path.join(ROOT, 'swiss', 'datasets', out_name)
    os.makedirs(out_dir, exist_ok=True)
    params = json.load(open(os.path.join(CAN, thermal_subdir, 'thermal_params.json')))
    # B2: q15 = 900 s steps from the 15-minute pipeline (data/canonical/q15, swiss/pipeline/build_15min.py); the default stays the hourly dataset
    dt_h = 0.25 if q15 else 1.0
    qd = os.path.join(CAN, 'q15')
    # Phase C (WP2): scenario weather / PV files (hourly, same columns and 2023 time stamps as the canonical ones) and cooled buildings; defaults leave every Phase A and B build unchanged
    assert weather_file is None or not q15, 'scenario weather files are hourly (Phase C)'
    cooled_buildings = tuple(cooled_buildings)
    assert all(r in ROLES for r in cooled_buildings), f'unknown role in {cooled_buildings}'
    assert not cooled_buildings or rc, 'cooling needs the RC thermal model (--rc)'
    w = pd.read_csv(weather_file if weather_file else (os.path.join(qd, 'weather_klo_2023_15min.csv') if q15 else os.path.join(CAN, 'weather_klo_2023_hourly.csv')), index_col='timestamp_utc', parse_dates=True)
    tar = pd.read_csv(os.path.join(qd, 'tariff_ekz_standard_2023_15min.csv') if q15 else os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    idx = w.index
    loc = idx.tz_convert('Europe/Zurich')
    cal = pd.DataFrame({'month': loc.month, 'hour': loc.hour + 1, 'day_type': loc.dayofweek + 1,
                        'daylight_savings_status': np.array([int(t.dst().total_seconds() > 0) for t in loc])}, index=idx)
    if q15:
        cal['minutes'] = loc.minute
    loss_coeff = LOSS_COEFF      # per HOUR: CityLearn's StorageDevice.loss_coefficient property rescales it to the step length itself (1 - (1 - c) ** step_hours)

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
        pv_w = pd.read_csv(pv_file if pv_file else (os.path.join(qd, 'pv_ac_w_per_kwp_2023_15min.csv') if q15 else os.path.join(CAN, 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv')), index_col='timestamp_utc', parse_dates=True).pv_ac_w_per_kwp
        assert (pv_w.index == idx).all()
        pv_caps = json.load(open(os.path.join(CAN, 'pv', 'pv_capacity_2023.json')))['buildings']

    if battery_kwh_per_kwp is not None:
        assert pv_ratio is not None, 'the battery rule is defined per kWp of PV (B4): pass --pv-ratio too'
    rc_params = None
    if rc:   # B7: single-node RC thermal model (M-005, D-038); per-building effective area from the energy closure
        from swiss.models.rc_building import simulate_ideal
        rc_params = json.load(open(os.path.join(CAN, 'rc', 'rc_params_2023.json')))
        rc_ghi = (w.beam_horizontal_wm2.fillna(0.0).clip(lower=0) + w.diffuse_wm2.fillna(0.0).clip(lower=0)).to_numpy()
    buildings, manifest = {}, {}
    for i, role in enumerate(ROLES, 1):
        d = pd.read_csv(os.path.join(qd, 'thermal', f'{role}_2023_thermal_15min.csv') if q15 else os.path.join(CAN, thermal_subdir, f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
        assert (d.index == idx).all()
        dh = pd.read_csv(os.path.join(CAN, thermal_subdir, f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)   # device sizes always from the hourly series
        name = f'Building_{i}'
        rc_q = rc_T = None
        if rc:
            rc_q, rc_T = simulate_ideal(rc_params['buildings'][role]['effective_area_m2'], w.temp_c.to_numpy(), rc_ghi, dt_s=3600.0 * dt_h)
            rc_q = rc_q * dt_h                      # kW -> kWh per step
        es = pd.DataFrame({
            'month': cal.month, 'hour': cal.hour, 'day_type': cal.day_type,
            'daylight_savings_status': cal.daylight_savings_status,
            'indoor_dry_bulb_temperature': SETPOINT_C if rc_T is None else rc_T,
            'non_shiftable_load': d.non_shiftable_load_kwh, 'dhw_demand': d.dhw_demand_kwh,
            'cooling_demand': 0.0, 'heating_demand': d.heating_demand_kwh if rc_q is None else rc_q, 'solar_generation': 0.0 if pv_w is None else pv_w.to_numpy(),
            'indoor_dry_bulb_temperature_cooling_set_point': 26.0,
            'indoor_dry_bulb_temperature_heating_set_point': SETPOINT_C, 'hvac_mode': 3 if role in cooled_buildings else 2})
        if q15:
            es['minutes'] = cal.minutes
        es.to_csv(os.path.join(out_dir, f'{name}.csv'), index=False)
        p = params[role]
        # device size = 1.1 x the highest power seen at the dataset's own resolution (kW): the 15-minute series has higher power peaks than the hourly one, and a device
        # sized on hourly peaks could not supply the derived 15-minute heat demand (the 15-minute exact optimum was infeasible in that case)
        src = d if q15 else dh
        peak_sh = float(src.e_hp_space_heating_kwh.max() / dt_h); peak_dhw = float(src.e_hp_baseline_kwh.max() / dt_h)
        sh_cap = buffer_kwh(role) * tank_scale
        mean_dhw_day = float(dh.dhw_demand_kwh.sum() / 365.0)
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
                                 'attributes': {'capacity': round(sh_cap, 4), 'efficiency': tank_eff, 'loss_coefficient': loss_coeff}}}
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
                                'attributes': {'capacity': round(dhw_cap, 4), 'efficiency': tank_eff, 'loss_coefficient': loss_coeff}}
        if role in cooled_buildings:   # Phase C: reversible heat pump = a cooling device of the same rating, efficiency and supply temperature as the heating device (A-040)
            b['cooling_device'] = {'type': 'citylearn.energy_model.HeatPump', 'autosize': False, 'attributes': dict(b['heating_device']['attributes'])}
            b['inactive_actions'] = ['heating_device']          # cooled buildings use the combined action: negative = cooling, positive = heating (CityLearn forbids both)
        elif cooled_buildings:
            b['inactive_actions'] = ['cooling_or_heating_device']
        if rc:
            b['type'] = 'swiss.citylearn_build.rc_dynamics.RCDynamicsBuilding'
            b['dynamics'] = {'type': 'swiss.citylearn_build.rc_dynamics.RCDynamics',
                             'attributes': {'area_eff': rc_params['buildings'][role]['effective_area_m2'], 'filename': 'rc_params.json'}}
        buildings[name] = b
        manifest[name] = {'role': role, 'heating_tank_kwh_th': round(sh_cap, 3), 'dhw_tank_kwh_th': round(dhw_cap, 3),
                          'hp_sh_nominal_kw': b['heating_device']['attributes']['nominal_power'],
                          'hp_dhw_nominal_kw': b['dhw_device']['attributes']['nominal_power']}
        if cooled_buildings:
            manifest[name]['cooled'] = role in cooled_buildings
            if role in cooled_buildings:
                manifest[name]['cooling_device_nominal_kw'] = b['cooling_device']['attributes']['nominal_power']
        if pv_w is not None:
            manifest[name]['pv_kwp'] = b['pv']['attributes']['nominal_power']
        if battery_kwh_per_kwp is not None:
            manifest[name]['battery_kwh'] = bat_kwh
    observations = {k: {'active': k in ('day_type', 'hour', 'outdoor_dry_bulb_temperature', 'net_electricity_consumption',
                                         'electricity_pricing', 'electricity_pricing_predicted_1', 'electricity_pricing_predicted_2',
                                         'electricity_pricing_predicted_3', 'heating_storage_soc', 'dhw_storage_soc') or (k == 'electrical_storage_soc' and battery_kwh_per_kwp is not None) or (k == 'indoor_dry_bulb_temperature' and rc),
                    'shared_in_central_agent': k in ('day_type', 'hour', 'outdoor_dry_bulb_temperature', 'electricity_pricing',
                                                      'electricity_pricing_predicted_1', 'electricity_pricing_predicted_2',
                                                      'electricity_pricing_predicted_3')}
                    for k in ['day_type', 'hour', 'outdoor_dry_bulb_temperature'] + (['indoor_dry_bulb_temperature'] if rc else []) + ['net_electricity_consumption', 'electricity_pricing',
                              'electricity_pricing_predicted_1', 'electricity_pricing_predicted_2', 'electricity_pricing_predicted_3',
                              'heating_storage_soc', 'dhw_storage_soc', 'electrical_storage_soc']}
    actions = {'heating_storage': {'active': True}, 'dhw_storage': {'active': True}, 'electrical_storage': {'active': battery_kwh_per_kwp is not None},
               'cooling_storage': {'active': False}, 'cooling_device': {'active': False}, 'heating_device': {'active': rc},
               'cooling_or_heating_device': {'active': bool(cooled_buildings)}}
    schema = {'random_seed': 0, 'central_agent': True, 'simulation_start_time_step': 0, 'simulation_end_time_step': len(idx) - 1,
              'episode_time_steps': None, 'rolling_episode_split': False, 'random_episode_split': False,
              'seconds_per_time_step': 3600.0 * dt_h, 'observations': observations, 'actions': actions,
              'reward_function': {'type': 'citylearn.reward_function.RewardFunction', 'attributes': {}},
              'buildings': buildings, 'root_directory': '.'}   # '.' = the schema's own folder (CityLearn 3.3.0 resolves it relative to schema.json), so the dataset is portable
    json.dump(schema, open(os.path.join(out_dir, 'schema.json'), 'w'), indent=1)
    json.dump(manifest, open(os.path.join(out_dir, 'build_manifest.json'), 'w'), indent=1)
    if climate_scenario is not None or weather_file or pv_file or cooled_buildings:   # Phase C: what this dataset is made of (kept outside build_manifest.json, which lists buildings only)
        json.dump({'climate_scenario': climate_scenario, 'weather_file': os.path.relpath(weather_file, ROOT) if weather_file else None,
                   'pv_file': os.path.relpath(pv_file, ROOT) if pv_file else None, 'cooled_buildings': list(cooled_buildings), 'pv_ratio': pv_ratio,
                   'battery_kwh_per_kwp': battery_kwh_per_kwp, 'rc': rc, 'cooling_set_point_c': 26.0, 'cooling_device_supply_c': 8.0},
                  open(os.path.join(out_dir, 'build_meta.json'), 'w'), indent=1)
    if rc:
        json.dump(rc_params, open(os.path.join(out_dir, 'rc_params.json'), 'w'), indent=1)
    print(json.dumps(manifest, indent=1))
    return out_dir


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tank-scale', type=float, default=1.0)
    ap.add_argument('--out-name', default='swiss_district_2023')
    ap.add_argument('--carbon-file', default=None)
    ap.add_argument('--tank-eff', type=float, default=TANK_EFF)
    ap.add_argument('--thermal-subdir', default='thermal')
    ap.add_argument('--q15', action='store_true', help='B2: 900 s steps from data/canonical/q15 (build_15min.py)')
    ap.add_argument('--rc', action='store_true', help='B7: single-node RC thermal model per building (scenario S3)')
    ap.add_argument('--battery-kwh-per-kwp', type=float, default=None, help='B4: add an assumed battery of this many kWh per kWp of PV (needs --pv-ratio)')
    ap.add_argument('--pv-ratio', type=float, default=None, help='B3: add assumed PV with this yield-to-demand ratio (0.5, 1.0, 1.5)')
    ap.add_argument('--weather-file', default=None, help='Phase C: hourly weather csv with the columns of data/canonical/weather_klo_2023_hourly.csv (scenario weather)')
    ap.add_argument('--pv-file', default=None, help='Phase C: hourly per-kWp PV csv with the column of data/canonical/pv/pv_ac_w_per_kwp_2023_hourly.csv')
    ap.add_argument('--cooled-buildings', nargs='*', default=[], help='Phase C: roles with a cooling device (needs --rc), e.g. MFH-small')
    ap.add_argument('--climate-scenario', default=None, help='label recorded in build_meta.json')
    a = ap.parse_args()
    main(a.tank_scale, a.out_name, a.carbon_file, a.tank_eff, a.thermal_subdir, a.pv_ratio, a.battery_kwh_per_kwp, a.rc, a.q15, a.weather_file, a.pv_file, a.cooled_buildings, a.climate_scenario)
