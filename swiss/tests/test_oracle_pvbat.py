"""Exact bill optimum for S1/S2 (oracle_pvbat.py): toy hand cases, structural properties, and replay in CityLearn."""
import os

import numpy as np
import pytest

from swiss.experiments import oracle_pvbat as o


def test_battery_toy_hand_computed():
    # 4 hours, no tanks, no PV. net0 = 2 kWh each hour; price 0.10,0.30 in pairs; battery 4 kWh, power 2, efficiency 0.9 round trip, DoD 0.9
    bat = o.battery_spec(4.0)
    price = np.array([0.10, 0.10, 0.30, 0.30]); net0 = np.full(4, 2.0)
    s = o.solve_building(net0, price, 0.0, [], bat)
    eta1 = 0.9 ** 0.5
    # charge as much as fits at the cheap hours (power 2/h, room (4 - 0.4)/eta1 grid-side), discharge at the dear hours
    room = (4.0 - bat['emin']) / eta1
    ch = min(2.0 * 2, room)
    assert s['c'][:2].sum() == pytest.approx(ch, abs=1e-6)
    assert s['u'][2:].sum() == pytest.approx(ch * 0.9, abs=1e-6)          # delivered = stored x eta1 = grid charge x eta1^2
    zero = o.zero_bill(net0, price, 0.0)
    assert zero - s['bill'] == pytest.approx(0.30 * ch * 0.9 - 0.10 * ch, abs=1e-6)
    assert (np.minimum(s['c'], s['u']) < 1e-6).all()                       # never both


def test_export_price_zero_vs_positive_and_guard():
    bat = o.battery_spec(10.0)
    pv_net = np.array([-3.0, -3.0, 2.0, 2.0])                             # exports then imports
    price = np.full(4, 0.2)
    free = o.solve_building(pv_net, price, 0.0, [], bat)
    paid = o.solve_building(pv_net, price, 0.08, [], bat)
    assert free['bill'] <= o.zero_bill(pv_net, price, 0.0) + 1e-9
    assert paid['bill'] <= o.zero_bill(pv_net, price, 0.08) + 1e-9
    assert free['export_kwh'] <= paid['export_kwh'] + 1e-9                 # an exported kWh is worth more when paid, so never less is exported
    with pytest.raises(AssertionError):
        o.solve_building(pv_net, price, 0.25, [], bat)                     # export price above import price is rejected


def test_battery_never_worse_than_none():
    rng = np.random.default_rng(1)
    net0 = rng.uniform(-2, 3, 48); price = np.where(np.arange(48) % 24 < 8, 0.15, 0.19)
    without = o.solve_building(net0, price, 0.05, [])
    with_b = o.solve_building(net0, price, 0.05, [], o.battery_spec(6.0))
    assert with_b['bill'] <= without['bill'] + 1e-9
    assert without['bill'] == pytest.approx(o.zero_bill(net0, price, 0.05), abs=1e-9)


@pytest.mark.skipif(not (os.path.isdir(os.path.join(o.DS, 'swiss_pv_2023')) and os.path.isdir(os.path.join(o.DS, 'swiss_pvbat_2023'))), reason='datasets not built')
def test_replay_in_citylearn_matches_program_for_s1_and_s2():
    inp = o.Inputs()
    for pvr, bat, sch in ((1.0, None, 'swiss_pv_2023'), (1.0, 1.0, 'swiss_pvbat_2023')):
        r = o.replay(inp, pvr, bat, 8.0, sch, n=1500)
        assert r['rel_diff_saving_pct'] < 0.5, r                           # stop condition of the plan: 0.5 %
        assert r['predicted_saving_chf'] > 0
