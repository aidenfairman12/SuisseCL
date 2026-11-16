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
