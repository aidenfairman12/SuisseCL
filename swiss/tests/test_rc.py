"""M-005 single-node RC model (Melillo et al. 2021 equation (1)): exact step, control inversion, energy closure, calibration file."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from swiss.models.rc_building import PRIORS, calibrate_area, heat_for_target, simulate_ideal, step_temperature, tau_seconds

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')


def test_exact_step_matches_fine_euler_integration():
    A, T, ta, I, q = 200.0, 19.0, 2.0, 150.0, 6.0
    H = PRIORS['H_w_per_k_m2'] * A; C = PRIORS['C_j_per_k_m2'] * A
    gain = PRIORS['g'] * A * I + PRIORS['L_internal_w_m2'] * A + 1000 * q
    x = T
    for _ in range(3600):                                   # 1 s Euler steps
        x += (-H * (x - ta) + gain) / C
    assert step_temperature(T, ta, I, q, A) == pytest.approx(x, abs=2e-3)


def test_no_heat_relaxes_to_asymptote_and_time_constant():
    A = 100.0
    t = 5.0
    for _ in range(24 * 30):
        t = step_temperature(t, 0.0, 0.0, 0.0, A)
    assert t == pytest.approx(PRIORS['L_internal_w_m2'] / PRIORS['H_w_per_k_m2'], abs=1e-3)   # T_inf = T_amb + L / H
    assert 15 < tau_seconds() / 3600 < 60                  # about 30 h with the default priors


def test_heat_for_target_inverts_the_step():
    A = 300.0
    for T, target, ta, I in [(18, 21, -3, 0), (22.5, 21, 8, 400), (21, 21, 15, 100)]:
        q = heat_for_target(T, target, ta, I, A)
        assert step_temperature(T, ta, I, q, A) == pytest.approx(target, abs=1e-9)


def test_energy_balance_over_a_step():
    # stored energy change = heat in + gains - losses (mean temperature over the step is not needed: check with the exact integral)
    A, T0, ta, I, q = 150.0, 20.0, 5.0, 0.0, 3.0
    T1 = step_temperature(T0, ta, I, q, A)
    H = PRIORS['H_w_per_k_m2'] * A; C = PRIORS['C_j_per_k_m2'] * A
    gain = PRIORS['L_internal_w_m2'] * A + 1000 * q
    tinf = ta + gain / H
    mean_T = tinf + (T0 - tinf) * (1 - np.exp(-3600 * H / C)) / (3600 * H / C)
    assert C * (T1 - T0) == pytest.approx((gain - H * (mean_T - ta)) * 3600, rel=1e-9)


def test_calibration_closure_and_file():
    w = pd.read_csv(os.path.join(CAN, 'weather_klo_2023_hourly.csv'))
    ta, g = w.temp_c.to_numpy(), w.ghi_wm2.fillna(0).to_numpy()
    params = json.load(open(os.path.join(CAN, 'rc', 'rc_params_2023.json')))
    for role, b in params['buildings'].items():
        q, T = simulate_ideal(b['effective_area_m2'], ta, g)
        assert q.sum() == pytest.approx(b['annual_derived_heat_kwh_th'], rel=2e-3)        # energy closure with the derived heat
        assert (q >= 0).all() and T.min() >= PRIORS['setpoint_c'] - 1e-6                  # heating only: never below the setpoint
    assert calibrate_area(1000.0, ta, g) > 0
