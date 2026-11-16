# Carbon method check against the EPFL 2016–2017 dataset (D-013, SRC-009) — 2026-11-17

Script `swiss/validation/compare_epfl_carbon.py`; numbers in `carbon_epfl_comparison.json`. The same code that produced the 2023 series (M-002) was run for 2016 and 2017 on Energy-Charts data and compared hour by hour with EPFL's GWP series (Vuarnoz & Aguacil Moreno 2020; attributional LCA, KBOB factors; imports from FR/AT/IT/DE assumed constant annual means). Rows are matched by position to the CET year (23:00 UTC start).

| Metric | 2016 | 2017 |
|---|---|---|
| Hourly Pearson / Spearman | 0.977 / 0.977 | 0.976 / 0.978 |
| Monthly-mean correlation (12 months) | 0.996 | 0.995 |
| Diurnal-profile correlation (24 h) | 0.996 | 0.951 |
| Mean (mine / EPFL), g CO2eq/kWh | 109.8 / 179.2 | 115.2 / 184.4 |
| Ratio of means | 0.61 | 0.63 |
| Regression slope (mine per EPFL) | 0.77 | 0.75 |
| Variability (coefficient of variation) mine / EPFL | 0.52 / 0.41 | 0.49 / 0.40 |
| Domestic-generation-only series vs EPFL, hourly r | 0.32 | 0.60 |
| Missing hours (mine) / neighbour-fallback flagged hours | 4 / 17 | 11 / 24 |

Lag scan (2016, EPFL shifted vs mine): correlation 0.977 at lag 0, 0.946/0.944 at ±1 h, 0.89 at ±2 h, so the position-based alignment is the best fit; the EPFL timestamp convention is therefore consistent with the UTC window used (hour marks).

## Interpretation
- **Pattern agreement is strong**: hour-to-hour, seasonal (winter high, summer low; January–March highest) and daily rhythm (night high, midday/evening low) match closely in both years. This supports the *timing and shape* of the 2023 series.
- **Level disagreement is large and consistent**: my series is about 60–63 % of EPFL's. EPFL's method (Swiss cradle-to-grave factors incl. transport/distribution losses, constant import mixes) differs from mine (IPCC lifecycle medians, hourly neighbour generation mixes, proxies). The level of the 2023 series should therefore be regarded as a **lower estimate** of what an EPFL-style accounting would give, not as validated.
- **The agreement is not independent evidence for the whole method**: both series are dominated by the import share (correlation of the import share with EPFL 0.84 and with mine 0.87), so a high correlation largely shows that both react to the same driver; the domestic-only series correlates poorly (0.32/0.60), i.e. the import term is what carries the signal.
- Mine has more variability (CV 0.5 vs 0.4), consistent with using hourly neighbour mixes where EPFL holds import mixes constant.
- Consistency check on levels (not verified): 2016–17 means of 110–115 g/kWh fall between my 2023 mean (58) and the reported UNIGE 2017–2024 average of ~98 (source unverified, ISS-033), which is plausible if intensity fell between 2017 and 2023, but this is not evidenced here.
- Verdict: **method check partially passed** — shape/timing yes; absolute level no (factor-set dependent). Use the series for relative (time-varying) carbon signals; do not quote its absolute value as a Swiss grid intensity.
