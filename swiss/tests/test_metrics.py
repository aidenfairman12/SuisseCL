"""B9 metrics: hand-computed toy cases (no CityLearn)."""
import numpy as np
import pytest

from swiss.experiments.metrics import compute_metrics


def test_import_only_no_pv():
    net = [[2.0, 1.0], [4.0, 0.0], [1.0, 3.0]]          # 3 steps, 2 buildings
    m = compute_metrics(net, [0.2, 0.1, 0.3], step_hours=1.0)
    assert m['import_kwh'] == 11.0 and m['export_kwh'] == 0.0
    assert m['peak_import_kw_coincident_gross'] == 4.0   # step 3: 1+3, step 2: 4+0, step 1: 3
    assert m['peak_net_kw_coincident'] == 4.0
    assert m['peak_import_kw_building_sum'] == 4.0 + 3.0
    assert m['import_cost_chf'] == pytest.approx(3 * 0.2 + 4 * 0.1 + 4 * 0.3)
    assert m['export_revenue_chf'] is None and m['bill_chf'] == m['import_cost_chf']
    assert m['pv_self_consumption'] is None and m['battery_equivalent_cycles'] is None
    assert m['comfort_violation_steps'] is None
    assert m['self_sufficiency'] == 0.0                  # load == import


def test_pv_export_and_accounting_identity():
    # one building, load 1 kWh every step, pv = 0,3,2 -> net = 1,-2,-1
    pv = [0.0, 3.0, 2.0]
    net = [1.0, -2.0, -1.0]
    m = compute_metrics(net, 0.30, pv_kwh=pv, price_export=0.08)
    assert m['load_kwh'] == pytest.approx(3.0)
    assert m['import_kwh'] == 1.0 and m['export_kwh'] == 3.0
    assert m['pv_self_consumption'] == pytest.approx(1 - 3.0 / 5.0)   # 2 of 5 kWh used on site
    assert m['self_sufficiency'] == pytest.approx(1 - 1.0 / 3.0)
    assert m['import_cost_chf'] == pytest.approx(0.30)
    assert m['export_revenue_chf'] == pytest.approx(0.24)
    assert m['bill_chf'] == pytest.approx(0.30 - 0.24)
    assert m['peak_net_kw_coincident'] == 1.0


def test_netting_per_building_not_between_buildings():
    net = [[3.0, -2.0]]                                  # one step: B0 imports 3, B1 exports 2
    m = compute_metrics(net, 0.1, price_export=0.05)
    assert m['import_kwh'] == 3.0 and m['export_kwh'] == 2.0
    assert m['peak_import_kw_coincident_gross'] == 3.0
    assert m['peak_net_kw_coincident'] == 1.0            # district meter with netting


def test_battery_cycles_and_load_derivation():
    # load 2 kWh/step, no pv; battery charges 1 in step 0, discharges 1 in step 1; capacity 2 kWh
    ch = [1.0, 0.0]; dis = [0.0, 1.0]
    net = [3.0, 1.0]                                     # load + charge - discharge
    m = compute_metrics(net, 0.2, battery_charge_kwh=ch, battery_discharge_kwh=dis, battery_capacity_kwh=2.0)
    assert m['load_kwh'] == pytest.approx(4.0)
    assert m['battery_equivalent_cycles'] == pytest.approx((1 + 1) / 2 / 2.0)
    assert m['self_sufficiency'] == pytest.approx(0.0)   # import 4 = load 4


def test_half_hour_steps_convert_to_kw():
    m = compute_metrics([1.0, 2.0], 0.1, step_hours=0.25)
    assert m['peak_import_kw_coincident_gross'] == 8.0   # 2 kWh in 15 min = 8 kW


def test_comfort_violations():
    temp = [20.0, 22.0, 24.0, 18.5]
    m = compute_metrics([1, 1, 1, 1], 0.1, indoor_temp=temp, comfort_lower=20.0, comfort_upper=23.0)
    assert m['comfort_violation_steps'] == 2
    assert m['comfort_degree_hours'] == pytest.approx(1.0 + 1.5)


def test_validation_errors():
    with pytest.raises(ValueError):
        compute_metrics([1.0, 1.0], 0.1, pv_kwh=[-1.0, 0.0])
    with pytest.raises(ValueError):
        compute_metrics([1.0, 1.0], [0.1, 0.1, 0.1])
    with pytest.raises(ValueError):
        compute_metrics([1.0, 1.0], 0.1, battery_charge_kwh=[0.0, 0.0])


def test_matches_baseline_cost_formula():
    """Zero PV/battery metrics equal the run_baselines formulas (import * price summed)."""
    rng = np.random.default_rng(0)
    net = rng.uniform(0, 5, size=(48, 3)); price = rng.uniform(0.1, 0.3, size=48)
    m = compute_metrics(net, price)
    assert m['import_cost_chf'] == pytest.approx(float((net.sum(axis=1) * price).sum()))
    assert m['peak_net_kw_coincident'] == pytest.approx(net.sum(axis=1).max())
