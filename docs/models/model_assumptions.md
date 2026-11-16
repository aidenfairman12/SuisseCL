# Model assumptions (summary; authoritative lists: decisions/assumptions_log.md, decision_log.md, parameter_registry.csv)

## M-001 heat-pump COP and thermal-demand derivation
- COP = η·(T_sup + 273.15)/(T_sup − T_out), capped at 20 (CityLearn's own form). η is calibrated per building so the annual SPF equals a literature value: SFH 3.7 (space heating, new building), MFH 3.1 (combined, 45 °C supply), DHW mode 2.8 (Arpagaus et al. 2023, Table 1). Calibration fixes the *level* of heat, not its timing.
- Supply temperatures: SFH 35 °C (floor heating, survey), MFH 45 °C (assumption), DHW 55 °C.
- Non-space-heating baseline of HP electricity (warm-day mean) is treated as DHW-like load; for SFH-mid and SFH-high the electric water heater stays in non-shiftable load (D-014a).
- No defrost, part-load or capacity-limit model. Thermal timing is **not validated** (the HDD-linearity diagnostic was found uninformative); no measured thermal output or indoor temperature exists.
## M-002 carbon intensity
Average (not marginal) consumption-based lifecycle intensity; IPCC AR5 medians plus proxies; first-order tracing; Energy-Charts data possibly missing small generation; hours with data gaps are interpolated or use neighbour annual means (flagged).
## Dataset-level assumptions (CityLearn)
Synthetic thermal tanks (D-017a); constant 21 °C indoor placeholder (no comfort modelling); no PV, battery, EV or cooling; weather forecasts not used; price forecasts exact.
