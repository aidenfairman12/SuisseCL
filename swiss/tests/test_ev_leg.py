"""B8 EV and B6 LEG scenarios (LP level): window structure, energy delivery, bill identities, LEG gain = energy + delta x grid - export."""
import json
import os

import numpy as np
import pytest

from swiss.experiments import oracle_ev_leg as el
from swiss.experiments import oracle_pvbat as o

ROOT = el.ROOT


@pytest.fixture(scope='module')
def inp():
    return o.Inputs()


def test_ev_windows_deliver_the_measured_energy_and_respect_power(inp):
    ev, info = el.build_ev(inp)
    e = ev[1]
    assert set(ev) == {1, 2} and info['windows'] > 300 and 0.4 < info['shiftable_share'] < 1.0
    total_window = sum(w[2] for w in e['windows'])
    assert total_window + e['fixed'].sum() == pytest.approx(e['base'].sum(), rel=1e-9)        # nothing created or lost by the split
    assert (e['cap'][e['fixed'] > 0] == 0).all()                                               # fixed charging sits outside the windows
    for a, b, en in e['windows'][:50]:
        assert en <= el.P_EV_KW * (b - a) + 1e-9


def test_flexible_ev_delivers_each_window_energy_and_never_costs_more(inp):
    n = 1500
    ev, _ = el.build_ev(inp, n)
    ev = {bi: {**v, 'windows': [w for w in v['windows'] if w[1] <= n]} for bi, v in ev.items()}
    unc = inp.scenario(1.0, 1.0, 8.0, n=n, ev={bi: {**v, 'flexible': False} for bi, v in ev.items()})
    flex, sols = inp.scenario(1.0, 1.0, 8.0, n=n, ev=ev, with_solution=True)
    assert flex['opt_bill'] <= unc['opt_bill'] + 1e-6
    s = sols[1]
    for a, b, en in ev[1]['windows']:
        assert s['ev'][a:b].sum() == pytest.approx(en, abs=1e-6)
    assert (s['ev'] <= ev[1]['cap'][:n] + 1e-9).all()


def test_leg_gain_and_zero_action_identity(inp):
    n = 800
    r0 = el.leg_district(inp, None, False, 0.0, n=n)
    r4 = el.leg_district(inp, None, False, 0.4, n=n)
    assert r4['bill_with_leg'] <= r0['bill_with_leg'] + 1e-6            # a larger discount cannot cost more
    assert r0['bill_with_leg'] <= r0['bill_before_leg_credit'] + 1e-6   # the credit is non-negative
    assert r4['zero_bill_with_leg'] <= r4['zero_bill'] + 1e-9 and r4['zero_internal_kwh'] >= 0
    assert r4['internal_kwh'] <= min(r4['import_kwh'], r4['export_kwh']) + 1e-6


def test_results_file_is_consistent_with_step_6():
    res = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'ev_leg.json')))
    s2 = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'oracle_pvbat.json')))['rungs']['S2']['8.0']
    assert res['ev']['S2_no_ev']['saving_pct'] == pytest.approx(s2['saving_pct'], rel=1e-6)
    assert res['ev']['S2_ev_flexible']['opt_bill'] <= res['ev']['S2_ev_uncontrolled_others_optimised']['opt_bill'] + 1e-6
