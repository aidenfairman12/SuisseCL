# WP1 registry draft (Phase C, climate scenarios): entries for the parent to merge

Not applied to any register. Proposed IDs are placeholders (SRC-014, DER-023 to DER-026, TR-018 and TR-019, A-032 to A-039, ISS-043 to ISS-045, EXP-021); renumber when merging.
Generated outputs and the report: `swiss/pipeline/build_climate.py`, `docs/experiments/validation_reports/climate_scenarios.md`, tests `swiss/tests/test_climate.py` (34 tests).

## Data source (docs/data/data_source_registry.csv, one SRC row)
- **SRC-014**: Climate CH2025 DAILY-LOCAL, station Zuerich / Kloten (KLO). Publisher MeteoSwiss and ETH Zurich (2025). Citation required: "MeteoSwiss & ETH Zurich (2025): Climate CH2025 - Daily Datasets. Federal Office of Meteorology and Climatology MeteoSwiss, Zurich, https://doi.org/10.18751/climate/scenarios/ch2025/data/1.0/" (version 1.0.0, created 2025-10-07 per the file header). Access: STAC collection `ch.meteoschweiz.ogd-climate-scenarios-ch2025` on data.geo.admin.ch, files at `https://rgw.cscs.ch/mchogd:cscs.meteoswiss.ogd.climate/ogd-climate-scenarios-ch2025/klo/`. Licence CC BY 4.0 (file header and STAC metadata; the MeteoSwiss documentation page says "may be used without restriction, source must be cited"). Access date 2026-11-19 (download approved by the owner in chat). Format CSV, semicolon separated, header block, then `DATE;<chain>...`; daily; 30 anonymous model-years (0001 to 0030), 365-day calendar, 21 to 26 regional climate model chains per variable (tas, tasmin, tasmax, rsds: 26 at ref91-20, gwl1.5, gwl2.0 and 24 at gwl3.0; hurs 21), `NA` for missing (about 750 values per file); levels ref91-20, gwl1.5, gwl2.0, gwl3.0; variables used: tas, tasmin, tasmax, rsds (global radiation, daily mean W/m2), hurs. Not used: sfcwind, pr, gwl2.5. Classification: modeled (bias-adjusted by quantile mapping and downscaled regional climate model output, calibration 1991-2020). Local path `data/raw/ch2025_klo/` (git-ignored, 27 MB, 20 data files and two metadata files `..._meta_stations.csv`, `..._meta_parameters.csv`). Check: station KLO exists in the station list (type: automatic weather station, 426 m, data since 1935-01-01).
- SHA-256 of the downloaded files (from `data/raw/ch2025_klo/SHA256SUMS.txt`):

| File | SHA-256 |
|---|---|
| ogd-climate-scenarios-ch2025_klo_hurs_gwl1.5.csv | 0414af241146a9713837ed1854987f2053f940c9626a158e5a12fe3133b5af2c |
| ogd-climate-scenarios-ch2025_klo_hurs_gwl2.0.csv | fe8b51fadae1aaaf9306655147d31178cf370807a95723d01c2c5b9019ac164b |
| ogd-climate-scenarios-ch2025_klo_hurs_gwl3.0.csv | b2a0b3d072f917f5271f5985e591341c68e7c733040b82e434d9339a2e7e8e28 |
| ogd-climate-scenarios-ch2025_klo_hurs_ref91-20.csv | 22d16fb7e6b640471679dd08328ec8208cba50c396965aaa09a4f53e318c8bc2 |
| ogd-climate-scenarios-ch2025_klo_rsds_gwl1.5.csv | 93750f6db1eaaa9a731dd1edfd633fc282d404588395601641cdf5a75c057671 |
| ogd-climate-scenarios-ch2025_klo_rsds_gwl2.0.csv | bff1f00fae90f599da4ab60c081f2a8ad31e31a1f8c0459c2c785530475aa284 |
| ogd-climate-scenarios-ch2025_klo_rsds_gwl3.0.csv | 2cab3e3ff36b9a9e74a87b5a4fd727e61c32b612b52ee2407211520fe0c1a0b8 |
| ogd-climate-scenarios-ch2025_klo_rsds_ref91-20.csv | 2acc339017d8f1ad22f0fbe83121f5c5ba88caad5aa4651ec9e1dad49704a04b |
| ogd-climate-scenarios-ch2025_klo_tas_gwl1.5.csv | f4fae033fa3cd5e5f3d04f8e22e6d001e6efb9c90fd693a1fd260dd5b80b91f7 |
| ogd-climate-scenarios-ch2025_klo_tas_gwl2.0.csv | 11882b5279d3679cc0a3ca89da827a4996de659dcecbae9a253d10f2d160f45d |
| ogd-climate-scenarios-ch2025_klo_tas_gwl3.0.csv | bdb7d9b354a410d1e5b94c2c4a8fac498a0212e5f92fe4485c3194aad55d3bab |
| ogd-climate-scenarios-ch2025_klo_tas_ref91-20.csv | e25302564a8fe7eb8b5e2ac05a6ad209bbdd2e0e576ba46a8c2fdb3f0dbc211a |
| ogd-climate-scenarios-ch2025_klo_tasmax_gwl1.5.csv | fca5542771b801e1a234ebe20952cc7632b09ada524302e4d142212e34c1b643 |
| ogd-climate-scenarios-ch2025_klo_tasmax_gwl2.0.csv | 9b2a553d68c52dcd59e56ca8a53d5f7d50ce9d2cd6d858f99c9c018bdbce39c2 |
| ogd-climate-scenarios-ch2025_klo_tasmax_gwl3.0.csv | 3ea4ea52cac79a6b60b732063e211eb8e9dbbc8059489e2ce8f7f8c169f55a03 |
| ogd-climate-scenarios-ch2025_klo_tasmax_ref91-20.csv | 828ce44bf6c76e643d2604ada194ac35dbc57cc6c060160218c0a6bf1ff10a4c |
| ogd-climate-scenarios-ch2025_klo_tasmin_gwl1.5.csv | 32873fc0663217c2509da1224cdc292fd351c9bc445ec788c3a09257170c3e2c |
| ogd-climate-scenarios-ch2025_klo_tasmin_gwl2.0.csv | c14b8d842159b9b12effa22cd645d77b5dd2a4e42ffd1bc16a0d154da193cee1 |
| ogd-climate-scenarios-ch2025_klo_tasmin_gwl3.0.csv | ff6a772bc310a3966957562ac925b18c22b61cd2d69d3fba04a187f42fbf65ef |
| ogd-climate-scenarios-ch2025_klo_tasmin_ref91-20.csv | 44c0e4cdbc56fdbeba35e4340162ea7b83c462525d2cef8b1760e49bd8d4e218 |
| ogd-climate-scenarios-ch2025_meta_parameters.csv | cbbccf0c4ff936d207914ef0d48ed8f13f9fc98677eb5956f4eaf0909e95af22 |
| ogd-climate-scenarios-ch2025_meta_stations.csv | efba63a7804e132387e68199a610966ca00bade92c61e272fb6a194280097fa8 |

## Derived datasets (data_source_registry.csv, DER rows)
- **DER-023**: `data/canonical/climate/weather_klo_<scenario>_hourly.csv` for gwl1.5, gwl2.0, gwl3.0 (typical warmed 2023) and hist_hw, gwl2.0_hw, gwl3.0_hw (default percentile 95 spells) and hist_hw99, gwl2.0_hw99, gwl3.0_hw99 (percentile 99): hourly weather with the columns of DER-007 (timestamp_utc, temp_c, rh_pct, ghi_wm2, diffuse_wm2, sunshine_min, beam_horizontal_wm2), 8760 rows. Classification: modeled (climate deltas) on measured (2023) anchor; synthetic in the spell weeks. `hist` is DER-007 itself (not duplicated).
- **DER-024**: `data/canonical/climate/pv_ac_w_per_kwp_<scenario>_hourly.csv` (same scenario names): PV per kWp by M-003 with scenario weather (same columns as the 2023 PV file).
- **DER-025**: `data/canonical/climate/heatwave_spells.json`: chosen spells (chain, model-year, start, severity, daily values), severity quantiles, rule, inserted rows.
- **DER-026**: `docs/experiments/validation_reports/climate_scenarios.md`: generated validation report (deltas, spells, reconstruction RMSE, scenario statistics, limitations).
- Size of `data/canonical/climate/`: about 7 MB (19 files, in the canonical manifest unless excluded by the parent).

## Transformation lineage (docs/data/transformation_log.md)
- **TR-018** inputs SRC-014 and DER-007; output DER-023 and DER-025; script `swiss/pipeline/build_climate.py` (functions `monthly_deltas`, `apply_deltas`, `select_spell`, `insert_spell`); parameters: monthly ensemble-median deltas by local calendar month (tas, tasmin, tasmax additive; rsds, hurs ratio), hot-day threshold 27 C for the diurnal shape, 7-day windows, percentile 95 (and 99), summer start 1 June to 25 August, ramp 6 rows, week 29 rows 4872 to 5039; units K, ratio, W/m2, %, C; temporal ops: daily climate signal applied to the hourly 2023 series through the observed normalised diurnal position; spell made hourly by a gamma-warped observed diurnal curve; missing values: `NA` in CH2025 (windows excluded, medians ignore NA), one missing diffuse/beam hour of 2023 kept missing; exclusions: windows with any NA among the five variables; checks: zero-delta identity, monthly mean warming equals the delta, reconstruction RMSE of 2023 from its own daily extremes, humidity 0 to 100, radiation not above the clear-sky cap, spell daily min/max/mean/radiation/humidity reproduced inside the inserted week.
- **TR-019** inputs DER-023 and DER-018 stage of M-003 (`swiss/models/pv.py`); output DER-024; script `swiss/pipeline/build_climate.py` calling `build_pv.pv_ac_w_per_kwp` (refactor of `swiss/pipeline/build_pv.py`: a function taking a weather frame; the 2023 output is unchanged, regression test `test_2023_pv_is_reproduced_exactly_by_the_refactored_function`).

## Assumptions (assumptions_log.md; block A-032 to A-039 reserved for WP1; the parent used A-028 to A-031 for the MPC study)
- **A-032** (A-C1): Climate change signal = monthly ensemble-median delta between a CH2025 warming level and the 1991-2020 reference at Kloten, applied additively to temperature (mean warming per month equals the tas delta; diurnal range changes by the tasmax minus tasmin delta) and as ratios to radiation and humidity; the 2023 day-to-day sequence is kept (delta change). Medians of daily radiation per month are used (the mean-based ratios are in the report).
- **A-033** (A-C2): Diurnal shape: the observed 2023 normalised position of each hour in its local day; sub-daily cycle carries no climate change signal beyond the range change.
- **A-034** (A-C3): Radiation scaling limited to max(Haurwitz clear-sky hourly mean, observed 2023 value of that hour); beam-horizontal and diffuse scaled with the same factor; the 2023 direct/diffuse split is kept.
- **A-035** (A-C4): Hot spells: 7-day windows, severity = mean tasmax, target = percentile 95 (default) or 99 of all valid windows of the level's ensemble, window chosen among those starting 1 June to 25 August closest to the target (deterministic); inserted over 2023 week 29 (rows 4872 to 5039) with a 6-row blend of temperature and humidity at both ends.
- **A-036** (A-C5): Spell to hourly: temperature from a gamma-warped mean diurnal curve of the 46 2023 hot days (hourly maximum >= 27 C) matching the spell's tasmin, tasmax and tas; CH2025 daily extremes are treated as extremes of the hourly series (hourly means are less extreme; difference not quantified).
- **A-037** (A-C6): Spell radiation: Haurwitz clear-sky shape scaled to the daily mean rsds, scale capped at the 99.9th percentile of the 2023 hourly ghi to clear-sky ratio; diffuse share from the 2023 median diffuse fraction by clearness-index bin; night values 0 (the 2023 file has a sensor offset of 1 to 3 W/m2 at night).
- **A-038** (A-C7): Spell humidity: constant dew point per day (Magnus formula) solved to match the daily mean hurs (capped at 100 %; CH2025 hurs has values above 100 %).
- **A-039** (A-C8): `sunshine_min` is not used by any model; it is carried from 2023 except in the spell rows where it is set to 60 times min(1, ghi / clear-sky) in daylight.

## Issues (issues_and_risks.md)
- **ISS-043**: The reference-level ensemble reaches daily maxima above 40 C at Kloten (reference maximum 42.7 C in the tasmax file, quantile-mapped model output); spells are therefore chosen at a percentile, not by the maximum. Open limitation.
- **ISS-044**: The default percentile-95 spell of the reference ensemble (mean tasmax 27.7 C) is milder than the hottest observed week of 2023 (hourly mean temperature 25.5 C over 168 h, August); `_hw99` files (30.9 C) are the stronger variant. Whether a different rule (summer-only percentile, absolute thresholds) is wanted is a decision for the owner.
- **ISS-045**: CH2025 hurs contains values above 100 % (max 106.1 in the reference file); CH2025 chain counts differ between variables (hurs 21 against 26); both handled as documented. Station-level bias adjustment of rsds is not validated here against 2023 radiation. Open limitation.

## Experiment (experiment_registry.csv)
- **EXP-021**: phase C WP1, climate scenarios build and validation; inputs SRC-014, DER-007; outputs DER-023 to DER-026; git commit: fill when committed; metrics: reconstruction RMSE of 2023 hourly temperature from its own daily extremes (all days / hot days) as in the report, scenario hot-day counts, spell severities (27.7, 30.0, 32.2 C at percentile 95; 30.9, 33.8, 36.4 at percentile 99); output location `docs/experiments/validation_reports/climate_scenarios.md`.

## Command for swiss/run_pipeline.sh (after the DER-016 line and before the q15 block)
```
$PY -I swiss/pipeline/build_climate.py >/dev/null           # DER-023 to DER-026 (needs data/raw/ch2025_klo/, git-ignored; see SRC-014)
```
Note for `docs/reproduction.md`: the CH2025 download is not scripted (files fetched with curl from the URL pattern above, hashes in SRC-014); add the 20 hashes or the `SHA256SUMS.txt` to the raw-data section.
