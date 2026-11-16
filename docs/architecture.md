# Architecture (Phase A, Task A1 findings — draft v0.1, 2026-11-16)

## 1. Verified environment
| Item | Value | Verified how |
|---|---|---|
| CityLearn | 3.3.0, clone commit `0eb78bc` ("Release CityLearn 3.3.0"); pip package in `cl/` also 3.3.0 | `citylearn.__version__`, `git log` |
| Python / OS | 3.11.5, macOS 26.5.2 x86_64 | runtime |
| torch / numpy / pandas | 2.2.2 / 1.26.4 / 2.3.3 (pinned, see HANDOFF s3) | runtime |
| Lockfile | `my_data/hpc/requirements.txt` (loose pins only). **No full lockfile yet** → to create (`pip freeze`, 31 packages). | file check |
| Git tags | `v0-cooling-baseline` | `git tag` |

Note: the pip-installed CityLearn in `cl/site-packages` is what runs; the clone is only used for its `data/` folder.

## 2. CityLearn capabilities relevant to the plan (from source/schema inspection)
- `energy_model.py`: `HeatPump` (heating & cooling, **Carnot-style COP** = (T_target+273.15)·efficiency/(T_target−T_out), capped), `ElectricHeater`, `StorageTank` (thermal storage: dhw/heating/cooling), `Battery`, `PV`.
- Heating-only buildings are supported in the shipped Quebec dataset: schema keys `heating_device`, `dhw_device`, `dynamics` (LSTM), `occupant`; no cooling device. HANDOFF noted nothing had been run on it; a smoke test was launched in this session (see log).
- Building CSV inputs are **thermal demands** (`heating_demand`, `dhw_demand`, kWh) plus `non_shiftable_load`; HP **electricity is computed by CityLearn**. Measured HP electricity (HEAPO) is therefore not a direct input.
- Weather CSV needs outdoor temperature/humidity and **direct and diffuse** irradiance (+1/2/3 h predictions); pricing and carbon CSVs are single series.
- Agents available: `BusinessAsUsualAgent`, RBC family, SAC, MARLISA (see `CityLearn/citylearn/agents`).

## 3. Proposed layered layout (extends, does not replace, existing repo)
| Plan layer | Location |
|---|---|
| 1 Source data | `data/raw/` (gitignored if licence/size demand; hashes in registry) |
| 2 Processing | `swiss/pipeline/` scripts, each logged in `docs/data/transformation_log.md` |
| 3 Canonical datasets | `data/canonical/` (15-min preserved; hourly derived) |
| 4 Building models | `swiss/models/` (COP curve, DHW split; Phase B: RC) |
| 5 CityLearn integration | `swiss/citylearn_build/` generating `schema.json` + CSVs; no edits to CityLearn |
| 6 Experiments | `swiss/experiments/` reusing `my_data/rl.py`, `rewards.py` where applicable |
| 7 Audit | `docs/` (this tree) |

Existing `my_data/` (US cooling baseline) is kept intact as a method sanity check (decision D-002).

## 4. Open design issue (ISS-004 / D-003)
CityLearn wants thermal demand and recomputes electricity via its own COP. Measured data are electricity. Any thermal series is therefore Derived/Modeled, and the pipeline needs a closed-loop check that CityLearn's simulated HP electricity reproduces measured HP electricity within stated tolerance. Not claimed as validation until done.
