# Experiment protocol (Phase A)

1. Dataset: `swiss/datasets/swiss_district_2023` built by `swiss/citylearn_build/build_dataset.py` from `data/canonical` (hashes in `MANIFEST.sha256`).
2. Environment: CityLearn 3.3.0 (pip package in `cl/`), central agent, 8,760 hourly steps (8,759 transitions), one deterministic episode (no learning, no random split). Seed 0 is recorded but nothing stochastic is used.
3. Run: `PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py` (about 4 minutes). Writes `swiss/experiments/results/baselines_2023.csv`, `reward_scales.json`, `baselines_2023_meta.json`. Scales are recomputed from the zero-action run each time.
4. Registration: each controller run is a row in `experiment_registry.csv` (git commit, software versions, metrics, status).
5. Interpretation limits: no comfort metric (no thermal dynamics), no carbon until D-013 series exists, tanks are synthetic (D-017a), CityLearn KPIs are normalised to its own counterfactual, so also read the raw district numbers.
6. Tests: `PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q`.

## RL experiments (D-023, D-030; added 2026-11-18)
7. Script: `swiss/experiments/rl.py` (kinds `sac_central`, `sac_decentral`, `marlisa`, `baselines`); cluster jobs `swiss/hpc/train.sbatch` and `swiss/hpc/submit_grid.sh` (UBELIX, epyc2, 4 CPUs, 12 h; the script stops training at 11 h and still evaluates).
8. Split: protocol `weeks` (default): 8 test weeks (blocks 3, 10, 16, 23, 29, 36, 42, 49 of 52 weekly blocks), 44 training weeks. Protocol `quarter`, folds 1 to 4: one held-out 13-week quarter, rotated for cross-validation. Training episodes are random day-aligned windows of 4 weeks that never touch a test step.
9. Evaluation: deterministic policy, each test window preceded by a 96-step warm-up from empty tanks, only the window scored; baselines are scored on the same windows. Results are district totals against "No control". Cost is reported raw and corrected for heat still stored at the window end, as a range (stored heat valued at the avoided electricity: window COP times the low, mean or high tariff).
10. Window cuts: agents bootstrap at the end of a training window (a time limit is not a real end; Pardo et al. 2017); plain SAC would store the end as terminal and learn that stored heat is worthless.
11. Ceiling: `swiss/experiments/oracle.py` computes the exact perfect-foresight cost optimum (linear program, replay-validated in CityLearn) and its dependence on tank size; every RL result is read against it (`validation_reports/oracle_cost_bound.md`).
12. Outputs per run: `swiss/experiments/rl_results/<kind>_<reward>_<protocol>_s<seed>/` with `config.json` (all settings, versions, git commit), `curve.csv` (training), `eval_curve.csv` (held-out, SAC only) and `eval_final.json`. Seeds 0 to 2. Registered in `experiment_registry.csv` after the runs finish.
13. Limits: one year of data (generalisation to other weeks of 2023, not other years), synthetic tanks (D-017a, ISS-032), no comfort term, the COP has no cycling effect (ISS-034), the bill saving available to any controller is below 0.9 % (oracle).

