# Phase B proposal (reordered) — rationale only; approved 2026-11-18, the implementation spec is `phase_b_plan.md`

Date: 2026-11-18 · Status: **proposal only; nothing is implemented, and Phase B is not authorised** (plan 7: Phase B needs Phase A approved first, then your
explicit authorisation of an updated plan, §9.6). Replaces the ordering suggested in `phase_a_completion_report.md` sections 11 and 11c; the tasks themselves (B1 to B9)
are the plan's, section 7.2. Every number below comes from a file in this repository or is cited to a paper; every unknown is a decision in section 9.

## 1. Why reorder: what the Phase A environment showed

| Evidence | Result | Source |
|---|---|---|
| Exact perfect-foresight cost optimum, tanks as assumed | **299 CHF a year = 0.84 % of the bill** (replay in CityLearn realises it exactly) | `validation_reports/oracle_cost_bound.md`, D-030 |
| Same optimum, tanks 0.5 to 8 times larger | 0.57 % to 2.17 % | same |
| One assumption changed at a time | ideal tank 1.48 %; tank x4 1.60 %; price spread x2 1.68 %; spread x5 4.38 %; spread x5 with tank x4 7.73 % | same (what-if table) |
| Rule controllers over the year | cost +0.29 % to +0.50 %; highest hour -3.8 % to -6.1 % for three of the four rules and +1.2 % for the strongest; mean daily peak about 0 | `mechanism_check_phase_a.md` |
| Central SAC, 40,000 steps, two rewards, one seed | no cost saving on the held-out weeks (+0.37 % to +0.56 %, raw and corrected), highest hour -2 % to -3 % | pilot, EL-0049 |

Reading: in the Phase A scenario a controller can only shift heat between two tariff tiers 4 Rp/kWh apart using small synthetic tanks. The ceiling is below 1 % of the
bill, so no learner can show value and the benchmark cannot tell controllers apart. This is a finding about the scenario, not a bug: savings grow roughly with
storage size times price spread, and published savings of several percent to tens of percent come from setups with more flexibility, such as building thermal mass
and large price gaps (20 % for optimal control of a heat pump with storage under a time-of-use tariff [7], 16.5 % for RL against a tuned rule-based controller [8], 6 to 8 % by pre-cooling a building [9]), while a PV-assisted heat pump saved only EUR 35 to 90 a year even with near-optimal RL [10]. In an open-source optimisation, heat storage lowered the cost of meeting electricity demand by 13 to 26 % for PV-coupled heat pumps [5]. The model also cannot show the real benefit of tanks
in the literature (fewer heat-pump on/off cycles) because the COP depends only on outdoor temperature (ISS-034). Swiss studies place heat-pump flexibility value in building thermal inertia, PV integration,
peaks and congestion rather than in tariff arbitrage [1][2][3][4]; a bill-only reward cannot see those.

## 2. Principles of the reordered plan
1. **Ceiling first.** Before any learning run on a scenario, compute the exact optimum of that scenario (`oracle.py` generalised). Proposed gate: run RL only where the ceiling on the
   headline metric is at least **3 %**; below that, report a documented negative result instead of spending cluster time. (The 3 % is a proposal; see decision 2.)
2. **One lever per rung.** Add one flexibility lever at a time (scenario ladder, section 3) so its value is measured separately.
3. **Honest provenance.** Anything assumed (PV size, battery size, thermal parameters, export price) is labelled assumed or synthetic and varied in a sensitivity run; no unsourced number is presented as data.
4. **Baselines always.** Zero action (a strong baseline that is rarely reported [6]) and the tuned rules are scored next to every learner on identical data, raw and corrected for window effects (D-030).
5. **Licences first.** Data with unclear or restricted licences (day-ahead prices, ElCom) are not downloaded without your approval (plan 3.2, ISS-006).
6. **Contract stays additive.** PV and battery already exist in `components.json` as phase-B, not-modeled components; they become modeled variables in a minor version.

## 3. Scenario ladder
| Rung | Adds | Plan tasks | Exact optimum | Notes |
|---|---|---|---|---|
| S0 | Phase A district (tanks, two-tier tariff) | done | done: 0.84 % | negative-result reference |
| S1 | PV generation and an export price | B3, part of B5 | to compute | PV raises the value of shifting load to midday; export price sets the gap to retail |
| S2 | S1 + battery | B4 | to compute | the strongest flexible asset CityLearn supports natively |
| S3 | S2 + building thermal model with a comfort band, heat-pump modulation | B7 | to compute | building thermal inertia is the main flexibility in the heat-pump literature [1][7][8][9] |
| S4 | S3 + richer tariff (time-of-use, dynamic or capacity component) | rest of B5 | to compute | data and licence dependent |
| S5 | EVs, local electricity sharing | B8, B6 | later | only with justified data |
Expected structure of the optimum: PV, battery, linear RC dynamics, export prices and a capacity charge are all linear, so the exact optimum should remain a linear program (to be confirmed per rung);
an exact ceiling is then available for every rung.

## 4. Proposed task order (maps to plan tasks B1 to B9)
| Order | Plan task | Content | Needs | Acceptance (plan 7.3) | Depends on |
|---|---|---|---|---|---|
| 1 | B1 Review Phase A | close the gate items: PV status of the houses (ISS-021), EKZ heat-pump type (ISS-019), HEAPO timestamp label (ISS-024); decide the ceiling threshold | decisions 1 and 2 | report updated | Phase A approval |
| 2 | B9 (subset) | evaluation metrics before any reward is set: peak and coincident peak, PV self-consumption, self-sufficiency, import and export cost, comfort violations once S3 exists | none | criterion 10 | 1 |
| 3 | B3 PV | building-level PV from MeteoSwiss irradiance with documented orientation, size and efficiency assumptions; reconstruct demand where PV hides it | decision 3 | criterion 3 | 1 |
| 4 | B5 (import and export) | export remuneration and import price per building; no tariff that does not apply | decision 4 | criteria 5, 6 | 3 |
| 5 | B4 Battery | synthetic battery sizes tied to PV, limits, efficiencies, energy conservation tests | decision 5 | criterion 4 | 3 |
| 6 | RL on S1 and S2 | ceiling first, then SAC and MARLISA with the existing protocol (held-out weeks, then quarter cross-validation), three seeds, cluster | cluster time | criterion 11 | 3 to 5 |
| 7 | B7 Thermal model | RC model with comfort band; compare with the Phase A representation | decision 6 | criterion 9 | 1 |
| 8 | B5 (richer tariffs) | time-of-use, dynamic or capacity tariffs where data are licensed | decision 7 | criterion 6 | 4 |
| 9 | RL on S3 and S4 | as step 6 | cluster time | criterion 11 | 7, 8 |
| 10 | B2 15-minute pipeline | moved later: resolution matters for peaks and PV but is not the main lever; the data are already preserved at 15 minutes | none | criteria 1, 2 | 6 |
| 11 | B6 LEG, B8 EV | as planned, only with verified assumptions and data | later | criteria 7, 8 | 9 |
| 12 | Phase B report | plan 7.4, with the updated Phase C proposal | | criterion 12 | all |

## 5. Detail of the first tasks
**B3 PV.** Evidence in hand: HEAPO PV flags (516 yes of 650 known households), HEAPO returned energy, ETH/EKZ `kWh_to_grid` (41 single-family houses export more than 100 kWh), MeteoSwiss
global and diffuse irradiance at Zurich/Kloten. Gaps: PV status unknown for two of the three selected houses and for the apartment buildings; no orientation or capacity data; import-only
meters hide self-consumed demand, so demand must be reconstructed. Capacity per building is therefore an **assumption** (decision 3), varied in a sensitivity run.
**B5 (import and export).** The retail price is in hand (EKZ standard). The export remuneration has no source in the repository (ElCom page: no stated data licence, ISS-006); the gap between retail and export
price is what makes self-consumption valuable, so this input needs your decision (decision 4).
**B4 Battery.** CityLearn supports an electrical battery natively. Sizes, power limits and efficiencies are assumptions labelled synthetic, with sensitivity runs and conservation tests, as for the tanks (D-017a).
**B7 Thermal model.** No measured indoor temperature or thermal output exists in HEAPO or ETH/EKZ (ISS-004). Three routes: (a) build on a published Swiss framework validated against monitoring data, built from mostly public data
and covering building inertia and buffer tanks [1] (availability, licence and input needs still to be checked); (b) calibrate a lumped RC model to heat-pump electricity versus weather, only partly identifiable and labelled synthetic;
(c) obtain a dataset with indoor temperature. Recommended: check (a) and (c) first, with (b) as the fallback. CityLearn already supports thermal-dynamics buildings and heat-pump modulation [11]; a comfort term then
enters the reward (D-018, D-019).

## 6. Rewards and evaluation
Report every learner on all metrics (cost raw and corrected, import and export, peak, coincident peak, self-consumption, comfort once modeled) instead of committing to one weight set; train with a weight sweep
and show the cost-versus-peak trade-off. Reward design in building RL is largely ad hoc [12]; a tunable policy can serve several preferences without retraining [13]. The reward choice still open under D-023 is
settled per rung, after its ceiling is known.

## 7. What stays as built
Phase A data, models, results and tests; the RL harness (`rl.py`, held-out weeks and quarter folds, bootstrapping at window ends, stored-heat correction), the exact-optimum tool, the cluster scripts, the data contract (additive version),
and the dashboard (Phase B components are shown only once modeled).

## 8. Risks and honest expectations
- Even with PV and a battery the saving may be modest, and the Phase A result may repeat; the ceiling-first gate makes that visible early and cheap.
- Most Phase B inputs (PV size, battery size, export price, thermal parameters) are assumptions; results show what is possible in a stated scenario, not what a real household would save.
- The thermal model cannot be validated against measured indoor temperature unless a dataset is found (route c).
- Wider price spreads need data with restrictive licences; the stylised spreads in the what-if table are not a tariff.
- Scope: Phase B is larger than Phase A; the ladder lets it stop at any rung with a clear result.

## 9. Decisions needed from you
1. Approve Phase A at the gate (plan 9.6), including the 13 open limitations (completion report section 7).
2. Approve the reordering and the ceiling-first rule, and the threshold (proposed: RL only where the exact ceiling is at least 3 % of the headline metric).
3. PV: how to set capacity per building (for example proportional to floor area or housing units, flagged assumed), and whether to treat the houses with unknown PV status as without PV.
4. Export remuneration: which source and licence (or a stated assumption), since ElCom data carry no stated licence.
5. Battery: sizing rule (assumption) and whether batteries sit per building or per district.
6. Thermal model: route (a), (b) or (c), in the order recommended in section 5.
7. Day-ahead or other wide-spread price data: approve or decline the download and its licence terms; otherwise use only the EKZ products in the data: the time-of-use grid fee (daily spread about 6 Rp/kWh) and the dynamic grid fee (about 3 Rp/kWh, a grid fee only), both for part of 2023.
8. Keep the 15-minute pipeline at position 10 or move it earlier.
9. The Phase A RL cluster grid: skip it, or run only central SAC with R-001 for three seeds as a documented negative result (my recommendation: the latter, three cheap jobs).

## References
[1] [Bottom-up heat pump flexibility estimation for Swiss buildings considering monitored building data](https://consensus.app/papers/details/w:cd78b892-e4ed-4396-a787-7dffbdfc3953/?utm_source=claude_desktop) (Meister et al., 2026, Applied Energy)
[2] [Exploratory Analysis of Direct Load Control Policies for Heat Pumps in the Future Swiss Electricity System](https://consensus.app/papers/details/w:2e30cdbc-7b95-4c8b-ac3e-50c086172707/?utm_source=claude_desktop) (Mellot et al., 2025, EEM)
[3] [Evaluating Direct Load Control Contracts for Heat Pumps: A Swiss Case Study](https://consensus.app/papers/details/w:57af2f70-11af-4ead-8bc6-7302e3a7ec64/?utm_source=claude_desktop) (Ellemund et al., 2026, EEM)
[4] [Decarbonising heat with optimal PV and storage investments: A detailed sector coupling modelling framework with flexible heat pump operation](https://consensus.app/papers/details/w:7509d58d-dd2e-48e7-929d-928896d13c08/?utm_source=claude_desktop) (Rinaldi et al., 2020, Applied Energy)
[5] [Decarbonizing heat with PV-coupled heat pumps supported by electricity and heat storage: Impacts and trade-offs for prosumers and the grid](https://consensus.app/papers/details/w:9b2f6d01-ee5b-480b-91bc-0ff19ef36c22/?utm_source=claude_desktop) (Pena-Bello et al., 2021, Energy Conversion and Management)
[6] [Multi-agent storage dispatch in building communities: Information availability, inter-building dynamics, and the distribution of benefits](https://consensus.app/papers/details/w:0df093e9-36c4-4a8c-a58a-43bf2c4227fd/?utm_source=claude_desktop) (Zaregarizi et al., 2026, Energy and Buildings)
[7] [Optimal control of heat pumps with thermal storage under time-of-use tariffs](https://consensus.app/papers/details/w:e81f65b8-e038-4878-acdf-916c2a8a1b99/?utm_source=claude_desktop) (Fleming et al., 2025, IEEE CDC)
[8] [Weather-adaptive reinforcement learning framework for heat pump control under time-of-use tariffs](https://consensus.app/papers/details/w:11670618-5e4a-45fe-92c1-e53f379a1720/?utm_source=claude_desktop) (Aschidamini et al., 2026, Energy Conversion and Management)
[9] [Building HVAC control with reinforcement learning for reduction of energy cost and demand charge](https://consensus.app/papers/details/w:5e063a2e-4aba-4329-bf5f-326f7ab5916f/?utm_source=claude_desktop) (Jiang et al., 2021, Energy and Buildings)
[10] [Operational Optimization of PV-Assisted Heat Pump Systems Using Reinforcement Learning](https://consensus.app/papers/details/w:68749c09-ab51-43ed-bc55-ec2f71bbadf2/?utm_source=claude_desktop) (Heinz et al., 2026, International Sustainable Energy Conference)
[11] [CityLearn v2: energy-flexible, resilient, occupant-centric, and carbon-aware management of grid-interactive communities](https://consensus.app/papers/details/w:a7edc1e0-fc6f-48ca-a499-67ee6bc0d44f/?utm_source=claude_desktop) (Nweye et al., 2024, Journal of Building Performance Simulation)
[12] [PIRS: Physics-Informed Reward Shaping for SAC-Based Building Energy Management](https://consensus.app/papers/details/w:cb9071f8-e6f4-47b0-acfb-ba3d50157679/?utm_source=claude_desktop) (Zaregarizi et al., 2026, ACM Sustainability Week)
[13] [A multi-objective multi-agent deep reinforcement learning approach to residential appliance scheduling](https://consensus.app/papers/details/w:803b00de-10d5-4fc1-a862-c619c16622ba/?utm_source=claude_desktop) (Lu et al., 2022, IET Smart Grid)
