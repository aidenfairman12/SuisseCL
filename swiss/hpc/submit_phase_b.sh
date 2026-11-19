#!/bin/bash
# Submit the Phase B RL grid (D-041/D-044): scenarios s1 (+PV), s2 (+battery), s3 (+RC thermal model with comfort), reward "bill", held-out weeks protocol, 3 seeds.
# Run from the deployed directory on UBELIX (~/SuisseCL_phaseB, see docs/phases/phase_b_rl_deployment.md). Prints "name jobid" per job.
set -euo pipefail
mkdir -p logs
sub() { local name=$1; shift; echo "$name $(sbatch --parsable --job-name="$name" swiss/hpc/train.sbatch "$@")"; }
for sc in s1 s2 s3; do
  for s in 0 1 2; do
    sub "pb_${sc}_sacc_s$s" sac_central --scenario $sc --reward bill --seed "$s" --train-steps 150000
    sub "pb_${sc}_sacd_s$s" sac_decentral --scenario $sc --reward bill --seed "$s" --train-steps 100000
    sub "pb_${sc}_marl_s$s" marlisa --scenario $sc --reward bill --seed "$s" --train-steps 100000
  done
done
