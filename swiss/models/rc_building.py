"""M-005 single-node (1R1C) building thermal model, equation (1) of Melillo et al. 2021 (J. Phys.: Conf. Ser. 2042 012009), per floor area:
    C dT/dt = -H (T - T_amb) + g I + L_emitter + L_internal
Pooled per-m2 priors (owner decision 2026-11-18): the same H, g, C and internal gain per m2 for every building; only the EFFECTIVE AREA of a
building is calibrated, so that the model with ideal control at the setpoint reproduces the building's annual derived heat demand (energy
closure; the derived heat is itself SPF-anchored, M-001, ISS-028). All priors are assumptions or unverified; the model is labelled synthetic.
The step is the exact solution for piecewise-constant inputs over one step (no integration error):
    T_{k+1} = T_inf + (T_k - T_inf) exp(-dt / tau),   tau = C / H,   T_inf = T_amb + (g I + L_internal + L_emitter) / H
Units here: power in kW, areas in m2, H in W/(K m2), C in J/(K m2), I in W/m2, time step in seconds.
"""
import numpy as np

PRIORS = {
    'H_w_per_k_m2': 1.03,        # median of the three houses' quasi-steady fits (EL-0064: 1.03, 2.09, 1.00); sweep 1.0 / 1.5 / 2.1
    'g': 0.026,                  # median of fitted solar aperture / floor area (0.044, 0.026, 0.017); dimensionless, sweep 0.017 / 0.026 / 0.044
    'C_j_per_k_m2': 110e3,       # medium-weight class of the ISO 13790 simplified method (from memory, unverified); sweep 80e3 / 110e3 / 165e3
    'L_internal_w_m2': 2.0,      # occupants and appliances, judgement; constant
    'setpoint_c': 21.0,          # D-018
    'comfort_lower_c': 20.0, 'comfort_upper_c': 24.0,   # comfort band, assumption
}
SWEEP = {'H_w_per_k_m2': (1.0, 1.5, 2.1), 'g': (0.017, 0.026, 0.044), 'C_j_per_k_m2': (80e3, 110e3, 165e3)}


def tau_seconds(p=None):
    p = {**PRIORS, **(p or {})}
    return p['C_j_per_k_m2'] / p['H_w_per_k_m2']


def step_temperature(T, t_amb, irradiance, q_heat_kw, area_eff, dt_s=3600.0, p=None):
    """Indoor temperature after one step with heat power q_heat_kw (kW, thermal; negative = cooling) delivered over the step."""
    p = {**PRIORS, **(p or {})}
    H = p['H_w_per_k_m2'] * area_eff                                  # W/K
    gain_w = p['g'] * area_eff * irradiance + p['L_internal_w_m2'] * area_eff + 1000.0 * q_heat_kw
    t_inf = t_amb + gain_w / H
    return t_inf + (T - t_inf) * np.exp(-dt_s * H / (p['C_j_per_k_m2'] * area_eff))


def heat_for_target(T, target, t_amb, irradiance, area_eff, dt_s=3600.0, p=None):
    """Thermal power (kW, may be negative) that brings the indoor temperature from T to `target` at the end of the step."""
    p = {**PRIORS, **(p or {})}
    H = p['H_w_per_k_m2'] * area_eff
    e = np.exp(-dt_s * H / (p['C_j_per_k_m2'] * area_eff))
    t_inf0 = t_amb + (p['g'] * area_eff * irradiance + p['L_internal_w_m2'] * area_eff) / H
    t_inf = (target - T * e) / (1.0 - e)                               # needed asymptote
    return (t_inf - t_inf0) * H / 1000.0


def simulate_ideal(area_eff, t_amb, ghi, p=None, dt_s=3600.0, t0=None, q_max=None):
    """Heating-only ideal control at the setpoint (heat never negative, no cooling). Returns (heat kW per step, indoor temperature per step).
    Indoor temperature rises above the setpoint when free gains exceed losses (the model has no cooling, windows or shading, Phase C).
    q_max (kW per step, optional) limits the heat pump output (the thermostat baseline cannot exceed the device)."""
    p = {**PRIORS, **(p or {})}
    T = p['setpoint_c'] if t0 is None else t0
    q = np.zeros(len(t_amb)); temp = np.zeros(len(t_amb))
    for k in range(len(t_amb)):
        q[k] = max(heat_for_target(T, p['setpoint_c'], t_amb[k], ghi[k], area_eff, dt_s, p), 0.0)
        if q_max is not None:
            q[k] = min(q[k], q_max[k])
        T = step_temperature(T, t_amb[k], ghi[k], q[k], area_eff, dt_s, p)
        temp[k] = T
    return q, temp


def calibrate_area(annual_heat_kwh, t_amb, ghi, p=None, dt_s=3600.0):
    """Effective area so that ideal control at the setpoint (simulate_ideal) delivers `annual_heat_kwh` over the year.
    The temperature path does not depend on the area (every term scales with it), so heat is proportional to the area and one reference run suffices."""
    q1, _ = simulate_ideal(1.0, np.asarray(t_amb, float), np.asarray(ghi, float), p, dt_s)
    return annual_heat_kwh / float(q1.sum() * dt_s / 3600.0)


# ----------------------------------------------------------------------------------------------------------------- Phase C: cooling (WP2)
# Cooling mode of the same single-node model (M-006 = M-005 + cooling). Heat removed from the room node: step_temperature already accepts negative heat.
# Assumptions (docs/phases/phase_c_drafts/wp2_registry_draft.md): reversible heat pump (cooling device = same rating and efficiency as the heating device, supply
# temperature 8 C as in the schema), COP from CityLearn's Carnot-fraction form, cooling only when the outdoor temperature is at least COOLING_MIN_OUTDOOR_C
# (the Carnot form gives COP 20 below the supply temperature, an artefact), cooling set point 26 C, cooling season June to September.
COOL_SETPOINT_C = 26.0
COOL_SUPPLY_C = 8.0
COOLING_MIN_OUTDOOR_C = 15.0
COOLING_MONTHS = (6, 7, 8, 9)            # local months in which the upper comfort limit is the cooling set point (26 C); otherwise 24 C
UPPER_HEATING_SEASON_C = 24.0


def cooling_cop(t_out, efficiency, t_supply=COOL_SUPPLY_C):
    """Carnot-fraction cooling COP exactly as citylearn.energy_model.HeatPump.get_cop(heating=False): eta (Tc + 273.15) / (T_out - Tc), set to 20 if < 0 or > 20."""
    t_out = np.asarray(t_out, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        c = efficiency * (t_supply + 273.15) / (t_out - t_supply)
    c = np.where((c < 0) | (c > 20) | ~np.isfinite(c), 20.0, c)
    return c


def cooling_capacity_kwh(t_out, nominal_power_kw, efficiency, dt_h=1.0, t_supply=COOL_SUPPLY_C, min_outdoor_c=COOLING_MIN_OUTDOOR_C):
    """Maximum heat removed per step (kWh thermal): nominal electric power x step x COP, zero when the outdoor temperature is below min_outdoor_c."""
    t_out = np.asarray(t_out, dtype=float)
    cap = nominal_power_kw * dt_h * cooling_cop(t_out, efficiency, t_supply)
    return np.where(t_out >= min_outdoor_c, cap, 0.0)


def simulate_thermostat(area_eff, t_amb, ghi, p=None, dt_s=3600.0, q_heat_max=None, q_cool_max=None, cool_setpoint=COOL_SETPOINT_C, t0=None):
    """Thermostat baseline with cooling: heat to the setpoint (as simulate_ideal) and, if the free-running temperature would exceed cool_setpoint, cool to it
    (limited by q_cool_max, kW thermal). q_cool_max None = no cooling device (identical to simulate_ideal). Returns (heat kW, cool kW, temperature) per step."""
    p = {**PRIORS, **(p or {})}
    T = p['setpoint_c'] if t0 is None else t0
    n = len(t_amb)
    q = np.zeros(n); qc = np.zeros(n); temp = np.zeros(n)
    for k in range(n):
        q[k] = max(heat_for_target(T, p['setpoint_c'], t_amb[k], ghi[k], area_eff, dt_s, p), 0.0)
        if q_heat_max is not None:
            q[k] = min(q[k], q_heat_max[k])
        if q_cool_max is not None and q[k] <= 0.0:
            t_free = step_temperature(T, t_amb[k], ghi[k], 0.0, area_eff, dt_s, p)
            if t_free > cool_setpoint:
                qc[k] = min(max(-heat_for_target(T, cool_setpoint, t_amb[k], ghi[k], area_eff, dt_s, p), 0.0), q_cool_max[k])
        T = step_temperature(T, t_amb[k], ghi[k], q[k] - qc[k], area_eff, dt_s, p)
        temp[k] = T
    return q, qc, temp
