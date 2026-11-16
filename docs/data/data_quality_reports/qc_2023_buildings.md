# QC report — six buildings, year 2023 (Task A4, TR-004)

Generated from `docs/data/data_quality_reports/qc_2023_buildings.json` by `swiss/pipeline/build_buildings_hourly.py`
(code version: HEAD `35c59a9` + uncommitted). Window: local year 2023 = UTC 2022-12-31 23:00 to 2023-12-31 22:45 → 8,760 hourly slots. No imputation, no interpolation, no outlier removal was applied; findings are flagged only.

## Checks and results
| Check | Result |
|---|---|
| Duplicate timestamps | 0 in all six 15-min series |
| Timestamp grid | all series reindexed to the full 15-min UTC grid (35,040 slots); local clock fields derived from UTC; DST-active hours = 5,208 (Mar 26 – Oct 29); local-hour sequence shows the spring skip of 02:00 |
| Negative values | 0 in all measured series |
| Zero runs ≥ 24 h | 0 in all measured series |
| Extreme hours (>5× P99) | 0 except MFH-small common-area meter (13 h; max 2.4 kWh) |
| **Double counting (HEAPO)** | `kWh_received_Total` = `kWh_received_HeatPump` + `kWh_received_Other` **exactly** (max |diff| < 1e-15 over 34,944 quarter-hours, all three SFH). **Total already includes the heat pump**, so non-HP load = Total − HP (= `Other`). Never add HP to Total. |
| EKZ HP meter export | 0.0 / 0.003 / 0.0 kWh to grid in 2023 → no PV signature on the HP meters |

## Per-building coverage (hours with a valid hourly value out of 8,760)
| Role | HP electricity | Non-HP load | Notes |
|---|---|---|---|
| SFH-low (HEAPO 7069411) | 8,736 | 8,736 (measured) | HP 4,721 kWh, other 5,998, total 10,719 |
| SFH-mid (HEAPO 8011310) | 8,736 | 8,736 | HP 6,038, other 5,255 |
| SFH-high (HEAPO 1181060) | 8,736 | 8,736 | HP 11,493, other 2,728 |
| MFH-small (EKZ 154832) | 8,760 | apartments synthetic 8,540; common areas measured 8,760 | HP 12,715 kWh; common 1,768; 5-apartment composite 10,402 |
| MFH-medium (EKZ 145442) | 8,760 | synthetic 8,509; common 8,760 | HP 25,716; common 18,925 (two meters; large vs HP, unexplained); 14-apt composite 37,025 |
| MFH-large (EKZ 197873) | 8,760 | synthetic 8,503; common 8,760 | HP 21,103; common 8,570; 24-apt composite 39,665 |

## Findings requiring attention
1. **Common 24 h gap in all three HEAPO series:** 2023-10-29 02:00 → 2023-10-30 00:00 local (= the whole UTC day 2023-10-29, the autumn DST-change day). Identical across three unrelated households → systematic source artefact, not a metering fault of individual buildings. Left as NaN (ISS-020); treatment is a decision for A5/A7.
2. **PV status of the three SFH remains unresolved.** The HEAPO daily file used as PV indicator (`kWh_returned_Total`) has no 2023 rows for 7069411/8011310 (daily files end in 2020) and only empty values for 1181060 (250 rows). Survey flag: 7069411 = no PV; others unknown. Import-only data would under-state demand if PV self-consumption exists (ISS-021).
3. **Synthetic apartment composites** have 220–257 missing hours because any missing hour in any of the 5/14/24 drawn meters voids the sum. They are *synthetic* and not the real building (ISS-018); treatment of the gaps to be decided in A5.
4. **MFH-medium common-area electricity (18.9 MWh) is large relative to its HP (25.7 MWh).** Could include loads other than common areas (e.g. garage, hot-water). Unexplained; not used for any claim yet.
5. **Seasonal plausibility (qualitative only):** HP kWh/day Jan vs Jul–Aug = 31.6/0.4 (SFH-low), 37.5/1.5 (mid), 60.5/10.0 (high). Summer residual is DHW and possibly other uses; SFH-high summer load of 10 kWh/day is high and unexplained. This is a plausibility look, not validation.
6. **Weather (HEAPO-supplied MeteoSwiss subset):** stations `Hg` (SFH-low, SFH-high) and `8jB` (SFH-mid) have full 8,760 h coverage of temperature, humidity, sunshine duration, precipitation, wind in 2023 (T range −11.3…35.5 and −12.9…36.0 °C). **No solar irradiance**; MFH have no station assignment; station IDs are hashed so real station/coordinates are unknown (ISS-022).
7. **Outputs are in UTC with derived local fields**; `treatment` group household 7069411 had a consultant visit — timing relative to 2023 not resolved because `AffectsTimePoint` is "unknown"/absent in 2023 daily rows (HP behaviour may have been changed before 2023; ISS-023).

## Not done in A4 (deferred)
Solar radiation, tariff and carbon alignment (A6); thermal-demand derivation and DHW split (A5); handling of NaN hours (A5/A7); CityLearn CSV/schema (A7).
