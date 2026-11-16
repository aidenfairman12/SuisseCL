"""Task A9: validation checks for the Phase A district (what can honestly be checked; NOT calibration).

Checks: V1 electricity closure, V2 heat/storage balance, V3 stability, V4 no double counting vs measured totals,
V5 tariff arithmetic (independent 15-min recompute), V6 seasonality, V7 demand-weather timestamp alignment.
Output: docs/experiments/validation_reports/validation_phase_a.json
Run: PYTHONPATH=. cl/bin/python -I swiss/validation/validate_phase_a.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from citylearn.agents.baseline import ZeroActionBaselineAgent  # noqa: E402
from citylearn.agents.rbc import BasicRBC  # noqa: E402
from citylearn.citylearn import CityLearnEnv  # noqa: E402

SCHEMA = os.path.join(ROOT, 'swiss', 'datasets', 'swiss_district_2023', 'schema.json')
CAN = os.path.join(ROOT, 'data', 'canonical')
OUT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'validation_phase_a.json')
ROLES = ['SFH-low', 'SFH-mid', 'SFH-high', 'MFH-small', 'MFH-medium', 'MFH-large']


def run(agent_cls):
    env = CityLearnEnv(SCHEMA, central_agent=True)
    ag = agent_cls(env); obs, _ = env.reset()
    while not env.terminated:
        obs, *_ = env.step(ag.predict(obs))
    return env


def arr(x):
    return np.asarray(x, dtype=float)


def main():
    res = {}
    envs = {'zero_action': run(ZeroActionBaselineAgent), 'basic_rbc': run(BasicRBC)}
    # V1/V2/V3
    v1, v2, v3 = {}, {}, {}
    for name, env in envs.items():
        for b, role in zip(env.buildings, ROLES):
            net = arr(b.net_electricity_consumption)
            rec = arr(b.non_shiftable_load) + arr(b.heating_electricity_consumption) + arr(b.dhw_electricity_consumption)
            v1[f'{name}|{role}'] = {'max_abs_err_kwh': float(np.abs(net - rec).max()), 'sum_net': float(net.sum())}
            for tag, dem, dev, sto, to_sto, tank in (('heating', b.heating_demand, b.energy_from_heating_device, b.energy_from_heating_storage,
                                                       b.energy_from_heating_device_to_heating_storage, b.heating_storage),
                                                      ('dhw', b.dhw_demand, b.energy_from_dhw_device, b.energy_from_dhw_storage,
                                                       b.energy_from_dhw_device_to_dhw_storage, getattr(b, 'dhw_storage', None))):
                n = len(arr(dev))
                err = arr(dem)[:n] - arr(dev) - arr(sto)
                key = f'{name}|{role}|{tag}'
                v2[key] = {'max_abs_demand_closure_err_kwh': float(np.abs(err).max())}
                if tank is not None and getattr(tank, 'capacity', 0) and tank.capacity > 0:
                    soc = arr(tank.soc)
                    cap = tank.capacity
                    stored_change = (soc[-1] - soc[0]) * cap
                    loss = arr(to_sto).sum() - arr(sto).sum() - stored_change
                    v2[key].update({'tank_capacity_kwh': float(cap), 'soc_min': float(soc.min()), 'soc_max': float(soc.max()),
                                    'implied_loss_kwh': float(loss), 'implied_loss_share_of_charge': float(loss / max(arr(to_sto).sum(), 1e-9))})
                    v3[key] = {'soc_in_0_1': bool(soc.min() >= -1e-9 and soc.max() <= 1 + 1e-9)}
            v3[f'{name}|{role}|finite'] = bool(np.isfinite(net).all() and (net >= -1e-9).all())
    res['V1_electricity_closure'] = v1
    res['V2_heat_and_storage_balance'] = v2
    res['V3_stability'] = v3
    # V4 no double counting vs measured totals (SFH, zero action)
    v4 = {}
    env = envs['zero_action']
    for i in range(3):
        role = ROLES[i]
        h = pd.read_csv(os.path.join(CAN, 'hourly', f'{role}_2023_hourly.csv'))
        net = arr(env.buildings[i].net_electricity_consumption)
        meas = h['kwh_total_f'].to_numpy()[:len(net)]
        v4[role] = {'sim_net_kwh': float(net.sum()), 'measured_total_kwh': float(meas.sum()),
                    'rel_diff': float((net.sum() - meas.sum()) / meas.sum()), 'max_abs_hourly_diff': float(np.abs(net - meas).max())}
    res['V4_no_double_counting_SFH'] = v4
    # V5 tariff arithmetic: SFH-mid cost from 15-min data x 15-min tariff vs hourly cost
    q = pd.read_csv(os.path.join(CAN, 'quarter_hourly', 'SFH-mid_2023_15min.csv'), index_col='timestamp_utc', parse_dates=True)
    t = pd.read_csv(os.path.join(ROOT, 'data', 'raw', 'ekz', 'extracted', 'tariff_data.csv'), sep=';', usecols=['timestamp_utc', 'energy_standard', 'grid_standard'])
    t['timestamp_utc'] = pd.to_datetime(t.timestamp_utc, utc=True); t = t.set_index('timestamp_utc').reindex(q.index)
    c15 = float((q.kwh_total * (t.energy_standard + t.grid_standard) / 100).sum())
    h = pd.read_csv(os.path.join(CAN, 'hourly', 'SFH-mid_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    tar = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    ch = float((h.kwh_total * tar.total_chf_kwh).sum())
    res['V5_tariff_arithmetic_SFH-mid'] = {'cost_15min_chf': c15, 'cost_hourly_chf': ch, 'rel_diff': (ch - c15) / c15,
                                           'note': 'measured hours only (24 h gap excluded in both); excl. VAT and levies'}
    # V6 seasonality
    v6 = {}
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
    for role in ROLES:
        d = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
        m = d.resample('MS').agg({'e_hp_kwh': 'sum', 'heating_demand_kwh': 'sum'})
        tm = w.temp_c.resample('MS').mean()
        v6[role] = {'corr_monthly_hp_elec_vs_temp': float(np.corrcoef(m.e_hp_kwh, tm)[0, 1]),
                    'peak_month_heating_demand': int(m.heating_demand_kwh.idxmax().tz_convert('Europe/Zurich').month),
                    'summer_share_of_heating_demand_JJA': float(m.heating_demand_kwh.iloc[[5, 6, 7]].sum() / m.heating_demand_kwh.sum())}
    res['V6_seasonality'] = v6
    # V7 alignment: lag scan of hourly HP electricity vs temperature in Nov-Mar
    v7 = {}
    for role in ROLES:
        d = pd.read_csv(os.path.join(CAN, 'thermal', f'{role}_2023_thermal_hourly.csv'), index_col='timestamp_utc', parse_dates=True)
        e = d.e_hp_kwh; tt = w.temp_c
        winter = e.index.tz_convert('Europe/Zurich').month.isin([11, 12, 1, 2, 3])
        # remove diurnal mean to focus on weather-driven variation
        res_c = {}
        for lag in range(-4, 5):
            x = tt.shift(lag)[winter]; y = e[winter]
            ok = x.notna() & y.notna()
            res_c[lag] = float(np.corrcoef(x[ok], y[ok])[0, 1])
        best = min(res_c, key=lambda k: res_c[k])  # most negative correlation
        v7[role] = {'corr_by_lag_h': res_c, 'best_lag_h': best}
    res['V7_timestamp_alignment_demand_vs_temperature'] = v7
    # V8 carbon arithmetic: independent emissions from net import x carbon series; ratio vs CityLearn KPI
    ci = pd.read_csv(os.path.join(CAN, 'carbon_intensity_citylearn_2023.csv')).carbon_intensity.to_numpy()
    def emis(env):
        imp = np.sum([np.maximum(arr(b.net_electricity_consumption), 0) for b in env.buildings], axis=0)
        return float((imp * ci[:len(imp)]).sum())
    e0, e1 = emis(envs['zero_action']), emis(envs['basic_rbc'])
    kpi = envs['basic_rbc'].evaluate()
    k = kpi[(kpi['level'] == 'district') & (kpi['cost_function'] == 'carbon_emissions_total')]['value'].iloc[0]
    res['V8_carbon_arithmetic'] = {'zero_action_kg': e0, 'basic_rbc_kg': e1, 'ratio_independent': e1 / e0,
                                   'ratio_citylearn_kpi': float(k), 'abs_diff': abs(e1 / e0 - float(k)),
                                   'zero_action_mean_g_per_kwh': e0 / sum(float(np.maximum(arr(b.net_electricity_consumption), 0).sum()) for b in envs['zero_action'].buildings) * 1000}
    json.dump(res, open(OUT, 'w'), indent=1)
    return res


if __name__ == '__main__':
    r = main()
    for k in ('V1_electricity_closure', 'V2_heat_and_storage_balance'):
        print(k, 'max err', max(v.get('max_abs_err_kwh', v.get('max_abs_demand_closure_err_kwh', 0)) for v in r[k].values()))
    print('V3', all(v if isinstance(v, bool) else v['soc_in_0_1'] for v in r['V3_stability'].values()))
    print('V4', r['V4_no_double_counting_SFH'])
    print('V5', r['V5_tariff_arithmetic_SFH-mid'])
    print('V6', {k: (round(v['corr_monthly_hp_elec_vs_temp'], 3), v['peak_month_heating_demand'], round(v['summer_share_of_heating_demand_JJA'], 3)) for k, v in r['V6_seasonality'].items()})
    print('V8', r['V8_carbon_arithmetic'])
    print('V7 best lags', {k: v['best_lag_h'] for k, v in r['V7_timestamp_alignment_demand_vs_temperature'].items()})
    print('loss shares', {k: round(v['implied_loss_share_of_charge'], 3) for k, v in r['V2_heat_and_storage_balance'].items() if 'implied_loss_share_of_charge' in v and 'basic_rbc' in k})
