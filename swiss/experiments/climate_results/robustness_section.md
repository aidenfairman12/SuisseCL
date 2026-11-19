## 5. Robustness of the MPC on the heat-wave cells (high adoption, WP4)

Eight held-out weeks (week 29 holds the p99 heat-wave week); saving against the thermostat on the same weeks; share of the held-out-week ceiling of the same cell. `scenario` = forecasters trained on the scenario year (the matrix MPC run); `trained_hist` = trained on 2023 only; T and G cases are SYNTHETIC forecast-weather errors (temperature bias in K plus 1 K noise; irradiance noise 30 %), fixed seeds; the plant always sees the true weather.

| Cell | Case | Saving | Share of ceiling | Cold K h | Degree-hours > 26 C | Cooling el. (kWh) | Highest hour kW |
|---|---|---|---|---|---|---|---|
| gwl3.0_hw99_high | scenario | 12.58 % | 75 % | 0.0 | 17228 | 621 | 155.5 |
| gwl3.0_hw99_high | trained_hist | 12.69 % | 76 % | 0.0 | 17228 | 622 | 155.6 |
| gwl3.0_hw99_high | T-2 | 11.62 % | 69 % | 0.3 | 17237 | 612 | 155.2 |
| gwl3.0_hw99_high | T-1 | 12.10 % | 72 % | 3.5 | 17231 | 618 | 155.6 |
| gwl3.0_hw99_high | T+1 | 12.38 % | 74 % | 96.5 | 17228 | 648 | 155.6 |
| gwl3.0_hw99_high | T+2 | 12.41 % | 74 % | 202.9 | 17227 | 666 | 155.8 |
| gwl3.0_hw99_high | T0n1 | 12.34 % | 74 % | 28.4 | 17229 | 627 | 155.6 |
| gwl3.0_hw99_high | G30 | 11.11 % | 66 % | 9.6 | 17228 | 618 | 155.4 |
| gwl3.0_hw99_high | T+2G30 | 11.14 % | 67 % | 202.5 | 17227 | 659 | 155.7 |
| gwl3.0_hw99_high | T-2G30 | 10.21 % | 61 % | 0.8 | 17236 | 613 | 155.1 |
| gwl3.0_hw99_high | T+2corr | 11.40 % | 68 % | 1.3 | 17231 | 647 | 155.8 |
| gwl2.0_hw99_high | scenario | 12.45 % | 77 % | 0.0 | 14404 | 482 | 155.5 |
| gwl2.0_hw99_high | trained_hist | 12.47 % | 77 % | 0.0 | 14404 | 482 | 155.7 |
| gwl2.0_hw99_high | T-2 | 11.45 % | 71 % | 0.3 | 14412 | 477 | 155.0 |
| gwl2.0_hw99_high | T-1 | 11.88 % | 73 % | 3.5 | 14407 | 484 | 155.7 |
| gwl2.0_hw99_high | T+1 | 12.30 % | 76 % | 101.0 | 14404 | 505 | 155.7 |
| gwl2.0_hw99_high | T+2 | 12.32 % | 76 % | 213.1 | 14403 | 520 | 155.7 |
| gwl2.0_hw99_high | T0n1 | 12.23 % | 75 % | 29.5 | 14405 | 488 | 155.7 |
| gwl2.0_hw99_high | G30 | 10.99 % | 68 % | 10.6 | 14405 | 483 | 155.5 |
| gwl2.0_hw99_high | T+2G30 | 10.97 % | 68 % | 213.1 | 14403 | 520 | 155.6 |
| gwl2.0_hw99_high | T-2G30 | 10.12 % | 62 % | 1.1 | 14411 | 479 | 155.0 |
| gwl2.0_hw99_high | T+2corr | 11.21 % | 69 % | 3.4 | 14407 | 507 | 155.7 |
| hist_hw99_high | scenario | 11.86 % | 77 % | 0.0 | 9866 | 315 | 155.7 |
| hist_hw99_high | trained_hist | 11.86 % | 77 % | 0.0 | 9866 | 315 | 155.7 |
| hist_hw99_high | T-2 | 10.96 % | 71 % | 0.3 | 9874 | 327 | 155.6 |
| hist_hw99_high | T-1 | 11.39 % | 74 % | 3.8 | 9869 | 322 | 155.7 |
| hist_hw99_high | T+1 | 11.76 % | 77 % | 106.0 | 9866 | 333 | 155.7 |
| hist_hw99_high | T+2 | 11.81 % | 77 % | 223.5 | 9865 | 347 | 155.8 |
| hist_hw99_high | T0n1 | 11.63 % | 76 % | 30.8 | 9867 | 326 | 155.6 |
| hist_hw99_high | G30 | 10.56 % | 69 % | 11.4 | 9867 | 314 | 155.7 |
| hist_hw99_high | T+2G30 | 10.56 % | 69 % | 227.8 | 9865 | 346 | 155.9 |
| hist_hw99_high | T-2G30 | 9.72 % | 63 % | 1.1 | 9872 | 329 | 155.6 |
| hist_hw99_high | T+2corr | 10.69 % | 70 % | 2.8 | 9870 | 337 | 155.8 |
