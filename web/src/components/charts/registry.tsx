"use client";
// Figure registry: names match the `figures` lists in swiss/dashboard/ui_map.yaml (lint checks this).
// The same components are used on the pages and inside audit cards.
import type { ComponentType } from "react";
import { Backtest, BuildingDaily, CarbonConsDom, EpflDiurnal, EpflMonthly, EpflTable, GhiVsDiffuse, KloVsHeapo, LineTime, PriceHeatmap, SelectionPools } from "./figures-inputs";
import { ActionMap, CopCurves, EnvInterface, HpSizing, HpSplitMonthly, RewardYear, SensitivityBars, SpfCheck, TankSizes } from "./figures-model";
import { CarbonImportStack } from "./figures-inputs";

type Fig = { title: string; source: string; Component: ComponentType };

export const FIGURES: Record<string, Fig> = {
  ts_temp: { title: "Hourly outdoor temperature 2023", source: "data/canonical/weather_klo_2023_hourly.csv: temp_c", Component: () => <LineTime keys={["temp_c"]} unit="°C" /> },
  ts_irradiance: { title: "Hourly irradiance 2023 (beam = global − diffuse)", source: "data/canonical/weather_klo_2023_hourly.csv: ghi_wm2, diffuse_wm2, beam_horizontal_wm2", Component: () => <LineTime keys={["ghi", "diffuse", "beam"]} unit="W/m²" colours={["#2b6cb0", "#90cdf4", "#2f855a"]} /> },
  ghi_vs_diffuse: { title: "Diffuse vs global irradiance (each point = one hour)", source: "data/canonical/weather_klo_2023_hourly.csv", Component: GhiVsDiffuse },
  klo_vs_heapo: { title: "KLO temperature vs HEAPO station 8jB (timestamp check, D-009)", source: "data/canonical/weather_klo_2023_hourly.csv, weather_heapo_2023_hourly.csv", Component: KloVsHeapo },
  price_heatmap: { title: "Mean price by local hour and weekday (two tiers)", source: "data/canonical/tariff_ekz_standard_2023_hourly.csv: total_rp_kwh; local time Europe/Zurich", Component: PriceHeatmap },
  carbon_cons_vs_dom: { title: "Consumption-based vs domestic-generation carbon intensity, with flagged hours", source: "data/canonical/carbon_ch_2023_hourly.csv", Component: CarbonConsDom },
  carbon_import_stack: { title: "Daily Swiss generation and imports by neighbour (MWh), with daily mean carbon intensity", source: "data/canonical/carbon_ch_2023_hourly.csv", Component: CarbonImportStack },
  epfl_monthly: { title: "Method check: monthly mean intensity, this model vs EPFL (2016, 2017)", source: "docs/data/data_quality_reports/carbon_epfl_comparison.json", Component: EpflMonthly },
  epfl_diurnal: { title: "Method check: mean by hour of day, this model vs EPFL", source: "docs/data/data_quality_reports/carbon_epfl_comparison.json", Component: EpflDiurnal },
  epfl_table: { title: "Method check: agreement statistics", source: "docs/data/data_quality_reports/carbon_epfl_comparison.json", Component: EpflTable },
  building_daily: { title: "Daily electricity per building, stacked by component (gap-filled day marked)", source: "data/canonical/hourly/<role>_2023_hourly.csv (daily sum only where all 24 hours exist)", Component: BuildingDaily },
  selection_pools: { title: "Candidate pools and the six picks (nearest to stratum median)", source: "data/interim/heapo_candidates.csv, ekz_meters.csv, selected_buildings.csv", Component: SelectionPools },
  backtest: { title: "Gap-fill backtest: method A (mean of neighbouring days, used) vs B (same weekday ±7 days)", source: "docs/data/data_quality_reports/backtest_gap_fill.json", Component: Backtest },
  cop_curves: { title: "COP vs outdoor temperature per building (M-001, calibrated η and supply temperature)", source: "swiss/models/heat_pump.py::cop evaluated at build time with data/canonical/thermal/thermal_params.json", Component: CopCurves },
  spf_check: { title: "Annual SPF: literature target vs implied by the derived heat", source: "docs/data/data_quality_reports/qc_thermal_2023.json", Component: SpfCheck },
  hp_split_monthly: { title: "Monthly HP electricity split: warm-day baseline (→ DHW demand, A-005) vs space heating", source: "data/canonical/thermal/<role>_2023_thermal_hourly.csv (local months)", Component: HpSplitMonthly },
  hp_sizing: { title: "Heat-pump nominal power vs peak electricity of the mode (TR-009 rule: 1.1 × peak)", source: "swiss/datasets/swiss_district_2023/schema.json, data/canonical/thermal/<role>_2023_thermal_hourly.csv", Component: HpSizing },
  tank_sizes: { title: "Tank capacities (kWh_th) in the main dataset and the sensitivity variants", source: "swiss/datasets/<variant>/build_manifest.json and schema.json", Component: TankSizes },
  env_interface: { title: "CityLearn interface configured in schema.json", source: "swiss/datasets/swiss_district_2023/schema.json", Component: EnvInterface },
  reward_year: { title: "R-001 contributions per day for the selected controller (from the run trace)", source: "swiss/experiments/results/traces/<controller>.csv.gz", Component: RewardYear },
  action_map: { title: "ALG-004 action map by local hour (from run_baselines.py::tariff_map)", source: "swiss/experiments/run_baselines.py::tariff_map (evaluated at build time)", Component: ActionMap },
  sensitivity_bars: { title: "Change against the uncontrolled run of each variant", source: "swiss/experiments/results/sensitivity_2023.csv", Component: SensitivityBars },
};

export function FigureView({ name, bare }: { name: string; bare?: boolean }) {
  const f = FIGURES[name];
  if (!f) return <p className="text-xs text-destructive">unknown figure {name}</p>;
  const C = f.Component;
  return (
    <figure className="space-y-1">
      {!bare && <figcaption className="text-sm font-medium">{f.title}</figcaption>}
      <C />
      <p className="text-[11px] text-muted-foreground">Source: {f.source}</p>
    </figure>
  );
}
