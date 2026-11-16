# Project overview

Swiss residential district energy simulation on CityLearn 3.3.0 (plan: `master_plan.md`; progress: `execution_log.md`). Phase A (Swiss heating baseline, hourly, six buildings) is implemented and awaiting review; Phases B and C are not authorized.
The district is a **constructed composite** of three single-family houses (HEAPO) and three multi-family heat pumps (ETH/EKZ), simulation year 2023, with measured heat-pump electricity, derived thermal demand, synthetic thermal tanks, KLO weather, the EKZ standard tariff and a modeled carbon-intensity series. See `phases/phase_a_completion_report.md`.
Layout: `swiss/` (code, tests, datasets), `data/` (raw ignored, interim, canonical), `docs/` (audit trail), `my_data/` (earlier US-cooling experiments, unchanged).
