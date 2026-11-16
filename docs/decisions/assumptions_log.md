# Assumptions log

| ID | Date | Assumption | Basis | Status |
|---|---|---|---|---|
| A-001 | 2026-11-16 | Zurich region represented by MeteoSwiss station(s) to be chosen (candidate Zurich/Kloten per ETH/EKZ paper; HEAPO matches households to 8 stations). | Source papers (reported) | proposed |
| A-002 | 2026-11-16 | SFH space-heating supply temperature 35 C (floor heating, HEAPO survey, all three SFH). | HEAPO survey | accepted |
| A-003 | 2026-11-16 | MFH space-heating supply temperature 45 C ('renovation' class); EKZ has no distribution info. If new buildings (30-35 C) the paper's combined SPF would be 3.5. | assumption | accepted, key uncertainty |
| A-004 | 2026-11-16 | DHW supply temperature 55 C, DHW-mode SPF 2.8 for all buildings (paper Table 1). | literature | accepted |
| A-005 | 2026-11-16 | Non-space-heating baseline of HP electricity = mean warm-day (daily mean T >= 16 C) consumption with the mean warm-day diurnal shape; modeled as dhw_demand. | method choice | accepted (D-014e) |
| A-006 | 2026-11-17 | Lignite and coal-derived gas use the coal-PC lifecycle median (820): the IPCC table has no lignite entry, so Germany's intensity is probably underestimated. | proxy | accepted, sensitivity x0.5/x1.5 |
| A-007 | 2026-11-17 | Fossil oil uses the coal-PC median (820): likely an overestimate; small share. | proxy | accepted |
| A-008 | 2026-11-17 | 'Waste' and 'Others' use the biomass-dedicated median (230): Swiss 'Others' (3.5 TWh) is largely waste incineration with a partly biogenic share. | proxy | accepted, key uncertainty for domestic intensity |
| A-009 | 2026-11-17 | Solar: PV rooftop 41 g/kWh for Switzerland, PV utility 48 for neighbours. | judgement | accepted |
| A-010 | 2026-11-17 | Imports carry the average generation-mix intensity of the exporting neighbour (neighbour's own imports ignored); exports leave at the Swiss average mix; pumped-storage excluded. | method D-013 | accepted |
