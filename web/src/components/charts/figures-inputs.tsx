"use client";
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { useBundle, useBundleFile } from "@/lib/bundle";
import type { Json, SeriesInputs } from "@/lib/types";
import { Chart } from "./echarts";
import { FLAG_COLOURS, NEUTRAL, ROLE_COL, WD, buildingGroupLabel, fmt, idxWhere, pairs, roleTip, timestamps, useBuildingLabel } from "./util";

const Loading = () => <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Loading…</div>;
const AX = { axisLabel: { fontSize: 10 }, nameTextStyle: { fontSize: 10 } };
const GRID = { left: 52, right: 14, top: 26, bottom: 62 };
const ZOOM = [{ type: "inside" as const }, { type: "slider" as const, height: 16, bottom: 6 }];
const LEG = { bottom: 26, textStyle: { fontSize: 10 }, itemHeight: 8 };

export const useSi = () => useBundleFile<SeriesInputs>("series_inputs").data;
type Q = Record<string, Json>;
export function useQc(id: string): Q | null {
  const { nodes } = useBundle();
  return (nodes[id]?.results as Q | undefined) ?? null;
}
const obj = (v: Json | undefined) => v as Q;
const arrn = (v: Json | undefined) => v as number[];

/** One or more series on a shared time axis. */
export function LineTime({ keys, unit, colours, step }: { keys: string[]; unit: string; colours?: string[]; step?: boolean }) {
  const si = useSi();
  const { colours: cls } = useBundle();
  if (!si) return <Loading />;
  const ts = timestamps(si);
  const option: EChartsOption = {
    grid: GRID, tooltip: { trigger: "axis" }, legend: LEG, dataZoom: ZOOM,
    xAxis: { type: "time", ...AX }, yAxis: { type: "value", name: unit, ...AX, scale: true },
    series: keys.map((k, j) => ({ type: "line", name: si.series[k].label, showSymbol: false, sampling: "lttb", step: step ? "end" : false, lineStyle: { width: 1 }, itemStyle: { color: colours?.[j] ?? cls[si.series[k].classification] ?? NEUTRAL[j] }, data: pairs(ts, si.series[k].values) })),
  };
  return <Chart option={option} height={300} />;
}

export function GhiVsDiffuse() {
  const si = useSi();
  if (!si) return <Loading />;
  const g = si.series.ghi.values, d = si.series.diffuse.values, neg = idxWhere(si.flags.beam_negative.values);
  const option: EChartsOption = {
    grid: { left: 52, right: 14, top: 20, bottom: 56 }, tooltip: { trigger: "item" }, legend: LEG,
    xAxis: { type: "value", name: "global W/m²", ...AX }, yAxis: { type: "value", name: "diffuse W/m²", ...AX },
    series: [
      { type: "scatter", name: "hours", symbolSize: 3, large: true, itemStyle: { color: "#2b6cb0", opacity: 0.35 }, data: g.map((x, i) => [x, d[i]]) },
      { type: "line", name: "diffuse = global", showSymbol: false, lineStyle: { type: "dashed", color: "#a0aec0" }, data: [[0, 0], [1150, 1150]] },
      { type: "scatter", name: `beam < 0 (${neg.length} h)`, symbol: "diamond", symbolSize: 11, itemStyle: { color: FLAG_COLOURS.beam_negative }, data: neg.map((i) => [g[i], d[i]]) },
    ],
  };
  return <Chart option={option} height={320} />;
}

export function KloVsHeapo() {
  const fig = useBundleFile<{ klo_vs_heapo_8jb: { rows: { shift_h: number; max_abs_diff_c: number; share_identical: number; n: number }[]; note: string } }>("figures").data;
  if (!fig) return <Loading />;
  const K = fig.klo_vs_heapo_8jb;
  return (
    <div className="space-y-1">
      <table className="w-full text-xs">
        <thead><tr className="text-left"><th>KLO hour t compared with HEAPO 8jB row</th><th>max |ΔT| (°C)</th><th>share identical</th><th>hours</th></tr></thead>
        <tbody>
          {K.rows.map((r) => <tr key={r.shift_h} className="border-t"><td>t {r.shift_h === 0 ? "" : r.shift_h < 0 ? `+ ${-r.shift_h} h` : `− ${r.shift_h} h`}</td><td className="tabular-nums">{r.max_abs_diff_c.toFixed(2)}</td><td className="tabular-nums">{(100 * r.share_identical).toFixed(1)} %</td><td className="tabular-nums">{r.n}</td></tr>)}
        </tbody>
      </table>
      <p className="text-xs text-muted-foreground">{K.note}</p>
    </div>
  );
}

export function PriceHeatmap() {
  const si = useSi();
  const z = useMemo(() => {
    if (!si) return [];
    const sum = Array.from({ length: 24 }, () => new Array(7).fill(0)), cnt = Array.from({ length: 24 }, () => new Array(7).fill(0));
    si.series.price.values.forEach((p, i) => { if (p != null) { sum[si.local_hour[i]][si.weekday[i]] += p; cnt[si.local_hour[i]][si.weekday[i]]++; } });
    return sum.flatMap((r, h) => r.map((v, d) => [d, h, cnt[h][d] ? +(v / cnt[h][d]).toFixed(2) : null]));
  }, [si]);
  if (!si) return <Loading />;
  const option: EChartsOption = {
    grid: { left: 50, right: 70, top: 14, bottom: 30 }, tooltip: { formatter: (p: unknown) => { const v = (p as { value: number[] }).value; return `${WD[v[0]]} ${v[1]}:00 local: ${v[2]} Rp/kWh`; } },
    xAxis: { type: "category", data: WD, ...AX }, yAxis: { type: "category", data: Array.from({ length: 24 }, (_, h) => String(h)), inverse: true, name: "local hour", ...AX },
    visualMap: { min: 15, max: 19.5, calculable: false, right: 0, top: "middle", inRange: { color: ["#ebf8ff", "#2b6cb0"] }, text: ["Rp/kWh", ""], textStyle: { fontSize: 10 } },
    series: [{ type: "heatmap", data: z, label: { show: true, fontSize: 9 } }],
  };
  return <Chart option={option} height={420} />;
}

export function CarbonConsDom() {
  const si = useSi();
  const { colours } = useBundle();
  if (!si) return <Loading />;
  const ts = timestamps(si), S = si.series, F = si.flags;
  const fb = idxWhere(F.neighbour_intensity_fallback_flag.values), ip = idxWhere(F.gap_interpolated_flag.values);
  const option: EChartsOption = {
    grid: GRID, tooltip: { trigger: "axis" }, legend: LEG, dataZoom: ZOOM,
    xAxis: { type: "time", ...AX }, yAxis: { type: "value", name: "gCO2eq/kWh", ...AX },
    series: [
      { type: "line", name: S.carbon.label, showSymbol: false, sampling: "lttb", lineStyle: { width: 1 }, itemStyle: { color: colours.modeled }, data: pairs(ts, S.carbon.values) },
      { type: "line", name: S.carbon_domestic.label, showSymbol: false, sampling: "lttb", lineStyle: { width: 1, type: "dotted" }, itemStyle: { color: "#4a5568" }, data: pairs(ts, S.carbon_domestic.values) },
      { type: "scatter", name: `neighbour fallback (${fb.length} h)`, symbol: "diamond", symbolSize: 6, itemStyle: { color: FLAG_COLOURS.neighbour_intensity_fallback_flag }, data: fb.map((i) => [ts[i], S.carbon.values[i]]) },
      { type: "scatter", name: `missing / interpolated (${ip.length} h, drawn on domestic line)`, symbol: "diamond", symbolSize: 9, itemStyle: { color: FLAG_COLOURS.gap_interpolated_flag }, data: ip.map((i) => [ts[i], S.carbon_domestic.values[i]]) },
    ],
  };
  return <Chart option={option} height={320} />;
}

type CarbonDaily = { days: string[]; mwh: Record<string, (number | null)[]>; mean_ci_consumption: (number | null)[] };
export function CarbonImportStack() {
  const d = useBundleFile<{ carbon_daily: CarbonDaily }>("figures").data?.carbon_daily;
  if (!d) return <Loading />;
  const cols: [string, string, string][] = [["domestic_generation_excl_pumped_mwh", "domestic generation (excl. pumped storage)", "#718096"], ["import_france_mwh", "import France", "#2b6cb0"], ["import_germany_mwh", "import Germany", "#c53030"], ["import_austria_mwh", "import Austria", "#dd6b20"], ["import_italy_mwh", "import Italy", "#2f855a"]];
  const option: EChartsOption = {
    grid: { left: 56, right: 48, top: 26, bottom: 62 }, tooltip: { trigger: "axis" }, legend: LEG, dataZoom: ZOOM,
    xAxis: { type: "category", data: d.days, ...AX, boundaryGap: false },
    yAxis: [{ type: "value", name: "MWh/day", ...AX }, { type: "value", name: "g/kWh", ...AX, splitLine: { show: false } }],
    series: [
      ...cols.map(([k, n, c]) => ({ type: "line" as const, name: n, stack: "s", areaStyle: { opacity: 0.8 }, showSymbol: false, lineStyle: { width: 0.5, color: c }, itemStyle: { color: c }, data: d.mwh[k] })),
      { type: "line" as const, name: "daily mean carbon intensity (g/kWh, right axis)", yAxisIndex: 1, showSymbol: false, lineStyle: { width: 1.5, color: "#b7791f" }, itemStyle: { color: "#b7791f" }, data: d.mean_ci_consumption },
    ],
  };
  return <Chart option={option} height={360} />;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function EpflMonthly() {
  const R = useQc("QC:carbon_epfl_comparison");
  const { colours } = useBundle();
  if (!R) return <Loading />;
  const lab = (y: number) => [`Dec ${y - 1} (1 h)`, ...MONTHS.map((m) => `${m} ${y}`)];
  const series: EChartsOption["series"] = [];
  for (const [y, type] of [["2016", "solid"], ["2017", "dotted"]] as const) {
    const m = obj(obj(R[y]).monthly_means);
    series.push({ type: "line", name: `this model ${y}`, lineStyle: { type }, itemStyle: { color: colours.modeled }, data: arrn(m.mine).map((v, i) => [lab(+y)[i], v]) });
    series.push({ type: "line", name: `EPFL ${y}`, lineStyle: { type }, itemStyle: { color: "#2d3748" }, data: arrn(m.epfl).map((v, i) => [lab(+y)[i], v]) });
  }
  const option: EChartsOption = { grid: { left: 50, right: 14, top: 20, bottom: 90 }, tooltip: { trigger: "axis" }, legend: LEG, xAxis: { type: "category", axisLabel: { fontSize: 8, rotate: 45 } }, yAxis: { type: "value", name: "gCO2eq/kWh", ...AX }, series };
  return (
    <div>
      <Chart option={option} height={330} />
      <p className="text-xs text-muted-foreground">The first bucket of each year holds only the 23:00 UTC hour of 31 December of the previous year (UTC monthly resampling of a CET year in compare_epfl_carbon.py).</p>
    </div>
  );
}

export function EpflDiurnal() {
  const R = useQc("QC:carbon_epfl_comparison");
  const { colours } = useBundle();
  if (!R) return <Loading />;
  const series: EChartsOption["series"] = [];
  for (const [y, type] of [["2016", "solid"], ["2017", "dotted"]] as const) {
    const m = obj(obj(R[y]).diurnal_means);
    series.push({ type: "line", name: `this model ${y}`, lineStyle: { type }, showSymbol: false, itemStyle: { color: colours.modeled }, data: arrn(m.mine) });
    series.push({ type: "line", name: `EPFL ${y}`, lineStyle: { type }, showSymbol: false, itemStyle: { color: "#2d3748" }, data: arrn(m.epfl) });
  }
  const option: EChartsOption = { grid: { left: 50, right: 14, top: 20, bottom: 56 }, tooltip: { trigger: "axis" }, legend: LEG, xAxis: { type: "category", data: Array.from({ length: 24 }, (_, h) => String(h)), name: "hour of day (Europe/Zurich local)", nameLocation: "middle", nameGap: 24, ...AX }, yAxis: { type: "value", name: "gCO2eq/kWh", ...AX }, series };
  return <Chart option={option} height={290} />;
}

export function EpflTable() {
  const R = useQc("QC:carbon_epfl_comparison");
  if (!R) return <Loading />;
  const ys = Object.keys(R).filter((k) => R[k] && typeof R[k] === "object" && "hourly_consumption_vs_epfl" in obj(R[k]));
  const h = (y: string) => obj(obj(R[y]).hourly_consumption_vs_epfl), dm = (y: string) => obj(obj(R[y]).hourly_domestic_vs_epfl), cv = (y: string) => obj(obj(R[y]).coefficient_of_variation);
  const n = (v: Json | undefined, d: number) => fmt(v as number, d);
  const rows: [string, (y: string) => string][] = [
    ["hourly Pearson r", (y) => n(h(y).pearson, 3)], ["hourly Spearman r", (y) => n(h(y).spearman, 3)],
    ["monthly-mean r", (y) => n(obj(R[y]).monthly_corr, 3)], ["diurnal-profile r", (y) => n(obj(R[y]).diurnal_corr, 3)],
    ["mean, this model (g/kWh)", (y) => n(h(y).mean_mine, 1)], ["mean, EPFL (g/kWh)", (y) => n(h(y).mean_epfl, 1)],
    ["ratio of means", (y) => n(h(y).ratio_mean, 3)], ["regression slope (model per EPFL)", (y) => n(h(y).slope_mine_per_epfl, 3)],
    ["domestic-only vs EPFL, hourly r", (y) => n(dm(y).pearson, 3)], ["coefficient of variation model / EPFL", (y) => `${n(cv(y).mine, 2)} / ${n(cv(y).epfl, 2)}`],
    ["missing hours (model) / neighbour-fallback hours", (y) => `${obj(R[y]).missing_mine_hours} / ${obj(R[y]).neighbour_fallback_hours}`],
  ];
  return (
    <table className="w-full text-xs">
      <thead><tr className="text-left"><th>statistic</th>{ys.map((y) => <th key={y}>{y}</th>)}</tr></thead>
      <tbody>{rows.map(([l, g]) => <tr key={l} className="border-t"><td>{l}</td>{ys.map((y) => <td key={y} className="tabular-nums">{g(y)}</td>)}</tr>)}</tbody>
    </table>
  );
}

export function BuildingDaily() {
  const si = useSi();
  const label = useBuildingLabel();
  if (!si) return <Loading />;
  const roles = Object.keys(si.buildings), days = Math.floor(si.n / 24);
  const ts = timestamps(si), dayLab = Array.from({ length: days }, (_, d) => new Date(ts[d * 24]).toISOString().slice(0, 10));
  const rowH = 128, grids: EChartsOption["grid"] = [], xs: EChartsOption["xAxis"] = [], ys: EChartsOption["yAxis"] = [], series: EChartsOption["series"] = [], titles: EChartsOption["title"] = [];
  roles.forEach((role, r) => {
    const b = si.buildings[role], top = 10 + r * (rowH + 22);
    (grids as object[]).push({ left: 52, right: 14, top, height: rowH });
    (xs as object[]).push({ type: "category", gridIndex: r, data: dayLab, axisLabel: { show: r === roles.length - 1, fontSize: 9 }, axisTick: { show: false } });
    (ys as object[]).push({ type: "value", gridIndex: r, name: "kWh/d", ...AX });
    (titles as object[]).push({ text: label(role), left: 56, top: top - 4, textStyle: { fontSize: 11 } });
    const gap = new Set(idxWhere(b.gap_filled_flag).map((i) => dayLab[Math.floor(i / 24)]));
    b.components.forEach((c, k) => {
      const y = Array.from({ length: days }, (_, d) => { let s = 0; for (let h = 0; h < 24; h++) { const v = c.values[d * 24 + h]; if (v == null) return null; s += v; } return +s.toFixed(2); });
      series.push({ type: "bar", name: c.label, stack: role, xAxisIndex: r, yAxisIndex: r, itemStyle: { color: c.classification === "synthetic" ? "#e03131" : k === 0 ? "#2b6cb0" : "#90cdf4" }, data: y,
        ...(k === 0 && gap.size ? { markLine: { silent: true, symbol: "none", label: { formatter: "gap-filled day (synthetic)", fontSize: 9, color: "#c53030" }, lineStyle: { color: "#c53030", type: "dashed" }, data: [...gap].map((g) => ({ xAxis: g })) } } : {}) });
    });
  });
  const option: EChartsOption = { title: titles, grid: grids, xAxis: xs, yAxis: ys, series, tooltip: { trigger: "axis" }, dataZoom: [{ type: "inside", xAxisIndex: roles.map((_, i) => i) }] };
  return <Chart option={option} height={roles.length * (rowH + 22) + 24} />;
}

type Sel = { sfh: { kwh_hp_2023: number[]; ids: number[] }; mfh: { kwh_per_unit_2023: number[]; units: number[]; ids: number[] }; picks: { role: string; id: number; units: number }[]; pool_sizes: { sfh: number; mfh: number } };
export function SelectionPools() {
  const s = useBundleFile<{ building_selection: Sel }>("figures").data?.building_selection;
  const { story } = useBundle();
  const label = useBuildingLabel();
  if (!s) return <Loading />;
  const sfhG = buildingGroupLabel(story, "SFH"), mfhG = buildingGroupLabel(story, "MFH");
  const sp = s.picks.filter((p) => p.role.startsWith("SFH")).map((p) => ({ p, v: s.sfh.kwh_hp_2023[s.sfh.ids.indexOf(p.id)] }));
  const mp = s.picks.filter((p) => p.role.startsWith("MFH")).map((p) => ({ p, v: s.mfh.kwh_per_unit_2023[s.mfh.ids.indexOf(p.id)] }));
  const band = (u: number) => (u < 7 ? "4–6 units" : u <= 14 ? "7–14 units" : u >= 24 ? "≥24 units" : "15–23 (no stratum)");
  const option: EChartsOption = {
    grid: [{ left: 150, right: 20, top: 16, height: 70 }, { left: 150, right: 20, top: 130, height: 150 }], tooltip: { trigger: "item", formatter: (p: unknown) => { const q = p as { marker?: string; seriesName: string; value: (number | string)[] }; return `${q.marker ?? ""} ${q.seriesName}: <b>${q.value[0]}</b>${q.value[2] ? `<div style="opacity:.65;font-size:11px">${roleTip(String(q.value[2]))}</div>` : ""}`; } }, legend: { bottom: 0, textStyle: { fontSize: 10 } },
    xAxis: [{ type: "value", gridIndex: 0, name: "HP electricity 2023 (kWh)", nameLocation: "middle", nameGap: 24, ...AX }, { type: "value", gridIndex: 1, name: "HP electricity 2023 per housing unit (kWh)", nameLocation: "middle", nameGap: 24, ...AX }],
    yAxis: [{ type: "category", gridIndex: 0, data: [`${sfhG} (pool)`], ...AX }, { type: "category", gridIndex: 1, data: ["4–6 units", "7–14 units", "15–23 (no stratum)", "≥24 units"], ...AX }],
    series: [
      { type: "scatter", name: `HEAPO pool of ${sfhG.toLowerCase()} (${s.pool_sizes.sfh})`, xAxisIndex: 0, yAxisIndex: 0, symbolSize: 8, itemStyle: { color: "#a0aec0" }, data: s.sfh.kwh_hp_2023.map((v) => [v, `${sfhG} (pool)`]) },
      { type: "scatter", name: `Selected ${sfhG.toLowerCase()}`, xAxisIndex: 0, yAxisIndex: 0, symbol: "diamond", symbolSize: 14, itemStyle: { color: "#2b6cb0" }, label: { show: true, formatter: (p: unknown) => label((p as { value: [number, string, string] }).value[2]), fontSize: 10 }, data: sp.map((q, k) => ({ value: [q.v, `${sfhG} (pool)`, q.p.role], label: { position: k % 2 ? "bottom" : "top" } })) },
      { type: "scatter", name: `EKZ pool of ${mfhG.toLowerCase()} (${s.pool_sizes.mfh})`, xAxisIndex: 1, yAxisIndex: 1, symbolSize: 8, itemStyle: { color: "#a0aec0" }, data: s.mfh.kwh_per_unit_2023.map((v, i) => [v, band(s.mfh.units[i])]) },
      { type: "scatter", name: `Selected ${mfhG.toLowerCase()}`, xAxisIndex: 1, yAxisIndex: 1, symbol: "diamond", symbolSize: 14, itemStyle: { color: "#2f855a" }, label: { show: true, formatter: (p: unknown) => label((p as { value: [number, string, string] }).value[2]), fontSize: 10 }, data: mp.map((q, k) => ({ value: [q.v, band(q.p.units), q.p.role], label: { position: k % 2 ? "bottom" : "top" } })) },
    ],
  };
  return <Chart option={option} height={340} />;
}

export function Backtest() {
  const R = useQc("QC:backtest_gap_fill");
  if (!R) return <Loading />;
  const keys = Object.keys(R), lab = keys.map((k) => k.replace("|", " · ").replace("kwh_", ""));
  const v = (k: string, f: string) => (obj(R[k])[f] as number);
  const option: EChartsOption = {
    grid: [{ left: 52, right: 14, top: 22, height: 140 }, { left: 52, right: 14, top: 230, height: 130 }], tooltip: { trigger: "axis" }, legend: { bottom: 0, textStyle: { fontSize: 10 } },
    xAxis: [{ type: "category", gridIndex: 0, data: lab, axisLabel: { show: false } }, { type: "category", gridIndex: 1, data: lab, axisLabel: { fontSize: 9, rotate: 40 } }],
    yAxis: [{ type: "value", gridIndex: 0, name: "hourly MAE (kWh)", ...AX }, { type: "value", gridIndex: 1, name: "daily MAPE (fraction)", ...AX }],
    series: [
      { type: "bar", name: "A: neighbouring days (used, D-011)", xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: "#2b6cb0" }, data: keys.map((k) => v(k, "hourly_MAE_kWh_A_neighbour_days")) },
      { type: "bar", name: "B: same weekday ±7 d", xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: "#a0aec0" }, data: keys.map((k) => v(k, "hourly_MAE_kWh_B_same_weekday")) },
      { type: "bar", name: "daily MAPE A", xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: "#2f855a" }, data: keys.map((k) => v(k, "daily_MAPE_A")) },
      { type: "bar", name: "daily MAPE B", xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: "#c6f6d5" }, data: keys.map((k) => v(k, "daily_MAPE_B")) },
    ],
  };
  return (
    <div>
      <Chart option={option} height={440} />
      <p className="text-xs text-muted-foreground">n days: {keys.map((k) => `${k} = ${v(k, "n_days")}`).join("; ")}. MAPE values are fractions as stored in the JSON.</p>
    </div>
  );
}

export { ROLE_COL };
