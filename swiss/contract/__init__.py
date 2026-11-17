"""Data contract v1 between the simulation and the dashboard (docs/dashboard/data_contract_v1.md).

recorder.py   one real CityLearn rollout -> full-year per-step arrays (read-only observation; the rollout is unchanged)
variables.py  data dictionary: unit, quantity, carrier, provenance and sources of every exported variable
export_v1.py  writes web/public/bundle/sim/ (manifest, buildings, components, conditions, runs/, comparisons)
validate.py   minimal JSON-Schema validator for schema/*.schema.json (no extra dependency)
"""
CONTRACT_VERSION = '1.0.0-draft'
