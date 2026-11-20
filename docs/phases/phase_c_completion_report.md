# Phase C completion report — future climate, cooling adoption and control (approved at the phase gate on 2026-11-20, D-056)

Date: 2026-11-19 · Status: draft by the agent; the owner has not yet reviewed it. Interpretation is marked "agent's reading". Every number below is taken from a generated result file or report (file names in brackets); none is typed from memory. Phase C was executed on the owner's chat instruction of 2026-11-19 (D-048); nothing is pushed.

## 1. Summary
### 1.1 What was built
- **Climate scenarios** for Kloten from CH2025 (MeteoSwiss, CC BY 4.0): typical warmed years for +1.5, +2.0 and +3.0 C global warming, built as monthly delta changes anchored on the observed 2023 hourly series, plus 7-day heat-wave variants (p95 and p99 spells from the CH2025 model chains) inserted over the July test week; scenario PV series (`swiss/pipeline/build_climate.py`, `climate_scenarios.md`).
- **Cooling** as a mode of the single-node RC building model and of CityLearn (M-006), and a second archetype with room units (two-zone model, M-007); exact optimum with cooling (ALG-012), cooling-aware thermostat, PV rule and receding-horizon MPC (ALG-013), climate impact metrics (`swiss/experiments/climate_metrics.py`).
- **Scenario matrix:** 26 cells for the central archetype A (six weather scenarios x adoption none, low, medium, high, plus two alternative-high cells), 20 cells for the room-unit archetype B (`climate_matrix.md`, `climate_matrix_ru.md`, `climate_archetypes.md`), robustness runs of the MPC on the heat-wave cells.
- **Dashboard** pages Climate, Cooling matrix, Scenario explorer and Houses (milestone 7b68d35); room-unit data were not yet in the dashboard when this draft was written.
- **Registers:** SRC-014, DER-023 to DER-027, TR-018 to TR-020, M-006, M-007, A-032 to A-047, A-050 to A-061, ISS-043 to ISS-052, ALG-012, ALG-013, EXP-021 to EXP-026, D-048 to D-055.

### 1.2 Headline results (central archetype A unless stated; `climate_matrix.md`, `climate_summary.json`)
- **Heating falls much more than cooling rises.** Thermostat heating electricity is 70,388 kWh in 2023 weather and 52,258 kWh at +3.0 C (-25.8 %). Added cooling electricity of the cooled buildings is 1,072 to 4,535 kWh a year across the low, medium and high levels (thermostat reference), 10,809 to 11,763 kWh in the alternative high assignment. Net district grid use (import minus export, thermostat) goes from 88,625 kWh (no cooling, 2023 weather) to 69,655 kWh (no cooling, +3.0 C) and from 90,312 to 72,866 kWh with high-level cooling.
- **Ceiling.** The exact optimum saves 15.96 % of the bill in 2023 weather (heating only) and 17.68 % at +3.0 C; with cooling 16.03 to 16.07 % (2023 weather) and 17.64 to 17.78 % (+3.0 C), always within about 0.1 point of the heating-only cell of the same climate.
- **Building mass.** Mass value (band minus pinned) is 1.40 to 1.58 points without cooling and 1.61 to 2.02 points with cooling at the three standard levels; 2.46 to 2.57 points in the alternative high assignment (houses and two apartment buildings cooled). The headline hypothesis (mass becomes much more valuable with cooling) is only weakly supported.
- **PV and cooling.** Under the default allocation rule PV covers 73 to 92 % of the cooling electricity directly with the thermostat and 71 to 98 % with the exact optimum (alternative high: 78 to 83 %); the battery adds 0 to 10 %; the rest comes from the grid (`climate_matrix.md` section 4). The rule is a bookkeeping choice.
- **Spill-over to the grid.** In the +3.0 C heat-wave cell with high adoption the cooled district imports 396 kWh more (thermostat) or 54 kWh more (optimum) than the heating-only district and exports 3,097 or 3,044 kWh less (section 3 of the matrix report). The summer peak does not change with the thermostat at the three standard levels; with the exact optimum it rises by 1.0 to 2.2 kW at +3.0 C (about 61 kW baseline) and by 2.8 kW (thermostat) and 4.1 kW (optimum) in the alternative high assignment.
- **Controllers on the eight held-out weeks.** MPC reaches 75 to 78 % of the exact optimum of the same weeks, the PV rule 37 to 45 %; the MPC without a peak term raises the highest hour to about 155 kW against 58 to 63 kW with the thermostat; with peak weight 0.1 it is 63 to 70 kW at the same or a slightly higher saving (`climate_matrix.md` section 2).
- **Archetype B (room units, f = 0.4):** cooling electricity is 0.40 of archetype A for the thermostat and 0.39 to 0.42 for the optimum (equal to f by construction), ceilings within 0.1 point, MPC share 75 to 78 % (`climate_archetypes.md`).

### 1.3 What Phase C did not establish
Cooling energy per building is a model output with unsourced parameters; no measured cooling exists for these buildings. The household load is a synthetic composite. The results describe one station, one weather year with climate deltas, and assumed adoption levels. They do not predict Swiss cooling demand.

## 2. Task status
| Task | Status | Assessment |
|---|---|---|
| C1 Review and update the proposal | Done | Proposal rewritten; S3-only basis because only the RC model reacts to weather |
| C2 Climate scenarios | Done | CH2025 Kloten, delta change on 2023 hours, heat-wave variants; hourly processing validated on 2023 (`climate_scenarios.md`) |
| C3 Cooling demand | Done (modeled) | M-006; parameters unsourced (A-040 to A-047); literature found by search, not read |
| C4 Adoption scenarios | Done with labelled defaults | 10.9, 30.4 and 52.2 % of dwelling units by whole buildings; not explicitly confirmed by the owner |
| C5 Heating and cooling integration | Done | Heating preserved (Phase B results reproduced); energy balance closes in rollouts (`test_climate_metrics.py`); replay equal to the program |
| C6 Scenario evaluation | Done for classical controllers | Ceiling, thermostat, PV rule, MPC, MPC with peak weight on 26 plus 20 cells |
| C7 Transferability and robustness | Partly | The Phase B RL learners were not re-run (none beat its reference in Phase B); MPC robustness to training weather and to forecast weather error tested on the heat-wave cells |

## 3. Acceptance criteria
Plan section 8.3: (1) historical and future climates represented: met. (2) climate inputs and hourly processing documented: met. (3) cooling modeled transparently: met (parameters unsourced). (4) three adoption scenarios: met (defaults). (5) heating-only and mixed districts comparable: met. (6) seasonal and peak metrics: met at district level; a per-building summer peak is not stored (partly). (7) controller performance compared across scenarios: met for classical controllers, RL not run. (8) assumptions traceable: met in the registers; the audit-bundle freshness is restored only by the final rebuild on a clean tree (pending). (9) validation limits documented: met. (10) reproducible: partly; the CH2025 download is a manual step with recorded hashes, the matrix commands are in `docs/reproduction.md`, a clean-clone reproduction was not run.
Proposal section 8: climates and heat waves (met); cooling replay-exact (met for the action mapping, not the physics, ISS-048, ISS-051); three adoption levels plus heating-only (met); metrics for every cell (met, per-building summer peak absent); ceiling, PV rule and MPC per cell (met); assumptions registered from A-032 (met); reproducible from scripts (partly); dashboard shows the matrix (met for archetype A, archetype B pending).

## 4. Climate datasets and scenario selection (`climate_scenarios.md`)
- **Source:** CH2025 DAILY-LOCAL, station Zuerich / Kloten, 20 files plus 2 metadata files (SHA-256 in SRC-014); 24 to 26 regional climate model chains, 30 model-years each, 365-day calendar, bias-adjusted by quantile mapping to 1991-2020.
- **Scenarios:** hist (2023 observed), gwl1.5, gwl2.0, gwl3.0 typical years; hist_hw99, gwl2.0_hw99, gwl3.0_hw99 (the matrix heat waves) and the p95 variants hist_hw, gwl2.0_hw, gwl3.0_hw (sensitivity only).
- **Selected spells (p99, mean tasmax of 7 days):** 30.9 C (reference, chain ICTP-REGCM-HADGEM), 33.8 C (+2.0 C), 36.4 C (+3.0 C); the p95 spells (27.7, 30.0, 32.2 C) are milder than the hottest observed week of 2023 (hourly mean 25.5 C over 168 h), which is why p99 is the heat-wave variant (ISS-044).
- **Scenario statistics (hourly files):** annual mean temperature 11.56 C (2023), 12.98 C (+2.0), 14.14 C (+3.0); days with hourly maximum at or above 30 C: 15, 34, 48; at or above 35 C: 2, 9, 12.
- **Validation:** reconstruction of the 2023 hourly series from its own daily minimum, maximum and mean gives RMSE 1.40 K over 362 days (hot days see the report); zero-delta identity tested; CH2025 ensemble statistics listed beside the scenario files.
- **Limits:** model chains, not observations; reference ensemble maxima reach 42.7 C at Kloten (ISS-043); CH2025 humidity exceeds 100 % in 0.01 to 0.03 % of values (ISS-045); the sub-daily cycle carries no climate signal; the hourly extremes are lower than the daily extremes by an amount not quantified.

## 5. Cooling model and archetypes
- **Archetype A, central (M-006):** one thermal node per building, whole building cooled, same device as the heating heat pump (rating, efficiency, 8 C supply), Carnot-fraction COP, off below 15 C outdoors, upper comfort limit 26 C in June to September (24 C otherwise), cooled buildings only; uncooled buildings float.
- **Archetype B, room units (M-007):** cooled fraction f = 0.4 (sensitivities 0.2 and 0.6) of the floor area, two independent zones, heating split by area, cooling capacity proportional to f, no schedule, no dehumidification.
- **Adoption (A-044, labelled defaults):** by dwelling units (46 in total): low MFH-small (10.9 %), medium MFH-medium (30.4 %), high MFH-large (52.2 %), alternative high MFH-medium, MFH-small and the three houses (47.8 %); whole buildings; one assignment per level, not nested; a level confounds adoption with building identity. Sources (searched 2026-11-19, summaries not read in full): no official statistic exists; today's estimates are 4 to 10 % of homes (survey and trade-association estimates, the 10 % excluding reversible heat pumps); Empa reports that over 50 % of households could have cooling systems later (scenario not confirmed); so 10 % and 50 % are supported as endpoints, 30 % is an interpolation, and the choice of which buildings are cooled has no source (regulation is reported to make fixed units harder in apartments than in houses, which is why `high_alt` with the houses is kept). Details in A-044.
- **Validation:** archetype A reproduces Phase B exactly; replay of the exact optimum in CityLearn equals the program (`hist_high` full year and 5,100 steps of `gwl3.0_hw99_high`: 0.000 % of the saving; `hist_hw99_high_ru` 5,100 steps: 0.000 %). The replay checks the action mapping, not the physics, because the program and CityLearn use the same RC step.
- **Literature status (reported by web search, not read):** fewer than one in ten Swiss homes has fixed air conditioning and portable units are popular (Swissinfo); Empa projects about 5 TWh a year of extra cooling demand in a moderate scenario and more than half of households with cooling later; a bottom-up Swiss housing-stock study gives about 10.2 TWh of cooling in 2050 (RCP 4.5) and notes that national residential cooling literature is scarce. No source was found for Swiss set points, partial-room cooling or schedules. The cooling parameters (26 C, 15 C cut-off, device equal to the heating device, f = 0.4) are assumptions.
- **Deferred by the owner (D-050, D-055, ISS-052):** reversible heat-pump supply-temperature variants (floor cooling) and ground-source passive cooling.

## 6. Scenario configurations
Every cell is an S3 district (assumed PV 1 kWp ratio, battery 1 kWh/kWp, RC building, export 8 Rp/kWh, EKZ two-tier tariff) with the scenario weather and PV. Cells are named `<weather scenario>_<adoption>` (`hist`, `hist_hw99`, `gwl2.0`, `gwl2.0_hw99`, `gwl3.0`, `gwl3.0_hw99` x `none`, `low`, `medium`, `high`; `gwl3.0_high_alt`, `gwl3.0_hw99_high_alt`) and `_ru` for archetype B (`_ru0.2`, `_ru0.6` sensitivities on `gwl3.0_hw99_high`). Cell datasets are generated (`swiss/pipeline/build_climate_datasets.py`, git-ignored). The control study uses the eight held-out weeks of Phase B (week 29 holds the inserted heat wave).

## 7. Controller comparison (`climate_matrix.md` section 2, `climate_matrix_ru.md`)
- **Exact optimum** (year, perfect foresight) is the ceiling; **thermostat** (heat to 21 C, cool to 26 C) is the reference; **PV rule** (Phase B rule on that thermostat); **MPC** (weather-conditioned forecasts, known weather, A-028) with and without the district peak weight 0.1.
- Shares of the exact optimum on the eight weeks: PV rule 37 to 45 %, MPC 75 to 78 % in both archetypes; with peak weight 0.1 the MPC saving is 11.40 to 12.95 % (central) at highest hours of 62.6 to 69.8 kW.
- Uncooled-building overheating hours are the same under the MPC and the thermostat (for example 17,228 against 17,228 K h for `gwl3.0_hw99_high`).
- **No RL in Phase C:** none of the Phase B learners beat its reference on any rung (`rl_phase_b.md`), and the exact-optimum gate is met, but a classical controller reaches 75 to 78 % of the ceiling; RL was not re-run (D-051).
- A flaw found before committing: the first MPC run gave uncooled buildings a free upper comfort slack and overstated its share of the ceiling; a penalty of 0.05 CHF per K h was added and all MPC runs repeated (D-051).

## 8. Seasonal and peak-demand results
- **Peaks:** the district peak of the exact optimum is 156.1 to 156.7 kW in winter for every cell (thermostat 72.6 to 80.1 kW); the summer peak of the optimum is 90.4 kW today, 73.0 to 73.2 kW at +2.0 C and 60.9 to 63.0 kW at +3.0 C (thermostat 37.1, 33.2, 32.9 kW) (`climate_matrix.md` section 1). The reason for the fall of the optimum's summer peak with warming was not analysed.
- **Seasonal import:** summer grid import (thermostat) in 2023 weather is 19,698 kWh without cooling and 19,833 kWh with high-level cooling (`climate_summary.json`).
- **Emissions index** per cell is in the cell JSONs ; the change from cooling is 0 to 73 kg a year (difference method, thermostat and optimum, standard and alternative cells).

## 9. Climate impact analysis (added consumption, PV mitigation, grid spill-over)
- **Method:** difference method (cell with cooling minus the heating-only cell of the same climate and controller) for added consumption, import, export and peaks; an hourly PV allocation rule (default: PV serves household load and DHW first, then the heat pump, then battery charging; sensitivity: heat pump first) only for the PV and battery coverage shares. Marginal attribution is not unique; the shares are bookkeeping (`swiss/experiments/climate_metrics.py`).
- **Added consumption** (central, thermostat, `climate_matrix.md` section 3): cooling electricity 1,072 to 4,535 kWh in the standard levels (alternative high 10,809 to 11,763 kWh); heating electricity changes by 9 to 22 kWh in the same cells (the cooled building also changes the district heating slightly).
- **Mitigation by PV:** section 4 of the matrix report lists PV direct, battery and grid shares per cell; with the heat-pump-first rule PV covers 95 to 99 % (thermostat) because cooling is served before other loads.
- **Spill-over to the grid:** added import 161 to 1,240 kWh (thermostat, standard levels) and added export reduction 857 to 3,317 kWh; most of the cooling electricity replaces exported PV. Per-house numbers (SFH and MFH) are in the cell JSONs and on the dashboard Houses page, not reproduced here.
- **Agent's reading:** in this model, cooling a district that already has PV and a battery changes the grid mainly by reducing exports, not by adding peaks; this depends on cooling being small (ISS-048) and on the PV and battery assumptions.

## 10. Robustness (`climate_matrix.md` section 5)
- Forecasters trained on 2023 only against trained on the scenario year: MPC share 76 % against 75 % (+3.0 C), 77 % against 77 % (+2.0 C and historical), as expected, since heating and cooling come from the RC model with known weather.
- Forecast weather bias: -2 K gives 69 % of the ceiling and 0.3 K h below 21 C; +2 K gives 74 % and 202.9 K h below 21 C (`gwl3.0_hw99_high`); irradiance noise of 30 % gives 66 %; +2 K with online correction and a 0.2 C margin gives 68 % and 1.3 K h cold. The errors are synthetic and labelled.

## 11. Limitations
- Cooling parameters are unsourced (A-040 to A-047, A-058 to A-061); cooling energy per building differs by archetype by construction (ISS-049); no latent load, shading or ventilation (ISS-048).
- Uncooled buildings overheat identically and strongly (8,244 K h above 26 C per building in 2023 weather) because the unshaded model and the pooled priors give every building the same temperature path; an indicator, not a prediction (ISS-046, ISS-050).
- The household load is a synthetic composite (ISS-040); tank sizes are unsourced (ISS-032); the MPC assumes known weather (A-028, ISS-047).
- One station, 2023 weather plus deltas; the heat waves come from model chains made hourly (ISS-043, ISS-044).
- The exact optima are perfect-foresight upper bounds. Replay checks the action mapping only (ISS-048, ISS-051).

## 12. Scientific implications (agent's reading, for the owner's review)
What the results support: within this model, the share of the bill that flexibility can save rises with warming (15.96 % to 17.68 %, mostly because the bill falls with heating); a forecast-based planner captures about three quarters of it and a PV rule about two fifths; cooling adds little electricity compared with the heating saved; PV covers most of it; the optimum's summer peak rises by 1 to 4 kW with cooling at +3.0 C but falls with warming overall; thermal mass is worth about 1.4 to 2.6 points depending on adoption assignment. What they do not support: a prediction of Swiss cooling demand, a claim about real buildings (no cooling data, synthetic load, unsourced device parameters), or a ranking of adoption levels (a level is a building choice, ISS-049 and the alternative-high cells show the dependence).

## 13. Provenance and registry status
SRC-014, DER-023 to DER-027, TR-018 to TR-020, M-006, M-007, ALG-012, ALG-013, A-032 to A-047 and A-050 to A-061, ISS-043 to ISS-052, EXP-021 to EXP-026, D-048 to D-055. Commits: 5fbaf2d (climate pipeline and cooling), 3c804fd and 392c287 (dashboard Phase B and forecast error), 8822bbe (matrix), 7b68d35 (dashboard Phase C), 46267cc (registers), e167f2c (room units). The audit bundle must be rebuilt on a clean committed tree to restore freshness and the registry lint.

## 14. Repository changes and reproduction
New modules: `swiss/pipeline/build_climate.py`, `build_climate_datasets.py`; `swiss/experiments/oracle_climate.py`, `climate_controllers.py`, `climate_matrix.py`, `climate_robust.py`, `climate_metrics.py`, `climate_archetypes.py`; extended `swiss/models/rc_building.py`, `swiss/citylearn_build/{rc_dynamics,build_dataset}.py`, `swiss/pipeline/build_pv.py`; dashboard `swiss/dashboard/phase_c.py`, `climate_series.py` and four web pages; cluster scripts `swiss/hpc/{climate_task.sbatch,submit_climate_matrix.sh,deploy_climate.sh}` (written, not run). Results: `swiss/experiments/climate_results/`, `climate_results_ru/`, generated reports in `docs/experiments/validation_reports/`. Reproduction commands are in `docs/reproduction.md` (CH2025 download is manual, hashes in SRC-014; matrix 75 minutes on 11 workers for archetype A and 42 minutes on 10 single-thread workers for archetype B).

## 15. Open decisions for the owner
1. Adoption levels (10.9, 30.4, 52.2 %), the building assignment and the 26 C set point (A-042, A-044) were not explicitly confirmed. Sources for the levels were searched on 2026-11-19: they support about 10 % and 50 % as endpoints and give no basis for 30 % or for which buildings are cooled (see section on adoption and A-044).
2. The wording of the dashboard findings, the Overview scope text and the story verdict (agent drafts).
3. Pushing to the repository and updating the public deployment (not done).
4. Whether to extend the model with reversible heat-pump supply-temperature variants and ground-source passive cooling (deferred), measured household loads, and shading or ventilation.
5. Whether to run the matrix again on the cluster with the written scripts if a larger design is wanted.

## 16. Stop
Phase C is implemented and awaits the owner's review. No further phase is started.
