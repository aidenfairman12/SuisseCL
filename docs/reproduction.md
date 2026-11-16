# Reproduction instructions (Phase A)

Tested environment: macOS x86_64, Python 3.11.5, `swiss/requirements-lock.txt` (CityLearn 3.3.0, torch 2.2.2, numpy 1.26.4, pandas 2.3.3, pytest 9.2.0). See also the top-level README for the CityLearn clone (`CityLearn/` at commit `0eb78bc`, used only for its datasets in the earlier US track; the Swiss pipeline runs on the pip package in `cl/`).

## 1. Environment
```bash
python3.11 -m venv cl && source cl/bin/activate
pip install -r swiss/requirements-lock.txt
```
## 2. Raw data (not in git; hashes and licences in `docs/data/data_source_registry.csv`)
Place originals under `data/raw/` (gitignored). All public, no accounts:
| Folder | Source | Notes |
|---|---|---|
| `data/raw/heapo/` | https://zenodo.org/records/15056919 (`heapo_data.zip`, 458 MB, md5 2b92b0d52487e1a733c35ee59860450d), extract into `heapo/extracted/` | CC BY 4.0 |
| `data/raw/ekz/` | https://zenodo.org/records/21398769 (`dataset.zip`, 904 MB, md5 dd40d5e24aee2a3563bc36285b463dbd), extract into `ekz/extracted/` | CC BY 4.0 |
| `data/raw/meteoswiss/` | https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/klo/ogd-smn_klo_h_historical_2020-2029.csv (+ `sma`, station/parameter metadata) | cite "Source: MeteoSwiss" |
| `data/raw/energy_charts/` | `cl/bin/python -I swiss/pipeline/download_energy_charts.py 2023` (72 requests, ~40 min, rate limited to 2/min; `all` adds 2016-17, ~2 h) | CC BY 4.0, attribution energy-charts.info |
| `data/raw/jasm/`, `data/raw/epfl/` | downloaded but **not used** by the Phase A pipeline (see completion report) | JASM has no stated licence (private use only, D-004) |
## 3. Rebuild derived data
```bash
bash swiss/run_pipeline.sh          # ~10 min (EKZ profiling reads 7 GB)
```
Order and transformation IDs are in the script header; outputs and hashes: `data/canonical/MANIFEST.sha256`.
## 4. Tests and experiments
```bash
PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q                       # 56 tests, ~1 min
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py         # ~4 min  (EXP-007..012)
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_sensitivity.py       # ~8 min (needs the swiss_sens_* datasets, see below)
PYTHONPATH=. cl/bin/python -I swiss/validation/validate_phase_a.py       # ~1 min
cl/bin/python -I swiss/validation/audit_registries.py                    # registry traceability audit
```
Sensitivity datasets: `build_dataset.py --tank-scale 0.5|2.0 --out-name swiss_sens_tank0.5|swiss_sens_tank2`, `--tank-eff 0.99 --out-name swiss_sens_eff0.99`, and `--thermal-subdir thermal_flatcop_T80 --out-name swiss_sens_flatcop` (the flat-COP thermal folder is produced by calling `build_thermal_demand.run(write=True, out_subdir='thermal_flatcop_T80', t_sh={'SFH': 80.0, 'MFH': 80.0})`).
## 5. Randomness and determinism
No stochastic element is used in Phase A (deterministic controllers, one episode). The apartment-composite draw is seeded (`SEED=20230101 + meter id`, D-006/D-015). Seed 0 in the CityLearn schema is unused.
## 6. Known gaps in reproducibility
End-to-end reproduction from a clean checkout has not been run; the rebuild step above was re-run on the existing tree and compared with the committed manifest (result in the completion report). Raw-data downloads depend on third-party availability (Zenodo, geo.admin.ch, Energy-Charts API). The Energy-Charts API may revise historical values.
