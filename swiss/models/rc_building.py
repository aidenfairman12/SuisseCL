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
