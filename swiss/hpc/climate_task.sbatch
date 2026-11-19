#!/bin/bash
# One task of the Phase C climate matrix (WP2b): one (cell, task) of swiss/experiments/climate_matrix.py, one CPU, one thread. NOT RUN YET: written so the matrix can be
# run on UBELIX later (see swiss/hpc/submit_climate_matrix.sh). Usage: sbatch --job-name=<name> --time=<t> swiss/hpc/climate_task.sbatch <arch: central|ru> <cell> <task: year|weeks:mpc|...>
# Needs: scikit-learn in ~/venvs/cl (the MPC forecasters use HistGradientBoostingRegressor; not checked on the cluster venv) and the cell dataset (built by the first job of the array).
#SBATCH --job-name=suissecl-climate
#SBATCH --output=logs/%x-%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=00:45:00
#SBATCH --partition=epyc2

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p logs
module load Python/3.11.3-GCCcore-12.3.0
source "$HOME/venvs/cl/bin/activate"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PYTHONPATH=. python swiss/experiments/climate_matrix.py one --arch "$1" --cell "$2" --task "$3"
