# Experiment protocol (Phase A)

1. Dataset: `swiss/datasets/swiss_district_2023` built by `swiss/citylearn_build/build_dataset.py` from `data/canonical` (hashes in `MANIFEST.sha256`).
2. Environment: CityLearn 3.3.0 (pip package in `cl/`), central agent, 8,760 hourly steps (8,759 transitions), one deterministic episode (no learning, no random split). Seed 0 is recorded but nothing stochastic is used.
3. Run: `PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py` (about 4 minutes). Writes `swiss/experiments/results/baselines_2023.csv`, `reward_scales.json`, `baselines_2023_meta.json`. Scales are recomputed from the zero-action run each time.
4. Registration: each controller run is a row in `experiment_registry.csv` (git commit, software versions, metrics, status).
5. Interpretation limits: no comfort metric (no thermal dynamics), no carbon until D-013 series exists, tanks are synthetic (D-017a), CityLearn KPIs are normalised to its own counterfactual, so also read the raw district numbers.
6. Tests: `PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q`.
