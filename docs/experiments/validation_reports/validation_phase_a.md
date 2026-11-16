# Phase A validation report (Task A9) — v0.1, 2026-11-16

**Scope statement.** There is no measured thermal output, indoor temperature or measured carbon series for these buildings, and the multi-family non-heat-pump load and the storage tanks are synthetic. What follows is **internal-consistency and plausibility checking, not calibration or validation against observations**, except where stated. Machine-readable results: `validation_phase_a.json` (script `swiss/validation/validate_phase_a.py`, code `d3de37c` + uncommitted), `swiss/experiments/results/sensitivity_2023.csv`.

| ID | Check | Result | Status |
|---|---|---|---|
| V1 | Electricity closure in CityLearn: net = non-shiftable + heating-device + DHW-device electricity (zero action and BasicRBC, 6 buildings) | max error 1.9e-6 kWh/step | pass |
| V2 | Heat balance: demand = heat from device + heat from storage; storage balance gives non-negative losses | max error 3.3e-6 kWh/step; losses ≥ 0 | pass |
| V3 | Stability: full-year runs finish; SOC within [0,1]; net import finite and non-negative | all true | pass |
| V4 | No double counting vs measured totals (SFH, zero action): simulated net electricity equals measured Total (HP + Other) | relative difference < 1e-6 in all three | pass |
| V5 | Tariff arithmetic: annual cost of SFH-mid from 15-min data × 15-min tariff vs hourly data × hourly tariff | identical (1.8e-16 relative; 1,836.18 CHF excl. VAT) | pass (shows hourly aggregation introduces no error; tariff itself is the published price) |
| V6 | Seasonality: monthly HP electricity vs monthly mean temperature | correlation −0.79 to −0.89 (all six); peak heating month January (all six); June–August share of annual heating demand 3–8 % (SFH), 15–17 % (MFH, hot-water baseline) | pass (qualitative) |
| V7 | Timestamp alignment of demand and weather: lag (−4…+4 h) of maximum anticorrelation in Nov–Mar | best lag 0 h (SFH-low, SFH-high), +1 h (SFH-mid, MFH-small), +4 h (MFH-medium), −4 h (MFH-large) | partial: SFH consistent with an offset of 0–1 h (the HEAPO label convention remains unconfirmed, ISS-024); the two large MFH show weak weather dependence and the lag is not identifiable |
| V8 | Carbon arithmetic: independent emissions (net import × carbon series) ratio BasicRBC / zero action vs CityLearn KPI | independent 1.0267, CityLearn KPI 1.0236 (difference 0.3 %, cause not isolated: CityLearn's counterfactual baseline may differ slightly from our zero-action run; time shifts of ±1 h do not explain it) | pass within 0.3 %; not exact |
| V9 | Heat-pump operation: derived COP and heat | η = 0.35–0.39 (≈ 40 % Carnot, consistent with Arpagaus et al. 2023); SPF targets met by construction; peak hourly heat unvalidated (ISS-030) | plausibility only |

## Finding from V2 that changes how to read A8
Under BasicRBC the implied losses are 12–19 % of the heat charged into the heating tanks and up to 45 % for the SFH-high DHW tank. Those losses come from the assumed charge/discharge efficiency of 0.95 each way plus 0.3 %/h standby loss (D-017a, assumptions, not data). Real water tanks have little charging loss, so the A8 result that price-aware rules do not save money is at least partly produced by this assumption. The sensitivity runs below test this.

## Sensitivity (A9 runs; see `sensitivity_2023.csv`)
| Variant | Controller | Cost vs uncontrolled | Import vs uncontrolled | Peak vs uncontrolled | High-tariff share (points) |
|---|---|---|---|---|---|
| reference | basic_rbc | +0.50 % | +1.20 % | -6.08 % | -2.86 |
| reference | tariff_rbc_r0.10 | +0.39 % | +1.16 % | -5.19 % | -3.14 |
| tanks_x0.5 | basic_rbc | +0.22 % | +0.69 % | -3.14 % | -1.94 |
| tanks_x0.5 | tariff_rbc_r0.10 | +0.15 % | +0.68 % | -3.57 % | -2.18 |
| tanks_x2 | basic_rbc | +1.10 % | +2.09 % | -6.74 % | -4.03 |
| tanks_x2 | tariff_rbc_r0.10 | +0.93 % | +2.01 % | +1.79 % | -4.43 |
| tank_eff_0.99 | basic_rbc | +0.33 % | +1.01 % | -6.13 % | -2.81 |
| tank_eff_0.99 | tariff_rbc_r0.10 | +0.22 % | +0.97 % | -5.19 % | -3.09 |
| flat_cop_T80 | basic_rbc | +0.47 % | +1.16 % | -5.97 % | -2.85 |
| flat_cop_T80 | tariff_rbc_r0.10 | +0.36 % | +1.12 % | -5.36 % | -3.13 |

Variants: tanks x0.5 / x2 (D-017a sizes), tank charge/discharge efficiency 0.99 instead of 0.95, flat-COP (effective supply temperature 80 °C; η 0.65–0.80, not physical, sensitivity only). Reference = EXP-001..006 settings. Uncontrolled cost = 35,750 CHF excl. VAT, import 214,715 kWh, peak 72.0 kW.

**Reading.** In every variant the price-aware and clock-based rules *raise* annual cost (+0.15 % to +1.10 %) while moving 1.9–4.4 points of import out of the high-tariff hours and changing the peak by −6.7 % to +1.8 %. Larger tanks shift more load but also lose more energy, so cost rises further; smaller tanks do less of everything. Raising tank efficiency to 0.99 reduces the cost penalty (+0.39 % → +0.22 % for the tariff rule) but does not turn it into a saving, so my earlier suspicion that the 0.95 efficiency alone caused the result is only partly right: the standby loss (0.3 %/h, copied from a CityLearn reference dataset, not varied here) and the small 1.27 tariff ratio also matter. A flatter COP changes little. **Conclusion supported by these runs: with these assumptions simple rules do not reduce cost; they reduce high-tariff exposure and sometimes peak. Whether a learned controller could do better is untested.**

## Carbon result (added 2026-11-17, after the carbon series was integrated)
With the modeled carbon series (D-013a, mean 58 g/kWh, ~63 g/kWh weighted by import) the CityLearn carbon KPI of the rule-based controllers is 1.017–1.024 (i.e. 1.7–2.4 % *more* emissions than uncontrolled), from the extra storage-loss energy and because the cheap night tariff coincides with the dirtiest hours of the modeled series (about 70 g/kWh around 00:00–05:00 local against about 43 g/kWh at 18:00–19:00). **Cost and carbon objectives point in opposite directions in this setup**; this depends on the modeled series and its limits (ISS-033).

## Not covered by A9 (explicit)
SPF sensitivity propagated through the controller runs (only demand totals: SPF 3.0 → about −19 % heat, 4.0 → +8 %), loss-coefficient sensitivity, tariff sensitivity (ElCom 2026), comparison with any measured thermal data (none exists), multi-year or held-out validation (single year, 2023).

