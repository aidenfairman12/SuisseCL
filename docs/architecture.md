# Architecture (Phase A, as built — v1.0, 2026-11-17)

Layer → location
1. Source data → `data/raw/` (gitignored; registry rows SRC-001..011, hashes recorded)
2. Processing → `swiss/pipeline/*.py` (TR-001..010, scripted; `swiss/run_pipeline.sh`)
3. Canonical datasets → `data/canonical/` (15-min extracts, hourly series, thermal, weather, tariff, carbon; `MANIFEST.sha256`) and `data/interim/` (candidate summaries)
4. Building/energy models → `swiss/models/heat_pump.py` (M-001), `swiss/pipeline/build_carbon.py` (M-002)
5. CityLearn integration → `swiss/citylearn_build/build_dataset.py` → `swiss/datasets/swiss_district_2023/` (stock CityLearn 3.3.0 classes only: `Building`, `HeatPump`, `StorageTank`; CityLearn itself is unmodified)
6. Experiment layer → `swiss/experiments/` (reward R-001, baseline controllers ALG-001..004, sensitivity runs; results in `swiss/experiments/results/`)
7. Audit and reporting → `docs/` (registries, logs, QC and validation reports, completion report); checks in `swiss/validation/` and `swiss/tests/` (56 tests)

Design notes: original-resolution data preserved (15-min extracts, Phase B-ready); hourly datasets are derived outputs; UTC index with derived local fields (D-007); every variable carries a classification (`data/canonical/hourly/columns.json`, registry rows). Extensions beyond stock CityLearn: none (a custom COP device was considered and declined, D-016).
