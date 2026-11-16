# Model registry

| ID | Name | Status | Purpose | Method | Inputs | Outputs | Parameters / sources | Validation | Limitations | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| M-001 | Heat-pump COP and thermal-demand derivation (Carnot fraction, CityLearn form) | accepted (D-014/a-e, D-016); implemented in swiss/models/heat_pump.py + build_thermal_demand.py; uses stock CityLearn HeatPump in A7 | derive heating/DHW thermal demand from measured HP electricity | COP = eta*(T_sup+273.15)/(T_sup-T_out); Q = E*COP | HP electricity (kWh), KLO T_out | heating_demand, dhw_demand (kWh, Derived) | eta from SPF 3.5 (literature, to be verified); T_sup 35/45/55 C (assumptions) | see design doc section 5 (to be done) | single supply temp; no defrost; no part-load; SPF anchor | empirical/derived |
