# Control methods beyond RL: ranked short list (research note, 2026-11-19)

Status: research note, not a decision. Nothing here has been run. Every expected gain is an **estimate (assumption)** unless it quotes a SuisseCL result or a cited paper.

## 1. Facts this note relies on (from the Phase B report)

| Scenario | Exact ceiling, test weeks | PV rule, test weeks | Best RL, test weeks | Gap ceiling minus PV rule |
|---|---|---|---|---|
| S1 PV | 5.5 % | about 0 % | +1.1 % (worse) | 5.5 points |
| S2 PV + battery | 14.6 % | 5.5 % | +3 % (worse) | 9.1 points |
| S3 S2 + RC mass | 14.8 % | 5.5 % | +58 % (worse, comfort broken) | 9.3 points |

The tariff matters most. The realistic baseline is the EKZ two-tier tariff, which is **known in advance**. Price forecasts are therefore not needed in the baseline. Only PV, electrical load and heat/DHW demand have to be forecast. Price forecasts matter only in the labelled day-ahead scenario.

Where the 9-point S2 gap probably comes from (hypothesis, testable from existing oracle trajectories): the PV rule only charges storage from PV surplus. The oracle also (a) charges the battery and tanks in the low-tier hours when tomorrow's PV will not fill them, and (b) discharges in high-tier hours. Point (a) needs only a coarse forecast of tomorrow's PV and load. This is why forecast-based methods are expected to recover a large share of the gap. **First action: break the oracle's S2 savings down into PV self-consumption, tier arbitrage and tank shifting**, using the oracle's own schedules (no new data).

## 2. Ranked short list

### 1 — Receding-horizon MPC: the oracle LP with forecasts (test first)

- **What**: re-solve the existing oracle LP (`swiss/experiments/oracle*.py`, HiGHS) every hour over a 24 to 48 h horizon. Use forecasts instead of actuals, apply only the first action, and replay in a CityLearn subclass exactly as the oracle replay does. In S3, the MPC uses the fitted RC model internally.
- **Expected gain (estimate)**: most of the gap in S2/S3, plausibly 60–90 % of the ceiling (about 9–13 % of the bill). This range is an assumption, not a measurement. The experiment in section 3 replaces it with a measured curve. Precedent: the 2022 CityLearn Challenge was won by forecasting + rolling-horizon optimisation (with an RL ensemble), and third place was a per-building forecast + LP solved each step [1]. In the same challenge, the SAC baseline did worse than the top eight entries, and a fine-tuned RBC beat the median entry [1]. The 2021 winner used optimisation-based policies with parameters adapted online [2]. An MPC-vs-RL comparison on CityLearn PV-battery systems found MPC more suitable in most practical settings [3].
- **Data and forecasts**: tariff exact (known). PV: seasonal-naive or persistence, then a small regression on irradiance. Load and DHW/heat: seasonal-naive (same hour last week) or a linear model. Langtry et al. found a simple linear MLP as accurate as state-of-the-art forecasters for MPC in multi-building storage systems, and three months of training data cost about 10 % more forecast error [4]. No new downloads are needed for the first tests. Archived NWP forecasts would be a later, labelled option that needs approval: Open-Meteo has a historical-forecast archive from 2021 [5], but its 2023 coverage and day-ahead lags for this site must be checked first.
- **Effort**: low to medium, about 2–4 days. The LP, replay and accounting already exist. New work: a rolling loop, a forecaster module, and an initial-state hand-off at each step.
- **Peaks**: add an optional peak term (max net import per day or per week) to the LP to draw the bill-versus-coincident-peak trade-off. This addresses the finding that the cost optimum raises peaks by +74 % to +96 %.
- **Risk**: S3 model mismatch. If the MPC uses the same RC parameters as the plant, the result is optimistic. Add one run with perturbed RC parameters (for example ±20 % on R and C, an assumption) to show sensitivity.

### 2 — Tuned rule: PV rule + tariff-aware night charging

- **What**: keep the PV rule and add a low-tier charge to a target state of charge (battery and tanks). The target comes from tomorrow's forecast PV surplus (e.g. `target = clip(a − b × forecast_surplus, 0, 1)`), with discharge in high-tier hours. Tune 3 to 6 thresholds by grid or Bayesian search on the training weeks only.
- **Expected gain (estimate)**: between the PV rule (5.5 %) and MPC. If the decomposition in section 1 shows tier arbitrage dominates, it may get close to MPC. It is cheap, transparent and deployable without a solver.
- **Data**: the same seasonal-naive forecast as method 1. The thresholds must not be tuned on test weeks.
- **Effort**: very low, about 1 day.
- **Role**: the strong non-learning baseline every learner must beat. The current hand-set PV rule is a weak bar.

### 3 — Imitation of the MPC (behavioural cloning, then DAgger)

- **What**: train a small network to map observations (plus the same forecasts) to MPC actions. Then run DAgger: roll out the clone, query the MPC on the visited states, and retrain. Lee and Zhang did this for residential heat-pump control: a DAgger clone of the MPC kept MPC-like efficiency with constraint satisfaction [6]. DAgger-trained MPC clones have also been used for constrained battery charging [7].
- **Clone the MPC, not the oracle**: the oracle's actions depend on information the policy cannot observe (the true future). Cloning it teaches actions that cannot be inferred from the state and creates a bias that DAgger cannot remove. The oracle stays the ceiling.
- **Expected gain**: at most the MPC's gain, typically slightly less. The value is a solver-free policy that runs fast and is close to RL in form. It is also the warm start for method 4.
- **Effort**: medium, about 3–5 days after method 1.
- **Gate**: only if method 1 works and fast, solver-free inference is wanted.

### 4 — Residual RL on top of the tuned rule or the MPC clone (the RL route most likely to work)

- **What**: the action is `a = a_base + δ`, with `|δ|` bounded (e.g. ≤ 0.2). SAC learns only δ, starts at δ = 0, and is initialised so that it reproduces the base policy. In S3, keep the thermostat as a hard backstop and let RL adjust only the setpoint within the comfort band. This removes the costly exploration that broke comfort (780 K·h).
- **Evidence**: the published evidence is mixed. A SAC + RBC hybrid cut operating costs by 39.5–84.3 % against fully rule-based control across battery configurations, in a different setup with a weaker baseline [8]. Online HVAC RL lost about 8–18 % during exploration and did not beat the RBC, whereas batch/offline RL (CQL) stays close to the data-collecting policy [9]. In the 2022 challenge, SAC on its own was behind the top entries [1]. A study comparing BC, DAgger and IBRL as initialisations for SAC on CityLearn exists (found by search, not read).
- **Expected gain (estimate)**: by construction it cannot do much worse than its base policy. Any gain is limited to the gap that remains above the base (after MPC, likely 1–4 points, assumption). This only clears the 3 % gate if the base leaves at least 3 points.
- **Effort**: medium, about 3–5 days plus cluster runs. `rl.py` already exists; it needs a wrapper that adds the base action.
- **Other RL fixes, ranked by expected value**: (i) warm start (BC from the tuned rule or the MPC) before any longer budget; (ii) put the forecasts the MPC uses into the observation; (iii) normalise reward terms by their reference-policy magnitudes rather than by hand; (iv) only after that, larger budgets (≥ 1 M steps) and more seeds.

### 5 — Stochastic or robust MPC (scenario-based)

- **What**: optimise over several forecast scenarios (e.g. 5 to 20 sampled from historical errors) with shared first-step actions, or add a chance constraint on comfort in S3. The 2022 winner used stochastic data augmentation in its optimisation for this reason [1]. Forecast stability and commitment period also change the outcome when switching costs exist [10].
- **Expected gain**: only the part of the method-1 loss that comes from forecast error. Measure it first (section 3). If deterministic MPC with seasonal-naive forecasts is already within about 1–2 points of perfect-forecast MPC, skip it.
- **Effort**: medium. The LP grows linearly with the number of scenarios.

Not listed: offline RL on its own (no dataset better than the rules; the closest CityLearn work builds the dataset from RBC runs [11]), and pure RL with larger budgets (the evidence above does not suggest budget is the main problem).

## 3. Which to test first, and how to measure forecast need

Test **method 1** first, with **method 2** built alongside as its baseline. Run on S2, the largest clean gap with no comfort risk. Then repeat on S3, then S1. Each run gives held-out-week bills against the reference, the PV rule and the oracle.

Four runs separate the losses:

1. MPC with perfect forecasts, horizon 24 h and 48 h → **loss from the finite horizon** (oracle uses the whole week/year).
2. MPC with seasonal-naive forecasts → **realistic lower bound**.
3. MPC with perfect forecast + synthetic noise scaled to forecast error (nRMSE 0, 10, 20, 30, 50 %; synthetic and labelled) → **gain versus forecast quality** curve. This answers "how much forecast quality is needed".
4. Optional: MPC with a peak term at 2 to 3 weights → bill-versus-peak trade-off.

Pass criterion (proposal): MPC with seasonal-naive forecasts beats the tuned rule by at least 2 points of the bill on the held-out weeks. Otherwise the tuned rule is the deliverable.

## 4. Is the model or data fidelity the limit?

- **Tariff and export price, not the controller, set most of the headroom.** With the two-tier tariff the ceiling is about 15 %. Under the day-ahead or pilot structures it is 16–21 % (Phase B report). It falls from 22.2 % to 10.4 % as export goes from 0 to 12 Rp/kWh. Better controllers cannot exceed these numbers. The tariff assumption is the biggest lever on any reported gain.
- **RC model**: mass adds 1.6 points under the single-node model. A single node probably understates fast air-temperature swings and overstates usable storage at a fixed comfort band (assumption). The low value may therefore come partly from the model, partly from the tariff (small price spread between tiers). Check this before claiming that mass has little value: re-run the S3 oracle at a stylised five-fold spread, which already exists as a scenario. If mass becomes valuable there, the limit is the tariff, not the RC model.
- **PV and load data**: hourly irradiance redistributed to 15 minutes by a clear-sky shape (A-022) removes intra-hour variability. This makes forecasts look easier at 15 minutes than they are. Report hourly as the reference, as now.
- **Missing pieces that would cap any controller**: tank sizes have no source (ISS-032); the COP model has no cycling or part-load effects (ISS-034). The MPC will exploit both just as the oracle does. Any result carries these as labelled assumptions.

## 5. References

[1] Nweye et al., "The CityLearn Challenge 2022: Overview, Results, and Lessons Learned", PMLR 220 (2023). https://proceedings.mlr.press/v220/nweye23a/nweye23a.pdf
[2] Khattar & Jin, "Winning the CityLearn Challenge: Adaptive Optimization with Evolutionary Search under Trajectory-based Guidance", AAAI 2023. https://arxiv.org/abs/2212.01939
[3] Zhan, Lei & Chong, "Comparing model predictive control and reinforcement learning for the optimal operation of building-PV-battery systems", E3S Web Conf. 396, 04018 (IAQVEC 2023). https://www.e3s-conferences.org/10.1051/e3sconf/202339604018
[4] Langtry et al., "Impact of data usage for forecasting on performance of model predictive control in buildings with smart energy storage", arXiv:2402.12539 (2024). https://arxiv.org/abs/2402.12539v2
[5] Open-Meteo Historical Forecast API. https://open-meteo.com/en/docs/historical-forecast-api
[6] Lee & Zhang, MPC-guided DAgger imitation for residential heat pump control (Cornell, 2021). https://arxiv.org/pdf/2104.00123v1.pdf
[7] "Deep-MPC: A DAGGER-Driven Imitation Learning Strategy for Optimal Constrained Battery Charging", arXiv:2406.15985. https://arxiv.org/pdf/2406.15985
[8] Hybrid SAC + RBC for battery/PV, Energy Reports (2022). https://iris.polito.it/bitstream/11583/2955660/1/1-s2.0-S2352484721014979.pdf
[9] "Safe Building HVAC Control via Batch Reinforcement Learning" (2022). https://www.aminer.org/pub/62b245cb5aee126c0fe70f53/safe-building-hvac-control-via-batch-reinforcement-learning
[10] Genov et al., "Balancing Forecast Accuracy and Switching Costs in Online Optimization of Energy Management Systems", arXiv:2407.03368. https://arxiv.org/abs/2407.03368
[11] "Optimization Solution Functions as Deterministic Policies for Offline Reinforcement Learning", arXiv:2408.15368. https://arxiv.org/pdf/2408.15368

Sources [6], [8], [9] and [11] were found by search and read only at abstract or summary level. Check their figures before quoting them in a report.

## 6. First test of method 1 on S2 (run 2026-11-19, `swiss/experiments/mpc.py`, results in `swiss/experiments/mpc_results/`)

Setup: S2 (PV + battery, 1 kWh/kWp), export 8 Rp/kWh, the eight held-out weeks (`rl.TEST_WEEKS`), same 96-step warm-up and scoring (`rl.window_metrics`) as the RL runs. The plant is CityLearn itself (the LP is re-solved every hour from CityLearn's tank and battery state; only the first action is sent), so forecast error and clipping show up in the realised bill. Zero-action bill on these weeks: 3046 CHF; exact optimum saves 14.55 %. One deterministic run per row, no seeds. S1 and S3 were not run.

| Controller (horizon 48 h unless noted) | Saving, raw bill | Share of ceiling | Highest hourly district peak |
|---|---|---|---|
| Zero action | 0 % | 0 % | 65.6 kW |
| PV rule (r = 0.1) | 5.65 % | 39 % | 64.4 kW |
| MPC, perfect forecasts (24 / 48 / 72 h) | 14.60 / 14.60 / 14.53 % | 100 % | about 120 kW |
| MPC, history-only forecasts (same hour last week for load and tank demand, same hour yesterday for PV) | 3.73 % (H24 3.54, H72 3.92) | 26 % | 117 kW |
| MPC, weather-conditioned forecasts (gradient boosting, trained outside the test weeks, weather taken as known) | 8.81 % (H24 8.96) | 61 % | 117 kW |
| same, plus lag features of the load itself | 9.06 % | 62 % | 121 kW |
| same, with the TRUE load (ablation) | 12.5 to 12.6 % | 86 to 87 % | 116 kW |
| same, with true PV and tank demand but forecast load (ablation) | 9.38 % | 64 % | 121 kW |
| MPC with perfect forecast plus synthetic error 0.1 / 0.3 / 0.5 x standard deviation | 12.89 / 9.71 / 6.69 % | 89 / 67 / 46 % | about 120 kW |

Findings:
1. **The receding-horizon structure and the 24 h horizon cost nothing.** With perfect forecasts MPC equals the exact ceiling at 24, 48 and 72 h. The gap to the ceiling is forecast error, not method.
2. **History-only forecasts are not enough.** Their nRMSE (RMSE over the series standard deviation, measured in `mpc_results/forecast_error.json`) is 0.55 to 0.99, and the bill saving (3.7 %) falls below the PV rule (5.65 %). This matches the synthetic-error curve, which falls about linearly from 14.6 % at no error to 6.7 % at 0.5.
3. **A weather-conditioned forecast beats the PV rule by about 3.2 points** (8.8 % against 5.65 %), recovering 61 % of the ceiling. PV is easy once irradiance is known (test-week nRMSE 0.07). **The binding forecast is the electrical load** (nRMSE 0.68, which weather and lags barely improve): with the true load the saving is 86 to 87 % of the ceiling; with true PV and tank demand but forecast load it stays at 64 %.
4. **Peaks get worse.** The highest district hour rises from 66 kW to 117 to 121 kW, as the exact optimum does, and the mean weekly peak rises by 17 to 40 %. No peak term was tested, so the bill-versus-peak trade-off is still open.

Assumptions and limits (labelled):
- A-M1 / A-M3: outdoor temperature (heat-pump COP and maximum output) and irradiance are taken as KNOWN over the horizon, a day-ahead weather forecast with no error. A real weather forecast will have errors; PV nRMSE 0.07 is therefore an optimistic bound. The synthetic-error curve gives the sensitivity.
- A-M2: stored energy at the end of the horizon is credited at the lowest tariff price (battery times eta1, tank heat divided by COP times round-trip efficiency). Not tuned; horizon 24, 48 and 72 h agree, which suggests it is not critical here.
- The comparison uses the raw bill. The version corrected for the stored energy at the end of the window (`cost_corrected`) is 0.3 to 0.9 points higher for MPC and is printed by `mpc_report.py`.
- The load series in this district is built from assumed household profiles (not measured for these buildings), so its randomness, which limits every forecaster here, may differ from real houses. This is the main reason to treat the 61 % as a result for this dataset.
- Not tested: S1, S3 (needs the RC model inside the MPC), peak term, perturbed model parameters, several seeds of the forecaster.

Consequence for the ranking: method 1 is confirmed as the right first method (14.6 % reachable, 8.8 to 9.1 % with a realistic forecaster, against 5.65 % for the PV rule). The next gain is in **load forecasting** and in the **stochastic variant (method 5)**, not in a longer horizon. A learned residual (method 4) can also target the load-forecast error, since a policy sees the realised load each step.

## 7. Recent Swiss rule and tariff changes that matter for the tariff side (searched 2026-11-19; unverified against official texts)

- **EKZ dynamic tariff, optional from 1 January 2026**: prices can change every 15 minutes with grid load and wholesale prices ([SRF](https://www.srf.ch/news/schweiz/dynamische-stromtarife-ekz-bieten-dynamische-tarife-an-viele-andere-firmen-noch-nicht)); prices for the next day are published from 18:00 ([EKZ technical description](https://www.ekz.ch/dam/ekz/privatkunden/strom/tarife-und-agb/Tarifdokumente/tarife-2026/EKZ_Dynamischer-Tarif-2026_technischer-Beschrieb.pdf)); valid in 2026 and recommended only with an energy management system ([EKZ tariff sheet](https://www.ekz.ch/dam/ekz/privatkunden/strom/tarife-und-agb/Tarifdokumente/tarife-2026/ekz-dynamischer-tarif-2026-tarifblatt.pdf)). Prices are known ahead, so MPC needs no price forecast; the load forecast stays the binding one (section 6). A blog reports a range of up to +15 and down to -5 Rp/kWh around the standard tariff ([freestate.ch](https://www.freestate.ch/blog/dynamische-stromtarife-schweiz-2026)); the price levels themselves were not found.
- **Export pay (Mantelerlass)**: a quarterly federal reference price with a minimum of 6 Rp/kWh for systems up to 30 kW ([Thurplus](https://www.thurplus.ch/ueber-thurplus/presse/news/detail.html/33/news/553)); ElCom [FAQ](https://www.elcom.admin.ch/dam/de/sd-web/weRgj22ICsTE/053-00004_20260616_AN_FAQ%20ES2050%20ab%20Mantelerlass_DE.pdf) gives 0 above 30 kW for systems with own consumption; a dynamic export tariff is reported from 2027 ([Technikblog](https://technikblog.ch/2026/09/der-dynamische-rueckliefertarif-ab-2027-verstaendlich-erklaert-die-drei-bausteine-der-neuen-einspeiseverguetung/)). Sources disagree on extra premiums. Use 6 Rp/kWh as a labelled export-price point next to 4 and 8; the S2 ceiling then lies between 19.4 and 15.6 % (Phase B report).
- **Local electricity communities (LEG)**: a search summary says storage may not be used to trade between the outside market and the LEG; I did not find the source text. Check ElCom's FAQ above before building that constraint into the LP.
- **Not tested here**: a replay of the real 2026 dynamic tariff needs a price archive that I have not found; any download needs your approval. The what-ifs are scenarios (2026 rules on 2023 data).

## 8. Peak term, S1 and S3 (run 2026-11-19; `swiss/experiments/mpc.py --peak-w / --scenario s1|s3 / --rc-perturb`, tables from `mpc_report.py <scenario>`)

Same protocol as section 6 (eight held-out weeks, 48 h horizon, one deterministic run per row). "Weather" = the weather-conditioned forecaster of section 6 (weather taken as known, A-M3). Peak term: one joint LP over the six buildings with a district peak variable P >= net import at every horizon step, cost `peak_w` CHF per kW of P (the weight acts every hourly re-solve, so it is a tuning knob, not a tariff). "Highest hour" is the largest district net import in the eight weeks; "weekly peak" is the mean of the eight weekly maxima.

**S2 (PV + battery), exact optimum 14.55 %**

| Controller | Saving | Share of ceiling | Highest hour | Weekly peak |
|---|---|---|---|---|
| Zero action | 0 % | 0 % | 65.6 kW | 48.7 kW |
| PV rule | 5.65 % | 39 % | 64.4 kW | 41.7 kW |
| MPC weather, no peak term | 8.81 % | 61 % | 117.3 kW | 57.7 kW |
| MPC weather, peak weight 0.1 | 8.94 % | 61 % | 63.4 kW | 40.1 kW |
| MPC weather, peak weight 0.3 | 8.79 % | 60 % | 60.3 kW | 39.4 kW |
| MPC weather, peak weight 1 | 7.91 % | 54 % | 57.1 kW | 36.4 kW |
| MPC perfect forecast, no peak term | 14.60 % | 100 % | 120.0 kW | 59.5 kW |
| MPC perfect forecast, peak weight 0.3 / 1 / 3 | 13.88 / 11.92 / 11.34 % | 95 / 82 / 78 % | 48.3 / 40.7 / 38.6 kW | 25.5 / 21.0 / 19.3 kW |

Reading: the peak is nearly free at small weights. With realistic forecasts a weight of 0.1 keeps the saving (8.94 %) and brings the highest hour from 117 kW to 63 kW, below the zero-action 65.6 kW, with the weekly peak 18 % below zero action. With perfect forecasts, weight 0.3 loses 0.7 points and cuts the highest hour by 26 % against zero action. The cost optimum's +74 % peak is therefore a property of the unconstrained bill optimum, not a necessary price of the saving. Weights 1 and above cost 1 to 3 more points.

**S1 (PV only), exact optimum 5.48 %**: MPC with perfect forecasts 5.48 % (100 %), with weather forecasts 3.39 % (62 %), PV rule -0.20 % (the rule loses money here). Highest hour unchanged (65.6 kW). S1 passes the 3 % gate at the ceiling and MPC with a realistic forecaster clears it.

**S3 (S2 + RC building with 21 to 24 C band), exact optimum 14.75 %, reference = thermostat**

| Controller | Saving | Share of ceiling | Highest hour | Weekly peak | Hours below 21 C (K h) |
|---|---|---|---|---|---|
| Thermostat | 0 % | 0 % | 63.2 kW | 41.6 kW | 0 |
| PV rule | 6.05 % | 41 % | 57.5 kW | 34.9 kW | 0 |
| MPC perfect forecast | 15.04 % | 102 % | 155.6 kW | 73.7 kW | 0 |
| MPC weather | 11.39 % | 77 % | 155.7 kW | 74.4 kW | 0 |
| MPC weather, peak weight 1 | 9.47 % | 64 % | 55.7 kW | 30.7 kW | 3.1 |
| MPC weather, planner model H and C x0.8 (plant unchanged) | 11.59 % | 79 % | 155.7 kW | 71.2 kW | **396** |
| MPC weather, planner model H and C x1.25 (plant unchanged) | 10.86 % | 74 % | 154.9 kW | 76.4 kW | 0 |

Reading: with the exact room model MPC is much better in S3 (11.4 %) than in S2 (8.8 %), because heating is a large, forecastable-from-weather load and building mass is one more storage; it clears the PV rule by 5.3 points. The peak without a peak term rises 146 % (155 kW against 63 kW), and with weight 1 falls to 56 kW at a cost of 1.9 points. **Model mismatch matters for comfort**: if the planner thinks the house has 20 % less conductance and capacity than it has (x0.8), comfort is violated for 396 K h over the eight weeks; the opposite error is safe. The saving itself moves little (10.9 to 11.6 %). Mitigations to test: a comfort margin (e.g. plan to 21.5 C), or correcting the model state from the observed room temperature each step (the planner already starts from the plant's temperature, so the error is in the dynamics, not the state).

Caveats specific to this section:
- MPC with perfect forecasts reaches 102 % of the S3 ceiling: the ceiling is a year-long optimum evaluated on the test weeks with the band 21 to 24 (upper limit relaxed to the thermostat path), and the MPC starts each week from a warm-up state with soft band slacks, so it is a different state path, not a better method than the exact optimum. Treat 100 to 102 % as "equal to the ceiling".
- The S3 plant is the CityLearn RC building with the same parameters as the planner (A-M4), so the x1.0 rows have no model error; only the x0.8 and x1.25 rows test it, and only for one assumed parameter change (both H and C together).
- Peak weights are in LP units, not tariff terms; a real demand charge would be set per month or year, so the result shows what is possible, not the right weight.
- One deterministic run per row; differences below about 0.3 points (e.g. weight 0.1 against none in S2) are not distinguishable.

**Updated ranking consequence.** MPC with a small peak weight is now a strong candidate on all three rungs: 8.9 % on S2 (against 5.65 % for the PV rule) with the peak below zero action, 11.4 % on S3 with the right model, 3.4 % on S1. Next: (1) a comfort margin or model-error handling for S3; (2) a better load forecast (section 6); (3) only then residual RL on the MPC.

## 9. S3 comfort safety and a better load forecast (run 2026-11-19; `mpc.py --rc-margin / --rc-correct`, `mpc_forecast.py`)

**Comfort margin and online model correction (S3, weather forecasts, 48 h, eight held-out weeks; reference = thermostat, ceiling 14.75 %).** "Planner x0.8" = the planner believes the house has 20 % less conductance and heat capacity than the CityLearn plant (assumed error, one direction only). Margin m = the planner keeps the room at 21 + m C or more; comfort is scored against 21 C. Correction = the planner adds a smoothed residual (predicted minus observed room temperature of the last step, clipped at 2 K, weight 0.3) to its dynamics each step.

| Planner model | Margin | Correction | Saving | Hours below 21 C (K h) |
|---|---|---|---|---|
| exact | 0 | no | 11.39 % | 0 |
| exact | 0 | yes | 11.39 % | 0 |
| exact | 0.25 | no | 10.25 % | 0 |
| exact | 0.5 | no | 9.10 % | 0 |
| exact | 1.0 | no | 6.78 % | 0 |
| x0.8 | 0 | no | 11.59 % | 396 |
| x0.8 | 0 | yes | 11.47 % | 200 |
| x0.8 | 0.2 | yes | 10.56 % | 0 |
| x0.8 | 0.3 | yes | 10.12 % | 0 |
| x0.8 | 0.5 | no / yes | 9.31 / 9.20 % | 0 / 0 |
| x0.8 | 1.0 / 1.5 | no | 6.99 / 4.58 % | 0 |
| x0.8, peak weight 0.3 | 0.5 | yes | 8.93 % | 0 (highest hour 64 kW) |

Reading: correction alone halves the comfort violation at a cost of 0.1 point; a margin of 0.2 C on top removes it for this error at a cost of 0.8 point (11.4 to 10.6 %). A margin without correction needs about 0.5 C, costing 2.3 points. Each tenth of a degree of margin costs about 0.4 to 0.5 points because the saving comes from preheating inside the band. Valid only for the tested error (x0.8, both parameters together, same direction as the failure); other errors (wrong gains, wrong COP, wrong DHW use) are untested, and in a real house the comfort constraint is measured, not modelled. An earlier version of the margin option was clipped by the thermostat path and had no effect; those runs were deleted and rerun after the fix.

**Better load forecast (offline test, `swiss/experiments/mpc_forecast.py`, S2 loads).** A model that sees the load observed just before the forecast origin, the 24 h mean, same-hour values a week and a day earlier (when already observed) and the weather, trained only outside the test weeks, gives a mean test-week nRMSE of **0.66 against 0.68** for the plain weather model, and 0.66 to 0.69 at every lead from 1 to 48 h. Even the one-hour-ahead forecast is that poor, so the load is mostly unpredictable from history and weather in this dataset; building 1 to 5 range from 0.50 to 0.89. The household load here is a synthetic composite of sampled EKZ apartment meters (docs/data/building_selection_design.md), so its noise is partly an artefact of how it was built, and real hourly household load is also noisy. I did not run MPC with this forecaster: a 0.02 improvement in nRMSE would move the bill by far less than the run-to-run differences.

Consequence: more forecast modelling of the load does not pay in this data. The next options are (a) **stochastic or robust MPC** (method 5), which plans against the load uncertainty instead of the mean; (b) **real-time feedback** (the plant sees the actual load each step, which the receding horizon already uses, and which a learned residual could exploit); (c) checking with measured, not synthetic, household loads before concluding anything about real houses (none for these buildings in the project, ISS list).

## 10. Stochastic (scenario-based) MPC on S2: negative result (run 2026-11-19; `mpc.py --scenarios K --share n --err-scale f`)

Method: for each building, K error scenarios (forecast of the weather model plus a block of out-of-sample forecast errors drawn from the training weeks at the same hour of day, errors shared across buildings in a step), one LP with the expected bill (cost / K), the first `share` steps of every tank's and the battery's net action shared by all scenarios, later steps free per scenario. Same state, bounds, terminal credit and eight held-out weeks as before; horizon 24 h unless noted; S2, exact optimum 14.55 %, deterministic weather MPC 8.96 %.

| Controller | Saving | Highest hour | Weekly peak |
|---|---|---|---|
| Deterministic, weather forecast (H24) | 8.96 % | 117 kW | 58.5 kW |
| Stochastic K=5 / 10 / 20, first action shared | 7.60 / 6.78 / 5.93 % | 115 / 91 / 77 kW | 55 / 52 / 50 kW |
| Stochastic K=10, first 6 steps shared | 5.75 % | 88 kW | 50 kW |
| Stochastic K=5 / 10, first 24 steps shared | 5.85 / 4.28 % | 83 / 87 kW | 49 kW |
| Stochastic K=10, horizon 48 h | 6.21 % | 97 kW | 51 kW |
| Stochastic K=5, sampled errors x0.25 / x0.5 | 9.05 / 8.94 % | 109 / 104 kW | 56 / 57 kW |
| Stochastic K=10, sampled errors x0.5 | 9.04 % | 99 kW | 53 kW |

Result: scenario-based stochastic MPC does not help on this problem; it loses 1.4 to 4.7 points, the loss grows with the number of scenarios and with the number of shared steps, and it goes away when the sampled errors are scaled down to a quarter or a half (which also recovers the deterministic result, a check that the implementation is consistent in the small-noise limit). The controller becomes more passive: peaks fall (a side effect, not a better bill).

What was checked: the scenario errors are the right size (load error 0.72 of the standard deviation out of sample on the training weeks against 0.68 on the test weeks; PV 0.07 against 0.07) and nearly uncorrelated in time (lag-1 autocorrelation 0.12), so the scenarios are not mis-scaled. My first hypothesis, that hindsight recourse (each scenario knowing its own later noise) makes the plan overvalue flexibility, predicts that sharing more steps should help; it made things worse, so that explanation is not supported. **The cause is not identified.** One more candidate that I did not test: sampled errors on tank demand and the household load together push the shared net tank and battery actions towards zero (the storage cannot be used against the price signal when the noise is as large as the signal). An implementation error that grows with the noise cannot be excluded either; the only evidence against it is the small-noise limit above.

Consequence: drop method 5 (stochastic or robust MPC) from the ranking for this data. The noise is close to white and as large as the signals, so the useful response to it is feedback (re-planning every hour with the observed load, which the deterministic MPC already does) and, possibly, a learned correction on top of it, not planning against scenarios. Remaining untested options for the gap between 62 % and 100 % of the ceiling: a learned residual policy on top of the MPC (needs training runs, a candidate for the cluster), a battery reserve rule, or measured instead of synthetic household loads.
