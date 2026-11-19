# WP3 and WP4 registry draft (for merging by the parent; none of the register files was edited by the WP3 fork)

## Assumptions (block A-050 to A-059)
| ID | Date | Assumption | Basis | Status |
|---|---|---|---|---|
| A-050 | 2026-11-19 | Phase C controller study protocol: the eight held-out weeks of Phase B (rl.TEST_WEEKS) with the RL warm-up of 96 steps from empty tanks and the bill scoring of `rl.window_metrics` (export 8 Rp/kWh); week 29 (steps 4872 to 5039) holds the inserted heat-wave week in the `*_hw99` scenarios; reference = thermostat (heat to 21 C, cool to 26 C where a cooling device exists). | continuity with EXP-017 and EXP-019 | accepted |
| A-051 | 2026-11-19 | Climate cells use the matrix of 6 scenarios (hist, hist_hw99, gwl2.0, gwl2.0_hw99, gwl3.0, gwl3.0_hw99) x 4 adoption levels (none, low, medium, high) plus the sensitivity assignment high_alt for the two gwl3.0 scenarios; heat waves are the 99th-percentile spells (the 95th-percentile files stay unused sensitivities). | proposal sections 3 and 5; WP1 finding that p95 spells are milder than the hottest observed week of 2023 | accepted |
| A-052 | 2026-11-19 | MPC with cooling: comfort lower limit 21 C (plus an optional margin), upper limit 24 C in the heating season and 26 C in the cooling season (June to September) for cooled buildings; soft constraints with slack penalties 5 CHF per K h (cold), 2 CHF per K h (hot, cooled buildings) and 0.05 CHF per K h (hot, uncooled buildings, as in the Phase B MPC); the upper limit never below the thermostat path. | as the exact optimum (oracle_climate), softened as in MPCAgentRC | accepted |
| A-053 | 2026-11-19 | MPC terminal credit in the cooling season: for a cooled building a lower end-of-horizon room temperature is valued as stored coolness at the lowest tariff price divided by the cooling COP (kWh per K = C x area / 3.6e6); in the heating season the stored heat is valued as in A-029; uncooled buildings get no credit in the cooling season. | extension of A-029 | accepted |
| A-054 | 2026-11-19 | MPC forecasters in the cells: gradient boosting (200 iterations, learning rate 0.08, 15 leaves, random_state 0) of household load including DHW electricity, DHW tank demand and PV on calendar and weather features (hour, weekday, temperature, diffuse and direct irradiance, 24 h mean temperature), trained on the scenario's own year outside the test weeks +- 1 week; weather over the horizon known (A-028). | continuity with EXP-019 | accepted |
| A-055 | 2026-11-19 | Robustness (WP4): synthetic forecast-weather error with fixed seed 7: temperature bias of -2, -1, +1, +2 K plus 1 K Gaussian noise, irradiance multiplicative Gaussian noise of 30 % (beam and diffuse together); the plant sees the true weather; planner COP, capacities, room model and PV forecast features use the forecast weather. Labelled synthetic. | judgement; no weather forecast archive used | accepted |
| A-056 | 2026-11-19 | PV allocation rule for the coverage shares of cooling electricity (climate_metrics.py): PV serves base load, DHW, heat pump heating, cooling and battery charging in this order; battery discharge serves the remaining load of the four loads in proportion; the alternative priority `hp_first` serves heating and cooling first. A bookkeeping choice, not a physical attribution. | proposal section 9 | accepted |
| A-057 | 2026-11-19 | Uncooled buildings float in summer with no shading, ventilation or other adaptation; the pooled per-m2 thermal priors (A-018) make their indoor temperature path identical in every building, so their overheating degree-hours are identical per building and large in warm scenarios. | model limitation of the RC model | accepted; reported |

## Experiments (CSV rows, columns as docs/experiments/experiment_registry.csv)
EXP-021  Phase C scenario matrix, exact optima and full-year CityLearn rollouts (thermostat and replayed optimum) per cell with climate_metrics, 26 cells -> swiss/experiments/climate_results/<cell>__year.json, docs/experiments/validation_reports/climate_matrix.md
EXP-022  Phase C controller study on the eight held-out weeks per cell: thermostat, PV rule, MPC, MPC with peak weight 0.1 -> climate_results/<cell>__weeks_<ctrl>.json
EXP-023  Phase C robustness of the MPC on the heat-wave cells with high adoption: forecasters trained on 2023 only, synthetic weather forecast error (A-055) -> climate_results/robust__*.json, robustness.json
EXP-024  Climate impact metrics and difference-method pairs (added consumption, PV coverage of cooling, spill-over) from EXP-021 -> climate_results/climate_summary.json
(git_commit and dates to be filled by the parent when merging; software: citylearn 3.3.0, scipy HiGHS, scikit-learn 1.9.1, local cl venv, 11 worker processes.)

## Algorithm ALG-012
| ALG-012 | Receding-horizon MPC with cooling (Phase C cells) | `swiss.experiments.climate_controllers.MPCClimate` (extends mpc.MPCAgent; forecasters `ClimateForecaster`; `ThermostatAgentCool` and `PVRuleCool` are the references) | minimise the bill over the next 48 h with the cooling variable, optional joint district peak term, soft comfort band, terminal credit including stored coolness | tank, battery and room-temperature state, forecasts of household load, DHW demand and PV, known weather (A-028) | net tank charge, battery power, combined heat/cool share of the device capacity (negative = cooling) | horizon 48 h, peak weight 0 or 0.1, margin 0, correction off (variants in WP4) | gradient-boosting forecasters (A-054) | n/a (deterministic) | known weather (A-028); modelled cooling (A-040 to A-047); synthetic household load (ISS-040) |

## Issues (from ISS-046)
- ISS-046  Overheating of uncooled buildings is large and identical per building in every warm scenario (A-057): the RC model has no shading, ventilation or behaviour, and the priors are pooled (A-018), so degree-hours above 26 C are an upper-bound indicator of discomfort, not a prediction per building.
- ISS-047  The MPC saving in the cells depends on known weather (A-028); the robustness cases (A-055) are synthetic errors, not archived forecast errors; no weather forecast archive was downloaded.
- ISS-048  Replay equality (WP2) checks the action mapping, not the physics, because the program and CityLearn use the same RC step; the cooling COP and device are assumed (A-040 to A-047).

## Commands to add to swiss/run_pipeline.sh (after the Phase C WP1 and WP2 lines)
```
$PY -I swiss/pipeline/build_climate_datasets.py --all >/dev/null          # 24 matrix cells (+ high_alt via --all-extra), git-ignored
PYTHONPATH=. $PY swiss/experiments/climate_matrix.py run --workers 11    # about 40 minutes on 12 cores; results in swiss/experiments/climate_results/
PYTHONPATH=. $PY swiss/experiments/climate_robust.py --workers 11        # WP4
PYTHONPATH=. $PY swiss/experiments/climate_matrix.py aggregate           # climate_summary.json and docs/experiments/validation_reports/climate_matrix.md
```
