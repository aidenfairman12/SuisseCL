# SuisseCL

Reinforcement-learning experiments for district energy control with
[CityLearn](https://github.com/citylearn-project/CityLearn), working toward
Swiss building data (heat pumps, Swiss tariffs and climate).

## Layout
- `my_data/run.py` – baseline controllers (do nothing, hour rule, RBCs) on full CityLearn datasets
- `my_data/rl.py` – train SAC / MARLISA on the first part of a dataset, score on held-out later weeks
- `my_data/rewards.py` – composite reward (comfort, cost, carbon, peak, ramping; normalised, weights swappable)
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
python my_data/rl.py scales                            # once: reward normalisation scales -> results/reward_scales.json
python my_data/rl.py sac_central --episodes 30 --reward composite --seed 0   # also: sac_decentral, marlisa
#   --weights comfort=1,cost=1,carbon=1,peak=1,ramp=1   (defaults shown)
CITYLEARN_DATA=/path/to/datasets python my_data/rl.py ...   # override dataset location
```
On UBELIX: run `my_data/hpc/setup_env.sh` once, then `cd my_data && sbatch hpc/train.sbatch <agent> --reward composite --seed 0`.

## Protocol
Dataset `citylearn_challenge_2023_phase_3_1` (6 buildings). Train on steps 0-1535,
evaluate on steps 1536-2207 (28 unseen days). All scores are CityLearn KPIs
normalised to CityLearn's conventional counterfactual (same buildings without storage and partial-load control, PV kept; lower is better).

## Status
- **Reward calibration issue.** With equal weights the composite reward barely distinguishes "cooling off" from
  "cooling to setpoint" on its comfort term (per-step comfort term 570 vs 494) while peak/ramp terms react strongly, so agents are
  paid for trading comfort away. A tuned parametric rule (`my_data/tuned_rule.py`, searched on this reward) converged to
  "cooling essentially off" (held-out discomfort 0.967), i.e. no better than do-nothing. Comfort weighting/scaling needs rework.
- Central SAC, composite reward, 2 seeds (held-out 28 days): cost 0.545 +/- 0.006, daily peak 0.603, discomfort 0.706 +/- 0.010
  (do-nothing: 0.350 / 0.565 / 0.977). The earlier comfort-only SAC reached discomfort 0.17 at cost 0.775.
- Per-building SAC and MARLISA (seeds 0-2) are still running on UBELIX; results are added when they finish.
- Datasets 2023 phase_3_1/3_2/3_3 hold identical building/weather/price data; they are one benchmark, not three.
- Next: Swiss phase 1 (heating-dominated setup; Quebec/Vermont datasets in CityLearn as stand-ins), then reward weighting
  on that setup. A research prompt for Swiss data sources is in `docs/swiss_data_research_prompt.md`.
