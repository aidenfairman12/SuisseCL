"""Reward function R-001 for the Swiss heating district (Task A8, decision D-019).

Penalty-only, district level (central agent). Terms (each >= 0), each divided by a reference scale:
  cost   : sum_b max(net_b, 0) * electricity_pricing          [CHF per step]
  peak   : (max(sum_b net_b, 0))**2                           [kW^2, smooth surrogate of peak demand]
  ramp   : |sum_b net_b(t) - sum_b net_b(t-1)|                [kW]
  carbon : sum_b max(net_b, 0) * carbon_intensity             [only if the observation exists; weight 0 otherwise]
reward = - sum_k w_k * term_k / scale_k.   Scales = mean of each term under the uncontrolled (zero-action) rollout
(computed by run_baselines.py, stored in results/reward_scales.json).
A comfort term is deliberately ABSENT: the Phase A dataset has no thermal dynamics or measured indoor temperature, and
heating/DHW demand is always met, so a comfort penalty would be meaningless (D-018/D-019).
"""
import json
import os
from typing import Any, List, Mapping, Union

import numpy as np
from citylearn.reward_function import RewardFunction

TERMS = ('cost', 'peak', 'ramp', 'carbon')
SCALES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'reward_scales.json')


class SwissDistrictReward(RewardFunction):
    def __init__(self, env_metadata: Mapping[str, Any], weights: Mapping[str, float] = None,
                 scales: Mapping[str, float] = None, **kwargs):
        super().__init__(env_metadata, **kwargs)
        self.weights = {'cost': 1.0, 'peak': 1.0, 'ramp': 1.0, 'carbon': 0.0}
        self.weights.update(weights or {})
        if scales is None and os.path.exists(SCALES):
            scales = json.load(open(SCALES))
        self.scales = {t: float((scales or {}).get(t, 1.0)) or 1.0 for t in TERMS}
        self._prev = None
        self.last_terms = None

    def reset(self):
        self._prev = None

    def terms(self, observations):
        net = np.array([o['net_electricity_consumption'] for o in observations], dtype=float)
        imp = np.maximum(net, 0.0)
        price = np.array([o['electricity_pricing'] for o in observations], dtype=float)
        district = float(net.sum())
        ramp = 0.0 if self._prev is None else abs(district - self._prev)
        self._prev = district
        carbon = 0.0
        if all('carbon_intensity' in o for o in observations):
            carbon = float((imp * np.array([o['carbon_intensity'] for o in observations], dtype=float)).sum())
        return {'cost': float((imp * price).sum()), 'peak': max(district, 0.0) ** 2, 'ramp': ramp, 'carbon': carbon}

    def calculate(self, observations: List[Mapping[str, Union[int, float]]]) -> List[float]:
        t = self.terms(observations)
        self.last_terms = t
        r = -sum(self.weights[k] * t[k] / self.scales[k] for k in TERMS)
        return [float(r)] if self.central_agent else [float(r) / len(observations)] * len(observations)


# ------------------------------------------------------------------------------------------------ Phase B: bill reward with export revenue and comfort (RL block, D-044)
TERMS2 = ('cost', 'peak', 'ramp', 'carbon', 'comfort')


class SwissBillReward(SwissDistrictReward):
    """Reward "bill" for the PV, battery and thermal-model scenarios S1 to S3 (decision D-044; replaces R-001's cost term, keeps its peak and ramp terms).
      cost    : sum_b [max(net_b, 0) * price - max(-net_b, 0) * export_price]    [CHF per step]; the stock CityLearn cost ignores exports (D-034)
      peak    : (max(sum_b net_b, 0))**2 ;   ramp : |sum_b net_b(t) - sum_b net_b(t-1)|      (as R-001)
      comfort : sum_b max(setpoint - T_indoor_b, 0) [K per step], only when the indoor temperature is observed (S3); the model has no cooling, so only the cold side counts (A-020)
    reward = - sum_k w_k term_k / scale_k  (scales: mean of each term under the scenario's reference controller, results/reward_scales_<scenario>.json; comfort scale 1 K)."""

    def __init__(self, env_metadata, weights=None, scales=None, export_price=0.08, setpoint=21.0, **kwargs):
        super().__init__(env_metadata, weights=weights, scales=scales, **kwargs)
        self.weights.setdefault('comfort', 0.0)
        self.scales.setdefault('comfort', 1.0)
        self.export_price, self.setpoint = float(export_price), float(setpoint)

    def terms(self, observations):
        net = np.array([o['net_electricity_consumption'] for o in observations], dtype=float)
        imp, exp = np.maximum(net, 0.0), np.maximum(-net, 0.0)
        price = np.array([o['electricity_pricing'] for o in observations], dtype=float)
        district = float(net.sum())
        ramp = 0.0 if self._prev is None else abs(district - self._prev)
        self._prev = district
        carbon = 0.0
        if all('carbon_intensity' in o for o in observations):
            carbon = float((imp * np.array([o['carbon_intensity'] for o in observations], dtype=float)).sum())
        comfort = 0.0
        if all('indoor_dry_bulb_temperature' in o for o in observations):
            comfort = float(np.maximum(self.setpoint - np.array([o['indoor_dry_bulb_temperature'] for o in observations], dtype=float), 0.0).sum())
        return {'cost': float((imp * price).sum() - self.export_price * exp.sum()), 'peak': max(district, 0.0) ** 2, 'ramp': ramp, 'carbon': carbon, 'comfort': comfort}

    def calculate(self, observations):
        t = self.terms(observations)
        self.last_terms = t
        r = -sum(self.weights.get(k, 0.0) * t[k] / self.scales.get(k, 1.0) for k in TERMS2)
        return [float(r)] if self.central_agent else [float(r) / len(observations)] * len(observations)
