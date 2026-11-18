"""Scenario tariffs (step 9): series properties and consistency with the Phase A ceiling under the standard tariff."""
import json
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')


def test_series_shape_and_labelled_structure():
    t = pd.read_csv(os.path.join(CAN, 'tariff_scenarios_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    std = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'))
    assert len(t) == 8760 and t.notna().all().all()
    np.testing.assert_allclose(t.standard_s0, std.total_chf_kwh, atol=1e-9)
    assert t.drop(columns='timestamp_utc').min().min() * 100 >= 8.0            # export price 8 Rp/kWh never exceeds an import price (LP guard)
    loc = pd.DatetimeIndex(t.timestamp_utc).tz_convert('Europe/Zurich')
    evening = (loc.hour >= 18)
    # time-of-use grid fee of Q4 2023: low 4.3 and high 9.3 Rp/kWh around the 2023 energy price, evening high every day
    diff = (t.tou_q4_2023 * 100 - std.energy_rp_kwh).round(4)                                  # = grid fee Rp/kWh of the scenario
    assert set(np.round(diff[evening], 2)) == {9.3} and set(np.round(diff[~evening], 2)) == {4.3}
    # stylised spreads keep the mean and stretch around it
    assert t.spread2.mean() == pytest.approx(t.standard_s0.mean(), abs=1e-6)
    assert (t.spread5.max() - t.spread5.min()) == pytest.approx(5 * (t.standard_s0.max() - t.standard_s0.min()), abs=1e-5)
    assert (t.tou_2024.max() - t.tou_2024.min()) > (t.standard_s0.max() - t.standard_s0.min())


def test_standard_tariff_ceiling_equals_phase_a():
    from swiss.experiments import oracle, oracle_tariffs as ot
    s0 = oracle.zero_action_import()
    price = ot.TARIFFS['standard_s0'].to_numpy()[:oracle.N]
    cost0, sav = ot.s0_tanks(s0, price)
    phase_a = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'oracle_cost.json')))['scales']['1.0']
    assert sav == pytest.approx(phase_a['saving_chf'], rel=1e-6)
    assert 100 * sav / cost0 == pytest.approx(phase_a['saving_pct'], rel=1e-6)


def test_results_file_is_consistent_with_earlier_rungs():
    res = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'oracle_tariffs.json')))
    std = res['tariffs']['standard_s0']
    s2 = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'oracle_pvbat.json')))['rungs']
    assert std['S1']['saving_pct'] == pytest.approx(s2['S1']['8.0']['saving_pct'], rel=1e-6)
    assert std['S2']['saving_pct'] == pytest.approx(s2['S2']['8.0']['saving_pct'], rel=1e-6)
    rc = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'oracle_rc.json')))['bands']['band 21-24']
    assert std['S3']['saving_pct'] == pytest.approx(rc['saving_pct'], rel=1e-6)
