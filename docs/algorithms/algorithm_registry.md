# Algorithm / controller registry

All Phase A controllers are stock CityLearn 3.3.0 classes (`cl/` venv, `pip` package; clone commit 0eb78bc). No learning algorithm is used in Phase A (plan 6.2 A8: no complex custom RL unless needed to show the environment works). SAC/MARLISA code from the earlier US-cooling track (`my_data/`) is not reused here.

| ID | Name | Source / implementation | Objective | Observations used | Actions | Hyper-parameters | Training | Seeds | Limitations |
|---|---|---|---|---|---|---|---|---|---|
| ALG-001 | ZeroActionBaselineAgent | `citylearn.agents.baseline.ZeroActionBaselineAgent` | uncontrolled reference: storage never charged/discharged | none | 0 for every action | none | none | n/a (deterministic) | not a realistic operator; tanks idle |
| ALG-002 | BusinessAsUsualAgent | `citylearn.agents.baseline.BusinessAsUsualAgent` (version `immediate-full-charge-v1`) | stock BAU: EV immediate full charge, earliest appliance start, PV-oriented storage rule | storage SOC, net consumption | derived from its rules (no EV/appliance/battery here) | defaults | none | n/a | oriented to EV/battery/PV assets that this district does not have; expected (and checked) to behave like ALG-001 |
| ALG-003 | BasicRBC | `citylearn.agents.rbc.BasicRBC` | heat-pump-storage rule: charge 9.1 %/h of capacity between 22:00-08:00, discharge 8 %/h otherwise (documented in class docstring; thresholds are CityLearn's) | hour | heating_storage, dhw_storage per building | none | none | n/a | fixed clock rule, ignores tariff structure, weather and weekends |
| ALG-004 | HourRBC with tariff-aware action map | `citylearn.agents.rbc.HourRBC`, custom `action_map` from `swiss/experiments/run_baselines.py::tariff_map` | charge thermal storage at rate r in local hours with low EKZ tariff, discharge at rate r in high-tariff hours (CityLearn hours 9-20 = local 08-19), idle at hour 8 | hour | heating_storage, dhw_storage per building | r in {0.05, 0.10, 0.20} of capacity per hour | none | n/a | HourRBC keys on hour only, so weekends are (incorrectly) treated like weekdays; rates r are assumptions, not optimised |

Evaluation protocol (all): one deterministic episode, 2023 local year, 8,759 steps, central agent, schema `swiss/datasets/swiss_district_2023/schema.json`, results `swiss/experiments/results/baselines_2023.csv`.
