# Heating and DHW model design (Task A5) — v0.1 DRAFT, 2026-11-16 — proposed, not implemented

## 1. What CityLearn needs and what we have
CityLearn takes **thermal** `heating_demand` and `dhw_demand` (kWh) and computes heat-pump electricity itself:
`COP(t) = η · (T_sup + 273.15) / (T_sup − T_out(t))`, capped at 20 (`HeatPump.get_cop`, verified in the installed source). η and `T_sup` are per-device scalars set in the schema. We have **measured electricity** only (no thermal output, no indoor temperature). So thermal demand is **Derived/Modeled** (D-003, accepted).

## 2. Findings from the data that shape the design (exploratory, daily HP electricity vs KLO temperature, 2023)
| Building | HP kWh/day on warm days (T ≥ 16 °C) | Survey/metadata on DHW | Reading |
|---|---|---|---|
| SFH-low | 0.2 | HP produces DHW (survey) but summer draw is tiny; survey also says an EV is present | HP ≈ space heating only in practice; **non-HP load likely contains EV charging** |
| SFH-mid | 1.6 | **Electric water heater** (survey) | DHW electricity sits in `kwh_other`, not in HP |
| SFH-high | 10.3 | **Electric water heater** (survey) | summer HP use 10 kWh/day unexplained (pool? DHW boost? cooling?) |
| MFH-small / medium / large | 10.5 / 28.9 / 25.6 | not in EKZ metadata | HP clearly serves DHW (30–44 % of annual) |
Winter fit (daily HP kWh vs max(15 °C − T, 0)): R² 0.85/0.92/0.80 (SFH), 0.64/0.48/0.66 (MFH) — MFH heat pumps are less weather-driven (shared DHW, possibly multiple loads).

## 3. Proposed method (model M-001, all outputs labelled Derived/Modeled)
1. **Weather:** KLO hourly outdoor temperature (DER-007), start-of-hour convention (D-009).
2. **Supply temperature:** space heating 35 °C for floor-heating houses (HEAPO survey: all three SFH are floor heating); MFH: 45 °C (assumption, EKZ has no distribution-system info). DHW device: 55 °C. All three are assumptions → A-002..A-004.
3. **η (Carnot fraction):** one η per building, set so that the **annual** implied seasonal factor (sum heat / sum electricity) equals a Swiss field SPF of **3.5** for air-source combined operation (2023 field study of 14 air-to-water heat pumps in new single-family houses, reported 3.5; WPZ Buchs 2021 reported ~3.6), with a sensitivity band 3.0–4.0. Austrian field Carnot-fraction range for air-source space heating: 0.32–0.44 is used as a plausibility bound on η. **This is calibration to a literature value, not to building data; it sets the level of heat, not its timing.** Primary papers still to be read in full before the numbers are registered.
4. **Split of HP electricity into space heating vs DHW** (for buildings where HP serves DHW): DHW electricity per day = mean of warm-day HP use (T ≥ 16 °C), distributed with the mean warm-day diurnal HP profile; space heating = remainder (clipped ≥ 0). Then `Q_sh = E_sh · COP_sh(T_out)`, `Q_dhw = E_dhw · COP_dhw(T_out)`.
5. **Buildings whose DHW is an electric water heater (SFH-mid, SFH-high) — decision needed (section 4).**
6. **Thermal storage:** none for Phase A baseline unless the data shows a buffer (no data); CityLearn storage tanks can be added later with documented sizes. Not claimed to exist.
7. **Indoor temperature / comfort:** no measurement. CityLearn needs a setpoint and dynamics; Phase A will use a documented setpoint (e.g. 21 °C heating) and **no measured comfort validation**. Proposed to disable the LSTM dynamics (no pre-trained Swiss thermal model exists) and run heating demand as a given input — discussed in A7.

## 4. Decisions needed from the user
- **Q1 (DHW with electric water heaters).** For SFH-mid and SFH-high the water heater's electricity is inside `kwh_other`. (a) *Leave it there:* `dhw_demand = 0`, non-shiftable load includes the heater; no double counting, no DHW flexibility in these two buildings (simple, honest, limitation documented). (b) *Separate it:* model DHW demand from a standard profile scaled by residents (JASM/SIA-type) and subtract the corresponding electricity from `kwh_other` (more realistic flexibility, but subtracts a *synthetic* series from measured data; uncertain). **Recommendation: (a) for Phase A**, revisit in Phase B.
- **Q2 (SPF anchor).** Calibrate η to the Swiss field SPF 3.5 (recommended; sensitivity 3.0–4.0).
- **Q3 (EV in SFH-low).** The survey says SFH-low has an EV, so its `kwh_other` probably includes charging, which the plan wants kept separate (Phase B). Options: keep as is and flag (recommended; EV charging is just a load), or swap the building for the next candidate in the SFH-low stratum.

## 5. About the "closed-loop check" in D-003 (correction)
If heat is derived with the same COP function CityLearn uses, re-simulating gives back the measured electricity **by construction**. That test only verifies the implementation (units, caps, indexing), not the physics, and must not be reported as validation. Real checks proposed instead:
 1. Linearity: derived daily heat vs heating degree-hours should be more linear than raw electricity vs temperature (COP-falling-with-cold explains the convexity); report R² before/after.
 2. Plausibility: annual heat per m² (SFH, HEAPO living area) vs typical Swiss space-heating intensities (to be sourced).
 3. SPF sensitivity band (3.0–4.0) propagated to heat totals.
 4. Where HP-meter data exist for several buildings, compare estimated DHW share with survey flags.
The closed-loop run is kept as an implementation test (not validation).
