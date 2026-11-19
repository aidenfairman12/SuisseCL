#!/bin/bash
# Submit the Phase B RL grid (D-041/D-044): scenarios s1 (+PV), s2 (+battery), s3 (+RC thermal model with comfort), reward "bill", held-out weeks protocol, 3 seeds.
# Run from the deployed directory on UBELIX (~/SuisseCL_phaseB, see docs/phases/phase_b_rl_deployment.md). Prints "name jobid" per job.
# The free QoS caps the sum of (CPUs x requested minutes) of running jobs (MaxCpuRunMinsPerUser): short requests let more jobs run at once. Measured speed: central SAC
# about 25 steps/s (150,000 steps in under 2 h), per-building SAC and MARLISA about 5 times slower, hence the walltimes and training caps below (training stops at the cap and is then evaluated).
set -euo pipefail
mkdir -p logs
sub() { local name=$1 time=$2; shift 2; echo "$name $(sbatch --parsable --job-name="$name" --time="$time" swiss/hpc/train.sbatch "$@")"; }
for s in 0 1 2; do for sc in s1 s2 s3; do
  sub "pb_${sc}_sacc_s$s" 03:30:00 sac_central --scenario $sc --reward bill --seed "$s" --train-steps 150000 --max-hours 3
done; done
for s in 0 1 2; do for sc in s1 s2 s3; do
  sub "pb_${sc}_sacd_s$s" 06:30:00 sac_decentral --scenario $sc --reward bill --seed "$s" --train-steps 100000 --max-hours 6
  sub "pb_${sc}_marl_s$s" 06:30:00 marlisa --scenario $sc --reward bill --seed "$s" --train-steps 100000 --max-hours 6
done; done
