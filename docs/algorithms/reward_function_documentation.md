# Reward function documentation

## R-001 `swiss.experiments.rewards.SwissDistrictReward` (D-019, accepted)
reward_t = − Σ_k w_k · term_k(t) / scale_k, central agent, penalty-only.

| Term | Definition | Unit | Default weight | Scale |
|---|---|---|---|---|
| cost | Σ_buildings max(net import, 0) × electricity_pricing | CHF per step (EKZ standard 2023, excl. VAT) | 1 | mean per-step value under zero-action rollout |
| peak | (max(district net import, 0))² | kW² | 1 | same |
| ramp | \|district net(t) − district net(t−1)\| | kW | 1 | same |
| carbon | Σ max(net,0) × carbon_intensity | gCO2eq-proportional | 0 (series not available yet) | same |

Why no comfort term: the earlier US-cooling track found the comfort term mis-scaled (HANDOFF section 4.3); for Phase A it is removed because the dataset has no indoor-temperature dynamics (constant 21 °C placeholder) and heating/DHW demand is always served, so comfort cannot be measured. Cost and peak/ramp are relative to the uncontrolled reference, so a score of −(w sum) corresponds to the zero-action controller.
Known weaknesses: equal weights are arbitrary; peak² surrogate emphasises winter evening peaks; without a comfort term, a learning agent could trade comfort silently if later given thermal dynamics (revisit in Phase B with an RC model).

## Presets used by the RL runs (`swiss/experiments/rl.py`, D-030)
| Preset | cost | peak | ramp | carbon | Purpose |
|---|---|---|---|---|---|
| `r001` | 1 | 1 | 1 | 0 | R-001 as documented above; comparable with all baselines |
| `cost` | 1 | 0.1 | 0.1 | 0 | cost-dominant: tests whether a learner finds bill savings; the small peak and ramp weights discourage spikes |
Which preset is the primary one is the owner's confirmation under D-023 (pending). Both are scored on all metrics (cost raw and corrected, import, highest hour, mean daily peak, high-tariff share, relative carbon, reward). The exact cost optimum bounds the bill saving of any controller at 0.84 % at the assumed tank sizes, so the cost term alone gives a very weak learning signal; peak and ramp have more relative headroom (the night-charging rule improves the highest hour by 6 % and the ramp term by 2 %).

