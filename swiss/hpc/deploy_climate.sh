#!/bin/bash
# Copy what the climate matrix needs to UBELIX without pushing (as deploy_phase_b.sh). NOT RUN. Target ~/SuisseCL_phaseC. Run from the repository root with the VPN on.
# Needs: swiss code, the canonical inputs of build_dataset.py (thermal, weather, tariff, PV, carbon, climate scenarios), the existing archetype A results if ARCH=ru is to be compared there.
set -euo pipefail
git rev-parse --short HEAD > COMMIT
rsync -av \
  --include='COMMIT' --include='swiss/' --include='swiss/__init__.py' --include='swiss/experiments/' --include='swiss/experiments/*.py' \
  --include='swiss/experiments/results/' --include='swiss/experiments/results/reward_scales*.json' \
  --include='swiss/models/' --include='swiss/models/*.py' --include='swiss/citylearn_build/' --include='swiss/citylearn_build/*.py' --include='swiss/pipeline/' --include='swiss/pipeline/*.py' \
  --include='swiss/hpc/' --include='swiss/hpc/*' --include='data/' --include='data/canonical/' --include='data/canonical/*.csv' --include='data/canonical/*.json' \
  --include='data/canonical/thermal/***' --include='data/canonical/pv/***' --include='data/canonical/climate/***' \
  --exclude='data/canonical/q15' --exclude='*' ./ ubelix:SuisseCL_phaseC/
