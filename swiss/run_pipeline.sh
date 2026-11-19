#!/usr/bin/env bash
# Rebuild all derived Phase A data from data/raw (see docs/reproduction.md). Run from the repository root.
set -euo pipefail
PY=cl/bin/python
$PY -I swiss/pipeline/profile_candidates.py all          # TR-001/002  -> data/interim/*_candidates.csv, ekz_*.csv
$PY -I swiss/pipeline/select_buildings.py                # TR-003      -> data/interim/selected_buildings.csv
$PY -I swiss/pipeline/build_buildings_hourly.py          # TR-004/006  -> data/canonical/{quarter_hourly,hourly}
$PY -I swiss/pipeline/build_weather.py                   # TR-005
$PY -I swiss/pipeline/build_tariff.py                    # TR-007
$PY -I swiss/pipeline/build_tariff_scenarios.py >/dev/null      # TR-014 -> DER-017
$PY -I swiss/pipeline/build_thermal_demand.py            # TR-008      -> data/canonical/thermal
$PY -I swiss/pipeline/build_pv.py                       # TR-012      -> data/canonical/pv
$PY -I swiss/pipeline/build_carbon.py 2023               # TR-010      -> data/canonical/carbon_ch_2023_hourly.csv
$PY - <<'PYEOF'
import pandas as pd
c = pd.read_csv('data/canonical/carbon_ch_2023_hourly.csv')
c[['carbon_intensity_kg_per_kwh']].rename(columns={'carbon_intensity_kg_per_kwh': 'carbon_intensity'}).to_csv('data/canonical/carbon_intensity_citylearn_2023.csv', index=False)
PYEOF
$PY -I swiss/citylearn_build/build_dataset.py --carbon-file data/canonical/carbon_intensity_citylearn_2023.csv >/dev/null   # DER-010
$PY -I swiss/citylearn_build/build_dataset.py --carbon-file data/canonical/carbon_intensity_citylearn_2023.csv --pv-ratio 1.0 --out-name swiss_pv_2023 >/dev/null   # DER-013
$PY -I swiss/citylearn_build/build_dataset.py --carbon-file data/canonical/carbon_intensity_citylearn_2023.csv --pv-ratio 1.0 --battery-kwh-per-kwp 1.0 --out-name swiss_pvbat_2023 >/dev/null   # DER-014
$PY -I swiss/pipeline/fit_rc_params.py >/dev/null                       # DER-015 (diagnostics)
$PY -I swiss/pipeline/build_rc_params.py >/dev/null                     # DER-015
$PY -I swiss/citylearn_build/build_dataset.py --carbon-file data/canonical/carbon_intensity_citylearn_2023.csv --pv-ratio 1.0 --battery-kwh-per-kwp 1.0 --rc --out-name swiss_rc_2023 >/dev/null   # DER-016
$PY -I swiss/pipeline/build_dayahead.py >/dev/null                         # DER-018 (needs data/raw/energy_charts/dayahead_ch_2023.json)
# Phase C (D-049, D-050): climate scenarios and cooled cell datasets. data/raw/ch2025_klo/ is a manual download (SRC-014, docs/reproduction.md section 2); the cells are git-ignored
if [ -d data/raw/ch2025_klo ]; then
  $PY -I swiss/pipeline/build_climate.py >/dev/null                         # TR-018, TR-019: DER-023 to DER-026 (data/canonical/climate/, in the manifest)
  $PY -I swiss/pipeline/build_climate_datasets.py --all >/dev/null          # TR-020: DER-027, 6 weather scenarios x 5 adoption levels (30 cells, the matrix runs 26) -> swiss/datasets/climate/ (about 25 minutes, not in git)
else
  echo "skipping the Phase C climate steps: data/raw/ch2025_klo is missing (SRC-014)"
fi
$PY -I swiss/pipeline/build_15min.py >/dev/null                           # B2: data/canonical/q15 (not in the manifest, not in git)
for spec in "swiss_district_2023_q15" "swiss_pv_2023_q15 --pv-ratio 1.0" "swiss_pvbat_2023_q15 --pv-ratio 1.0 --battery-kwh-per-kwp 1.0" "swiss_rc_2023_q15 --pv-ratio 1.0 --battery-kwh-per-kwp 1.0 --rc"; do
  set -- $spec; name=$1; shift
  $PY -I swiss/citylearn_build/build_dataset.py --carbon-file data/canonical/q15/carbon_intensity_citylearn_2023_15min.csv --q15 "$@" --out-name $name >/dev/null   # DER-019 to DER-022
done
(cd data/canonical && find . -type f ! -name MANIFEST.sha256 ! -path './q15/*' | sort | xargs shasum -a 256 > MANIFEST.sha256)
echo "pipeline done"
