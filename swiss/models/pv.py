"""M-003 PV yield model (Phase B, task B3), built on pvlib 0.16.1: hourly AC energy per kWp from MeteoSwiss global and diffuse irradiance.

Chain (all pvlib functions; parameters are assumptions or PVWatts defaults, see `PARAMS` and docs/models/parameter_registry.csv):
  1. `solarposition.get_solarposition` (NREL SPA) at the interval midpoint for Zurich/Kloten.
  2. Direct normal irradiance from GHI and DHI with `irradiance.dni` (no measured DNI is available, ISS-005).
  3. `irradiance.get_total_irradiance` on a south-facing plane, tilt 30 deg, Perez transposition (all-sites composite 1990),
     extraterrestrial radiation and relative airmass from pvlib, ground albedo 0.20.
  4. `temperature.sapm_cell` (open rack, glass/glass parameters), constant wind speed assumed (no wind in the weather file),
     `pvsystem.pvwatts_dc` (gamma -0.4 %/K), `pvsystem.pvwatts_losses` with the PVWatts default loss items (14.08 %), and
     `inverter.pvwatts` (nominal efficiency 0.96, DC/AC ratio 1.2 so peaks above 1/1.2 of kWp are clipped).
Not modelled: shading from the actual surroundings, horizon, snow beyond the loss item, module degradation, real wind. Results are
modeled (D-021) and depend on assumed parameters; the annual specific yield is a plausibility check, not a validation against
measured PV output.

Input timestamps are the START of the hour (UTC), as in weather_klo_2023_hourly.csv (D-009); irradiance is the hourly mean,
so the sun position is taken at start + 30 min.
"""
import numpy as np
import pandas as pd
from pvlib import atmosphere, inverter, irradiance, pvsystem, solarposition, temperature

PARAMS = {
    'latitude_deg': 47.4793, 'longitude_deg': 8.5371, 'altitude_m': 426.0,   # Zurich/Kloten station, approximate public metadata, unverified
    'tilt_deg': 30.0, 'azimuth_deg': 180.0,            # south; assumption (B3 plan 4.3)
    'albedo': 0.20,                                    # assumption
    'perez_model': 'allsitescomposite1990',
    'sapm_open_rack_glass_glass': True,                # temperature model parameters from pvlib's SAPM table
    'wind_speed_ms': 2.0,                              # assumed constant (PVWatts convention); no wind data in the weather file
    'gamma_pdc_per_k': -0.004,                         # typical crystalline silicon, PVWatts default
    'losses_percent': 'pvwatts_default',               # pvsystem.pvwatts_losses() defaults, 14.08 %
    'inverter_eta_nom': 0.96, 'dc_ac_ratio': 1.2,      # PVWatts defaults
}


def _losses_fraction():
    return pvsystem.pvwatts_losses() / 100.0


def specific_yield_kwh_per_kwp(ts_start_utc, ghi_wm2, dhi_wm2, temp_c, params=None, step_minutes=60):
    """Mean AC power per kWp (DC nameplate) over the interval starting at ts_start_utc, in kW/kWp; for hourly steps this equals kWh/kWp per hour.
    Zero when the sun is below the horizon. `step_minutes` sets the interval length (60, or 15 for the 15-minute pipeline); irradiance is the mean over that interval."""
    p = dict(PARAMS, **(params or {}))
    ts = pd.DatetimeIndex(ts_start_utc)
    if ts.tz is None:
        ts = ts.tz_localize('UTC')
    mid = ts + pd.Timedelta(minutes=step_minutes / 2.0)
    ghi = pd.Series(np.clip(np.nan_to_num(np.asarray(ghi_wm2, dtype=float)), 0, None), index=mid)
    dhi = pd.Series(np.clip(np.nan_to_num(np.asarray(dhi_wm2, dtype=float)), 0, None), index=mid)
    dhi = np.minimum(dhi, ghi)
    ta = pd.Series(np.asarray(temp_c, dtype=float), index=mid)
    sp = solarposition.get_solarposition(mid, p['latitude_deg'], p['longitude_deg'], altitude=p['altitude_m'])
    zen = sp['apparent_zenith']
    dni = irradiance.dni(ghi, dhi, zen).fillna(0.0).clip(lower=0.0)
    dni_extra = irradiance.get_extra_radiation(mid)
    am = atmosphere.get_relative_airmass(sp['apparent_zenith'])
    poa = irradiance.get_total_irradiance(p['tilt_deg'], p['azimuth_deg'], sp['apparent_zenith'], sp['azimuth'], dni, ghi, dhi,
                                          dni_extra=dni_extra, airmass=am, albedo=p['albedo'], model='perez',
                                          model_perez=p['perez_model'])['poa_global'].fillna(0.0).clip(lower=0.0)
    poa = poa.where(sp['elevation'] > 0, 0.0)
    a, b, dt = temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass'].values()
    tcell = temperature.sapm_cell(poa, ta, p['wind_speed_ms'], a, b, dt)
    pdc = pvsystem.pvwatts_dc(poa, tcell, 1.0, p['gamma_pdc_per_k']) * (1.0 - _losses_fraction())
    pac = inverter.pvwatts(pdc, 1.0 / p['dc_ac_ratio'], eta_inv_nom=p['inverter_eta_nom'])
    return np.clip(np.nan_to_num(pac.to_numpy()), 0.0, None)      # kW per kWp over one hour = kWh/kWp


# ---- capacity rule (assumption, plan 4.3) ----
SIZING = {'floors_sfh': 2, 'floors_mfh': 4, 'floor_area_per_mfh_unit_m2': 80.0, 'usable_roof_share': 0.5,
          'module_kwp_per_m2': 0.20}


def rooftop_cap_kwp(floor_area_m2, multi_family, sizing=None):
    """Upper limit on PV size from a rooftop proxy: footprint = floor area / floors; usable PV area = share * footprint."""
    s = dict(SIZING, **(sizing or {}))
    floors = s['floors_mfh'] if multi_family else s['floors_sfh']
    return floor_area_m2 / floors * s['usable_roof_share'] * s['module_kwp_per_m2']


def capacity_kwp(annual_import_kwh, annual_yield_kwh_per_kwp, yield_to_demand, cap_kwp):
    """Default rule: annual PV yield = yield_to_demand * annual import, limited by the rooftop cap. Returns (kWp, cap_binding)."""
    want = yield_to_demand * annual_import_kwh / annual_yield_kwh_per_kwp
    return float(min(want, cap_kwp)), bool(want > cap_kwp)
