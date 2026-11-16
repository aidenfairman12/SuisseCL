"""Composite reward for CityLearn: comfort + cost + carbon + peak + ramping.

Every term is a non-negative penalty, divided by a reference scale (its mean value under a reference
rollout, see `rl.py scales`), then multiplied by a weight. Reward = -sum(weight * penalty / scale).
With scales applied, equal weights mean "equally important", the same idea as the 2020 CityLearn
challenge (5 equally weighted KPIs normalised to a reference controller).

Terms (district level):
  comfort : sum over buildings of CityLearn's ComfortReward penalty (degrees outside the band, powered)
  cost    : sum over buildings of max(net import, 0) * electricity price
  carbon  : sum over buildings of max(net import, 0) * carbon intensity
  peak    : max(district net import, 0) ** 2          (smooth surrogate for peak demand)
  ramp    : |district net import(t) - district net import(t-1)|
Central agent gets the district reward. Decentralised agents get their own comfort/cost/carbon share plus
1/n of the shared peak and ramp terms, so the per-building rewards sum to the central reward.
"""
import json, os, logging
from typing import Any, List, Mapping, Union
import numpy as np
from citylearn.reward_function import RewardFunction, ComfortReward

TERMS = ('comfort', 'cost', 'carbon', 'peak', 'ramp')
SCALES_PATH = os.environ.get('COMPOSITE_SCALES', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'reward_scales.json'))
LOGGER = logging.getLogger(__name__)

class CompositeReward(RewardFunction):
    def __init__(self, env_metadata: Mapping[str, Any], weights: Mapping[str, float] = None, scales: Mapping[str, float] = None,
                 band: float = 1.0, lower_exponent: float = 2.0, higher_exponent: float = 3.0, **kwargs):
        super().__init__(env_metadata, **kwargs)
        self.weights = {t: 1.0 for t in TERMS}
        self.weights.update(weights or {})
        unknown = set(self.weights) - set(TERMS)
        if unknown: raise ValueError(f'Unknown reward terms {unknown}; use {TERMS}')
        if scales is None:
            if os.path.exists(SCALES_PATH):
                scales = json.load(open(SCALES_PATH))
            else:
                LOGGER.warning('No reward scales file at %s; using scale 1.0 (terms will be unbalanced). Run `rl.py scales`.', SCALES_PATH)
                scales = {}
        self.scales = {t: float(scales.get(t, 1.0)) or 1.0 for t in TERMS}
        self._comfort_kwargs = dict(band=band, lower_exponent=lower_exponent, higher_exponent=higher_exponent)
        self._comfort = None   # built lazily: the env passes env_metadata after construction
        self._prev = None

    def reset(self):
        self._prev = None

    def raw_terms(self, observations):
        """Per-building comfort/cost/carbon penalties and shared peak/ramp, all >= 0."""
        if self._comfort is None:
            self._comfort = ComfortReward(dict(self.env_metadata, central_agent=False), **self._comfort_kwargs)
        comfort = -np.asarray(self._comfort.calculate(observations), dtype=float)
        net = np.array([o['net_electricity_consumption'] for o in observations], dtype=float)
        imp = np.maximum(net, 0.0)
        price = np.array([o['electricity_pricing'] for o in observations], dtype=float)
        carbon_i = np.array([o['carbon_intensity'] for o in observations], dtype=float)
        district = float(net.sum())
        peak = max(district, 0.0) ** 2
        ramp = 0.0 if self._prev is None else abs(district - self._prev)
        self._prev = district
        return dict(comfort=comfort, cost=imp * price, carbon=imp * carbon_i, peak=peak, ramp=ramp)

    def calculate(self, observations: List[Mapping[str, Union[int, float]]]) -> List[float]:
        t = self.raw_terms(observations)
        w, s, n = self.weights, self.scales, len(observations)
        shared = w['peak'] * t['peak'] / s['peak'] + w['ramp'] * t['ramp'] / s['ramp']
        per_building = (w['comfort'] * t['comfort'] / s['comfort'] + w['cost'] * t['cost'] / s['cost']
                        + w['carbon'] * t['carbon'] / s['carbon'])
        if self.central_agent:
            return [float(-(per_building.sum() + shared))]
        return [float(-(pb + shared / n)) for pb in per_building]

    def get_required_observation_names(self):
        return None
