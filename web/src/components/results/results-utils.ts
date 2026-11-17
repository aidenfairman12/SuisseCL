import { useBundleFile } from "@/lib/bundle";
import type { Results, ResultRow, Trace } from "@/lib/types";

export const REF = "ALG-001_zero_action";
export type ResultsFull = Results & { reward_scales: Record<string, number>; sensitivity: Record<string, string | number | null>[]; experiment_rule: string; trace_checks: Record<string, Record<string, { rel_diff: number }>> };
export const useResults = () => useBundleFile<ResultsFull>("results").data;

/** Trace arrays of a controller (identical controllers share one file: `same_as`). */
export function useTrace(res: ResultsFull | null, controller: string) {
  const t = res?.traces[controller];
  const src = t ? (t.same_as ?? controller) : null;
  return useBundleFile<Trace>(src ? `trace_${src}` : null).data?.arrays ?? null;
}

export const HEADLINE = ["cost_chf_excl_vat", "district_peak_kw", "district_import_kwh", "high_tariff_import_share", "ramping_sum_kw", "reward_return"];
/** Higher is better only for the reward return; everything else is lower-is-better. */
export const lowerBetter = (col: string) => col !== "reward_return";

export function fmtKpi(v: number | string | null | undefined, col: string): string {
  if (v == null) return "n/a";
  const x = +v;
  if (col.startsWith("kpi_") || col.endsWith("_share")) return x.toFixed(4);
  return Math.abs(x) >= 1000 ? Math.round(x).toLocaleString("en-US").replace(/,/g, " ") : x.toFixed(2);
}
export function pctVs(row: ResultRow, ref: ResultRow, col: string): number | null {
  const v = row[col], v0 = ref[col];
  if (v == null || v0 == null || +v0 === 0) return null;
  return ((+v - +v0) / Math.abs(+v0)) * 100;
}

// Which hours drive a KPI (display rule only; values come from the run trace).
type Drill = { type: "max" | "daily_max" | "top" | "bottom"; of: string; label: string };
export const DRILL: Record<string, Drill> = {
  district_peak_kw: { type: "max", of: "net", label: "peak hour of district net electricity" },
  kpi_all_time_peak_average: { type: "max", of: "net", label: "peak hour of district net electricity" },
  mean_daily_peak_kw: { type: "daily_max", of: "net", label: "daily peak hours" },
  kpi_daily_peak_average: { type: "daily_max", of: "net", label: "daily peak hours" },
  cost_chf_excl_vat: { type: "top", of: "term_cost", label: "top 1 % cost hours" },
  kpi_cost_total: { type: "top", of: "term_cost", label: "top 1 % cost hours" },
  term_cost_sum: { type: "top", of: "term_cost", label: "top 1 % cost hours" },
  district_import_kwh: { type: "top", of: "import", label: "top 1 % import hours" },
  kpi_electricity_consumption_total: { type: "top", of: "import", label: "top 1 % import hours" },
  high_tariff_import_share: { type: "top", of: "import", label: "top 1 % import hours" },
  ramping_sum_kw: { type: "top", of: "term_ramp", label: "top 1 % ramps" },
  kpi_ramping_average: { type: "top", of: "term_ramp", label: "top 1 % ramps" },
  term_ramp_sum: { type: "top", of: "term_ramp", label: "top 1 % ramps" },
  term_peak_sum: { type: "top", of: "term_peak", label: "top 1 % squared-peak hours" },
  term_carbon_sum: { type: "top", of: "term_carbon", label: "top 1 % carbon-term hours" },
  kpi_carbon_emissions_total: { type: "top", of: "term_carbon", label: "top 1 % carbon-term hours" },
  reward_return: { type: "bottom", of: "reward", label: "1 % most negative reward steps" },
};

export function drillHours(T: Record<string, (number | null)[]>, col: string): number[] {
  const d = DRILL[col];
  if (!d) return [];
  const n = T.district_net_kwh.length;
  let v: (number | null)[];
  if (d.of === "net") v = T.district_net_kwh;
  else if (d.of === "import") { v = new Array(n).fill(0); for (let b = 1; b <= 6; b++) for (let i = 0; i < n; i++) v[i] = (v[i] as number) + Math.max(T[`b${b}_net_kwh`][i] ?? 0, 0); }
  else v = T[d.of];
  const x = (i: number) => v[i] ?? -Infinity;
  const idx = Array.from({ length: n }, (_, i) => i);
  if (d.type === "max") return [idx.reduce((a, b) => (x(b) > x(a) ? b : a), 0)];
  if (d.type === "daily_max") { const o: number[] = []; for (let s = 0; s < n; s += 24) { let b = s; for (let i = s; i < Math.min(s + 24, n); i++) if (x(i) > x(b)) b = i; o.push(b); } return o; }
  const k = Math.max(1, Math.round(n * 0.01));
  idx.sort((a, b) => (d.type === "bottom" ? x(a) - x(b) : x(b) - x(a)));
  return idx.slice(0, k).sort((a, b) => a - b);
}
