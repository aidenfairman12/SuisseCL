#!/bin/bash
# One-time environment setup on UBELIX (CPU-only PyTorch; the env simulation is CPU-bound).
set -euo pipefail
module load Python/3.11.3-GCCcore-12.3.0
python -m venv "$HOME/venvs/cl"
source "$HOME/venvs/cl/bin/activate"
pip install --upgrade pip
pip install "torch==2.2.2" --index-url https://download.pytorch.org/whl/cpu
pip install "numpy<2" "pandas<3" "citylearn==3.3.0"
python -c "import citylearn, torch, numpy, pandas; print('ok', citylearn.__version__, torch.__version__, numpy.__version__, pandas.__version__)"
