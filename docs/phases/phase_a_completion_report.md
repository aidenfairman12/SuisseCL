# Phase A completion report — Swiss heating baseline (draft for user review)

Date: 2026-11-17 · Plan: `master_plan.md` v1.0 · Log: `execution_log.md` (EL-0001…) · Status: **Phase A implemented; one item pending (see 1.3); awaiting your review. Phases B and C not started.** Updated 2026-11-17 after the carbon method check.
Code/data state: commits `615e8b4`…`2fe420b` plus the final documentation commit (see section 9).

## 1. Summary
### 1.1 What was built
A reproducible hourly CityLearn 3.3.0 simulation of a **constructed six-building Swiss district** for the local year 2023: three single-family houses (HEAPO, air-source heat pumps with measured heat-pump meters) and three multi-family heat pumps (ETH/EKZ heat-pump meters) with a synthetic apartment-load composite; derived heating/DHW thermal demand; synthetic thermal tanks; KLO weather incl. diffuse radiation; EKZ standard two-tier tariff; modeled carbon-intensity series; four stock baseline controllers; reward R-001; validation, sensitivity, 56 automated tests, scripted pipeline and a registry audit.
### 1.2 Task status
| Task | Status | Notes |
|---|---|---|
| A1 repo/framework inspection, audit structure | **Completed** | CityLearn 3.3.0 verified; stock classes only; lockfile `swiss/requirements-lock.txt`; Quebec end-of-episode error never explained (not needed) |
| A2 dataset verification/acquisition | **Completed**, with deviations | HEAPO, ETH/EKZ, MeteoSwiss, Energy-Charts, IPCC factors used. JASM and the EPFL carbon dataset were downloaded but **not used**. ElCom 2026 not queried (licence unstated; EKZ 2023 used). HoroCarbon and Electricity Maps not usable. Swissgrid/SFOE route blocked (403), replaced by Energy-Charts |
| A3 building selection | **Completed** | D-006, user-accepted; composite, not real neighbours |
| A4 data processing | **Completed**, with open data caveats | hourly, DST-safe, QC reports; HEAPO 24 h gap filled (D-011, synthetic); SFH PV status unresolved |
| A5 heating and DHW model | **Completed**, thermal timing unvalidated | M-001 (D-014…D-016); SPF-anchored level |
| A6 weather, tariff, carbon | **Completed**, carbon level unvalidated | weather and tariff done; carbon is modeled; EPFL 2016–17 method check run (D-013b): shape agrees (hourly r 0.98), level is 61–63 % of EPFL, so use only for relative signals |
| A7 CityLearn integration | **Completed** | stock classes, full-year episode runs |
| A8 baselines and reward | **Completed** | ALG-001…004, R-001 (no learning agent, per plan) |
| A9 validation and evaluation | **Completed within limits** | internal-consistency checks pass; **no validation against observed thermal data is possible** |
### 1.3 Pending before Phase A can be signed off
1. ~~EPFL 2016–17 method check~~ done 2026-11-17 (`data/data_quality_reports/carbon_epfl_comparison.md`): partially passed.
2. Your review of the working defaults I applied without an explicit instruction (section 8).

## 2. Acceptance criteria (plan 6.3) — honest assessment
| # | Criterion | Assessment |
|---|---|---|
| 1 | Six representative buildings configured | **Met**, as a composite (3 HEAPO SFH + 3 EKZ multi-family heat pumps); multi-family non-heat-pump load is synthetic |
| 2 | CityLearn runs hourly | **Met** (8,760 steps, 27 s) |
| 3 | Heating, DHW, heat pump represented | **Met with caveats**: thermal demand derived, DHW of two houses stays in non-shiftable load, tanks synthetic |
| 4 | Weather integrated | **Met** (KLO hourly incl. diffuse; direct = horizontal beam; no real forecasts) |
| 5 | Tariffs and carbon documented and integrated | **Tariff met** (EKZ 2023, deviation from "2026" accepted D-012). **Carbon met but modeled; method check done: shape agrees, level 61–63 % of the EPFL reference** |
| 6 | Double counting checked | **Met** for the houses (Total = HP + Other exactly); not checkable for multi-family composites (synthetic) |
| 7 | Baseline controllers run | **Met** (EXP-007…012) |
| 8 | Data quality and validation reports | **Met**: `data_quality_reports/`, `validation_reports/`; validation is internal-consistency only |
| 9 | Everything registered | **Met** by `registry_audit.md` (0 broken references); completeness of descriptions is my judgement |
| 10 | Reproducible with documented instructions | **Partly verified**: `reproduction.md` written; rebuild from raw reproduced all 31 manifested files byte-identically (EL-0043); not run from a clean machine |

## 3. Final building selection (D-006)
| Role | Source/ID | Size | 2023 HP electricity (kWh, measured) | Notes |
|---|---|---|---|---|
| SFH-low | HEAPO 7069411 | 220 m², 4 res. | 4,721 | EV in survey (ISS-026); HP DHW per survey but summer use ≈0 |
| SFH-mid | HEAPO 8011310 | 166 m² | 6,038 | electric water heater (DHW in non-shiftable) |
| SFH-high | HEAPO 1181060 | 260 m² | 11,493 | electric water heater; unexplained 10 kWh/day summer HP use (ISS-027) |
| MFH-small | EKZ 154832 | 5 units | 12,715 | + common-area meter measured, apartment load synthetic |
| MFH-medium | EKZ 145442 | 14 units | 25,716 | metadata flag `hp` False although HP meter (ISS-019) |
| MFH-large | EKZ 197873 | 24 units | 21,103 | same |

## 4. Dataset inventory and provenance
Full detail: `data/data_source_registry.csv` (SRC-001…011, DER-001…011), `data/transformation_log.md` (TR-001…010). Raw files hashed; derived files in `data/canonical/MANIFEST.sha256`.
| Used | Source | Licence/access | Classification |
|---|---|---|---|
| yes | HEAPO (Zenodo 15056919) | CC BY 4.0 | measured |
| yes | ETH/EKZ load profiles and tariffs (Zenodo 21398769) | CC BY 4.0 | measured |
| yes | MeteoSwiss OGD KLO hourly | open, cite source | measured |
| yes | Energy-Charts API (CH, DE, FR, AT, IT, flows) | CC BY 4.0 | measured (ENTSO-E-derived; completeness unverified) |
| yes | IPCC AR5 Annex III Table A.III.2 | published | literature |
| yes | Arpagaus et al. 2023 (SPF) | published paper | literature |
| downloaded, **unused** | JASM/CESAR profiles | **no stated licence**; private use only (D-004) | modeled (simulated) |
| yes (check only) | EPFL hourly emission factors 2016–17 (CC BY 4.0 data) | used for the carbon method check, not as an input | modeled |
| not obtained | HoroCarbon, Electricity Maps (paid), ElCom 2026 tariffs, Swissgrid/SFOE | see ISS-006, 013, 015, 017 | — |
## 5. Model and algorithm inventory
Models: M-001 heat-pump COP/thermal demand; M-002 carbon intensity (`models/model_registry.md`, `parameter_registry.csv`, `model_assumptions.md`). Algorithms: ALG-001 zero action, ALG-002 BAU (identical to ALG-001 here), ALG-003 BasicRBC, ALG-004 tariff-aware HourRBC (r = 0.05/0.10/0.20); reward R-001 (`algorithms/`). No learning algorithm in Phase A.
## 6. Data quality and validation findings
- Quality: no duplicates, negatives or long zero runs in measured series; **all three HEAPO series miss the same 24 h (2023-10-29)**, filled as synthetic (D-011, backtested); EKZ complete; synthetic composites had hour gaps, fixed by D-015; weather complete (one diffuse hour NaN set to 0).
- HEAPO Total = HP + Other exactly (double-counting resolved for houses).
- Electricity and heat balances close to 1e-6 kWh; storage SOC bounded; tariff arithmetic consistent; seasonality qualitatively correct; demand–weather alignment 0–1 h for houses, not identifiable for the two large multi-family buildings.
- Derived heat: η = 0.35–0.39 (≈ 40 % Carnot, consistent with the primary paper); heat 79–153 kWh/m²a for the houses (plausibility only). **Heat timing is unvalidated**: the HDD-linearity diagnostic proved uninformative (reported openly in `qc_thermal_2023.md`).
- Controllers (EXP-007…012, 2023): zero action import 214,715 kWh, peak 72.0 kW, cost 35,750 CHF excl. VAT. Rule-based controllers shift 1.9–4.4 points of import out of the high tariff and change the peak by −6.7 %…+1.8 %, but **raise cost by 0.15–1.1 % and carbon by 1.7–2.4 %** in all five sensitivity variants (tank size ×0.5/×2, tank efficiency 0.99, flat COP). Cost and carbon pull in opposite directions (cheap night hours have the highest modeled carbon). All from synthetic tanks and a modeled carbon series: **indicative only**.
## 7. Known limitations and outstanding issues
Authoritative list: `decisions/issues_and_risks.md` (ISS-001…033). Most important for interpretation:
- Composite district, not real neighbours; multi-family non-heat-pump load synthetic.
- No measured thermal output, indoor temperature or comfort; indoor temperature is a constant placeholder; thermal timing unvalidated; peak hourly heat probably high (ISS-030).
- Storage is synthetic (sizes, efficiency 0.95, loss 0.3 %/h); every controller conclusion depends on it (ISS-029, ISS-032).
- Carbon is a first-order model with generic factors and proxies, mean 58 g/kWh; EPFL check: pattern matches (r ≈ 0.98) but level is 61–63 % of EPFL's, so absolute values are a lower estimate (ISS-033, D-013b).
- SFH PV status unknown (ISS-021); EKZ heat-pump type air/ground unknown (ISS-019); HEAPO timestamp convention unconfirmed (ISS-024, ISS-031); SPF level from literature (ISS-028).
- JASM unused and without licence; ElCom 2026 not used.
## 8. Working defaults applied by me that you have not explicitly confirmed (please review)
D-007 time convention; D-009 MeteoSwiss end-of-interval convention (inferred, unverified in docs); D-010 single station KLO; D-015 apartment composite rule; D-017a tank sizes and efficiency; D-018 CityLearn conventions (constant 21 °C, inactive forecasts); the proxy emission factors A-006…A-009; the choice to keep carbon weight 0 in R-001; D-013b (carbon series used for relative signals only).
## 9. Repository changes
Commits: `615e8b4` docs tree; `f325273` pipeline + tests; `b068bf9` derived data; `ba4adc3` log; `2ac0b40` thermal/CityLearn dataset; `8204282` docs; `d3de37c` A8; `2fe420b` A9/carbon; final documentation commit follows. New directories: `swiss/` (pipeline, models, citylearn_build, experiments, validation, tests, datasets), `data/` (raw ignored, interim, canonical), `docs/` (full tree). CityLearn and `my_data/` untouched (only `my_data/hpc/requirements-dev.txt` added).
## 10. Reproduction
`docs/reproduction.md`; rebuild script `swiss/run_pipeline.sh`; tests `PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q` (56 pass).
## 11. Proposed modifications to Phases B and C (for your approval; nothing implemented)
**Phase B (15-min, PV, battery, tariffs, LEG, RC model, EV):**
- *Reorder:* start with B1 data review and the unresolved items above (SFH PV status via returned energy, EKZ heat-pump type, HEAPO label convention).
- *15-min pipeline (B2):* feasible now (15-min extracts already preserved); CityLearn at 900 s steps must be tested (not tried).
- *PV (B3):* HEAPO PV flags (516 yes of 650 known) and returned energy; ETH/EKZ `kWh_to_grid` (41 single-family houses export >100 kWh); SFOE/MeteoSwiss radiation for a PV model; **demand reconstruction needed** where PV self-consumption hides load.
- *Tariffs (B5):* the EKZ file already contains pilot ToU, dynamic and unit tariffs for 2023–24 (good for dynamic-tariff studies; applicability limited to pilot participants); export remuneration needs a separate source (ElCom).
- *RC thermal model (B7):* **blocked by data**: no measured indoor temperature in HEAPO or ETH/EKZ. Needs another dataset (e.g. Empa NEST measurements, seen in search, not evaluated) or an explicitly synthetic calibration; recommend a decision before B starts.
- *EV (B8):* ETH/EKZ has 56 EV-charging meters and 18 controlled-charging customers; HEAPO survey has EV flags (SFH-low).
- *Learning controllers:* reward needs a comfort term once thermal dynamics exist; Phase A showed small baseline gains, so expect small RL gains unless flexibility assets are larger or tariffs more dynamic.
**Phase C (climate, cooling):**
- Hourly future-climate weather for Zurich is not yet sourced; cooling-demand data are not in HEAPO/EKZ; JASM has simulated cooling profiles (climate undocumented, no licence) — recommend identifying a cooling data source and the adoption evidence **before** authorizing C; the KLO 2023 series could serve as a baseline for delta-change scenarios.
## 11b. Carbon method check (added 2026-11-17)
2016 and 2017 reconstructed with the same code and compared with the EPFL hourly series: hourly Pearson 0.977/0.976, monthly 0.996/0.995, diurnal 0.996/0.951; means 110/115 vs 179/184 g CO2eq/kWh (ratio 0.61/0.63). Agreement is driven by the import share (correlation with EPFL 0.84), so it supports timing and shape, not the absolute level. Full discussion: `docs/data/data_quality_reports/carbon_epfl_comparison.md`.

## 12. Stop
Per plan 9.5 I stop here. I will not start Phase B or C without explicit authorization and an updated plan.
