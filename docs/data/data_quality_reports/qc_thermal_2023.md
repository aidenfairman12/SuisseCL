# Thermal demand derivation — checks and results (A5, TR-008, 2023)

Source numbers: `qc_thermal_2023.json`. All heat values are **Derived** (electricity × modeled COP).

| Building | HP electricity kWh | Heating demand kWh_th | DHW/baseline kWh_th | η_sh / η_dhw | Baseline share of HP elec | Heat per m² (SFH) |
|---|---|---|---|---|---|---|
| SFH-low | 4,730 | 17,255 | 187 | 0.369 / 0.373 | 1.4 % | 78 (total 79) |
| SFH-mid | 6,054 | 20,621 | 1,346 | 0.370 / 0.382 | 7.9 % | 124 (total 132) |
| SFH-high | 11,523 | 30,913 | 8,871 | 0.349 / 0.388 | 27.5 % | 119 (total 153) |
| MFH-small | 12,715 | 31,837 | 7,581 | 0.374 / 0.373 | 21.3 % | – |
| MFH-medium | 25,716 | 62,302 | 17,418 | 0.360 / 0.356 | 24.2 % | – |
| MFH-large | 21,103 | 48,445 | 16,974 | 0.365 / 0.369 | 28.7 % | – |

## What passed
- Calibration reproduces the SPF targets (SFH SH 3.7, MFH combined 3.1, DHW-mode 2.8) to 1e-3; no NaN, no negative values; the electricity split conserves energy (tests).
- Calibrated Carnot fractions η = 0.35–0.39 fall inside the 0.32–0.44 range reported (snippet, **primary paper not yet read**) for Austrian air-source field data. Weak plausibility support only.
- Heat per m² for the three SFH (79–153 kWh/m²a incl. hot water) is within the broad range expected for Swiss houses (reference values not yet sourced, so **plausibility only, not validation**).
- Implementation test: our COP function equals `citylearn.energy_model.HeatPump.get_cop` for the same η and T_sup (this is a code-consistency test and is true by construction, not evidence for the model).

## What did NOT support the model (important)
- Planned check #1 (D-003/design §5): derived daily heat should be *more* linear in heating degree-days than raw electricity. Result on cold days (T<12 °C, 196 days): R² of derived heat vs HDD is **lower** than R² of electricity vs HDD for all six buildings (SFH 0.67/0.83/0.54 vs 0.85/0.92/0.80; MFH 0.38/0.20/0.41 vs 0.64/0.48/0.66).
- Measured electricity is almost exactly linear in HDD (curvature ≈ 0), whereas the Carnot-form COP makes derived heat concave (curvature −0.2 to −0.4). Raising the effective supply temperature (45–80 °C) flattens but does not remove it, and would need η > 0.6 (physically implausible).
- Interpretation (not established): the real COP varies less over this range than the Carnot form with a fixed supply temperature implies (heating-curve supply temperature, capacity limits, solar/internal gains and thermal mass also matter). **The temperature dependence of the derived heat is therefore uncertain; the annual level (via SPF) is better anchored than its timing.**
- Sensitivity of annual totals to SPF ±: SPF≈3.0 on SFH basis gives −19 % total heat; 4.0 gives +8 % (e.g. SFH-mid 17.8/22.0/23.7 MWh).

## Limitations carried forward
SFH-high summer HP use (10 kWh/day) is unexplained (ISS-027); SFH-low may include EV charging in non-shiftable load (ISS-026); MFH supply temperature is an assumption (A-003); no measured thermal output or indoor temperature exists, so no thermal validation is possible in Phase A.

## Addendum (2026-11-16, after attempting the custom-COP calibration) — the linearity diagnostic is NOT a valid test
- I tried to calibrate a linear COP slope (custom device) on the same diagnostic. Profiling daily R² against the slope showed the criterion keeps improving for **negative** slopes (COP rising as it gets colder, e.g. SFH-low R² 0.85 at slope 0 → 0.88 at −0.04 K⁻¹; MFH-medium 0.41 → 0.51). That is physically implausible, so the criterion (derived heat ∝ daily HDD) is biased by effects it ignores (solar and internal gains, thermal mass, capacity limits, defrost, DHW/standby mixed into electricity, daily-mean vs hourly temperature). It therefore **cannot be used either to reject the Carnot form or to calibrate a COP slope**. The earlier "did not support the model" statement above should be read as "this diagnostic is uninformative", not as evidence against the Carnot form.
- Independent evidence from the primary paper already used for the SPF (Arpagaus et al. 2023, section 3.3, Fig. 4): the Carnot efficiency of variable-speed air-source heat pumps was "about 40 % over the entire temperature range" (30–50 % band). That is exactly the form CityLearn's `HeatPump` uses (COP = η·T_sup/(T_sup − T_out)) with η ≈ 0.4. Our calibrated η = 0.35–0.39 is consistent with it.
- Consequence: a custom COP device is **not justified by the data**, and the stock CityLearn heat pump with these η values is literature-supported. Held-out check (fit on Jan–Mar, test on Oct–Dec) also gave no support for any slope other than the boundary value, which confirms the data cannot identify the slope.
