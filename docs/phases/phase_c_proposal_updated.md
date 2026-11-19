# Phase C proposal, updated after Phase B (for the owner's approval; nothing implemented)

Date: 2026-11-19 · Replaces the proposal of `phase_a_completion_report.md` section 11 and the Phase C wording of `master_plan.md` section 8. Phase C stays unauthorised until the owner approves this document.

## 1. Question
How do warmer climates and more cooling change district electricity demand (summer peaks, seasonal totals), and does that change what a controller can save? Phase B answered the heating-and-PV version: the exact ceiling is 0.84 % of the bill without PV and 6 % to 16 % with assumed PV and battery (S1 to S3), mostly from tanks, battery and PV, little from building mass. Cooling adds a summer load that coincides with PV generation, which is where the Phase B result could change.

## 2. What Phase B changes for Phase C
- **Method that carries over**: ceiling-first (exact optimum with replay, then RL only where the ceiling is at least 3 % of the bill); labelled assumptions; provenance classes; additive data contract.
- **Model pieces that carry over**: PV (pvlib, any weather), battery, export accounting, metrics module, RC building model (single node, per m2 priors), thermostat baseline, scenario machinery in `rl.py`.
- **Gaps Phase C has to close**: the RC model has no cooling (indoor temperature exceeds 24 C in about 2,700 hours a year under heating only, A-020); the CityLearn building classes needed for cooling (`cooling_device`, `cooling_storage` actions, a heat pump in cooling mode) are not yet used in the Swiss datasets; weather is hourly only (ISS-035) and has no future-climate series.
- **Finding to respect**: cost-optimal schedules raise coincident peaks (S2 +74 %, S3 +96 %), so summer-peak questions need a peak-aware objective or a peak constraint in the ceiling (the learners' reward already has a peak term).

## 3. Climate scenarios (task C2): data route to decide
Checked by web search on 2026-11-19 (reported, not verified in the data):
| Route | What it offers | Open points |
|---|---|---|
| A. CH2025 official datasets (MeteoSwiss) | 30-year **daily** series per station (DAILY-LOCAL, seven variables) and on a 1 km grid, four warming levels between 1.5 and 3.0 C plus the 1991-2020 reference; CC BY 4.0; open data (opendata.swiss, STAC collection `ch.meteoschweiz.ogd-climate-scenarios-ch2025`) | which seven variables (radiation?), whether Zurich/Kloten is a station, no hourly product found; needs our own hourly disaggregation (delta change on the KLO 2023 hourly series) and its validation (plan C2) |
| B. SLF/EPFL hourly scenarios built on CH2018 (delta change) | hourly temperature, precipitation, humidity, wind and shortwave radiation 1990-2100 for 72 MeteoSwiss stations (extended to 116 IMIS stations), data and code free | whether KLO or a Zurich-area station is included; CH2018 not CH2025; diffuse radiation needed by the PV model may be absent |
**Recommendation**: first check route B for Kloten and the radiation variables (a licence and metadata check, no download); if it fits, use it as the hourly source and cross-check its warming against CH2025 daily deltas; otherwise use route A with a documented delta-change disaggregation of the 2023 KLO hours. Decision needed from you: which route, and approval to download the chosen files (small).

## 4. Cooling demand and system (task C3)
- No measured cooling exists in HEAPO or ETH/EKZ; the JASM profiles contain simulated cooling but have no licence (D-004, not usable for publication). Cooling demand will be **modeled** (labelled synthetic): extend the RC model with a cooling mode (set point 26 C as in CityLearn defaults, cooling COP from the Carnot-fraction form of CityLearn's heat pump, internal and solar gains as in M-005).
- Compare against the Phase B representation (heating-only) as in `rc_vs_phase_a.md`; no validation against measured cooling is possible (state this as in ISS-004).

## 5. Cooling adoption levels (task C4): proposal for your approval
Evidence found (reported): fixed air conditioning in roughly 5 to 10 % of Swiss homes (sources disagree; reversible heat pumps are not counted in that figure); sales rising sharply after the 2025 heatwaves; Empa (2021) projects that cooling demand adds about 5 TWh per year in a moderate scenario and that more than half of households could have cooling systems by mid-century. The evidence is thin and partly commercial, so the percentages below are a proposal, not a measurement:
| Level | Share of dwelling units with cooling | Reading |
|---|---|---|
| low | 10 % | roughly today |
| medium | 30 % | assumed intermediate |
| high | 50 % | Empa's order of magnitude for later this century |
Representation across the six buildings: apartment buildings get the share as a fraction of units (units cooled by the same heat pump or split units are an assumption to document); the houses get cooling as a whole: low none, medium SFH-high, high SFH-mid and SFH-high (a deterministic assignment, not a random draw).

## 6. Scenario matrix and gates (tasks C5 to C7)
Reference: historical climate (2023 hourly) with the three adoption levels and the heating-only district; warming levels moderate (+2 C) and high (+3 C, within CH2025's 1.5 to 3.0 C range) times three adoption levels, optionally +1.5 C. For every cell compute the exact optimum (with replay) of the S3 district with cooling, report summer and annual import, coincident and summer peaks, PV self-consumption, heating and cooling energy, relative emissions, and apply the 3 % gate before any RL. Transferability (C7): evaluate the Phase B learners (if they finish and pass) on the cooling scenarios without retraining, then retrain only where the gate passes.

## 7. Work packages and effort (agent time, my estimate)
1. Climate route check and hourly weather (1 to 2 days, data decision needed)
2. RC cooling extension, CityLearn integration, tests (2 days)
3. Adoption representation and scenario datasets (1 day)
4. Exact optima and metrics across the matrix, replay (2 days; the 15-minute path stays optional)
5. RL on gated cells (cluster, hours to a day), report (1 day)

## 8. Decisions needed from you
1. Climate data route (A or B) and permission to download the chosen small files.
2. Adoption levels 10, 30, 50 % and the building assignment of section 5, or your own.
3. Whether the peak-aware objective is in scope for Phase C (recommended: report coincident and summer peaks in every cell, optionally add a peak constraint to the exact programs).
4. Whether the dashboard and data contract should be extended to Phase B and Phase C scenarios (not done in Phase B).
