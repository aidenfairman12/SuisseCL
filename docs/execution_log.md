# Execution Log

**Log version:** 1.0 (2026-11-16)
**Governing plan:** [master_plan.md](master_plan.md) — version 1.0

This is the append-only record of what has actually been done, kept separate
from the master plan. The master plan says what *should* happen; this log says
what *did* happen.

## Conventions

- **Append-only.** Never edit or delete past entries. Corrections are new
  entries that reference the entry they correct.
- **Versioning.** The log is versioned through Git history plus the header
  above. Bump the minor version (1.1, 1.2, …) when entries are added in a
  commit; bump the major version if the log format changes.
- **Entry IDs.** `EL-NNNN`, sequential, never reused.
- **Plan changes.** Any change to `master_plan.md` must (a) bump its version
  header and (b) have a `plan-change` entry here with the reason and the
  approving user instruction.
- **Phase gates.** Phase authorization changes are recorded as `gate` entries,
  quoting the user's authorization.
- **Entry types:** `setup`, `gate`, `plan-change`, `task`, `decision`,
  `blocker`, `finding`, `experiment`, `report`.
- **Commit reference.** Each entry records the Git commit it relates to, or
  `pending` and is backfilled in a later entry if needed.

## Phase status

| Phase | Authorization | Status |
|---|---|---|
| A | Authorized (master plan v1.0, §9.1) | Not started |
| B | Not authorized | — |
| C | Not authorized | — |

## Entries

### EL-0001 — 2026-11-16 — setup
- **Action:** Saved the user-provided implementation plan verbatim as
  `docs/master_plan.md` (v1.0) and created this execution log.
- **Context:** User instruction: "keep this document as the master plan in the
  project repository, and maintain a separate, versioned execution log."
- **Scope note:** No Phase A tasks (A1–A9) have been started. The plan's
  "Initial execution instruction" (begin Phase A) has not yet been executed in
  this session; it is awaiting an explicit go-ahead.
- **Pre-existing repo state (observed, not yet analysed under Task A1):**
  prior work exists in `my_data/` (baseline controllers, SAC/MARLISA training,
  composite reward, UBELIX Slurm scripts, results CSVs), `docs/HANDOFF.md` and
  `docs/swiss_data_research_prompt.md`, with CityLearn cloned alongside
  (not vendored). This work must be reviewed, not overwritten (plan §9.2).
- **Known tension to resolve in Task A1:** `docs/` already contains two files;
  the plan's §5.1 layout (`docs/data/`, `docs/models/`, …) will be added around
  them rather than replacing them. Also, the plan targets CityLearn 3.3.0 —
  the installed/cloned version has not yet been verified.
- **Commit:** pending

### EL-0002 — 2026-11-16 — gate
- **Authorization:** User instruction "Start Phase A". Phase A authorized per master plan v1.0 §9.1. Phases B and C remain unauthorized.

### EL-0003 — 2026-11-16 — task (A1, partial → see EL-0005 for status)
- **Done:** Inspected repo, `docs/HANDOFF.md`, `docs/swiss_data_research_prompt.md`, README, CityLearn clone and installed package.
- **Verified:** CityLearn 3.3.0 (clone commit `0eb78bc`; pip package in `cl/` reports 3.3.0); Python 3.11.5; torch 2.2.2, numpy 1.26.4, pandas 2.3.3.
- **Findings:** CityLearn HeatPump uses a Carnot-style COP and takes *thermal* demand as input (ISS-004); heating-only schema keys exist in the Quebec dataset; no full dependency lockfile exists yet.
- **Created:** audit tree under `docs/` per §5.1 (registries seeded, empty where nothing is known), `docs/architecture.md` (draft), `docs/decisions/{decision_log,assumptions_log,issues_and_risks}.md`.
- **Commit:** pending

### EL-0004 — 2026-11-16 — task (A2, source verification; no downloads)
Web/metadata verification only; nothing downloaded. Details in `docs/data/data_source_registry.csv`.
- **HEAPO (SRC-001):** verified Zenodo 15056919, CC BY 4.0, open, 458 MB zip, 1,408 Zurich HP households, 2018-11-03..2024-03-21, 15-min/daily, UTC. Meter = TOTAL household kWh; separate HP-only meter only for some households. No indoor temperature or thermal output.
- **ETH/EKZ (SRC-002):** verified Zenodo 21398769 (v1, published 2026-07-21), CC BY 4.0, open, 904 MB, 2,447 installations, 2023–2024, 15-min, includes tariff price profiles. Timezone not stated on record; metadata fields not listed on record page.
- **JASM/CESAR (SRC-003):** the profiles exist (hourly, J, residential SFH/MFH × 12 construction periods × retrofit scenario, 9 MB package) but are **modeled (EnergyPlus)**, climate location unstated, and **no licence is stated** → blocker ISS-001.
- **MeteoSwiss (SRC-004):** open with citation; hourly files exist; UTC; only global radiation confirmed (diffuse/direct not) → ISS-005.
- **ElCom (SRC-005):** 2026 tariffs available via LINDAS SPARQL; no licence stated on page; annual components only, no time-of-use info seen → ISS-006.
- **HoroCarbon (SRC-006):** page could not be fetched (access denied to tool); reported file is a 2017–2024 hourly *average*, not a historical series; licence unverified. Not claimed usable.
- **Not covered:** SFOE PV (Phase B, deferred), CH2018/CH2025 (Phase C, out of scope).

### EL-0005 — 2026-11-16 — report (status at end of this working session)
| Task | Status |
|---|---|
| A1 repo/framework inspection, audit structure | Mostly done; CityLearn heating-only smoke test launched, result pending (see EL-0006) |
| A2 dataset verification | Done for metadata; **acquisition blocked on user approval** (ISS-009) and licence issues (ISS-001, ISS-006) |
| A3–A9 | Not started (depend on data) |

**Approvals needed from user:** (1) download HEAPO (458 MB) and ETH/EKZ (904 MB) zips; (2) how to handle JASM licence gap (contact Empa vs. skip, using modeled archetype alternative); (3) carbon-intensity alternative if HoroCarbon cannot be verified; (4) confirm decision D-002 (new `swiss/` package) and D-003 (thermal-demand route).

### EL-0006 — 2026-11-16 — finding (A1, CityLearn heating-only smoke test)
- **Test:** `CityLearnEnv` on `quebec_neighborhood_without_demand_response_set_points` (20 buildings, heating_device + dhw_device + LSTM dynamics), central agent, zero actions, `simulation_end_time_step=71`. Script was a throwaway in the session scratchpad (not in repo).
- **Result:** environment **initialises** (2.4 s) and steps, but raises `IndexError: index 72 out of bounds for axis 0 with size 72` in `building_ops.get_observations_data` on the step after 71 steps (the 72nd), i.e. `env.terminated` was not yet true when observations beyond the window were requested. The same truncation (`71`) on `citylearn_challenge_2023_phase_3_1` (6 buildings) finishes cleanly after 71 steps.
- **Not yet determined:** whether this is specific to the Quebec schema (episode/terminal settings), to truncating the window, or a CityLearn 3.3.0 bug. A full-length (6480-step) Quebec run did not complete within a 2-minute foreground limit and was stopped, so **full-episode heating-only operation is still unverified**. Logged as ISS-010.
- **Implication:** the Swiss builder must set `simulation_start/end_time_step` and episode settings explicitly and test the final step; no CityLearn source change made.
- **Commit:** pending

### EL-0007 — 2026-11-16 — report (end of this working session, Phase A **in progress**)
Phase A is **not complete** and the agent is paused at a data-acquisition approval point (plan §3.2 / §9.4). No data has been downloaded; no CityLearn code modified; nothing committed.

### EL-0008 — 2026-11-16 — task (A2, acquisition)
- **Authorization:** user replied "Approve both" to the question on downloading HEAPO and ETH/EKZ.
- **Downloaded** (Zenodo, public, no account/credentials) to `data/raw/` (gitignored): HEAPO `heapo_data.zip` 458,317,017 B, md5 matches Zenodo (`2b92b0d5…`); EKZ `dataset.zip` 904,206,916 B, md5 matches Zenodo API (`dd40d5e2…`). SHA-256 values in the registry. Extracted copies sit next to the zips; zips are the preserved originals.
- **Nothing else downloaded.** JASM, MeteoSwiss, ElCom, HoroCarbon not touched.

### EL-0009 — 2026-11-16 — finding (A2, profiling; headers/metadata only, no processing)
Profiling script was a throwaway in the session scratchpad (not in repo); numbers below are reproducible from the files.
- **HEAPO:** 1,408 households; CSVs are `;`-delimited, timestamps UTC. Metadata for 1,358. Building type (survey): **house 1,347, apartment 9** → HEAPO is effectively all single-family; **no usable multi-family sample**. Heat pump: air-source 778, ground-source 576. PV: 516 yes / 134 no (650 known). Living area median 180 m² (mean 193). Residents mean 2.9. DHW/heat distribution flags exist in metadata. **HP-only sub-meter (`kWh_received_HeatPump`) is non-empty in only 93 of 1,407 15-min files**; the rest have only total household kWh (ISS-003 quantified). `Weather_ID` links each household to one of 8 stations.
- **ETH/EKZ:** 2,447 meters; `;`-delimited, `timestamp_utc`. Meter `installation_type`: Apartment 1,528, Single-family house 495, Common areas 241, Heat pump 113 (separate HP meters), Water heater 2, EV charging 6, others. `object_type`: Apartment building 1,789 meters, Single-family house 627, Underground garage 31. Flags: `1_hp` True 313, `1_ewh` (electric water heater) 548, `1_ev` 56. 15-min columns: `kWh_to_installation`, `kWh_to_grid` (+ kvarh). `object_id` groups meters of one building; `0_num_housing_units` present (mostly empty in head rows). Tariff file: 70,176 quarter-hours (2023–2024) with `energy_standard`, `energy_unit_low`, `energy_unit_cn`, `grid_standard/tou/dyn/unit` — **units not stated in the files (probably Rp/kWh; unverified, to confirm in arXiv:2607.19294)**.
- **Implications for A3 (not yet decided):** multi-family buildings can only come from EKZ (apartment-building objects with common-area meters); single-family heat-pump houses from HEAPO and EKZ. The two datasets are different households, so a "district" is a constructed composite, not six real neighbours (plan A3: do not imply matching). Also the EKZ tariff file gives a real Zurich-utility price series, which may partially resolve the Task A6 tariff question (needs licence/scope check; ElCom still needed for context).
- **Issues updated:** ISS-003 quantified; new ISS-011 (HEAPO has no multi-family), ISS-012 (EKZ tariff units unconfirmed).

### EL-0010 — 2026-11-16 — decision
- **User decisions:** (1) JASM/CESAR may be used; project is private for now — recorded as D-004 with the condition that no JASM-derived data is redistributed/published until the licence is clarified; ISS-001 marked resolved-for-private-use. (2) `swiss/` package confirmed → D-002 accepted. (3) User asked for an explanation of D-003; explanation given in chat, D-003 remains **proposed** pending user confirmation.
- JASM files not yet downloaded.

### EL-0011 — 2026-11-16 — decision
- **D-003 accepted** by user as proposed (derived heat demand = HP electricity × COP(T_out), labelled Derived; closed-loop check required before it is called validated).
- **D-005 recorded:** user's carbon-intensity instruction (Electricity Maps primary; EPFL 2016–17 benchmark; Swissgrid/SFOE secondary check; acceptance condition: do not finalise carbon input until coverage, resolution, quality, licence verified).

### EL-0012 — 2026-11-16 — finding (A2/A6, carbon-intensity investigation; research only)
No account created, no API key used, nothing downloaded for this step.
- **Electricity Maps (SRC-008) — NOT verified, blocked on user action (ISS-013).** Their docs/help/dataset pages return 403 / a bot-verification challenge to my tools (WebFetch and the built-in browser); I did not attempt to bypass it. From search snippets only (reported, unverified): academic access gives API + CSV access to historical signals for non-commercial research, requires an accredited institution + verified academic email + attribution, is at the company's discretion, and **forbids redistribution/sublicensing and sharing keys/downloads with non-affiliated users**; historical depth is stated inconsistently (5 vs 10 years, zone-dependent). The only v4 "past" path I saw was `carbon-intensity-fossil-only`; the standard carbon-intensity v4 path is unconfirmed. Procedure steps 1–7 (coverage, seasonal test dates, lifecycle vs direct, estimation flags) **cannot be executed** until access exists. Redistribution restriction matters for any public repo/paper: the series would have to stay out of git.
- **EPFL benchmark (SRC-009) — verified.** Mendeley dataset CC BY 4.0 (v2, 2016-02-16), hourly kg CO2-eq/kWh and CED factors for 2016 and 2017, reference time GMT+1, attributional cradle-to-grave LCA with T&D losses; domestic generation technologies from ENTSO-E, Swiss imports from Swissgrid, **FR/AT/IT/DE import mixes assumed constant annual means**. Note the *article* is CC BY-NC-ND 4.0 (the user's message said CC BY 4.0, which holds for the dataset) — ISS-014. Suitable as methodology/seasonality benchmark only. Not downloaded.
- **Swissgrid/SFOE (SRC-010) — partly characterised (ISS-015).** Daily import/export flows on opendata.swiss; Swissgrid production hourly only for medium/large plants; formats/paths unverified.
- **Status:** Phase A carbon input is **not finalised** (per acceptance condition).
- **Decision needed from user:** (a) check Electricity Maps CH coverage and decide whether to apply for academic access (I will not create accounts/apply on your behalf without explicit go-ahead; you must handle credentials), and whether the redistribution limits are acceptable; (b) approve downloading the EPFL xlsx (small) as benchmark; (c) approve exploring Swissgrid/SFOE downloads (public).

### EL-0013 — 2026-11-16 — decision
- **User:** will check Electricity Maps CH coverage and apply for academic access themselves ("I'll check/apply"). No account/application made by the agent. ISS-013 stays open, waiting on user.
- **Carbon input** remains unfinalised (D-005). Still unapproved: downloading the EPFL xlsx and exploring Swissgrid/SFOE files.
- **Info to bring back when available:** CH zone coverage and start date, whether lifecycle + direct and consumption-based hourly values are offered, the exact v4 endpoint, the licence/redistribution text actually granted, and an API key handled by the user (not pasted into chat or committed).

### EL-0014 — 2026-11-16 — task (A2, acquisition #2)
- **Authorization:** user "Yes, download" (JASM, EPFL, Swissgrid/SFOE).
- **Downloaded** (public, no account): JASM package files to `data/raw/jasm/` (zip, `residential_hour_profile_EMPA.csv`, README, datapackage.json; commercial CSV not fetched as out of scope — contained in the zip); EPFL `Swiss Mix 2016_2017.xlsx` to `data/raw/epfl/` (SHA-256 matches the value Mendeley publishes). Hashes in registry.
- **Not obtained:** Swissgrid/SFOE (opendata.swiss returned 403; not bypassed) → ISS-017.
- **JASM profile (headers only):** columns Date/Time (no year), Building_type (SFH/MFH), Construction_period (12), retrofit_scenario (2), space heating / DHW / combined / cooling / electricity demand in J per hour. Licence field empty in README and datapackage (ISS-016); use stays under D-004 (private only).
- **Next candidates (no approval needed beyond what exists):** profile EPFL xlsx; read the ETH/EKZ paper for tariff units (ISS-012); begin A3 building-selection design. Waiting on: Electricity Maps (user), Swissgrid/SFOE route (ISS-017).

### EL-0015 — 2026-11-16 — task (A3, building-selection design)
- **Scripts added:** `swiss/pipeline/profile_candidates.py` (TR-001/002), `swiss/pipeline/select_buildings.py` (TR-003). Outputs in `data/interim/` (DER-001..003, summary statistics only; derived, registered). Code version at run time: HEAD `35c59a9` + uncommitted changes (nothing committed yet).
- **Findings:** HEAPO: 1,021/1,407 households have ≥95 % coverage in 2023, only 292 in 2022; HP sub-meter ≥90 % coverage in 2023: 67 (47 with total also ≥90 %); 237 households have >20 % zero-valued quarter-hours in 2023 (QC concern for A4). EKZ: 210 identified apartment-building objects but all have 0 apartment meters (ISS-018); 113 dedicated HP meters (67 on apartment buildings, units known 1–61, 109/113 ≥95 % coverage 2023); 187 EKZ SFH meters with HP flag and full coverage.
- **Output:** `docs/data/building_selection_design.md` (v0.1 draft): six proposed buildings (3 HEAPO SFH, 3 EKZ MFH), rules, measured/derived/modeled table, risks. Decision D-006 *proposed*; ISS-018, ISS-019 added.
- **Status of A3:** design drafted; **not final** — needs user review, then A4 QC may trigger replacements (rule defined).

### EL-0016 — 2026-11-16 — decision
- **User accepted D-006** (six-building composite, simulation year 2023). A3 design is final; building IDs may only change via the A4 QC replacement rule, each replacement logged.
- **Next:** A4 data processing for the six buildings (timestamp/DST handling, QC reports, hourly aggregation, PV/zero-run checks). Weather station (HEAPO `Weather_ID`, MeteoSwiss) and EKZ tariff units (ISS-012) are prerequisites; carbon input still pending (D-005/ISS-013).

### EL-0017 — 2026-11-16 — task (A4, first pass: building datasets and QC; weather/tariff/carbon deferred)
- **Authorization:** user "Start A4". No new downloads or accounts.
- **Added:** `swiss/pipeline/build_buildings_hourly.py` (TR-004). Outputs (all derived, registered DER-004..006, hashed in `data/canonical/MANIFEST.sha256`): 15-min 2023 extracts, hourly datasets with column classification (`columns.json`), HEAPO weather subset; QC report `docs/data/data_quality_reports/qc_2023_buildings.{md,json}`.
- **Key results:** (1) HEAPO Total = HP + Other exactly → ISS-003 resolved for SFH (D-008); (2) all three HEAPO series share one missing 24 h block on the DST-change day 2023-10-29 (ISS-020); (3) PV status of SFH unresolved (ISS-021); (4) MFH non-HP load is a synthetic seeded apartment composite (pool 1,125 meters) plus measured common-area meters; 220–257 hours missing in composites; (5) weather: only temperature/humidity/sunshine/precip/wind for 2 anonymised stations, no irradiance (ISS-022); (6) no duplicates, negatives, or long zero runs in measured series.
- **Decisions:** D-007 (time convention) and D-008 recorded; D-007 flagged reviewable.
- **A4 status:** partially complete — building-level dataset construction, timestamp/DST handling, hourly aggregation, missing-data treatment (flag only), QC report done; **weather alignment incomplete** (needs MeteoSwiss radiation = download approval, ISS-022), tariff/carbon deferred to A6. No tests written yet (plan 9.3) — to do.

### EL-0018 — 2026-11-16 — task (A4/A6, weather)
- **Authorization:** user "Yes, download" (MeteoSwiss).
- **Downloaded** (public OGD, no account) to `data/raw/meteoswiss/`: station metadata, parameter metadata, data inventory, hourly historical 2020–2029 for `KLO` (Zurich/Kloten) and `SMA` (Zurich/Fluntern). Hashes in registry.
- **Findings:** KLO has hourly global (`gre000h0`) and diffuse (`ods000h0`) radiation; SMA has no diffuse radiation → KLO chosen (D-010). MeteoSwiss provides no direct-normal irradiance → `beam_horizontal = global − diffuse` derived (ISS-005 partly resolved). Timestamp convention determined empirically as end-of-interval (D-009). HEAPO weather station `8jB` is Kloten (exact match after 1 h relabel); `Hg` is not Fluntern.
- **Output:** `swiss/pipeline/build_weather.py` → `data/canonical/weather_klo_2023_hourly.csv` (DER-007; 8,760 h; 1 diffuse hour missing; annual GHI 1,281 kWh/m², mean T 11.6 °C); QC `qc_weather_klo_2023.json`. TR-005.
- **New issue:** ISS-024 (smart-meter interval labelling unknown).
- **A4 status:** weather alignment done at hourly level; **A4 remaining:** unit tests for pipeline, handling decision for NaN hours (ISS-020), tariff/carbon (A6). "Predicted" 1/2/3-h weather columns to be decided in A7 (not invented here).

### EL-0019 — 2026-11-16 — decision
- **User:** Electricity Maps requires a paid API key, so it is **not viable now** (ISS-013 → closed as "not pursued"; D-005 primary source unavailable). Carbon input remains unfinalised; per D-005 the EPFL benchmark (2016–17 only) and a Swissgrid/SFOE-based reconstruction must be presented as alternatives for approval — pending.
- User asked for an explanation of the planned automated tests and the 24 h HEAPO gap (answered in chat; no code change).

### EL-0020 — 2026-11-16 — task (A4: gap fill and automated tests)
- **Gap fill:** user asked for the average of neighbouring days. Backtest first (`swiss/pipeline/backtest_gap_fill.py`): neighbouring days vs same weekday of neighbouring weeks on 87 complete days/house. Neighbouring days won on daily energy error for HP in all three houses and on most hourly-MAE comparisons; same-weekday was slightly better for non-HP load hourly MAE in SFH-low/high. Adopted as **D-011**. Implemented as `fill_gap_days` in the pipeline: new columns `kwh_hp_f`, `kwh_other_f`, `kwh_total_f`, `gap_filled_flag`; raw columns unchanged; 24 filled hours per SFH, all on 2023-10-29, classified synthetic. Fill uncertainty is large (see D-011).
- **Tests:** added `swiss/tests/test_pipeline.py` (pytest 9.2.0 installed into `cl/`; `my_data/hpc/requirements-dev.txt`). 34 tests, all pass: unit (hourly-sum completeness rule, zero runs, gap fill, 8,760-h local year, DST skip/repeat, 5,208 DST hours) and data tests (index integrity, no negatives, hourly=15-min energy conservation, Total=HP+Other, only 24 flagged hours on 2023-10-29, pinned annual HP totals, composite apartment meters distinct, weather relabel vs raw MeteoSwiss, manifest SHA-256, raw zip MD5). Mutation check: breaking the fill formula makes the unit test fail. Data tests skip if data is absent.
- **Note:** `MANIFEST.sha256` regenerated after the rebuild. Run: `cl/bin/python -m pytest swiss/tests -q`.
- **A4 status:** building datasets, QC, weather, gap treatment, tests done. Remaining open items for A4/A5: NaN hours in synthetic MFH composites (220–257 h), PV status of SFH (ISS-021), smart-meter label convention (ISS-024).

### EL-0021 — 2026-11-16 — task (A6 tariff; user question on gap fill)
- **User question** (average neighbouring Sundays instead?): answered from the existing backtest; decision D-011 unchanged — restricted to the 10 backtest Sundays, neighbouring days still win for HP in all three houses and for non-HP load in two; same-weekday only better on non-HP hourly MAE in SFH-high. Small n (10 Sundays) noted. User said move on.
- **Paper read** (arXiv:2607.19294, saved text via pdftotext): tariff units Rp/kWh excl. VAT; EKZ standard energy + grid tariffs two-tier, high 07:00–20:00 weekdays; smart-meter timestamps = START of 15-min interval (UTC). Resolves ISS-012 and ISS-024 (EKZ). EKZ air/ground-source still unstated; `1_hp` = "meter monitors a heat pump" (ISS-019 remains: selected medium/large MFH have installation type 'Heat pump' but `1_hp` False).
- **Built:** `swiss/pipeline/build_tariff.py` → DER-008 (TR-007); 8,760 h, exactly two levels (15.05/19.05 Rp/kWh), schedule verified against the documented rule by a new test (35 tests pass).
- **D-012 proposed:** use EKZ standard 2023 as the primary tariff, ElCom 2026 only as sensitivity (deviation from plan A6 wording "2026"); excludes VAT/levies. Awaiting user.
- **Carbon:** still open; next step is to propose EPFL-benchmark / Swissgrid-reconstruction alternatives (Electricity Maps not viable, EL-0019).

### EL-0022 — 2026-11-16 — decision
- **User accepted D-012:** EKZ standard 2023 two-tier tariff is the primary Phase A tariff (deviation from plan A6 "2026" wording, accepted). ElCom 2026 stays an optional sensitivity scenario (not yet queried).
- **Remaining A6:** carbon-intensity input (alternatives to be proposed). **Remaining A4/A5 items:** composite NaN hours, SFH PV status (ISS-021), ISS-019.

### EL-0023 — 2026-11-16 — finding (A6 carbon, research)
- **Authorization:** user "Research carbon". Only small test API queries were made (a few KB each, not stored in the repo; outputs in /tmp): Energy-Charts `public_power` for CH (2016-07-12, 2023-01-15, 2023-07-12), `cbpf` for 2023-07-12, `public_power` for FR and IT (2023-07-12). No account, key, or bulk download.
- **Findings:** Energy-Charts (Fraunhofer ISE) API is keyless, CC BY 4.0 with attribution (per API docs), rate-limited to 2 req/min. CH hourly generation by technology (nuclear, run-of-river, reservoir, pumped storage, others, wind, solar, load, net cross-border) is available for 2016 and 2023; cross-border physical flows per neighbour (AT, FR, DE, IT) are 15-minute; FR/IT (and presumably DE/AT) have full technology breakdown. Other options checked: Electricity Maps free CSV needs a free account, 5 downloads, and reports *direct* intensity only in the CSV description (lifecycle unclear, CH 2023 not confirmed; pages blocked to my tools); HoroCarbon = multi-year average; UNIGE reports a Swiss consumption-based annual mean of ~98 gCO2eq/kWh (year/method not verified).
- **Proposal D-013** (modeled consumption-based lifecycle intensity from Energy-Charts + lifecycle emission factors; 2016–17 reconstruction compared to the EPFL dataset as a method check). Not approved; emission-factor values unverified. ISS-025 added.
- **Waiting on user:** approval of the bulk download (~72 requests for 2023 + ~144 for 2016–17 at ≤2/min, a few MB total) and of D-013.

### EL-0024 — 2026-11-16 — decision / acquisition start
- **User approved D-013 and the bulk Energy-Charts download.**
- `swiss/pipeline/download_energy_charts.py` (resumable, throttled 31 s/request, honours Retry-After) started in the background: 216 requests (2023 and 2016–17 × CH/DE/FR/AT/IT `public_power` + CH `cbpf`), raw JSON to `data/raw/energy_charts/` (gitignored), log in `download.log`. Expected duration ≈ 1.9 h. Reconstruction (TR-008), emission-factor verification and the 2016–17 method check follow once data is complete.

### EL-0025 — 2026-11-16 — failure and fix (acquisition)
- First launch of `download_energy_charts.py` failed on every request with `SSLCertVerificationError` (the python.org interpreter in `cl/` has no CA bundle); 0 files saved. Stopped it, switched the fetch to `curl` (TLS verification kept ON, nothing disabled), restarted; first file saved OK. Download runs as a plain background shell process (not a tracked task): progress is `ls data/raw/energy_charts/*.json | wc -l` (216 expected) and `download.log`.

### EL-0026 — 2026-11-16 — commit
- User asked to commit. Three commits: `615e8b4` (docs and audit tree), `f325273` (pipeline scripts, tests, requirements-dev), `b068bf9` (derived datasets under `data/interim` and `data/canonical`). `data/raw/` is gitignored (not committed).
- **Version note:** registry/transformation-log rows that say "git 35c59a9 + uncommitted" refer to outputs produced before these commits; the code that produced them is in `f325273` (later scripts edits, if any, are logged separately).
- Energy-Charts download still running (check `ls data/raw/energy_charts/*.json | wc -l`, 216 expected).

### EL-0027 — 2026-11-16 — task (A5 design started; no code)
- **Exploration:** daily HP electricity vs KLO temperature for the six buildings; HEAPO survey flags for the three SFH (floor heating all; DHW by HP only SFH-low, electric water heater for SFH-mid/high; EV in SFH-low). Winter R² 0.85/0.92/0.80 (SFH), 0.48–0.66 (MFH); warm-day HP use ≈ DHW: 0.2/1.6/10.3 kWh/day (SFH), 10.5/28.9/25.6 (MFH).
- **Sources found (not yet read in full):** Swiss field SPF ≈ 3.5 (14 air-to-water HPs, IEA HPC 2023-era paper), WPZ Buchs 2021 ≈ 3.6, Austrian field Carnot-fraction range 0.32–0.44 (air-source space heating). Staffell et al. 2012 is the empirical COP-regression reference. Numbers to be verified from primary papers before entering the parameter registry.
- **Written:** `docs/models/heating_dhw_model_design.md` (v0.1), `models/model_registry.md` (M-001 proposed), D-014 (proposed), ISS-026..028. Correction recorded: the D-003 "closed-loop check" is tautological if the same COP form is used (implementation test only).
- **Waiting on user:** Q1 (DHW with electric water heaters), Q2 (SPF anchor), Q3 (EV in SFH-low).
- **Background job:** Energy-Charts download running (see EL-0025).

### EL-0028 — 2026-11-16 — decision
- **User answered Q1: option (a).** Recorded as D-014a. D-014 overall remains proposed pending Q2 (SPF anchor) and Q3 (EV in SFH-low).

### EL-0029 — 2026-11-16 — decision
- **User answered Q2: SPF 3.5** (D-014b). Next: verify the source paper; Q3 (EV in SFH-low) still open.

### EL-0030 — 2026-11-16 — task (A5, SPF source verified)
- **Read** Arpagaus et al. (2023), IEA HPC Paper 478 (full text via pdftotext of the Sp.se PDF). Table 1 (2018 field data): AWHP new building SH 3.7 / DHW 2.8 / SH+DHW 3.5; renovation (45–40 °C) SH 3.3 / SH+DHW 3.1; old (55–50 °C) SH 2.9. BWHP new SH+DHW 4.9. SPF boundary = EnergieSchweiz SPF+ (compressor, fan, control electronics, standby; not sink pump nor auxiliary heaters). Values entered in `models/parameter_registry.csv` with citation (Carnot-fraction range 0.32–0.44 still unverified, snippet only).
- **Consequence:** the user's 3.5 is the *combined* new-building value; D-014c proposes mapping SFH → 3.7 (SH) and MFH → 3.1 (combined, 45 °C) or keeping 3.5 everywhere — awaiting user.
- Energy-Charts download: count with `ls data/raw/energy_charts/*.json | wc -l`.

### EL-0031 — 2026-11-16 — decision
- **User chose per-mode SPF values** (D-014d): SFH 3.7 (SH), MFH 3.1 (combined, 45 °C assumption). Q3 (EV in SFH-low) still open. A5 implementation can start once Q3 is answered (or proceeds with SFH-low kept and flagged, the recommended default).

### EL-0032 — 2026-11-16 — decision
- **User answered Q3: keep SFH-low** (D-014e). M-001 accepted; A5 implementation starts. Uniform treatment recorded: non-space-heating baseline of HP electricity → `dhw_demand` for all six (labelled "HP baseline load").

### EL-0033 — 2026-11-16 — task (A5 implemented: M-001 thermal demand)
- **Code:** `swiss/models/heat_pump.py` (COP, η calibration, baseline split), `swiss/pipeline/build_thermal_demand.py` → DER-009 (`data/canonical/thermal/`), TR-008. Also D-015 (apartment composite rule; 0 NaN hours now) and the pipeline rebuild; MANIFEST regenerated. 44 tests pass (9 new: COP equals CityLearn's `get_cop`; η calibration; SPF targets met; no NaN/negatives; split conserves energy).
- **Results:** see `docs/data/data_quality_reports/qc_thermal_2023.md`. η = 0.35–0.39; SFH heat 79–153 kWh/m²a; baseline (DHW-like) share 1–29 % of HP electricity.
- **Negative finding (not hidden):** the linearity diagnostic does not support the Carnot-form temperature dependence (derived heat less linear vs HDD than raw electricity for all six). Annual heat level is anchored by the literature SPF; timing is uncertain. Candidate follow-ups (need user input): (i) accept and document as limitation (current), (ii) add a flatter-COP sensitivity run in A9, (iii) custom device with empirical COP (heavier; deviates from stock CityLearn).
- **Not yet done in A5:** model assumptions doc (`models/model_assumptions.md`) polish, DHW storage decision (none, unchanged), read primary paper for Carnot range. Energy-Charts download in progress (25/216 files at last check).

### EL-0034 — 2026-11-16 — finding and course correction (A5)
- **User chose "Custom COP device".** Before building, I tried to calibrate its slope: held-out check (fit Jan–Mar, test Oct–Dec) and an R²-vs-slope profile. The profile improves for *negative* slopes in all six buildings, so the HDD-linearity criterion is ill-posed and the slope is not identifiable from electricity data. Also found in the paper already used for SPF: variable-speed air-source heat pumps have a Carnot efficiency of about 40 % over the whole temperature range, which is the stock CityLearn form with η ≈ 0.4 (ours 0.35–0.39).
- **Consequence:** no custom device was implemented. The earlier "negative finding" (EL-0033) is reclassified as "uninformative diagnostic" (addendum in `qc_thermal_2023.md`). D-016 proposed: keep the stock HeatPump, sensitivity in A9. Needs user confirmation because it overrides their choice, made on my earlier framing.
- **New issue ISS-029:** no storage assets in the Phase A district → controllers have little to act on; design decision required before A8.
- Energy-Charts download: 33/216 files.

### EL-0035 — 2026-11-16 — decision
- **User accepted D-016:** stock CityLearn HeatPump with calibrated η; no custom COP device in Phase A; flatter-COP sensitivity run planned for A9. M-001 implementation considered complete for A5 (apart from the model-assumptions document and storage design, ISS-029).

### EL-0036 — 2026-11-16 — proposal (storage options, D-017)
- User asked for storage options (ISS-029). Computed per-building peaks from DER-009: peak heat kWh_th/h SFH 22/16/33, MFH 28/108/97; p99 13.5/13.0/16.8, 15.3/59.5/46.0; peak HP electricity 4.9/4.4/11.2, 6.8/21.2/18.1 kWh/h; DHW demand per day 0.5/3.7/24.3 (SFH), 21/48/47 (MFH). Four options recorded as D-017 (proposed). New caution ISS-030: derived hourly peaks look high for houses. Awaiting user choice.

### EL-0037 — 2026-11-16 — task (A7 first pass: CityLearn dataset and environment)
- **User chose storage option 1 (tanks):** D-017 accepted, sizes D-017a; conventions D-018 (base `Building` class, constant 21 °C indoor placeholder, no real forecasts, carbon null).
- **Built:** `swiss/citylearn_build/build_dataset.py` → `swiss/datasets/swiss_district_2023/` (DER-010, TR-009): schema.json, six building CSVs, weather.csv, pricing.csv, `build_manifest.json` (tank sizes, nominal powers). Stock `HeatPump` (heating, DHW), `StorageTank` heating buffer (6) and DHW tank (5; none for SFH-low), no PV/battery.
- **Result:** `CityLearnEnv` initialises (0.3 s) and runs the full 2023 episode (8,759 steps, 27 s) with zero actions and with constant 0.5 charging actions; **no end-of-episode error** (ISS-010 no longer blocking). 12 action slots reported (heating_storage + dhw_storage per building even though SFH-low has no DHW tank — to be checked in A8), 25 observations.
- **Implementation consistency (not validation):** simulated HP electricity (SH + DHW devices) equals measured within 1 % in every building (e.g. Building_1 4,731 vs 4,730 kWh; Building_5 25,712 vs 25,716).
- **Tests:** 47 pass (3 new integration tests, ~42 s total).
- **Open before A7 can be called complete:** carbon series (waiting on download, 46/216 files), action-list check, documentation of reproduction commands, reward function (A8).

### EL-0038 — 2026-11-16 — experiment (A8 baselines: EXP-001..006)
- **Run:** `swiss/experiments/run_baselines.py` (new), 6 controllers x 1 deterministic year; registered in `experiments/experiment_registry.csv`; protocol in `experiment_protocol.md`; algorithm, controller and reward docs written; D-019 proposed. Tests: `swiss/tests/test_baselines.py` (3 pass; BAU identical to zero action, tariff map hours, RBC changes the load and conserves energy).
- **Results (district, 2023):** zero action: 214,715 kWh import, peak 72.0 kW, cost 35,750 CHF excl. VAT, 40.0 % of import in high tariff. BAU identical to zero action (as predicted). BasicRBC: +1.2 % energy (storage losses), peak 67.6 kW (−6.1 %), cost +0.5 %, high-tariff share 37.1 %. Tariff-aware HourRBC r=0.05/0.10/0.20: high-tariff share 37.7/36.9/36.4 %, cost +0.5/+0.4/+0.3 %, all-time peak 69.3/68.3/72.9 kW, energy +1.0–1.2 %.
- **Interpretation:** the environment responds to storage actions (load shifts out of high tariff by up to 3.6 points; peak moves), so it functions as a control testbed. But with the synthetic tanks and a tariff ratio of 1.27, simple price-aware rules do **not** save money (storage losses of ~1 % of energy outweigh the price gain) and gains in peak are small. Expected benefit of any controller here is therefore small and sensitive to the tank assumption (D-017a) — to be quantified with x0.5/x2 tank sensitivity in A9. Not a validation of anything.
- **Limits:** CityLearn KPI ratios are relative to its counterfactual (zero action = 1.0); carbon KPI = 1.0 because no carbon series; comfort KPIs are NaN; HourRBC ignores weekends.
- Energy-Charts download: ~55/216 files.

### EL-0039 — 2026-11-16 — decision
- **User accepted D-019:** reward R-001 (cost + peak + ramp, carbon weight 0 until D-013 series exists, no comfort term) and baseline set ALG-001..004. A8 complete for baseline controllers and reward; no learning agent in Phase A.
- **Remaining Phase A:** carbon series (download 64/216 at last check) and its integration; A9 validation (energy balance, double counting recap, tariff and carbon arithmetic, seasonal patterns, weather alignment, tank-size and SPF sensitivity, flatter-COP sensitivity); architecture/model-assumption docs; reproduction instructions; completion report and revised roadmap for B and C; final registry audit.

### EL-0040 — 2026-11-16 — task (A9 validation and sensitivity)
- **A8 committed** as `d3de37c`. **Added:** `swiss/validation/validate_phase_a.py`, `swiss/experiments/run_sensitivity.py`; `build_thermal_demand.run` and `build_dataset.main` gained optional parameters (output subdir, `t_sh`, `tank_eff`) with unchanged defaults; sensitivity datasets under `swiss/datasets/swiss_sens_*` and `data/canonical/thermal_flatcop_T80/` (derived, for sensitivity only).
- **Validation (report `docs/experiments/validation_reports/validation_phase_a.md`):** V1 electricity closure, V2 heat/storage balance, V3 stability, V4 no double counting vs measured totals, V5 tariff arithmetic: pass. V6 seasonality: pass qualitatively. V7 alignment: SFH lag 0–1 h, large MFH not identifiable (ISS-031). Carbon arithmetic blocked (no series). V2 showed storage losses of 12–19 % of heat charged (45 % in one DHW tank) under the assumed efficiency 0.95 and 0.3 %/h standby loss.
- **Sensitivity (15 full-year runs):** in all five variants the price-aware and BasicRBC rules raise cost by 0.15–1.10 % while shifting 1.9–4.4 points of import out of the high tariff and changing peak by −6.7 % to +1.8 %. Tank efficiency 0.99 reduces but does not remove the cost penalty. Flat COP changes little. Standby-loss sensitivity not yet run (ISS-032).
- **Not claimed:** any calibration/validation against observed thermal data (none exists).
- Remaining Phase A: carbon series (download ~80/216), docs (architecture, model assumptions, reproduction instructions, lockfile), completion report + revised roadmap, final registry audit.

### EL-0041 — 2026-11-17 — task (A6 carbon reconstruction, 2023)
- **Authorization:** user "go ahead with the carbon reconstruction now" (2023 data complete; 2016–17 download still running, ~108/216).
- **Verified emission factors** from the IPCC AR5 WG3 Annex III PDF (Table A.III.2, lifecycle medians): nuclear 12, hydro 24, biomass 230, geothermal 38, wind on/offshore 11/12, solar PV rooftop 41 / utility 48, coal 820, gas CC 490. Proxies (not in the table) documented as A-006..A-009.
- **Built:** `swiss/pipeline/build_carbon.py` → DER-011 (`data/canonical/carbon_ch_2023_hourly.csv`, `carbon_intensity_citylearn_2023.csv`), TR-010, model M-002, 5 tests. Issues found and handled: neighbours' technology columns are NaN for long periods when plants do not operate (DE nuclear after 2023-04-15; FR offshore wind early 2023) → treated as structural zero (NaN runs ≥ 48 h); 4 hours with missing cross-border flow data at the last hour of four monthly chunks → interpolated and flagged; 120 hours of neighbour data gaps → neighbour annual-mean fallback (flagged).
- **Result:** consumption-based lifecycle intensity mean 58.1 g/kWh (p5 28.9, p95 133, max 246; highest in March, ~119 monthly mean), domestic generation only 32.1 g/kWh, import share 24 %; intraday: highest around 00:00–05:00 local (~70), lowest ~18:00–19:00 (~43). Proxy sensitivity ±50 %: 46.8–69.4 g/kWh. Annual TWh from the source: nuclear 23.3, hydro 36.5, solar 4.9, others 3.5, wind 0.17; net flow into CH −5.05 TWh (Italy −20.2). Plausibility caveats in ISS-033.
- **Integration:** main CityLearn dataset rebuilt with `carbon_intensity.csv` (kg/kWh); baselines re-running to populate carbon KPIs (previous no-carbon results kept as `baselines_2023_nocarbon.csv`).
- **Pending:** EPFL 2016–17 method comparison (needs the rest of the download), V8 carbon arithmetic check, registry rows for the re-run.

### EL-0042 — 2026-11-17 — experiment (baselines re-run with carbon; V8)
- Baselines re-run on the dataset that now includes the carbon series: EXP-007..012 registered (EXP-001..006 retained; no-carbon results kept in `baselines_2023_nocarbon.csv`). Carbon KPI (CityLearn, counterfactual = 1): BasicRBC 1.0236, tariff-RBC r=0.05/0.10/0.20: 1.0174/1.0208/1.0193; cost KPI 1.0035–1.0054; other results unchanged.
- **V8 carbon arithmetic:** independent ratio 1.0267 vs KPI 1.0236 (0.3 % unexplained difference). Interpretation recorded in the validation report: cost and carbon conflict (cheap night hours have the highest modeled carbon intensity), subject to ISS-033.
- Energy-Charts download ~119/216; the 2016–17 method check still pending.

### EL-0043 — 2026-11-17 — task (A9 close-out: docs, audit, reproducibility, completion report)
- **Docs written:** `architecture.md` (v1.0), `models/model_assumptions.md`, `reproduction.md`, `project_overview.md`; lockfile `swiss/requirements-lock.txt`; `swiss/run_pipeline.sh`.
- **Registry audit:** `swiss/validation/audit_registries.py` → `experiments/validation_reports/registry_audit.md`: PASS, 0 broken references (negative test: an invented non-existent issue ID was detected, then removed).
- **Reproducibility check:** `bash swiss/run_pipeline.sh` re-run on the existing tree (about 10 minutes): all 31 previously manifested derived files were byte-identical (SHA-256); only the new `carbon_intensity_citylearn_2023.csv` was added to the manifest. The CityLearn dataset files were unchanged. Not run from a clean checkout.
- **Completion report:** `phases/phase_a_completion_report.md` written (task status, acceptance criteria assessment, inventories, findings, limitations, defaults awaiting confirmation, proposed changes to B and C). Pending: EPFL 2016–17 carbon method check. Per plan 9.5 I stop and await approval; Phases B and C remain unauthorized.

### EL-0044 — 2026-11-17 — validation (carbon method check, user: "wait and run it")
- Download finished (216/216 files, no errors). `swiss/validation/compare_epfl_carbon.py` (openpyxl added to the lockfile) reconstructed 2016 and 2017 with the 2023 code and compared with EPFL: hourly r 0.977/0.976, monthly r 0.996/0.995, diurnal r 0.996/0.951; means 110/115 vs 179/184 g/kWh (ratio 0.61/0.63); lag scan peaks at 0 h. Correlation is driven by the shared import-share driver; domestic-only series correlates poorly (0.32/0.60). Verdict: shape and timing supported, level not (D-013b: use for relative signals only). Report `carbon_epfl_comparison.md`; TR-011; ISS-033 updated; completion report updated (A6 now completed with the level caveat; pending item closed).
- Phase A still awaits the user's review; Phases B and C remain unauthorized.

### EL-0045 — 2026-11-17 — housekeeping after the architecture audit (user: "do d027 and housekeeping")
- Decision D-027 logged (48-hour contract sample first). Earlier the same day D-020..D-026 were logged from the audit answers, and contract v1 (`swiss/contract/`, `web/public/bundle/sim/`, `docs/dashboard/data_contract_v1.md`) and the mechanism check (`swiss/validation/mechanism_check.py`) were added on branch `contract/v1-draft`.
- DER-010 regenerated: `build_dataset.py` now writes `root_directory: "."` instead of an absolute path. All five datasets (`swiss_district_2023` and the four `swiss_sens_*`) were rebuilt with the documented commands; **only the `schema.json` files changed**, every CSV and manifest was byte-identical. CityLearn 3.3.0 resolves a relative root against the schema's folder (`citylearn/utils/file_handler.py`), and the full test suite, which includes annual totals compared with `baselines_2023.csv`, passes unchanged.
- Documentation brought up to date: root README (Swiss project first, legacy `my_data/` kept), `web/README.md` hosting section (public hosting, D-020), `docs/architecture.md` (layer 8, contract), `docs/reproduction.md` (test count and new commands). The dated Phase A completion report is left as written.

### EL-0046 — 2026-11-17 — full-year contract bundle and review of the frontend branches (user: "do the full length contract bundles also; check the lint errors by the frontend agent")
- Exported the full-year contract bundle to `web/public/bundle/sim_full/` (12 files, about 57 MB raw, 8,759 steps, six controllers) with `export_v1.py --full`; D-028 amends D-027. The exporter's dirty-tree check now ignores its own output folder. New tests `swiss/tests/test_contract_full.py` (9) check schema validity, annual totals against `baselines_2023.csv`, balances and tank conservation over the year, and that the 48-hour sample is an exact slice of the full year. Contract hooks take a `variant` argument.
- Reviewed the frontend branches (`docs/dashboard/visualization_review_02.md`): `visualization/district-redesign-contract` passes the dashboard lint (0 errors), `tsc` and ESLint (1 warning) and merges cleanly into `contract/v1-draft`; the older `visualization/district-redesign` still has the 4 lint errors of review 01. Open: the heat-flow arrows are not driven by values.



### EL-0047 — 2026-11-17 — polish after the frontend merges (user: "fix all 4 yourself. consider the front end agent finished")
- Verified `main` at 8863723 (PRs #6 and #7) in code and on the live site: lint 0 errors, `tsc` clean, no console errors, Results numbers equal the mechanism check; a fresh clone passes 146 tests (2 skipped need raw data).
- Contract: added the boolean attribute `electric_water_heater` (the frontend had compared my free-text description to an exact string) and rewrote the situation tag texts in plain language, generated from the thresholds. Frontend: cutaway uses the flag; Results shows the high-tariff share in percentage points, the three-way split of the extra electricity (tank losses, stored remainder, COP timing) and of the relative carbon change, a data-driven reading, and the local date of the highest hour; the last ESLint warning (memo dependency) is gone. D-029 records that the simulation workstream now maintains `web/src/**`.

### EL-0048 — 2026-11-18 — Phase A sign-off documents (user: "yes do the first two": completion report and issue statuses)
- Issue register: 23 update rows appended to `issues_and_risks.md`. 15 issues closed with the decision or log entry that settles them (ISS-002, 005, 006, 007, 008, 009, 010, 011, 015, 016, 017, 020, 022, 026, 029); 8 issues keep their open status with a clarified limitation and an owner-acknowledgement note where relevant (ISS-004, 018, 019, 021, 023, 025, 027, 028). Evidence checked before closing: downloads approved and completed (EL-0008, EL-0014), JASM used by no code, absent from git and from the dashboard, decisions D-006, D-007, D-010, D-011, D-012, D-013, D-014a/d/e, D-017a, D-019. With the dashboard's own status rule: 33 issues, 13 open limitations, 19 closed, 1 noted.
- Decision log: statuses corrected where later decisions settled them (D-005 superseded by D-013, D-013a method check done, D-014 and D-014c accepted through D-014d/e, D-017 accepted as D-017a). No decision content changed.
- `phase_a_completion_report.md` refreshed in place (status, section 1.3, criterion 10, controller results with the mechanism decomposition, register status, working defaults accepted, repository changes, test count, section 11c); original assessments kept.
- Phase A awaits the owner's approval at the phase gate (plan 9.6); Phases B and C remain unauthorized.

### EL-0049 — 2026-11-18 — RL on the Swiss environment: protocol, episode-end fixes and the exact cost optimum (user: "yes lets start the RL ... do the episode-end fixes and exact optimum")
- Cluster check (read-only SSH, VPN on): UBELIX clone `~/SuisseCL` was at `35c59a9` (before the Swiss work) with four finished US-project result files not yet on the laptop; they were copied down. Cluster environment matches the pins (torch 2.2.2+cpu, numpy 1.26.4, pandas 2.3.3, citylearn 3.3.0). Nothing was submitted.
- Feasibility on the laptop: SAC (central and per building) and MARLISA run on the Swiss environment unchanged; steady state about 30 ms/step (central SAC), about 150 ms/step (per-building SAC, MARLISA); the first episode is exploration only and misleadingly fast.
- Found and fixed two artefacts of short episodes: empty-tank starts (rules looked 1.5 % worse than over the year; now evaluated from a 96-step warm-up) and SAC treating a window end as terminal (now bootstrapped). Stored heat at a window end is reported as a corrected-cost range.
- `swiss/experiments/oracle.py`: exact perfect-foresight cost optimum per tank (linear program). A first version missed the heat pump output shared between direct supply and charging; the replay check in CityLearn caught it (281 vs 306 CHF) and after the fix the program and the environment agree exactly (299.08 CHF). Ceiling 0.84 % of the bill at the assumed tank sizes, 0.57 % to 2.17 % for 0.5 to 8 times the size.
- Two 40,000-step local pilots of central SAC (R-001 and cost-dominant) did not beat no control (cost +0.4 % to +0.56 % on the test weeks, highest hour -2 % to -3 %); single seed, about a quarter of the planned budget.
- Records: D-030, ISS-034, ISS-032 update, ALG-005 to ALG-007, protocol and reward-preset documentation, `validation_reports/oracle_cost_bound.md`. Reward choice (D-023) still pending.


### EL-0050 — 2026-11-18 — Phase B step 1 (B1 review), per `docs/phases/phase_b_plan.md`
- Thresholds restated from the plan: ceiling-first gate = exact optimum saves at least 3 % of cost, else a negative result and no RL (D-032); replay of an exact optimum must match CityLearn within 0.5 % (stop condition); no cluster jobs until Phase B is finished; every commit, push and download needs the owner's approval; data contract changes stay additive (v1.1).
- ISS-021 (PV status): re-checked in the raw HEAPO files. `kWh_returned_Total` is empty in the daily, monthly and cumulative files of all three houses for all years (0 non-empty values). The household table gives `Installation_HasPVSystem` = False for SFH-low (7069411) and no value for SFH-mid (8011310) and SFH-high (1181060). No new evidence: **stays open**. Consequence for B3 (plan 4.3): the two unknown houses are treated as "with assumed PV", SFH-low as having no PV, and the scenario is labelled "with assumed PV".
- ISS-019 (EKZ heat-pump type): `metadata.csv` has no air/ground field; flags `1_hp`, `1_hp-add`, `1_hp-wh` only, and `1_hp` is still False for MFH-medium (145442) and MFH-large (197873). **Stays open**; the flat-COP sensitivity variant remains the only handling.
- ISS-024 (HEAPO timestamp label): the HEAPO files carry no documentation of the interval label beyond the column names; I did not find a source in the files on disk. **Stays open** (ISS-031 describes the effect: at most about 1 h).
- No code, data or registry change in this step. Nothing committed.

### EL-0051 — 2026-11-18 — Phase B step 2 (B9 metrics subset)
- New `swiss/experiments/metrics.py`: `compute_metrics()` from a rollout's arrays (net, optional PV, battery charge/discharge and capacity, import and export price, indoor temperature with band). Metrics: import and export energy, three peak definitions (gross coincident, netted coincident, sum of building peaks), PV self-consumption, self-sufficiency, import cost, export revenue, bill (= import cost − export revenue), battery equivalent cycles, comfort violations (steps, degree-hours). Absent inputs give `None`, never 0. Sign convention follows CityLearn (import positive); the PV sign convention in CityLearn 3.3.0 is still to be verified in B3.
- `swiss/tests/test_metrics.py`: 8 hand-computed toy cases (accounting identity, per-building netting, battery cycles, kW conversion, comfort, input validation).
- Issue register gained 3 update rows (EL-0050); row count in `swiss/tests/test_dashboard.py` updated 70 to 73. The dashboard freshness test fails until the audit bundle is rebuilt, which the commit cycle does after the code commit (needs the owner's approval to commit).

### EL-0052 — 2026-11-18 — Phase B task B2a: 15-minute feasibility spike (scratch only, nothing added to the repo)
- Method: one building (Building_2 = SFH-mid) derived from the hourly Swiss dataset by repeating each hour four times (energy columns divided by 4; weather, price and carbon repeated), `seconds_per_time_step` 900, end step 35,039, run with the stock zero-action agent and BasicRBC. Script and data live in the session scratchpad, not in the repo. This is only a mechanical test: it adds no 15-minute information, so it says nothing about 15-minute behaviour.
- Result: CityLearn 3.3.0 builds and runs the 35,040-step year without error (about 22 s per rollout). Zero-action import 11,316.7 kWh and cost 1,839.73 CHF at 900 s against 11,315.6 kWh and 1,839.56 CHF at 3600 s (+0.01 %); BasicRBC 11,414.3 vs 11,413.0 kWh. So tank losses (`loss_coefficient` per step), heat-pump energy limits and the cost accounting scale correctly with the step length for this building.
- What did not break: episode length, tariff indexing (price repeated), DST (UTC index keeps 2023 at exactly 35,040 steps), contract-style per-step energy.
- What still needs work for a real B2: (1) the `hour` observation repeats four times per hour; CityLearn has an optional `minutes` column, not added or tested; (2) the thermal derivation (M-001) and the HEAPO/EKZ extracts in `data/canonical/quarter_hourly/` must be run at 15 minutes (heat timing is unvalidated, ISS-004); (3) forecasts (`*_predicted_k`) are in steps, so k = 1..3 now means 15 to 45 minutes, not 1 to 3 hours; (4) the contract bundle grows about four times (D-028), so monthly chunking is needed; (5) only one building and two controllers were run, the full six-building district, the rewards and the exact optimum were not.
- Not done on purpose: no half-working 15-minute environment is committed (plan 4, B2a).

### EL-0053 — 2026-11-18 — Phase B step 3 (B3 PV, scenario S1 "with assumed PV")
- Verified CityLearn 3.3.0 PV convention from the source and by rollout: the schema `solar_generation` column is inverter AC output per kWp in W/kW, the PV device scales it by `nominal_power`/1000 and the step length, `building.solar_generation` is stored negative (kWh per step), and `net_electricity_consumption` with PV equals the no-PV value plus `solar_generation` (checked per building over 300 steps in `swiss/tests/test_pv.py`).
- New model M-003 `swiss/models/pv.py` (own implementation: pvlib is not installed and adding it would change the pins): sun position at interval midpoint, south plane tilt 30 degrees, isotropic transposition, NOCT cell temperature, loss chain. Parameters are assumptions (A-011, A-012; parameter registry). `swiss/pipeline/build_pv.py` writes `data/canonical/pv/` (DER-012): annual specific yield **1,160.6 kWh/kWp** for 2023 (GHI 1,280.5 kWh/m2), zero at night, inside the assumed plausibility range 900-1250 (the range itself is unsourced; 2023 was a sunny year; no comparison with measured PV).
- Capacity rule (A-013, A-014): annual PV yield = ratio x annual no-control import, ratios 0.5, 1.0, 1.5, capped by a rooftop proxy. At ratio 1.0 the cap binds for SFH-mid (8.3 kWp), MFH-small (10), MFH-medium (28) and MFH-large (48); SFH-low gets 9.3 kWp and SFH-high 12.3 kWp. For MFH-small and MFH-medium the cap binds at every ratio, so the 50 %/150 % sensitivity does not vary there. The no-control import of the apartment buildings includes the synthetic composite load.
- `build_dataset.py --pv-ratio` adds the PV device and `solar_generation`; the default `swiss_district_2023` was rebuilt and is unchanged (git shows no diff). Scenario dataset `swiss_pv_2023` (ratio 1.0, DER-013) added; `run_pipeline.sh` extended.
- Registries: M-003, TR-012, DER-012, DER-013, A-011 to A-014, 10 parameter rows, D-033; row counts in `swiss/tests/test_dashboard.py` updated. No demand reconstruction was needed (no building is known to have PV; ISS-021 stays open and is restated in D-033).
- Tests: `swiss/tests/test_pv.py` (6). Nothing committed.

### EL-0054 — 2026-11-18 — B3 PV model switched to pvlib (owner: "install pvlib ... if more accurate/consistent")
- Installed pvlib 0.16.1 (pulls h5py 3.16.0) into `cl/` with a constraint file holding numpy 1.26.4 and pandas 2.3.3; afterwards numpy, pandas, scipy 1.17.1 and torch 2.2.2 are unchanged. `swiss/requirements-lock.txt` updated. The cluster venv is not updated (no cluster jobs until Phase B ends); it needs the same install before PV runs there.
- `swiss/models/pv.py` now uses pvlib (SPA sun position, DNI from GHI and DHI, Perez transposition, SAPM cell temperature, PVWatts DC, losses and inverter). Annual specific yield 2023: **1,148.9 kWh/kWp** against 1,160.6 from the first own implementation (1 % apart), so the earlier number in EL-0053 is superseded. Capacities at ratio 1.0: SFH-low 9.35, SFH-mid 8.3 (cap), SFH-high 12.41, MFH-small 10, MFH-medium 28, MFH-large 48 kWp (the last four capped). Wind speed (2 m/s) and the loss total are assumptions; the plausibility range 900-1250 is still unsourced and there is no comparison with measured PV output.
- Registries, decision D-033 and `test_pv.py` updated; datasets `swiss_pv_2023` and the manifest rebuilt; `swiss_district_2023` unchanged.

### EL-0055 — 2026-11-18 — Phase B step 4 (B5): check whether ElCom data contain export remuneration → STOP condition reached
- Local data: the EKZ `tariff_data.csv` has only consumption prices (energy and grid columns, Rp/kWh excl. VAT); it has no export or feed-in column. No ElCom file is on disk (SRC-005 was never downloaded).
- ElCom page `elcom.admin.ch/en/tariff-data-and-visualisations` (read as a web page, not downloaded): the published tariff data are household and business consumer tariffs by commune and operator, components total, energy, charges, grid usage, grid surcharge, metering; products standard and cheapest; no producer or feed-in component is described. No licence is stated (ISS-006).
- ElCom publications found by search (reported, not verified in the data): the feed-in remuneration (Rückliefervergütung) is agreed by contract between grid operator and producer (EnG art. 15); from 1 January 2026, absent an agreement, the reference market price published by the SFOE applies. This is a legal rule, not a published per-operator data series.
- Not done: I did not query the LINDAS SPARQL endpoint to list the cube's properties, because that is a data retrieval and needs your approval. The page description and the legal framework both point the same way, so I expect the answer to be "absent".
- Per `phase_b_plan.md` section 5 (stop condition) and 4.4 I stop here and ask the owner how to source export prices. No code or data changed; nothing committed.

### EL-0056 — 2026-11-18 — LINDAS query (approved by the owner): ElCom cubes contain NO export remuneration
- Read-only SPARQL queries to `https://lindas.admin.ch/query` (graph `elcom/electricityprice`), a few KB, nothing stored in the repo. Cubes: `electricityprice` (per provider), `-canton`, `-swiss`, `sunshine`, `sunshine-cat`. Properties of the price cubes: total, energy, gridusage, charge (community fees), aidfee, fixcosts, meteringrate, discounts, working and power prices, plus category, product, operator, municipality, period.
- One property is labelled "Feed-in remuneration at cost (KEV)" (`aidfee`). A sample value (Swiss median, category H4, standard product, 2023) is **2.3 Rp/kWh** inside a total of 27.203, i.e. it is the grid surcharge consumers pay (Netzzuschlag) that funds feed-in remuneration, not a price a producer receives. It must not be used as an export price.
- Conclusion: the ElCom data lack export remuneration; the plan's stop condition stands. Awaiting the owner's choice of export price source (assumed sweep, or the SFOE reference market price after a licence and series check). Nothing committed.

### EL-0057 — 2026-11-18 — Export price source chosen by the owner: SFOE reference market price; pre-download check
- Owner choice (after EL-0056): use the SFOE (BFE) reference market price as the export price source.
- Reported (web search, not verified in the data): the SFOE computes and publishes reference market prices quarterly, for photovoltaics as the quarterly average of the day-ahead (Swissix) price weighted by the actual 15-minute feed-in, excluding VAT, in CHF/MWh; two figures quoted by the search summary are Q3 2025 57.31 and Q4 2025 95.08 CHF/MWh (reported, unverified). The legal default for feed-in remuneration without a contract is this price from 1 January 2026.
- Sources: `https://www.bfe.admin.ch/en/reference-market-prices` (schedule only, no prices, no licence stated) and the I14Y entry `https://www.i14y.admin.ch/en/catalog/datasets/BFE-DS-0020/description` (JavaScript page, my fetch returned only the title, so format, URL and licence are **not yet confirmed**). Related documents: `https://pubdb.bfe.admin.ch/en/sammlungen/referenz-marktpreise`.
- Consequences to flag before use: a quarterly price is a flat number per quarter (no hourly shape), and the series published may start only after 2023 (unverified), so a 2023 value may have to come from a different source or be stated as an assumption. The 2023 local year is the simulation year.
- Not downloaded. Awaiting the owner's approval for the download and a licence decision (no licence text found; general admin.ch terms are linked). Nothing committed.

### EL-0058 — 2026-11-18 — Phase B step 4 (B5 import and export), assumed export price
- Owner choice: assumed sweep. `swiss/models/export_price.py` (sweep 0, 4, 8, 12 Rp/kWh, default 8), `swiss/experiments/accounting.py` (rollout arrays, scenario metrics, replay check), `swiss/tests/test_accounting.py` (5 tests, one full-year S1 rollout).
- CityLearn 3.3.0 accounting (source, `building.py`): building cost = max(net, 0) x electricity price; exports are never credited, and the reward cost term follows the same rule. Export revenue and the bill are therefore computed outside the environment; `replay_check` shows the import part equals the environment's cost series (relative difference below 1e-4; observed 0 to 6 digits).
- Zero-action results, full year 2023, district: S0 import 214,715 kWh, cost 35,750.32 CHF (equals Phase A). S1 (assumed PV, ratio 1.0, six buildings, 116.1 kWp in total): PV generation 133,349 kWh, import 157,880 kWh, export 76,513 kWh, import cost 25,631.24 CHF, PV self-consumption 42.6 %, self-sufficiency 26.5 %, coincident peak 72.0 kW (unchanged: it occurs on a winter evening). Bill with export revenue: 25,631 (0 Rp), 22,571 (4), 19,510 (8), 16,450 CHF (12). These are zero-action numbers for the assumed scenario, not a claim about real houses.
- Consequences: the Phase B value of a controller on S1 will depend on the export price; with an export price near the import price, shifting load to PV hours gains little; with export price 0 self-consumption is worth the full import tariff. A reward preset that counts export revenue is needed for RL (plan 4.7, later).
- Registries: A-015, D-034, 2 parameter rows; counts in `test_dashboard.py` updated. Nothing committed.

### EL-0059 — 2026-11-18 — Phase B step 5 (B4 battery), scenario S2
- `build_dataset.py --pv-ratio R --battery-kwh-per-kwp K` adds a stock CityLearn `Battery` per building (needs the PV option because the size rule is per kWp), activates the `electrical_storage` action and the `electrical_storage_soc` observation. Defaults unchanged: `swiss_district_2023` and `swiss_pv_2023` rebuild byte-identical (git shows no diff). New dataset `swiss_pvbat_2023` (DER-014): battery kWh equal PV kWp per building (9.35, 8.3, 12.41, 10, 28, 48 kWh).
- Behaviour verified by rollout (`swiss/tests/test_battery.py`, 4 tests, 240 steps, charge/rest/discharge schedule): SoC stays within [0.1, 1.0]; grid-side power never exceeds nominal power (0.5 x capacity); stored energy changes by sqrt(eta) x grid energy on charging and grid energy / sqrt(eta) on discharging, so **the `efficiency` value in the CityLearn Battery is the round-trip efficiency**, and total loss is positive and bounded; an idle battery changes nothing; net consumption with battery = PV-only net + battery electricity. Without flattening the curves CityLearn draws random efficiency and power curves and degrades capacity, which would break reproducibility and the linear program of step 6.
- Registries: M-004, A-016, A-017, six parameter rows, DER-014, D-035; row counts in `test_dashboard.py` updated. `run_pipeline.sh` extended. Not done: the battery does nothing under the stock baseline controllers (they only act on tanks); controller and optimum on S2 come in steps 6 and 7. Nothing committed.

### EL-0060 — 2026-11-18 — Phase B step 6: exact ceilings on S1 and S2 (`oracle_pvbat.py`)
- New `swiss/experiments/oracle_pvbat.py`: one linear program per building (tanks as in Phase A, plus battery `Eb_t = Eb_{t-1} + sqrt(eta) c_t - u_t / sqrt(eta)` with power and energy bounds, plus import and export variables; objective import cost minus export revenue). It stays linear (flat battery curves, constant efficiency). Export price above any import price is rejected (unbounded). Full-year solve about 5 s per scenario.
- Two things found while validating by replay, both fixed before the numbers below: CityLearn's battery action is a fraction of the **nominal power** (not of the capacity, as for the tanks); with the wrong scaling the replay missed the program by 33 % of the saving. After the fix, replay equals the program to 0.00 CHF for S1 (18,334.05) and S2 (16,467.18), and for 1,500 steps in `swiss/tests/test_oracle_pvbat.py`. The plan's stop condition (replay more than 0.5 % off) is not triggered.
- Results at 8 Rp/kWh (district, full year, zero-action bill 19,510 CHF for both rungs): S1 optimum saves 1,176 CHF (6.03 %), S2 saves 3,043 CHF (15.60 %). Across export prices 0, 4, 8, 12 Rp/kWh: S1 7.98, 7.14, 6.03, 4.51 %; S2 22.21, 19.35, 15.60, 10.44 %. What-ifs at 8 Rp/kWh: battery 0.5 kWh/kWp 11.74 %, 2 kWh/kWp 20.09 %; PV x0.5 (battery 1) 10.64 %, PV x1.5 15.91 %; S1 PV x0.5 4.79 %, PV x1.5 6.11 %. For comparison Phase A (S0) is 0.84 %.
- Reading: the S1 gain comes from the tanks absorbing PV surplus instead of exporting it at a low price (S1 has no battery); the S2 gain adds the battery. With the export price near the import price the gain shrinks, as expected. Tank sizes are still synthetic (ISS-032), so the S1 number carries that uncertainty.
- Gate (D-032, recorded as D-036): S1 and S2 both pass, RL is authorised by the rule on both; scripts to be written, not submitted (item 9). Report: `docs/experiments/validation_reports/oracle_cost_bound_s1_s2.md`; raw: `swiss/experiments/oracle_results/oracle_pvbat.json`. ALG-008 and D-036 registered; row counts in `test_dashboard.py` updated. Nothing committed.

### EL-0061 — 2026-11-18 — Order change (D-037) and start of step 8 (B7 thermal model)
- Owner decision: RL on S1 and S2 moves after step 11; `phase_b_plan.md` task table and decisions table updated, D-037 registered, row count in `test_dashboard.py` updated. Step 8 starts with the checks of routes (a) and (c) of plan 4.8, before anything is built.

### EL-0062 — 2026-11-18 — Step 8 (B7), checks before building: routes (a) and (c)
- **(a) Validated Swiss framework.** Meister et al. 2026, Applied Energy, "Bottom-up heat pump flexibility estimation for Swiss buildings considering monitored building data" (found with the literature search, abstract read, full text not read): bottom-up framework from building thermal inertia and buffer tanks, designed to run for arbitrary Swiss communities from primarily public data, validated against three monitoring datasets (measured heat loss, cooldown events, smart-meter data of 243 heat pumps). Reported results include that setpoint adjustment can cut power by up to 90 % over four-hour windows at 0 degrees C, and that blocking creates rebound peaks and comfort violations. **Not found:** a code repository, a data availability statement or a licence; two web searches returned nothing. Without code, using it means re-implementing it from the paper (inputs, parameters and licence unverified). Related Swiss work found: Melillo et al. 2021 (200 digital twins from smart-meter data, distributions of heat-loss and thermal-capacity parameters) and Melillo et al. 2023 (10 Swiss heat pumps, grey-box models).
- **(c) Dataset with indoor temperature.** None found with Swiss heat-pump electricity and measured indoor temperature. HEAPO (used) and ETH/EKZ (used) have none (ISS-004). DOMOS Sion demonstrator (Zenodo 8238570): 15 houses near Sion with heat-pump sub-meter and PV sub-meter since January 2021; indoor temperature, weather, resolution and licence not stated on the project page. iHomeLab RAPT (Zenodo 3581894, five Lucerne houses, five-minute power traces): indoor temperature not mentioned. DOMOS Aalborg has indoor sensors but is Danish. The searches are not exhaustive and the dataset pages were not opened beyond the project page.
- **Consequence.** Route (b), a lumped RC model calibrated to heat-pump electricity versus weather, partially identifiable and labelled synthetic, is the remaining route. It cannot be validated against indoor temperature. Parameter priors could come from the Melillo digital-twin distributions (numbers not read). Comfort violations in S3 would then be properties of an assumed building, not measurements. Nothing built or downloaded; nothing committed.

### EL-0063 — 2026-11-18 — Step 8: DOMOS Sion record checked (owner choice), not usable
- Zenodo record 8238570 (page read, nothing downloaded): domOS Sion Living Lab, 15 single-family houses near Sion, total and heat-pump sub-metered electricity and PV where present, from January 2021. **Access is restricted** (case by case for research, licence agreement to be signed), no licence terms, no file list (5.2 MB in total), time resolution not stated, and **no indoor temperature or weather is listed**. It cannot anchor a thermal model and would need a licence agreement the owner has not approved. Route (c) is therefore closed for now; ISS-004 stays open. Nothing downloaded; nothing committed.

### EL-0064 — 2026-11-18 — Step 8 (B7): the owner's equation and what our data can identify (`swiss/pipeline/fit_rc_params.py`)
- Owner pasted the heat balance of Melillo et al. 2021, "Statistical analysis of 200 digital twins for thermal load of Swiss buildings created from smart grid monitoring data", J. Phys.: Conf. Ser. 2042 012009 (attribution corrected by the owner on 2026-11-18; I had first called it the Meister paper; the passage describes a Nelder-Mead calibration): C_l dT/dt = -H (T_inside - T_ambient) + g I + L_emitter + L_internal, per floor area (C_l in J/Km2, H in W/Km2, g dimensionless, I in W/m2). This is a single-node, one-resistance one-capacitance (1R1C) model, i.e. exactly route (b) with a published structure. The glyphs of the paste were garbled but the equation is unambiguous.
- Identifiability check on our data (daily quasi-steady regression over 195 heating days: heat demand = a + b T_out + c GHI, so C_l drops out; output `data/canonical/rc/rc_quasi_steady_fit_2023.json`, file added to the canonical manifest). Heat demand is derived from heat-pump electricity and a modeled COP, so H depends on the SPF assumption (ISS-028):
  | Building | H (W/K) [bootstrap 5-95 %] | H per m2 | balance temp (C) | g_eff (m2) | R2 |
  |---|---|---|---|---|---|
  | SFH-low | 227 [210, 245] | 1.03 | 24.6 | 9.7 | 0.84 |
  | SFH-mid | 347 [331, 366] | 2.09 | 18.5 | 4.3 | 0.87 |
  | SFH-high | 261 [228, 297] | 1.00 | 29.1 | 4.4 | 0.64 |
  | MFH-small | 203 [174, 238] | 0.51 | 35.8 | 8.4 | 0.54 |
  | MFH-medium | 305 [220, 393] | 0.27 | 37.2 | -5.2 | 0.15 |
  | MFH-large | 353 [301, 408] | 0.18 | 28.9 | 5.5 | 0.44 |
- Reading: for the three houses H is reasonably determined (R2 0.64 to 0.87, per m2 values 1.0 to 2.1 W/Km2 are in a plausible range, not checked against a source), but the implied balance temperatures of 18 to 29 C are above or at the 21 C setpoint, which means the derived heat contains offsets (internal gains absorbed, the unexplained summer use of SFH-high ISS-027, DHW leakage, SPF error); g_eff is poorly constrained. For the apartment buildings the fit is weak (R2 0.15 to 0.54, one negative g_eff), consistent with their synthetic apartment loads and with the unidentifiable timing found in A9 (ISS-031). C_l is not identifiable from this data at all.
- Consequence: only H (houses) and loosely g can be taken from data; C_l, and everything for the apartment buildings, must come from priors or from the paper's size-independent per-m2 parameters. The model would be labelled synthetic with data-informed H for the houses. Nothing is integrated into CityLearn yet; nothing committed.

### EL-0065 — 2026-11-18 — Step 8 (B7): RC model with pooled per-m2 priors (owner decision), standalone, not yet in CityLearn
- Owner instructions: use pooled per-m2 priors; the equation is from Melillo et al. 2021 (title and citation given by the owner; EL-0064 and the issue rows corrected).
- `swiss/models/rc_building.py`: exact discrete step of C dT/dt = -H (T - T_amb) + g I + L_emitter + L_internal, inversion for a target temperature, ideal-control simulation, energy-closure calibration. `swiss/pipeline/build_rc_params.py` writes `data/canonical/rc/rc_params_2023.json`. Priors H 1.03 W/Km2, g 0.026, C 110 kJ/Km2, internal gain 2 W/m2, time constant about 30 h (A-018, A-019).
- Result of the closure: effective area / floor area is 1.35 (SFH-low), 2.14 (SFH-mid), 2.05 (SFH-high), 1.37 (MFH-small), 0.96 (MFH-medium), 0.43 (MFH-large). The three houses need more heat than the pooled per-m2 loss implies for their floor area (about 1.35 to 2.1 times), and MFH-large (24 units, 80 m2 per unit assumed) much less. So the pooled prior does not describe all six buildings at their floor areas; the energy level of each is matched by the effective area, not by physics. The owner may want to know before relying on S3 comfort results.
- Model behaviour worth knowing: with heating-only ideal control at 21 C the indoor temperature is above 24 C in about 2,700 hours a year (solar and internal gains, no cooling or shading); the annual heat from the dynamic simulation is 12 % lower than from the quasi-steady formula because the building stores free gains, which is why the calibration uses the dynamic simulation. A comfort rule for the upper limit is needed (A-020). Free-running (cooling) behaviour is Phase C.
- Registries: M-005, A-018 to A-020, 8 parameter rows, TR-013, DER-015, D-038; `tests`: `swiss/tests/test_rc.py` (5). Row counts in `test_dashboard.py` updated. Not done: CityLearn integration (a `Dynamics`/`DynamicsBuilding` subclass, heat-pump action as partial load, comfort term in the reward) and the exact optimum for S3. Nothing committed.

### EL-0066 — 2026-11-18 — Step 8 (B7) completed: RC model in CityLearn and exact ceiling for S3 with sweep
- CityLearn integration by subclassing (`swiss/citylearn_build/rc_dynamics.py`, `RCDynamicsBuilding` + `RCDynamics`): heat delivered to the room is `heating_demand`, set by the `heating_device` action (fraction of nominal power x COP) as CityLearn's LSTM building does; indoor temperature from the exact RC step. CityLearn's loader insists on a `filename` for any dynamics component (it assumes LSTM weights), so the dataset carries a documentation file `rc_params.json`. `build_dataset.py --rc` adds it (default datasets unchanged). New dataset `swiss_rc_2023` (DER-016, S3 = S2 + RC). `swiss/experiments/thermostat.py`: thermostat baseline (ALG-009); its first two steps show a start-up transient of at most 0.4 kWh.
- `swiss/experiments/oracle_rc.py`: per-building LP with space heat as a decision, exact RC dynamics as linear equalities, comfort band, tank, battery, PV and export; baseline path always feasible (the heat pump cannot always reach 21 C in extreme cold). Replay in CityLearn (first 1,500 steps): predicted and realised bill equal to 0.01 CHF, temperature within 0.008 K, for both band variants.
- Results (district, full year, export 8 Rp/kWh): thermostat baseline bill 20,894 CHF. Optimum: band 20 to 24 C 16,538 (saves 4,356, 20.85 %); band 21 to 24 C (pure shifting) 17,559 (3,335, 15.96 %); no thermal flexibility (tanks and battery only) 17,888 (3,006, 14.39 %). Building thermal mass is worth 329 CHF (1.6 points); letting the house run colder is worth another 1,021 CHF but that is energy saving. Export price 0/4/12 Rp/kWh: 22.85, 19.87, 10.61 %. Sweep H x C (12 points): 15.31 % to 16.91 %, higher C helps (+1.4 points from 80 to 165), higher H hurts slightly. **Gate passed everywhere** (D-039). Report `docs/experiments/validation_reports/oracle_cost_bound_s3.md`, raw `oracle_results/oracle_rc.json`.
- Honest reading: the S3 ceiling is similar to S2 (15.6 %) because the same battery, tanks and PV dominate; the thermal model adds a small share, and S3's baseline bill (20,894) is not comparable to S2's (19,510) because the heat profile is modelled, not derived. The comfort term for the reward and the RL jobs are in the RL block (D-037). Registries: D-039, ALG-009, DER-016; row counts updated; `run_pipeline.sh` extended. Nothing committed.

### EL-0067 — 2026-11-18 — Phase B step 9 (B5 richer tariffs), first part: pilot structures and stylised spreads
- EKZ pilot tariffs found in `tariff_data.csv` (checked, 2023 and 2024): time-of-use grid fee (2023 Q4: 4.3 low, 9.3 Rp/kWh high from 18:00 to midnight on every day type; 2024: seasonal, 3.7 to 10.0), dynamic grid fee (2023 Q4 and 2024, 3.7 to 6.3 Rp/kWh, changing day by day), unit product (single price, energy 10.35 and grid 5.8). All pilot columns start on 1 October 2023; 2024 energy prices (17.5 and 19.0) are far above 2023 (10.35 and 11.45), so only the grid-fee structures are carried over, on the 2023 energy tariff.
- `swiss/pipeline/build_tariff_scenarios.py` writes `data/canonical/tariff_scenarios_2023_hourly.csv` (DER-017): standard (equals DER-008), ToU Q4 2023, ToU 2024, dynamic 2024, spread x2, spread x5. Price ranges: standard 15.05 to 19.05, ToU Q4 14.65 to 20.75, ToU 2024 and dynamic 14.05 to 21.45, x2 13.5 to 21.5, x5 8.9 to 28.9 Rp/kWh.
- `swiss/experiments/oracle_tariffs.py`: exact optimum per tariff on S0 (tanks), S1, S2, S3 (pure shifting). The numbers under the standard tariff reproduce the earlier results exactly (0.84, 6.03, 15.60, 15.96 %). Results in D-040; report `docs/experiments/validation_reports/oracle_cost_bound_tariffs.md`. Only the price vector changes versus the replay-validated programs; no new replay was run for these tariff variants (the realised bill is the net series times the price).
- Not done: day-ahead market prices (plan item 7: licence per price zone first, ask before any download; derived series stay out of the public bundle). Registries: TR-014, DER-017, D-040; counts updated; `run_pipeline.sh` extended. Nothing committed.

### EL-0068 — 2026-11-18 — Standing approvals for the rest of Phase B (D-041)
- The owner asked to finish Phase B without updates and answered the open questions: day-ahead download if CC BY 4.0; LEG and EV as labelled scenarios; the agent chooses the RL reward and submits the full jobs if everything works; commits after each step, no pushes. Recorded as D-041. Remaining work: day-ahead scenario, B2 15-minute pipeline, B6 LEG, B8 EV, RC-versus-Phase-A comparison and district metrics, RL block, Phase B report with updated Phase C proposal.

### EL-0069 — 2026-11-18 — Step 9 part 2: day-ahead scenario tariff (approved by D-041)
- Licence check: the Energy-Charts API documentation (`openapi.json`, path `/price`) states that the bidding-zone CH day-ahead data are CC BY 4.0 "from Bundesnetzagentur | SMARD.de" and published without changes. Downloaded 8,760 hourly values for the 2023 local year (153 KB, EUR/MWh, mean 107.5, min -142.9, max 268.8, 76 negative hours) to `data/raw/energy_charts/dayahead_ch_2023.json` (SRC-012, gitignored). Free, no key.
- `swiss/pipeline/build_dayahead.py` (DER-018): import = grid fee + spot x 0.97 + adder (revenue neutral to S0), floored at 0 (8 hours); export = spot floored at 0. The exact programs now accept a per-step export price series (guard: export never above the import price in any step). Results in D-042 and `docs/experiments/validation_reports/oracle_cost_bound_tariffs.md` (last row): S0 2.11 %, S1 6.49 %, S2 20.04 %, S3 20.76 %.

### EL-0070 — 2026-11-18 — Step 10 (B2): 15-minute pipeline and environment
- Pipeline `swiss/pipeline/build_15min.py` (TR-016, DER-019) and datasets at 900 s (DER-020, `build_dataset.py --q15`). Checks (`swiss/tests/test_q15.py`, `qc_15min_2023.json`): hourly HP electricity, non-shiftable load and derived heat and hot water are exact aggregates of the 15-minute series (difference below 1e-9), no NaN, DST days have 92 and 100 quarter-hours, irradiance hourly means preserved to 1e-13, PV annual yield 1,151.3 against 1,148.9 kWh/kWp hourly (+0.2 %), tariff native. HEAPO gap day filled at 15 minutes with the same rule.
- Problems found and fixed on the way (each would have given wrong 15-minute results): (1) a first thermal split with a quarter-hour baseline profile changed the heating/hot-water split by up to 26 % (A-023); (2) a tank action moves at most capacity x step length per step, the program allowed capacity per step; (3) CityLearn rescales `loss_coefficient` to the step length itself, so the schema value stays per hour; (4) device sizes taken from hourly peaks could not supply 15-minute heat demand (exact optimum infeasible): devices sized on 15-minute peaks (A-024, SFH-high 7.8 to 11.5 kW); (5) zsh word-splitting slips in my own shell loops built two datasets wrongly once, noticed and rebuilt.
- Results: D-043 (zero-action agreement to 0.008 %, ceilings S0 0.87, S1 6.50, S2 16.16, S3 16.26 / 21.13 %, replay exact for S1, S2, S3 band 20-24 and, after a rerun in a fresh process, S3 band 21-24; one earlier mismatch not reproduced, ISS-037). Rollout cost at 900 s about 2 minutes per year per environment (123 s). `swiss/experiments/oracle_q15.py`, report `oracle_cost_bound_q15.md`.
- 15-minute files are not tracked in git (about 160 MB) and not in the manifest; `run_pipeline.sh` regenerates them. Nothing committed yet.

### EL-0071 — 2026-11-18 — RL block: deployment and submission of the Phase B grid on UBELIX (D-041, D-044)
- Local checks before submitting: `rl.py` runs on s2 and s3 (SAC central, 4,032 steps), baselines per scenario (zero action or thermostat and the PV rule at three rates) on the eight held-out weeks, reward scales per scenario (`results/reward_scales_s1..s3.json`), `swiss/tests/test_rl_scenarios.py`. Baselines on the test weeks (bill change vs reference, corrected): s1 PV rule -0.13 % to +0.02 %; s2 -5.5 % to -5.9 %; s3 -5.5 % to -5.8 %. Exact optimum on the same weeks (`rl_reference.json`): s1 5.48 %, s2 14.55 %, s3 14.75 %.
- Deployment without a push: `swiss/hpc/deploy_phase_b.sh` copied 21 MB (code, four scenario datasets, scale files, COMMIT = 5f61a67) to `~/SuisseCL_phaseB`; environment `~/venvs/cl` after `module load Python/3.11.3-GCCcore-12.3.0` reproduces the pins (citylearn 3.3.0, torch 2.2.2+cpu, numpy 1.26.4, pandas 2.3.3, scipy 1.17.1). A smoke job (22719497, SAC central s3, 2,016 steps) finished in 76 s and wrote config.json, curve.csv and eval_final.json.
- Submitted 27 jobs (free QoS, 4 CPUs, 8 GB, 12 h, training capped at 11 h; SAC central 150,000 steps, SAC per building and MARLISA 100,000 steps; seeds 0 to 2; scenarios s1 to s3; reward bill): pb_s1_sacc_s0 22719752, pb_s1_sacd_s0 22719753, pb_s1_marl_s0 22719754, pb_s1_sacc_s1 22719755, pb_s1_sacd_s1 22719756, pb_s1_marl_s1 22719757, pb_s1_sacc_s2 22719758, pb_s1_sacd_s2 22719759, pb_s1_marl_s2 22719760, pb_s2_sacc_s0 22719761, pb_s2_sacd_s0 22719762, pb_s2_marl_s0 22719763, pb_s2_sacc_s1 22719764, pb_s2_sacd_s1 22719765, pb_s2_marl_s1 22719766, pb_s2_sacc_s2 22719767, pb_s2_sacd_s2 22719768, pb_s2_marl_s2 22719769, pb_s3_sacc_s0 22719770, pb_s3_sacd_s0 22719771, pb_s3_marl_s0 22719772, pb_s3_sacc_s1 22719773, pb_s3_sacd_s1 22719774, pb_s3_marl_s1 22719775, pb_s3_sacc_s2 22719776, pb_s3_sacd_s2 22719777, pb_s3_marl_s2 22719778.
- Results are collected with `rsync` from `~/SuisseCL_phaseB/swiss/experiments/rl_results/` and aggregated by `swiss/experiments/rl_report.py`. Nothing else runs on the cluster.

### EL-0072 — 2026-11-18 — RL block: grid resubmitted with shorter requests (supersedes the job list of EL-0071)
- The first submission of 27 jobs asked 12 h each and the free QoS cap on running CPU-minutes (MaxCpuRunMinsPerUser) let only 4 run at once, which would have taken more than two days. I cancelled my own 27 job IDs by number (22719752 to 22719778 and, after a script that had not been updated was submitted by mistake, the second set 22719801 to 22719827; no other job of the user was touched) and resubmitted with walltimes matched to the measured speed: central SAC 3.5 h (training cap 3 h, 150,000 steps), per-building SAC and MARLISA 6.5 h (training cap 6 h, 100,000 steps or fewer if the cap is reached). 11 jobs run at once.
- Order: the nine central SAC jobs first (seeds 0 to 2 by scenario), then per-building SAC and MARLISA. Jobs: pb_s1_sacc_s0 22719845, pb_s2_sacc_s0 22719846, pb_s3_sacc_s0 22719847, pb_s1_sacc_s1 22719848, pb_s2_sacc_s1 22719849, pb_s3_sacc_s1 22719850, pb_s1_sacc_s2 22719851, pb_s2_sacc_s2 22719852, pb_s3_sacc_s2 22719853, pb_s1_sacd_s0 22719854, pb_s1_marl_s0 22719855, pb_s2_sacd_s0 22719856, pb_s2_marl_s0 22719857, pb_s3_sacd_s0 22719858, pb_s3_marl_s0 22719859, pb_s1_sacd_s1 22719860, pb_s1_marl_s1 22719861, pb_s2_sacd_s1 22719862, pb_s2_marl_s1 22719863, pb_s3_sacd_s1 22719864, pb_s3_marl_s1 22719865, pb_s1_sacd_s2 22719866, pb_s1_marl_s2 22719867, pb_s2_sacd_s2 22719868, pb_s2_marl_s2 22719869, pb_s3_sacd_s2 22719870, pb_s3_marl_s2 22719871.
- Lesson recorded: a shell loop that patches a script and then runs a remote command must verify the patch (the first patch was lost when its command was denied); `scancel -u` on a shared account is not used.

### EL-0073 — 2026-11-18 — B6 LEG and B8 EV scenarios (labelled, D-041, D-045)
- Framework facts read from the EKZ LEG conditions document (SRC-013): participants in one municipality, same grid level, same substation, communicating smart meters, generation of at least 5 % of the connection power; grid-use tariff discounted by 40 % (20 % with a transformation) on the energy exchanged inside the LEG; the internal price is freely agreed; residual supply unchanged. The statute was not read (ISS-039).
- `swiss/experiments/oracle_ev_leg.py`: EV windows and a joint LEG program over the six buildings (the exact programs gained an EV block and a build-only mode; the S1 and S2 results are unchanged, `test_oracle_pvbat.py` passes). Results in D-045 and `docs/experiments/validation_reports/ev_leg_scenarios.md`. Tests `swiss/tests/test_ev_leg.py`. No CityLearn replay (no EV or LEG in the environment).
- Reading: with a 24 CHF per year value of EV flexibility on top of tanks and battery, the EV adds load (about 380 CHF a year for two vehicles) but little extra flexibility value; the LEG moves the district bill by 1 to 2 % (zero action) because only 3 to 4 % of imports coincide with exports; its larger effect is on who pays (allocation), which the district total does not show.

### EL-0074 — 2026-11-19 — Phase B documents
- Written: `docs/phases/phase_b_completion_report.md` (plan 7.4), `docs/phases/phase_c_proposal_updated.md` (climate route CH2025 daily versus the hourly CH2018-based scenarios, cooling adoption evidence and a proposal of 10, 30 and 50 %, scenario matrix and gate, decisions needed), `swiss/validation/compare_rc_phase_a.py` (RC against the Phase A representation), `swiss/experiments/phase_b_metrics.py` (district metrics: the cost optimum raises the coincident import peak, S2 +74 %, S3 +96 %), `swiss/experiments/rl_report.py`; README, HANDOFF, reproduction.md and the plan status updated. Web checks for Phase C (reported, not verified in the data): CH2025 daily local and gridded datasets are CC BY 4.0 with four warming levels (1.5 to 3.0 C); hourly scenarios exist only on CH2018 (72 MeteoSwiss stations); fixed air conditioning in about 5 to 10 % of Swiss homes; Empa 2021 projects more than half of households with cooling later in the century.

### EL-0075 — 2026-11-19 — RL grid status and a connection problem (stop point for the owner)
- Nine central SAC runs finished (3 scenarios x 3 seeds) and were collected; results in `docs/experiments/validation_reports/rl_phase_b.md` and section 8b of the completion report: no central SAC run beat its reference on the held-out weeks (bill +1.1 % S1, +2.9 % S2, +59 % S3 with 782 K·h below 21 C), while the PV rule saves about 5.5 % on S2 and S3; exact optimum on the same weeks 5.5 %, 14.6 %, 14.8 %.
- The eighteen per-building SAC and MARLISA runs were running (11 jobs) or queued (5) at the last contact. Later `ssh ubelix` attempts time out (`submit01.unibe.ch:22`), most likely the university VPN dropped; my polling monitors failed silently for about an hour before I noticed. The jobs run on the cluster independently. Needed from the owner: reconnect the VPN; then collect with `rsync -a ubelix:SuisseCL_phaseB/swiss/experiments/rl_results/ swiss/experiments/rl_results/`, run `swiss/experiments/rl_report.py` and refresh section 8b.
- Lesson: a monitor that swallows ssh errors must print an error line; use `-o ConnectTimeout` and report failures.

### EL-0076 — 2026-11-19 — RL results collected after the VPN returned (partial)
- `ssh ubelix` reachable again. 15 runs had finished (nine central SAC, six per-building SAC or MARLISA); nine jobs (22719860 to 22719871 subset: s1_sacd_s1, s2_sacd_s1, s3_sacd_s1, s3_marl_s1, s1_sacd_s2, s1_marl_s2, s2_sacd_s2, s3_sacd_s2, s3_marl_s2) were still running with 38 min to 5.3 h of walltime left. Collected with rsync, `rl_report.py` regenerated `rl_phase_b.md`, section 8b and EXP-017 updated (status partial).
- Reading: no learner beat its reference; per-building SAC and MARLISA are no better than central SAC (S2 +5 %, S3 +86 % to +91 %, one seed each). The 9 remaining runs are not expected to change the reading but are not collected; a later `rsync` plus `rl_report.py` refreshes the tables.

### EL-0077 — 2026-11-19 — Control-methods study, RL collection completed, registers
- Research note `docs/phases/control_methods_shortlist.md` (ranked methods, sources) written at the owner's request; receding-horizon MPC implemented (`swiss/experiments/mpc.py`, `mpc_report.py`, `mpc_forecast*.py`) and run locally on S1 to S3 (EXP-019, EXP-020); commits 3dc907d, 0f87d7c, 72b8ffc (bundles). Decisions D-046, D-047, assumptions A-028 to A-031, issues ISS-040 to ISS-042, ALG-011.
- The last three RL jobs (22719868, 22719870, 22719871) finished (6 h 3 min, 6 h 2 min, 5 h); results collected with rsync, `rl_report.py` regenerated `rl_phase_b.md`: 24 of 27 runs have results; three S2 MARLISA runs ran out of memory (ISS-042). Reading unchanged: no learner beat its reference.
- Lesson: a margin option that is clipped by an existing bound has no effect and gives identical numbers; compare a variant with its base before trusting a null result.

### EL-0078 — 2026-11-19 — Phase C work (authorised by the owner in chat), registers merged
- Phase C proposal rewritten (`docs/phases/phase_c_proposal_updated.md`) and executed with local commits at milestones (owner approval for commits; pushes not approved): 5fbaf2d (WP1 climate pipeline from CH2025 Kloten files, WP2 cooling model, exact optimum with cooling, climate impact metrics), 8822bbe (WP3 scenario matrix of 26 cells with cooling-aware thermostat, PV rule and MPC, WP4 robustness), 3c804fd (dashboard Scenarios and Controllers pages), 392c287 (forecast error of the weather-conditioned forecaster measured on the test weeks and plotted; cooling archetypes written into the proposal), 7b68d35 (dashboard Climate, Cooling matrix, Scenario explorer and Houses pages). The room-unit archetype (WP2b) was still running when this entry was written.
- Registers merged from the fork drafts: SRC-014, DER-023 to DER-027, TR-018 to TR-020, M-006, parameter rows for the cooling parameters, assumptions A-032 to A-047 and A-050 to A-057, issues ISS-043 to ISS-048, algorithms ALG-012 (exact optimum with cooling) and ALG-013 (cooling MPC and references), experiments EXP-021 to EXP-024, decisions D-048 to D-053. Drafts collided and were reconciled: ISS-043 to ISS-046 of the WP2 draft and ISS-046 to ISS-048 of the WP3 draft overlapped the WP1 block, so the WP2 issues were merged into ISS-048 and the WP3 overheating and known-weather issues kept ISS-046 and ISS-047 (the dashboard refers to ISS-046); both drafts named ALG-012 (exact optimum from WP2 kept, the cooling MPC became ALG-013); EXP-021 was used by both the WP1 and the WP3 draft (WP1 and WP2 merged into EXP-021, the matrix is EXP-022, the controller study EXP-023, robustness EXP-024). Ids reserved for WP2b: A-058 to A-069, EXP-025 to EXP-028, ISS-049 to ISS-052, further M ids; A-048 and A-049 are unused.
- `data/canonical/MANIFEST.sha256` regenerated (19 climate files added, no existing entry changed); `swiss/run_pipeline.sh` runs the climate steps when `data/raw/ch2025_klo/` exists; docs/reproduction.md section 4c lists the matrix commands.
- Lessons: (1) a margin option that was clipped by an existing bound had no effect and gave identical numbers (EL-0077); (2) the first WP3 MPC run let uncooled buildings overheat at no cost (free slack), inflating its share of the exact optimum; it was found before the commit and all MPC tasks were rerun with the Phase B penalty; (3) the first matrix used unthreaded workers: load average about 35 on 12 cores, later runs set one thread per worker; (4) a register row appended after the closing prose of a markdown table is not parsed: insert rows inside the table.
- The dashboard freshness tests fail until the audit bundle is rebuilt on a clean committed tree (expected after register edits).

### EL-0079 — 2026-11-19 — Room-unit archetype merged into the registers
- WP2b (commit e167f2c): archetype B implemented, replay equal on `hist_hw99_high_ru`, matrix of 20 cells in 42 minutes on 10 single-thread workers. Registers: A-058 to A-061, ISS-049 to ISS-052, D-054, D-055, M-007 (five parameter rows), EXP-025, EXP-026; ALG-012 and ALG-013 notes. Row counts in `test_dashboard.py` updated (decisions 63, assumptions 59, issues 95, models 7, parameters 79, experiments 26). The audit bundle needs the parent's rebuild on a clean tree; freshness tests fail until then.
- Check made while merging: the overheating numbers quoted in the WP2b draft (46,168 and 41,220 district degree-hours, 8,246 uncooled zone) match `climate_summary.json` and `climate_summary_ru.json`.
