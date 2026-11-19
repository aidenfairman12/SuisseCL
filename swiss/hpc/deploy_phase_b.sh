#!/bin/bash
# Copy the files an RL job needs to UBELIX without pushing (the cluster clone ~/SuisseCL predates the Swiss work). Run from the repository root with the VPN on.
# Target: ~/SuisseCL_phaseB (created). Needs: swiss code, the four scenario datasets, the reward scale files, and a COMMIT file naming the source commit.
set -euo pipefail
git rev-parse --short HEAD > COMMIT
rsync -av \
  --include='COMMIT' --include='swiss/' --include='swiss/__init__.py' \
  --include='swiss/experiments/' --include='swiss/experiments/*.py' --include='swiss/experiments/results/' --include='swiss/experiments/results/reward_scales*.json' \
  --include='swiss/models/' --include='swiss/models/*.py' --include='swiss/citylearn_build/' --include='swiss/citylearn_build/*.py' \
  --include='swiss/hpc/' --include='swiss/hpc/*' --include='swiss/datasets/' \
  --include='swiss/datasets/swiss_district_2023/***' --include='swiss/datasets/swiss_pv_2023/***' --include='swiss/datasets/swiss_pvbat_2023/***' --include='swiss/datasets/swiss_rc_2023/***' \
  --exclude='*' ./ ubelix:SuisseCL_phaseB/
