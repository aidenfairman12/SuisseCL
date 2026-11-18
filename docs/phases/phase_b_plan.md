# Phase B plan — authoritative implementation specification

Date: 2026-11-18 (order of step 7 changed by D-037) · Status: **approved by the owner on 2026-11-18 (D-031, D-032). This file is the single source of truth for Phase B.**
It supersedes the task order and the "Phase B is not authorized" wording of `master_plan.md` section 7; the task definitions B1 to B9 and the acceptance criteria
(plan 7.2 and 7.3) still apply unchanged. If this file and `master_plan.md` section 7 disagree, **this file wins**. If this file and a decision in
`docs/decisions/decision_log.md` disagree, the decision log (newer row) wins and you must report the conflict.
Rationale and evidence for the order: `phase_b_reordered_proposal.md` (read it once; do not re-open its decisions, they are closed below).

## 0. Read this first (reading order for a new agent)
1. `README.md` and `docs/HANDOFF.md` (environment pins, CityLearn 3.3.0 traps, **working agreements**).
2. This file, completely.
3. `docs/phases/phase_a_completion_report.md` (what exists, 13 open limitations) and `docs/phases/phase_b_reordered_proposal.md` (why this order).
4. `docs/decisions/decision_log.md` rows D-017a, D-021, D-023, D-029, D-030, D-031, D-032 and `docs/decisions/issues_and_risks.md`.
5. `docs/experiments/validation_reports/oracle_cost_bound.md` (the Phase A ceiling and the what-if table) and `swiss/experiments/oracle.py`, `swiss/experiments/rl.py`.

## 1. Working agreements (non-negotiable)
- **Ask the owner before every commit, every push, every data download, and every cluster job.** Approval for one does not cover another. (HANDOFF section 8.)
- **No cluster jobs until Phase B is finished** (D-032 item 9). Local runs of unit tests and of the exact optimum are fine. RL grids are written and tested but not submitted.
- Commit cycle: commit code, then on the clean tree run `swiss/dashboard/build_bundle.py`, `swiss/contract/export_v1.py` and `export_v1.py --full --out web/public/bundle/sim_full`, then commit the bundles as a second commit. Adding a decision-log or registry row changes the audit bundle and needs the row count in `swiss/tests/test_dashboard.py` updated.
- You own `swiss/**`, `data/**`, `docs/**`, `web/public/bundle/**` and (D-029) `web/src/**`. Any `web/src` change must pass `swiss/dashboard/lint.py`, `tsc` and ESLint.
- Never present an assumed number as data. Provenance classes (D-021): measured, derived, modeled, synthetic, plus the assumed-parameter badge. Hot water is "hot water and other base load". Carbon is relative-only.
- Every new data source, model, algorithm, experiment and decision is registered (data source registry, model registry, algorithm registry, execution log, decision log, issues). Do not invent names, URLs or numbers; mark claims verified, reported or unverified.
- The data contract stays **additive**: minor version bump (v1.1), `null` means absent, never 0, existing files and fields unchanged.
- Do not edit CityLearn itself. Use stock classes; extend through subclasses in `swiss/`.
- Full test suite must pass before each commit request (`PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q`, last full run 164 passed).

## 2. Approved decisions that govern Phase B
| # | Decision | Where recorded |
|---|---|---|
| 1 | Phase A approved, including its 13 open limitations; Phase B authorised according to this plan | D-031 |
| 2 | Reordering approved; **ceiling-first rule**: run RL on a scenario only if its exact optimum saves at least **3 %** of the headline metric (cost); otherwise write a negative result | D-032 |
| 3 | PV capacity is an **assumption**, set by the rule in 4.3, varied in a sensitivity run | D-032 |
| 4 | Export remuneration from the ElCom data (licence unstated, ISS-006; the owner approved its use). First verify the data really contain export remuneration; if not, stop and ask | D-032 |
| 5 | Battery per building first; district-level or other sizing only later as a variation | D-032 |
| 6 | Thermal model: routes (a) validated Swiss framework and (c) dataset with indoor temperature first; (b) synthetic lumped RC is the fallback. A comfort term re-enters the reward once a thermal model exists | D-032 |
| 7 | Day-ahead price data: download approved, but check the licence per price zone first and **do not publish derived series in the public bundle** without a licence check (the dashboard is public by choice) | D-032 |
| 8 | 15-minute pipeline: undecided by the owner; default is task order position 10 with an early cheap feasibility spike (task B2a) | D-032 |
| 9 | No cluster jobs until Phase B is finished | D-032 |
| 10 | RL work (scripts and reward preset) is not started until steps 8 to 11 are done, so it is designed once with the final reward and environment | D-037 |

## 3. Reality of the tariff (read before touching B5)
The current Swiss household standard is a **two-tier tariff** (high and low tariff). Our S0 baseline uses the EKZ standard product (15.05 and 19.05 Rp/kWh excluding VAT, high tariff weekdays 07:00 to 20:00 local). **S0 stays the realistic baseline and is never replaced.**
Time-variable products exist in Switzerland but are pilots or opt-in: the EKZ time-of-use grid fee (daily spread about 6 Rp/kWh) and dynamic grid fee (about 3 Rp/kWh, grid fee only), both for part of 2023 only; a Swiss field project tested price schemes from flat to real-time prices with a household appliance controller [1], and a 2,447-installation 15-minute smart-meter dataset includes a subset on novel grid tariffs [2]. Retail dynamic tariffs elsewhere are opt-in with modest uptake [5][6]. Therefore:
- A richer tariff (rung S4) is a **labelled scenario** ("what if prices varied more"), never a claim about current Swiss prices. Dashboard text must say so.
- The what-if spreads in the Phase A oracle report are stylised, not tariffs.
- Results are reported for S0 first, then the scenario tariffs next to it.

## 4. Scenario ladder and task specifications
Ladder: S0 Phase A district (done, ceiling 0.84 %) → S1 PV and export price → S2 + battery → S3 + thermal model with comfort band → S4 + richer tariff scenario → S5 EV and LEG (only with justified data).
Task order (each step needs your commit/push requests to the owner as in section 1):

| Order | Task | Output | Accept when |
|---|---|---|---|
| 1 | B1 review | closed gate items (ISS-021 PV status, ISS-019 EKZ heat-pump type, ISS-024 HEAPO timestamp label) or documented as still open; this plan's thresholds restated in the execution log | report section added; issue rows updated |
| 2 | B9 metrics subset | module computing peak grid import, coincident district peak, PV self-consumption, self-sufficiency, import and export cost, battery cycles, comfort violations (once S3) from a rollout | unit tests with hand-computed toy cases |
| 3 | B3 PV | hourly building PV series, provenance modeled + assumed badge | 4.3 checks |
| 4 | B5 import and export | export price per building from ElCom; accounting identity import_cost − export_revenue = bill | 4.4 checks |
| 5 | B4 battery | CityLearn electrical storage per building | 4.5 checks |
| 6 | Ceiling on S1, S2 | oracle generalised (PV, battery, export); written ceiling table | 4.6; gate applied |
| 7 | RL on S1/S2 | **moved after step 11 (D-037, owner 2026-11-18)**: gate passed (D-036); scripts, export-aware reward preset and jobs are done as one block with the final reward, after steps 8 to 11; jobs are submitted only when the owner lifts item 9 | per 4.7 |
| 8 | B7 thermal model | routes (a) and (c) checked first, then (b) | 4.8 |
| 9 | B5 richer tariffs | scenario tariffs incl. downloaded day-ahead prices | 3 and 4.4 |
| 10 | B2 15-minute pipeline | 15-minute dataset and environment | criteria 1, 2 |
| 11 | B6 LEG, B8 EV | only with verified assumptions and data | criteria 7, 8 |
| 12 | Phase B report | plan 7.4 plus updated Phase C proposal | criterion 12 |

**B2a feasibility spike (do after step 2, half a day at most):** run one building at 900 s through the existing builder, only to learn what breaks (episode length, tariff indexing, DST, contract per-step energy). Write findings into the execution log. Do not commit a half-working 15-minute environment.

### 4.3 PV (B3)
Inputs: MeteoSwiss global and diffuse irradiance (Zurich/Kloten) already in `data/canonical`; HEAPO PV flags and returned energy, ETH/EKZ `kWh_to_grid` as plausibility checks only.
**Default capacity rule (assumption, flagged):** per building, choose kWp so that annual PV yield equals annual building electricity import (heat pump included) — the literature finds optimal household PV systems generate roughly the household's consumption [3] — capped by a rooftop proxy that you derive from floor area and document; vary yield-to-demand at 50 %, 100 %, 150 % in the sensitivity run. Buildings with unknown PV status are treated as having the scenario PV; the scenario is labelled "with assumed PV", not a description of the real houses. Where a building really has PV, reconstruct hidden self-consumed demand before adding the assumed PV (document the method), or exclude that building from S1 and say so.
Orientation and tilt: assumed south, tilt 30° (documented), efficiency and loss chain documented. Swiss PV-battery studies [4] and building-database sizing methods [3] are the references to compare against.
Checks: annual specific yield (kWh/kWp) within a documented plausible Swiss range, zero at night, energy units in kWh per step, tests for sign convention in CityLearn (generation is negative in `solar_generation` conventions: verify against the 3.3.0 source, do not assume).

### 4.4 Tariffs and export (B5)
Verify first that the ElCom data contain export (feed-in) remuneration for the utility zone; record the file, table, year and licence status in the data source registry and ISS-006. If absent: stop and ask the owner. Import and export prices are separate series; CityLearn needs an explicit check of how export revenue enters the cost KPI (HANDOFF traps; write a replay test that your own accounting equals the environment's). Day-ahead prices: licence per zone before download (ask the owner at download time); store raw under `data/raw/` (gitignored); derived series stay out of `web/public/bundle` unless the licence allows.

### 4.5 Battery (B4)
Per building. Capacity, power, efficiency and depth-of-discharge are **assumptions** with sources where available, labelled synthetic; start from a documented kWh-per-kWp rule (state it) and sweep. Tests: energy conservation including losses, SoC bounds, power limits, no simultaneous charge and discharge when the optimiser is run.

### 4.6 Ceiling per rung
Generalise `swiss/experiments/oracle.py`: add PV, battery dynamics, export price as linear constraints (the problem should stay a linear program; confirm). Validate every rung by **replay in CityLearn** (the Phase A tool replays exactly to 0.01 CHF; keep that standard). Produce a table like the Phase A report: ceiling in CHF and % of bill, and what-if rows (battery ×0.5/×2, PV ×0.5/×1.5, export price). **Gate:** ceiling < 3 % on cost → record a negative result for that rung, do not queue RL, continue the ladder.

### 4.7 RL on a rung (written now, run later)
Reuse `swiss/experiments/rl.py` (held-out weeks protocol, bootstrapping at window ends, stored-heat correction) and `swiss/hpc/*`. Extend rewards only through the existing preset mechanism. Report every learner next to zero-action, tuned rules and the exact optimum, on all B9 metrics, raw and corrected. Three seeds. Do not submit jobs (item 9).

### 4.8 Thermal model (B7)
Check (a): the validated Swiss framework (Meister et al. [7]: availability, licence, inputs) and (c): any dataset with indoor temperature (HEAPO and ETH/EKZ have none, ISS-004). Report what was found before building anything. Fallback (b): lumped RC calibrated to heat-pump electricity versus weather, partially identifiable, labelled synthetic. Compare against the Phase A representation (plan 7.2 B7). CityLearn 3.3.0 supports dynamics buildings and heat-pump modulation; the COP model has no cycling benefit (ISS-034) — state this in results. Once a thermal model exists, add a comfort term to the reward (D-018, D-019) and a comfort-violation metric.

## 5. Stop conditions (stop and report instead of continuing)
- A data source licence is unclear and the owner has not approved it.
- ElCom data lack export remuneration.
- A replay of an exact optimum differs from the environment by more than 0.5 %.
- A full test run fails and the cause is not in your change.
- Any step would need a cluster job, a commit, a push, or a download that is not yet approved.

## 6. Expectations
Phase B may end with several negative results (ceiling below 3 %). That is a valid, defensible outcome: it answers, with a reproducible method, where controller value exists and where it does not; it matches Swiss system studies that find heat-pump flexibility value in building inertia, PV and peaks rather than tariff arbitrage [7][8]. Deliverables that remain useful in every case: the ceiling-first method, the extended environment (PV, battery, export, thermal), the metrics module, the value-of-storage and value-of-PV curves, and the documented RL protocol ready to run.

## References
[1] [Smart grid, load management and dynamic pricing for electricity: Simulation results from a field project in Switzerland](https://consensus.app/papers/details/w:bc0283e9-70e8-476a-8530-ce0dd7b5eafc/?utm_source=claude_desktop) (Antonioli Mantegazzini et al., 2018)
[2] [Dataset on residential electricity load profiles in Switzerland](https://consensus.app/papers/details/w:0ff5a78c-415f-43f9-a502-e8d272c91b4b/?utm_source=claude_desktop) (Kaiser et al., 2026)
[3] Galvin 2022 (Germany, optimal PV and storage per household); Rieck 2025 (building-database PV sizing). Consensus search results of 2026-11-18; read the papers before citing numbers.
[4] Han 2022 (Swiss PV-battery techno-economics by customer group); Li 2023 (Swiss community PV placement).
[5] Stute et al. 2024, Advances in Applied Energy (dynamic tariffs and flexibility, Germany).
[6] Bhagwat et al. 2020 (dynamic retail tariffs: choices and barriers).
[7] Meister et al. 2026, Applied Energy (Swiss heat-pump flexibility from monitored data).
[8] Mellot et al. 2025 (direct load control for heat pumps, Swiss system).
Further references: `phase_b_reordered_proposal.md`, references [1] to [13].
