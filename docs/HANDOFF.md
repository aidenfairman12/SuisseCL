# HANDOFF: state of the SuisseCL project (read this first)

Written for an agent with no prior context. Last updated 2026-11-16. The owner also has a separate implementation doc for
"Swiss phase 1"; this file covers what exists, what was learned, and the traps already found.

## 1. Goal
Apply RL / learned control for district energy management (CityLearn) to **Swiss** buildings (heat pumps, Swiss tariffs,
hotter summers with A/C). The work so far used a US, **cooling-driven** CityLearn dataset to build and test the pipeline.
That work is a *method sanity check*, not a Swiss result. Swiss data research is a separate track:
`docs/swiss_data_research_prompt.md`.

## 2. Repo map
- `my_data/run.py` baseline controllers on full datasets (do-nothing, BAU, hour rule, BasicBatteryRBC, RBCSmartPolicy).
- `my_data/rl.py` train SAC / MARLISA (train = steps 0-1535, test = 1536-2207), `--reward composite`, `--seed`, `--weights`,
  `--preset challenge`; `rl.py scales` computes reward normalisation; `rl.py baselines` scores baselines on the test window.
- `my_data/rewards.py` `CompositeReward` (comfort, cost, carbon, peak, ramp; each divided by a reference scale).
- `my_data/tuned_rule.py` 10-parameter rule + differential-evolution search on the composite reward.
- `my_data/reward_diagnostics.py` reproduces the comfort-term problem (section 4). `my_data/aggregate.py` mean +/- std over seeds.
- `my_data/make_report.py` + `metrics_template.html` -> `metrics_overview.html` (guide to all 21 KPIs).
- `my_data/hpc/` UBELIX scripts. `my_data/results/` KPI CSVs, `curve_*.csv` learning curves, `reward_scales.json`.
- Tag `v0-cooling-baseline` marks the repo state when this handoff was written (cooling-dataset phase; some cluster runs still finishing).

## 3. Environment (do not "fix" these pins)
- Laptop is **Intel x86_64 macOS**. The newest PyTorch with an Intel-Mac wheel is **2.2.2**, which was built against NumPy 1.x.
  So: `torch==2.2.2`, `numpy<2` (1.26.4) and `pandas<3` (2.3.3; pandas 3 needs NumPy 2). With NumPy 2 the 2023 datasets fail
  ("Could not infer dtype of numpy.float32") because their thermal model is a PyTorch LSTM.
- The cluster venv (`~/venvs/cl`) uses the **same pins** on purpose so results are comparable. CPU-only torch there.
- CityLearn 3.3.0 is **not** vendored. Clone it next to the repo (`CityLearn/`, commit `0eb78bc`); the datasets live in its
  `data/datasets/` (the pip package does not ship them). `CITYLEARN_DATA` overrides the dataset root.
- Local virtualenv: `cl/` (gitignored). Python: `cl/bin/python`.

## 4. Findings so far (with evidence)
1. **`env.evaluate()` KPIs are normalised to a "conventional counterfactual"** (same buildings, no storage, no partial-load
   control, PV kept), NOT to a business-as-usual rollout (docs: `CityLearn/docs/baselines.md`). An earlier statement to the owner
   said BAU; it was corrected. Lower is better; 1.0 = counterfactual.
2. **Do-nothing is a trap on the cooling dataset:** zero action leaves cooling off, so cost/carbon/peaks look great
   (cost 0.35) but 98% of hours are uncomfortable. Always read cost AND comfort together.
   `BusinessAsUsualAgent` == do-nothing here (no EVs/appliances; it does not run cooling).
3. **Comfort-term problem (most important open issue).** Equal weights make agents trade comfort away. Measured per-step raw
   terms (train window, `reward_diagnostics.py`): cooling off comfort=570, cooling-to-setpoint 494 (barely different) while
   peak 17 vs 55, ramp 2.0 vs 4.2, cost 0.11 vs 0.22. `mid_params` has LOWER discomfort proportion than cooling-off (0.58 vs
   0.96) but a WORSE comfort term (748), so the comfort penalty seems to punish overcooling (below setpoint, cubic below the
   band) at least as hard as being hot. This is a **hypothesis**, not verified. The reference scale for comfort (1887) comes
   from BasicBatteryRBC, whose cubed cold overshoots dominate the mean (heavy tail).
   Consequence: a tuned rule searched on this reward converged to "cooling essentially off" (cool_gain=0.007, held-out
   discomfort 0.967). An equal-weight mean of KPI ratios is also gameable (cooling off scores 0.69 vs 1.32 for a sensible rule).
4. Results on the held-out 28 days (district KPIs, lower better; mean over seeds, n in brackets):

   | | cost | daily peak | ramping | discomfort |
   |---|---|---|---|---|
   | do-nothing / BAU | 0.350 | 0.565 | 0.879 | 0.977 |
   | BasicBatteryRBC | 1.304 | 1.432 | 1.268 | 0.699 |
   | tuned rule (n=1) | 0.459 | 0.641 | 0.903 | 0.967 |
   | SAC central, composite (n=2) | 0.545 | 0.603 | 0.833 | 0.706 |
   | SAC per-building, composite (n=1) | 0.426 | 0.576 | 0.842 | 0.906 |
   | MARLISA, composite (n=2) | 0.422 | 0.552 | 0.779 | 0.921 |
   | SAC central, comfort-only reward (n=1, early run) | 0.775 | 0.819 | 0.955 | 0.170 |

   Central SAC seeds agree closely (cost +/-0.006). Per-building agents lean further towards giving up comfort.
   Seed counts will grow as cluster jobs finish (section 6).
5. SAC defaults differ from the schema's agent block (discount 0.99 vs 0.9, lr 3e-4 vs 1e-3, batch 256 vs 512, alpha 0.2 vs 1.0;
   MARLISA nets [400,300] vs [256,256]). `--preset challenge` applies the schema values; not yet run.
6. `citylearn_challenge_2023_phase_3_1/3_2/3_3` contain **identical** building/weather/price data (only schema.json differs):
   one benchmark, not three. Price is a two-level tariff (0.03025 / 0.06605); carbon varies 0.27-0.56.
7. Winners: 2023 control track = CHESCA (hierarchical, heuristics + control + ML, not pure RL); 2021 = optimisation-as-policy with
   evolutionary tuning. 2022 and other 2023 teams were not confirmed. Organisers note plain RBC / model-free RL can underperform MPC.
8. Seeds work: different seeds differ, the same seed reproduces exactly. The first training episode is pure random exploration
   (CityLearn default); learning starts in episode 2.

## 5. Traps already hit (CityLearn 3.3.0 specifics)
- A custom reward is constructed with `env_metadata=None`; build anything needing it lazily (see `rewards.py`).
- `calculate()` must name its argument `observations` (it is called by keyword).
- `MARLISA` and per-building SAC need `central_agent=False`; central SAC needs `True`. Per-building agents are ~4-10x slower
  than central (6 networks, 2 updates/step): central ~35-45 min/30 episodes, per-building ~2-3 h on UBELIX.
- Schema agent type `SACBasicRBC` does not exist in 3.3.0. Schema keys like `action_scaling_coef` are swallowed.
- Mid-training evaluation of MARLISA mutates internal buffers, so learning curves use the *training* episode KPIs, not test.
- Reward + KPI quirk: legacy `evaluate()` names are historical; `evaluate_v2()` has 214 `*business_as_usual*` rows (unused).
- Quebec dataset (heating-only, 20 buildings, 6480 h) and Vermont (heating+cooling, 47 buildings, 8760 h) exist in CityLearn's
  `data/datasets/` and were inspected (schemas/CSV headers only) as stand-ins for Swiss heating; **nothing was run on them**.

## 6. UBELIX (HPC) usage
- SSH alias `ubelix` (needs university VPN). Project clone: `~/SuisseCL`; datasets copied to `~/SuisseCL/my_data/datasets`
  (gitignored); venv `~/venvs/cl`. The old temporary folder `~/suissecl_run` is being deleted by the owner; do not use it.
- Submit from `~/SuisseCL/my_data`: `sbatch --job-name=<name> hpc/train.sbatch <sac_central|sac_decentral|marlisa> --episodes 30 --reward composite --seed N`.
  Partition `epyc2`, 4 CPUs, 8 GB, 12 h, `--nodes=1` is mandatory (cluster rejects `--mem` without it). QoS is free ("job_gratis").
- Results land in `~/SuisseCL/my_data/results/` (`rl_<run>.csv` at the end, `curve_<run>.csv` rewritten every episode).
- Sync workflow (single author, no commits from the cluster): `rsync` finished files to the laptop, commit locally, push, then on
  the cluster delete those same files and `git pull`. Do not commit partial curves of jobs that are still running.
- Jobs still running when this was written: `sac_decentral_s0`, plus seed-2 jobs `sac_central_s2`, `sac_decentral_s2`,
  `marlisa_s2` (started late; per-building ones may take ~3 h). Collect with the sync workflow above, then re-run
  `cl/bin/python my_data/aggregate.py`.

## 7. Open decisions and recommended next steps
> **2026-11-18:** the items below are Phase A history. The current plan is `docs/phases/phase_b_plan.md` (D-031, D-032); read it first. No cluster jobs until Phase B is finished.

1. **Fix the comfort term / reward before any weight sweep.** Make `reward_diagnostics.py` pass: comfort(cooling-to-setpoint)
   must be clearly lower than comfort(cooling off). Then pick the scale from a sensible reference (not a heavy-tailed one) or use a
   bounded penalty, and treat comfort as a near-constraint. This must be redone for heating anyway (Swiss).
2. After that, sweep the comfort weight (e.g. 1, 3, 10) for central SAC and the tuned-rule search; plot cost vs comfort vs peaks.
3. Swiss phase 1: heating-dominated setup on Quebec/Vermont as stand-ins, Swiss-like high/low tariff and low-carbon series as
   placeholders; decide central vs per-building agents for 20-47 buildings. Real Swiss data comes from the research track.
4. Optional: run `--preset challenge` for central SAC; behaviour-cloning warm start only if a strong teacher rule exists.

## 8. Working agreements
- Ask the owner before: submitting cluster jobs, committing/pushing, downloading data, cancelling jobs.
- Never put the owner's email in commits beyond the existing repo-level git config; do not commit from the cluster.
- Do not invent dataset names, URLs or numbers; mark claims verified / reported / unverified.
