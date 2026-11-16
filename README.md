# SuisseCL

Reinforcement-learning experiments for district energy control with
[CityLearn](https://github.com/citylearn-project/CityLearn), working toward
Swiss building data (heat pumps, Swiss tariffs and climate).

## Layout
- `my_data/run.py` – baseline controllers (do nothing, hour rule, RBCs) on full CityLearn datasets
- `my_data/rl.py` – train SAC / MARLISA on the first part of a dataset, score on held-out later weeks
- `my_data/make_report.py` + `metrics_template.html` – builds `metrics_overview.html`, a guide to all 21 KPIs
- `my_data/hpc/` – UBELIX (Slurm) setup and job script
- `my_data/results/` – district KPI tables (CSV)

## Setup
CityLearn is not vendored here. Clone it next to this repo at the tested commit
(the datasets live in its `data/` folder; the pip package does not ship them):

```bash
git clone https://github.com/citylearn-project/CityLearn.git
git -C CityLearn checkout 0eb78bc   # CityLearn 3.3.0
python3.11 -m venv cl && source cl/bin/activate
pip install -r my_data/hpc/requirements.txt   # citylearn 3.3.0, torch 2.2.2, numpy<2, pandas<3
```

`numpy<2` and `pandas<3` are required: the 2023 datasets use a PyTorch LSTM
thermal model that fails under NumPy 2 with torch 2.2.2.

## Running
```bash
python my_data/run.py [dataset ...]                    # baselines, default 2023 phase_3_1..3
python my_data/rl.py baselines                         # baselines on the held-out window
python my_data/rl.py sac_central 30                    # also: sac_decentral, marlisa
CITYLEARN_DATA=/path/to/datasets python my_data/rl.py ...   # override dataset location
```
On UBELIX: run `my_data/hpc/setup_env.sh` once, then `sbatch my_data/hpc/train.sbatch <agent> 30`.

## Protocol
Dataset `citylearn_challenge_2023_phase_3_1` (6 buildings). Train on steps 0-1535,
evaluate on steps 1536-2207 (28 unseen days). All scores are CityLearn KPIs
normalised to a business-as-usual run (lower is better).

## Status
- Held-out result so far: SAC (central) cut uncomfortable hours to 0.17 (best rule: 0.70) at
  cost 0.775; the schema's default reward is comfort-only, so cost/peak gains are incidental.
- Single seed, single dataset. SAC per-building and MARLISA runs are in progress on UBELIX.
- Next: composite reward (comfort + cost + carbon + peaks), multiple seeds, then Swiss data.

Notes: phase_3_1/3_2/3_3 contain identical building/weather/price data (only `schema.json` differs).
