#!/bin/bash
# Submit the Phase C climate matrix (archetype B room units by default; ARCH=central for archetype A) to UBELIX as one Slurm job per (cell, task). NOT RUN: written in WP2b so the
# matrix can be moved to the cluster later. Run from the deployed directory (see swiss/hpc/deploy_climate.sh) with the VPN on:  bash swiss/hpc/submit_climate_matrix.sh [ru|central]
# Conventions as submit_phase_b.sh: short walltimes (the free QoS caps running CPU-minutes), one CPU per job, never `scancel -u`, cancel own job IDs only. Measured on a laptop with 10
# single-thread workers: one MPC task (eight weeks) about 13 minutes, the year task about 2 minutes plus rollouts, PV rule / thermostat tasks about 1 to 2 minutes.
set -euo pipefail
ARCH=${1:-ru}
mkdir -p logs
PY="PYTHONPATH=. python"
# 1. build the cell datasets on the cluster (they are git-ignored and regenerated on demand); one job, the task jobs wait for it
build=$(sbatch --parsable --job-name="cl_build_$ARCH" --time=00:40:00 --cpus-per-task=1 --mem=4G --partition=epyc2 --output=logs/%x-%j.out \
  --wrap="module load Python/3.11.3-GCCcore-12.3.0; source \$HOME/venvs/cl/bin/activate; export OMP_NUM_THREADS=1; $PY swiss/experiments/climate_matrix.py build --arch $ARCH")
echo "build $build"
# 2. the cell list of the architecture (printed by the script so that this file never drifts from climate_matrix.py)
cells=$(PYTHONPATH=. python swiss/experiments/climate_matrix.py cells --arch "$ARCH")
sub() { local name=$1 time=$2 cell=$3 task=$4; echo "$name $(sbatch --parsable --dependency=afterok:$build --job-name="$name" --time="$time" swiss/hpc/climate_task.sbatch "$ARCH" "$cell" "$task")"; }
for cell in $cells; do
  short=${cell//[^a-zA-Z0-9]/_}
  sub "cl_${short}_mpc" 00:40:00 "$cell" weeks:mpc
  sub "cl_${short}_mpcp" 00:40:00 "$cell" weeks:mpc_peak0.1
  sub "cl_${short}_year" 00:30:00 "$cell" year
  sub "cl_${short}_pvr" 00:15:00 "$cell" weeks:pv_rule
  sub "cl_${short}_thm" 00:15:00 "$cell" weeks:thermostat
done
# collect later with: rsync -a ubelix:SuisseCL_phaseC/swiss/experiments/climate_results_ru/ swiss/experiments/climate_results_ru/   then   climate_matrix.py aggregate --arch ru
