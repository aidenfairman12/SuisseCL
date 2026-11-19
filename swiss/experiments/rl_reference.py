"""Exact optimum on the RL test windows (reference for the Phase B RL results, D-044).

The year-long exact optimum (oracle_pvbat.py for s1 and s2, oracle_rc.py for s3 with the pure-shifting band 21-24) is evaluated on the same eight held-out weeks as the learners
(rl.TEST_WEEKS), next to the zero-action / thermostat bill of those weeks: saving over the test windows = sum over the windows of (reference bill - optimum bill). The optimum
schedule was planned over the whole year with perfect foresight, so state carried into a window is optimal, which a learner started from a warm-up cannot match: an upper reference.
Run: PYTHONPATH=. cl/bin/python swiss/experiments/rl_reference.py     Output: swiss/experiments/oracle_results/rl_reference.json
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.experiments import oracle_pvbat as o, oracle_rc as rcm, rl  # noqa: E402

EXPORT = 0.08


def test_index():
    return np.concatenate([np.arange(s, e + 1) for s, e in rl.test_windows('weeks')])


def bills(price, imp, exp):
    return price * imp - EXPORT * exp


def main():
    idx = test_index()
    inp = rcm.RCInputs('h')
    price = inp.price
    out = {'test_steps': int(len(idx)), 'export_price_chf_kwh': EXPORT, 'scenarios': {}}
    for name, bat in (('s1', None), ('s2', 1.0)):
        tot, sols = inp.scenario(1.0, bat, 8.0, with_solution=True)
        zero, opt = 0.0, 0.0
        for bi, s in enumerate(sols):
            net0 = inp.net_s0[bi] - inp.kwp[1.0][bi] * inp.pv_per_kwp
            zero += bills(price[idx], np.maximum(net0, 0)[idx], np.maximum(-net0, 0)[idx]).sum()
            opt += bills(price[idx], s['imp'][idx], s['exp'][idx]).sum()
        out['scenarios'][name] = {'zero_bill_test_chf': float(zero), 'optimum_bill_test_chf': float(opt), 'saving_pct': float(100 * (zero - opt) / zero),
                                  'year_saving_pct': tot['saving_pct']}
        print(name, out['scenarios'][name], flush=True)
    tot, sols = rcm.scenario(inp, {}, 'band 21-24', 8.0, with_solution=True)
    zero, opt = 0.0, 0.0
    for bi, s in enumerate(sols):
        cop = inp.heat_tank[bi]['cop']
        base = inp.net_s0[bi] - inp.derived_heat[bi] / cop - inp.kwp[1.0][bi] * inp.pv_per_kwp
        net0 = base + s['q_thermostat'] / cop
        zero += bills(price[idx], np.maximum(net0, 0)[idx], np.maximum(-net0, 0)[idx]).sum()
        opt += bills(price[idx], s['imp'][idx], s['exp'][idx]).sum()
    out['scenarios']['s3'] = {'zero_bill_test_chf': float(zero), 'optimum_bill_test_chf': float(opt), 'saving_pct': float(100 * (zero - opt) / zero), 'year_saving_pct': tot['saving_pct']}
    print('s3', out['scenarios']['s3'], flush=True)
    json.dump(out, open(os.path.join(rl.ROOT, 'swiss', 'experiments', 'oracle_results', 'rl_reference.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
