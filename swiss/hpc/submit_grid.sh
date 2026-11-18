#!/bin/bash
# Submit the first Swiss RL grid (3 seeds). Run from ~/SuisseCL on UBELIX after `git pull`.
#   CENTRAL_REWARDS="r001"        (default)  or  CENTRAL_REWARDS="r001 cost"   to also run the cost-dominant reward on central SAC
# Per-building SAC and MARLISA always use r001 (they are about 5x slower per step). Prints one job id per line.
set -euo pipefail
mkdir -p logs
CENTRAL_REWARDS=${CENTRAL_REWARDS:-r001}
sub() { local name=$1; shift; echo "$name $(sbatch --parsable --job-name="$name" swiss/hpc/train.sbatch "$@")"; }
for s in 0 1 2; do
  for r in $CENTRAL_REWARDS; do sub "sac_c_${r}_s$s" sac_central --reward "$r" --seed "$s" --train-steps 150000; done
  sub "sac_d_r001_s$s" sac_decentral --reward r001 --seed "$s" --train-steps 100000
  sub "marlisa_r001_s$s" marlisa --reward r001 --seed "$s" --train-steps 100000
done
