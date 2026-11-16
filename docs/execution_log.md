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
