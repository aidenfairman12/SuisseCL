# SuisseCL

A Swiss residential district energy simulation built on [CityLearn](https://github.com/citylearn-project/CityLearn) 3.3.0, with a public dashboard
(https://suisse-cl.vercel.app/). The aim is a research-quality, auditable simulation of a Swiss district (heat pumps, thermal storage, Swiss tariff and weather)
and an environment for evaluating and training district energy controllers.

**Status.** Phase A (hourly heating baseline, six representative buildings, four stock controllers, validation) is implemented and approved (2026-11-18, D-031). Phase B (PV, batteries, export prices, thermal model, richer tariff scenarios, 15-minute resolution, EVs) is authorised and follows `docs/phases/phase_b_plan.md`; Phase C (future climate, cooling) has not started.
Everything is documented for audit: sources and licences, transformations, assumptions, decisions, open issues and validation limits (`docs/`).
The six buildings are a **constructed composite** of representative models from two datasets (three HEAPO houses, three ETH/EKZ apartment-building heat-pump
meters); they are not neighbours. Thermal storage is synthetic and heat timing is unvalidated.

## Layout
| Path | What |
|---|---|
| `swiss/` | Swiss simulation: `pipeline/` (raw data to canonical datasets), `models/` (heat pump), `citylearn_build/` (CityLearn dataset), `experiments/` (controllers, reward, results), `validation/`, `contract/` (data contract v1), `dashboard/` (audit-bundle builder), `tests/` |
| `data/` | `raw/` (gitignored, licensed), `interim/`, `canonical/` (hourly and 15-minute series, `MANIFEST.sha256`) |
| `docs/` | Master plan, execution log, decision/assumption/issue logs, registries, QC and validation reports, Phase A completion report, dashboard docs |
| `web/` | Next.js dashboard (static export); reads `web/public/bundle/*.json` (audit bundle) and `web/public/bundle/sim/` (data contract v1) |
| `my_data/` | Earlier US cooling-control experiments on CityLearn challenge datasets (legacy; see the end of this file) |
| `CityLearn/`, `cl/` | Local CityLearn clone and virtualenv (both gitignored) |

## Setup
```bash
python3.11 -m venv cl && source cl/bin/activate
pip install -r swiss/requirements-lock.txt      # CityLearn 3.3.0, torch 2.2.2, numpy 1.26.4, pandas 2.3.3, ...
```
Raw data are not in git; sources, licences and download steps are in `docs/reproduction.md` and `docs/data/data_source_registry.csv`.

## Common commands (from the repository root)
```bash
PYTHONPATH=. cl/bin/python -m pytest swiss/tests -q                      # full test suite (about 3 minutes, includes real rollouts)
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py        # baseline controllers, full year
cl/bin/python -I swiss/contract/export_v1.py                            # data contract v1 sample for the dashboard (about 5 minutes)
cl/bin/python -I swiss/contract/export_v1.py --full --out web/public/bundle/sim_full   # full-year contract bundle (about 57 MB, about 5 minutes)
cl/bin/python -I swiss/validation/mechanism_check.py                    # mechanism-check report from the exported comparisons
PYTHONPATH=. cl/bin/python -I swiss/dashboard/build_bundle.py           # audit bundle (build on a clean committed tree)
PYTHONPATH=. cl/bin/python -I swiss/dashboard/lint.py --check-fresh     # dashboard guards: provenance, roles, carbon wording, freshness
cd web && npm ci && npm run dev                                         # dashboard on http://localhost:3000
```

## Where to read first
- `docs/phases/phase_b_plan.md`: **authoritative Phase B specification** (start here if you are implementing).
- `docs/phases/phase_a_completion_report.md`: what was built, acceptance criteria, limitations.
- `docs/experiments/validation_reports/mechanism_check_phase_a.md`: what the controller results do and do not show.
- `docs/dashboard/data_contract_v1.md`: the simulation-to-dashboard data contract (draft v1).
- `docs/architecture.md`, `docs/reproduction.md`, `docs/decisions/decision_log.md`, `docs/decisions/issues_and_risks.md`.
- `docs/HANDOFF.md`: environment pins, CityLearn 3.3.0 traps and working agreements (ask the owner before committing, pushing or downloading).

---

# Legacy: US cooling experiments (`my_data/`)
Reinforcement-learning experiments for district cooling control on CityLearn challenge datasets; kept for reference. The Swiss work above does not depend on it.

## Layout
- `my_data/run.py` – baseline controllers (do nothing, hour rule, RBCs) on full CityLearn datasets
- `my_data/rl.py` – train SAC / MARLISA on the first part of a dataset, score on held-out later weeks
- `my_data/rewards.py` – composite reward (comfort, cost, carbon, peak, ramping; normalised, weights swappable)
- `my_data/make_report.py` + `metrics_template.html` – builds `metrics_overview.html`, a guide to all 21 KPIs
- `my_data/hpc/` – UBELIX (Slurm) setup and job script
- `my_data/results/` – district KPI tables (CSV)

## Setup
CityLearn is not vendored here. Clone it next to this repo at the tested commit (the datasets live in its `data/` folder; the pip package does not ship them):

```bash
git clone https://github.com/citylearn-project/CityLearn.git
git -C CityLearn checkout 0eb78bc   # CityLearn 3.3.0
python3.11 -m venv cl && source cl/bin/activate
pip install -r my_data/hpc/requirements.txt   # citylearn 3.3.0, torch 2.2.2, numpy<2, pandas<3
```

`numpy<2` and `pandas<3` are required: the 2023 datasets use a PyTorch LSTM thermal model that fails under NumPy 2 with torch 2.2.2.

## Running
```bash
python my_data/run.py [dataset ...]                    # baselines, default 2023 phase_3_1..3
python my_data/rl.py baselines                         # baselines on the held-out window
python my_data/rl.py scales                            # once: reward normalisation scales -> results/reward_scales.json
python my_data/rl.py sac_central --episodes 30 --reward composite --seed 0   # also: sac_decentral, marlisa
#   --weights comfort=1,cost=1,carbon=1,peak=1,ramp=1   (defaults shown)
CITYLEARN_DATA=/path/to/datasets python my_data/rl.py ...   # override dataset location
```
On UBELIX: run `my_data/hpc/setup_env.sh` once, then `cd my_data && sbatch hpc/train.sbatch <agent> --reward composite --seed 0`.

## Protocol
Dataset `citylearn_challenge_2023_phase_3_1` (6 buildings). Train on steps 0-1535, evaluate on steps 1536-2207 (28 unseen days). All scores are CityLearn KPIs
normalised to CityLearn's conventional counterfactual (same buildings without storage and partial-load control, PV kept; lower is better).

## Status (as of the last legacy run)
- **Reward calibration issue.** With equal weights the composite reward barely distinguishes "cooling off" from "cooling to setpoint" on its comfort term
  (per-step comfort term 570 vs 494) while peak/ramp terms react strongly, so agents are paid for trading comfort away. A tuned parametric rule
  (`my_data/tuned_rule.py`, searched on this reward) converged to "cooling essentially off" (held-out discomfort 0.967), i.e. no better than do-nothing.
  Comfort weighting/scaling needs rework.
- Central SAC, composite reward, 2 seeds (held-out 28 days): cost 0.545 +/- 0.006, daily peak 0.603, discomfort 0.706 +/- 0.010 (do-nothing: 0.350 / 0.565 / 0.977).
  The earlier comfort-only SAC reached discomfort 0.17 at cost 0.775.
- Per-building SAC and MARLISA (seeds 0-2) were still running on UBELIX; results were to be added when they finished.
- Datasets 2023 phase_3_1/3_2/3_3 hold identical building/weather/price data; they are one benchmark, not three.
- This track led to the Swiss work above (heating-dominated setup; Quebec/Vermont datasets in CityLearn were considered as stand-ins).
  Research prompt for Swiss data sources: `docs/swiss_data_research_prompt.md`.
