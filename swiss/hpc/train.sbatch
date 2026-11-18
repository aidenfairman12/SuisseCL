#!/bin/bash
# Swiss RL job (adapted from my_data/hpc/train.sbatch). Run from the repository root on UBELIX (~/SuisseCL), after `git pull`.
# Usage: sbatch --job-name=<name> swiss/hpc/train.sbatch <sac_central|sac_decentral|marlisa> [--reward r001|cost] [--seed N] [--train-steps N]
# The partition, CPU, memory and the mandatory --nodes=1 follow docs/HANDOFF.md section 6. rl.py stops training at --max-hours (default 11)
# so that evaluation and the result files are always written inside the 12-hour limit.
#SBATCH --job-name=suissecl-rl
#SBATCH --output=logs/%x-%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --partition=epyc2

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p logs
module load Python/3.11.3-GCCcore-12.3.0
source "$HOME/venvs/cl/bin/activate"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
PYTHONPATH=. python swiss/experiments/rl.py "$@"
