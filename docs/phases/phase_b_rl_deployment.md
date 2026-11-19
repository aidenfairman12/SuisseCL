# Phase B RL deployment on UBELIX (D-044)

The cluster clone `~/SuisseCL` is at commit 35c59a9, before the Swiss work, and the owner does not push (D-041). The RL jobs therefore run from a copy:

1. `swiss/hpc/deploy_phase_b.sh` (repository root, VPN on) copies swiss code, the four scenario datasets, the reward scale files and a `COMMIT` file to `~/SuisseCL_phaseB`.
2. On the cluster (bash login shell): `cd ~/SuisseCL_phaseB && bash swiss/hpc/submit_phase_b.sh` submits 27 jobs (scenarios s1, s2, s3; SAC central 150,000 steps, SAC per building and MARLISA 100,000 steps; seeds 0, 1, 2; reward `bill`; 12 h limit with an 11 h training cap). The environment is `~/venvs/cl` after `module load Python/3.11.3-GCCcore-12.3.0` (citylearn 3.3.0, torch 2.2.2+cpu, numpy 1.26.4, pandas 2.3.3, scipy 1.17.1: the pins of HANDOFF section 3, checked 2026-11-18).
3. Collect: `rsync -av ubelix:SuisseCL_phaseB/swiss/experiments/rl_results/ swiss/experiments/rl_results/`; aggregate with `swiss/experiments/rl_report.py`.
