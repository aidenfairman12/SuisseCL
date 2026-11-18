"""B5: scenario accounting from a finished CityLearn rollout (no change to the environment).

CityLearn 3.3.0 prices only imports: building cost = max(net, 0) * electricity_pricing (checked in building.py); exported energy
earns nothing there and the reward cost term uses the same rule. Export revenue is therefore computed here, from the same net series,
and bill = import cost - export revenue (swiss.experiments.metrics). `replay_check` asserts that the import part equals the
environment's own cost series, which is the "accounting equals environment" test of the plan (4.4).
"""
import numpy as np

from swiss.experiments.metrics import compute_metrics
from swiss.models.export_price import export_price_chf_per_kwh


def rollout_arrays(env):
    """Per-step arrays (T, B) from a finished episode: net, pv generation (>= 0), env import cost, import price (T,)."""
    bs = env.buildings
    n = len(bs[0].net_electricity_consumption)
    net = np.stack([np.asarray(b.net_electricity_consumption, dtype=float)[:n] for b in bs], axis=1)
    pv = np.stack([-np.asarray(b.solar_generation, dtype=float)[:n] for b in bs], axis=1)
    cost = np.stack([np.asarray(b.net_electricity_consumption_cost, dtype=float)[:n] for b in bs], axis=1)
    price = np.asarray(bs[0].pricing.electricity_pricing, dtype=float)[:n]
    return net, pv, cost, price


def scenario_metrics(env, export_rp=None, step_hours=1.0):
    """B9 metrics for a finished rollout; export_rp None leaves export revenue absent (None), never 0."""
    net, pv, _, price = rollout_arrays(env)
    pe = None if export_rp is None else export_price_chf_per_kwh(len(net), export_rp)
    return compute_metrics(net, price, step_hours=step_hours, pv_kwh=pv if pv.any() else None, price_export=pe)


def replay_check(env, rtol=1e-4):
    """Own import cost vs the environment's cost series (float32 in CityLearn); returns (own, env, relative difference)."""
    net, pv, cost, price = rollout_arrays(env)
    own = compute_metrics(net, price)['import_cost_chf']
    theirs = float(cost.sum())
    rel = abs(own - theirs) / max(abs(theirs), 1e-12)
    assert rel <= rtol, f'accounting differs from environment: {own} vs {theirs} (rel {rel:.2e})'
    return own, theirs, rel
