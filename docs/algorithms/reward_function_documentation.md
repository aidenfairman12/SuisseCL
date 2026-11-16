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
