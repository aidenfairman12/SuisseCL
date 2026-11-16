# Building selection design (Task A3) — v0.1, 2026-11-16

Status: **accepted by user 2026-11-16 (D-006); subject to A4 QC replacement rule.** Six candidate buildings were chosen by a rule-based script
(`swiss/pipeline/select_buildings.py`) on summary statistics only; no hourly series has been inspected or cleaned yet.

## 1. Constraints from the verified data (ISS-003, ISS-011)
- The two measured sources cover **different physical buildings**. A six-building "district" is therefore a **constructed composite**, not six neighbours. No claim of spatial or electrical adjacency is made.
- HEAPO: ~all single-family houses; heat-pump sub-meter in only 93/1,407 households (47 with ≥95 % coverage in 2022 or 2023 on both meters in 2023; see below). Survey states air- vs ground-source.
- ETH/EKZ: the 1,458 apartment meters sit in one anonymous catch-all object — **whole multi-family buildings cannot be reassembled from them**. What EKZ does provide for multi-family buildings is a **dedicated heat-pump meter** (67 on "Apartment building" objects, `num_housing_units` known, 4–61 units) plus, for some, common-area meters. EKZ metadata does **not** state air- vs ground-source.
- Only **calendar year 2023** is covered by both datasets (HEAPO ends 2024-03-21; EKZ starts 2023). Simulation year proposed: **2023**.
- Source import meters record electricity *received*; PV self-consumption would hide demand. PV status is unknown for most HEAPO households (flag filled for 650/1,408). PV detection via returned energy (HEAPO daily files; EKZ `kWh_to_grid`) is a Task A4 check; PV is not modelled in Phase A.

## 2. Selection rules (fixed before looking at IDs)
Common: ≥95 % non-null 15-min coverage in 2023 on the relevant meter(s); no duplicate timestamps.
- **Single-family (3):** HEAPO, air-source, dedicated HP sub-meter, building type "house", living area known. Pool split in terciles of 2023 HP electricity (low/mid/high); take the household nearest the stratum median. Pool: 26 households (9/8/9).
- **Multi-family (3):** EKZ "Heat pump" meters on "Apartment building" objects, ≥4 housing units, ≥95 % coverage in 2023 **and** 2024. Strata by units: small 4–6, medium 7–14, large ≥24; take the meter nearest the stratum median of kWh per housing unit. Pool: 59 meters (38/18/3).
Rationale: spread over consumption level and building size, no cherry-picking on data "niceness"; fully reproducible. Alternatives considered: random draw with seed (rejected: less covers extremes); picking best-coverage (rejected: biases towards unrepresentative clean data).

## 3. Proposed six
| Role | Source / ID | Size | 2023 HP electricity (measured, kWh) | Other |
|---|---|---|---|---|
| SFH-low | HEAPO 7069411 | 220 m², 4 residents | 4,723 | total 10,721 kWh; PV flag False |
| SFH-mid | HEAPO 8011310 | 166 m², 4 res. | 6,038 | total 11,293; PV status unknown |
| SFH-high | HEAPO 1181060 | 260 m², 2 res. | 11,493 | total 14,221; PV status unknown |
| MFH-small | EKZ meter 154832 (object 229735) | 5 units | 12,715 | `1_hp` True |
| MFH-medium | EKZ meter 145442 (object 293577) | 14 units | 25,698 | `1_hp` False in metadata |
| MFH-large | EKZ meter 197873 (object 274987) | 24 units | 21,101 | `1_hp` False; only 3 in pool |

Per-unit HP electricity differs strongly (≈2.5 / 1.8 / 0.9 MWh per unit for small/medium/large) — large building's HP meter may not cover all heating or DHW. To be checked, not assumed.

## 4. What is measured vs derived vs modeled per building
| Variable | SFH (HEAPO) | MFH (EKZ) |
|---|---|---|
| Heat-pump electricity | measured (HP sub-meter) | measured (HP meter) |
| Non-shiftable (other) electricity | measured (`kWh_received_Other`, or Total − HP) | **not measured for this building**: synthetic composite = sampled EKZ apartment meters (statistically drawn, scaled by housing units) + common-area meters when linked; label *synthetic* |
| Heating thermal demand | derived: HP electricity × COP(T_out) (D-003) | same |
| DHW thermal demand | modeled split (rule TBD; EKZ `1_hp-wh`/`1_ewh` flags and HEAPO survey `DHW_Production_*` inform it) | same |
| Indoor temperature | **not available** → modeled by CityLearn dynamics/ not measured | same |
| Weather | measured (MeteoSwiss station of HEAPO `Weather_ID`) | measured (station TBD, Zürich area) |
| Tariff | assumption (EKZ price file; ISS-012) | same |

## 5. Risks / open points for review
1. EKZ HP type unknown (air vs ground) while CityLearn's COP is air-source-like; ground-source would have higher, flatter COP. Mitigation: record as assumption; sensitivity test in A9.
2. Three MFH are anchored on **one HP meter each** plus a synthetic electricity composite; apartment loads cannot be matched to the building.
3. MFH-medium/large `1_hp` flags False despite an HP meter — metadata inconsistency to resolve (inspect profiles in A4) before final acceptance; fallback picks exist in the pool.
4. SFH PV status unknown for two of three; check returned energy in A4; replace by next-nearest household if PV found.
5. One simulation year (2023); heating season only from Jan-Dec 2023, cold-year representativeness not assessed.
6. Selection is on summary statistics; a replacement rule (next nearest to stratum median) is defined if A4 QC rejects a building, and every replacement will be logged.
