#!/bin/bash
# Usage: sbatch hpc/train.sbatch <sac_central|sac_decentral|marlisa> [episodes] [reward]
# Run from the project directory on the cluster (contains rl.py, run.py, datasets/).
#SBATCH --job-name=cl-rl
#SBATCH --output=logs/%x-%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --partition=epyc2

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p logs results
module load Python/3.11.3-GCCcore-12.3.0
source "$HOME/venvs/cl/bin/activate"
export CITYLEARN_DATA="$PWD/datasets"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
python rl.py "$@"
