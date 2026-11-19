# Reproduction instructions (Phase A and Phase B)

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
| `data/raw/energy_charts/dayahead_ch_2023.json` (Phase B) | `curl -s "https://api.energy-charts.info/price?bzn=CH&start=2022-12-31T23:00Z&end=2023-12-31T22:59Z" -o data/raw/energy_charts/dayahead_ch_2023.json` (153 KB, 1 request) | CC BY 4.0 from Bundesnetzagentur \| SMARD.de, stated in the API documentation (SRC-012) |
| `data/raw/jasm/`, `data/raw/epfl/` | downloaded but **not used** by the Phase A pipeline (see completion report) | JASM has no stated licence (private use only, D-004) |
## 3. Rebuild derived data
```bash
bash swiss/run_pipeline.sh          # ~10 min (EKZ profiling reads 7 GB)
```
Order and transformation IDs are in the script header; outputs and hashes: `data/canonical/MANIFEST.sha256`.
## 4. Tests and experiments
```bash
PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q                       # 139 tests, ~3 min (incl. real rollouts)
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py         # ~4 min  (EXP-007..012)
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_sensitivity.py       # ~8 min (needs the swiss_sens_* datasets, see below)
PYTHONPATH=. cl/bin/python -I swiss/validation/validate_phase_a.py       # ~1 min
cl/bin/python -I swiss/validation/audit_registries.py                    # registry traceability audit
cl/bin/python -I swiss/contract/export_v1.py                             # ~5 min: contract v1 sample (web/public/bundle/sim/), real rollouts
cl/bin/python -I swiss/contract/export_v1.py --full --out web/public/bundle/sim_full   # ~5 min: full-year contract bundle (about 57 MB)
cl/bin/python -I swiss/validation/mechanism_check.py                     # mechanism-check report from comparisons_year.json
PYTHONPATH=. cl/bin/python -I swiss/dashboard/build_bundle.py            # audit bundle (build on a clean committed tree)
```
Sensitivity datasets: `build_dataset.py --tank-scale 0.5|2.0 --out-name swiss_sens_tank0.5|swiss_sens_tank2`, `--tank-eff 0.99 --out-name swiss_sens_eff0.99`, and `--thermal-subdir thermal_flatcop_T80 --out-name swiss_sens_flatcop` (the flat-COP thermal folder is produced by calling `build_thermal_demand.run(write=True, out_subdir='thermal_flatcop_T80', t_sh={'SFH': 80.0, 'MFH': 80.0})`).
### 4b. Phase B (pins: `swiss/requirements-lock.txt` now includes pvlib 0.16.1 and h5py 3.16.0)
`bash swiss/run_pipeline.sh` also builds, in this order: PV series and capacities (`build_pv.py`, TR-012), scenario tariffs (`build_tariff_scenarios.py`, TR-014), RC parameters (`fit_rc_params.py`, `build_rc_params.py`), the day-ahead tariff (`build_dayahead.py`, TR-015, needs the raw file above), the 15-minute data under `data/canonical/q15/` (`build_15min.py`, TR-016; not in git and not in the manifest) and the datasets `swiss_pv_2023`, `swiss_pvbat_2023`, `swiss_rc_2023` and their `_q15` versions (`build_dataset.py --pv-ratio 1.0 --battery-kwh-per-kwp 1.0 --rc --q15`). Exact optima and scenario results (each writes a JSON in `swiss/experiments/oracle_results/` and a report in `docs/experiments/validation_reports/`):
```bash
PYTHONPATH=. cl/bin/python swiss/experiments/oracle_pvbat.py     # S1, S2 ceilings with replay (~3 min)
PYTHONPATH=. cl/bin/python swiss/experiments/oracle_rc.py        # S3 ceilings, comfort bands, H x C sweep, replay (~8 min)
PYTHONPATH=. cl/bin/python swiss/experiments/oracle_tariffs.py   # scenario tariffs incl. day-ahead on S0 to S3 (~5 min)
PYTHONPATH=. cl/bin/python swiss/experiments/oracle_q15.py       # 15-minute ceilings (~16 min)
PYTHONPATH=. cl/bin/python swiss/experiments/oracle_ev_leg.py    # EV and LEG scenarios (~5 min)
PYTHONPATH=. cl/bin/python swiss/experiments/phase_b_metrics.py  # district metrics (B9)
PYTHONPATH=. cl/bin/python swiss/validation/compare_rc_phase_a.py
PYTHONPATH=. cl/bin/python swiss/experiments/rl.py scales --scenario s1   # reward scales (also s2, s3); baselines: rl.py baselines --scenario s1 --reward bill
bash swiss/hpc/deploy_phase_b.sh; (on UBELIX) bash swiss/hpc/submit_phase_b.sh      # RL grid, see docs/phases/phase_b_rl_deployment.md
PYTHONPATH=. cl/bin/python swiss/experiments/rl_report.py        # after rsync of the results
```
Test suite at the end of Phase B: 221 tests, about 16 minutes (several run real year-long rollouts, including two at 900 s).
## 5. Randomness and determinism
No stochastic element is used in Phase A and in the exact optima (HiGHS is deterministic here: repeated solves gave identical values); the RL runs of Phase B are stochastic (seeds 0 to 2: network initialisation, exploration, training windows); no stochastic element is used in Phase A (deterministic controllers, one episode). The apartment-composite draw is seeded (`SEED=20230101 + meter id`, D-006/D-015). Seed 0 in the CityLearn schema is unused.
## 6. Known gaps in reproducibility
End-to-end reproduction from a clean checkout has not been run; the rebuild step above was re-run on the existing tree and compared with the committed manifest (result in the completion report). Raw-data downloads depend on third-party availability (Zenodo, geo.admin.ch, Energy-Charts API). The Energy-Charts API may revise historical values.
