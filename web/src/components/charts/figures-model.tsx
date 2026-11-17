"use client";
import { useState } from "react";
import type { EChartsOption } from "echarts";
import { useBundle, useBundleFile } from "@/lib/bundle";
import type { Results, Trace } from "@/lib/types";
import { Chart } from "./echarts";
import { useQc, useSi } from "./figures-inputs";
import { ROLE_COL, axisTip, roleTip, timestamps, useBuildingLabel } from "./util";

const Loading = () => <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Loading…</div>;
const AX = { axisLabel: { fontSize: 10 }, nameTextStyle: { fontSize: 10 } };
const LEG = { bottom: 0, textStyle: { fontSize: 10 }, itemHeight: 8 };

type CopB = { eta_sh: number; T_sup_sh_c: number; eta_dhw: number; T_sup_dhw_c: number; cop_sh: number[]; cop_dhw: number[]; hours_cop_sh_capped_at_20: number };
type Figs = {
  cop_curves: { t_out_c: number[]; buildings: Record<string, CopB> };
  hp_split_monthly: { months: string[]; buildings: Record<string, { e_hp_baseline_kwh: number[]; e_hp_space_heating_kwh: number[] }> };
  hp_sizing: { rows: { building: string; role: string; peak_sh_elec_kwh: number; nominal_sh_kw: number; peak_baseline_elec_kwh: number; nominal_dhw_kw: number; peak_measured_hp_kwh: number }[] };
  tanks: { variants: Record<string, { role: string; heating_tank_kwh_th: number; dhw_tank_kwh_th: number; tank_efficiency: number; loss_coefficient: number }[]> };
  env_interface: { observations_active: string[]; observations_inactive: string[]; shared_in_central_agent: string[]; actions_active: string[]; actions_inactive: string[]; central_agent: boolean; seconds_per_time_step: number; simulation_end_time_step: number; building_classes: string[]; device_classes: string[] };
  action_maps: Record<string, { local_hour: number[]; action: number[]; rate: number }>;
};
const useFigs = () => useBundleFile<Figs>("figures").data;

export function CopCurves() {
  const c = useFigs()?.cop_curves;
  const label = useBuildingLabel();
  if (!c) return <Loading />;
  const series: EChartsOption["series"] = [];
  const sel: Record<string, boolean> = {}, tip: Record<string, string> = {};
  for (const [role, b] of Object.entries(c.buildings)) {
    const nSh = `${label(role)}, space heating`, nDhw = `${label(role)}, hot water`;
    tip[nSh] = roleTip(role, `η ${b.eta_sh.toFixed(3)}`, `${b.T_sup_sh_c} °C supply`);
    tip[nDhw] = roleTip(role, `η ${b.eta_dhw.toFixed(3)}`, `${b.T_sup_dhw_c} °C supply`);
    series.push({ type: "line", name: nSh, showSymbol: false, lineStyle: { width: 2 }, itemStyle: { color: ROLE_COL[role] }, data: c.t_out_c.map((t, i) => [t, b.cop_sh[i]]) });
    series.push({ type: "line", name: nDhw, showSymbol: false, lineStyle: { width: 1, type: "dotted" }, itemStyle: { color: ROLE_COL[role] }, data: c.t_out_c.map((t, i) => [t, b.cop_dhw[i]]) });
    sel[nDhw] = false;
  }
  const option: EChartsOption = {
    grid: { left: 46, right: 14, top: 14, bottom: 100 }, tooltip: { trigger: "axis", formatter: axisTip({ series: tip }) },
    legend: { bottom: 0, type: "scroll", textStyle: { fontSize: 9 }, selected: sel },
    xAxis: { type: "value", name: "outdoor temperature (°C), range of the 2023 KLO series", nameLocation: "middle", nameGap: 26, axisLine: { onZero: false }, ...AX }, yAxis: { type: "value", name: "COP", min: 0, max: 21, axisLine: { onZero: false }, ...AX }, series,
  };
  const cap = Object.entries(c.buildings).map(([r, b]) => `${label(r)}: ${b.hours_cop_sh_capped_at_20} h`).join(" · ");
  return (
    <div>
      <Chart option={option} height={400} />
      <p className="text-xs text-muted-foreground">Hours in 2023 where the space-heating COP hits the CityLearn cap of 20 (outdoor temperature close to supply temperature): {cap}. Click the dotted hot-water entries in the legend to show them.</p>
    </div>
  );
}

export function SpfCheck() {
  const q = useQc("QC:qc_thermal_2023");
  const label = useBuildingLabel();
  if (!q) return <Loading />;
  const roles = Object.keys(q).filter((k) => /^(SFH|MFH)-/.test(k)), g = (k: string, f: string) => (q[k] as Record<string, number>)[f];
  const option: EChartsOption = {
    grid: { left: 40, right: 14, top: 20, bottom: 50 }, tooltip: { trigger: "axis", formatter: axisTip({ head: Object.fromEntries(roles.map((r) => [label(r), r])) }) }, legend: LEG,
    xAxis: { type: "category", data: roles.map(label), axisLabel: { fontSize: 9, interval: 0, width: 80, overflow: "break" } }, yAxis: { type: "value", name: "SPF", ...AX },
    series: [
      { type: "bar", name: "target SPF (literature, D-014d)", itemStyle: { color: "#a0aec0" }, data: roles.map((r) => g(r, "spf_target")) },
      { type: "bar", name: "implied SPF space heating", itemStyle: { color: "#2b6cb0" }, data: roles.map((r) => +g(r, "implied_spf_sh").toFixed(3)) },
      { type: "bar", name: "implied SPF combined (SH + DHW)", itemStyle: { color: "#2f855a" }, data: roles.map((r) => +g(r, "implied_spf_combined").toFixed(3)) },
    ],
  };
  return <Chart option={option} height={290} />;
}

export function HpSplitMonthly() {
  const s = useFigs()?.hp_split_monthly;
  const label = useBuildingLabel();
  if (!s) return <Loading />;
  const roles = Object.keys(s.buildings), rowH = 92;
  const grids: object[] = [], xs: object[] = [], ys: object[] = [], series: EChartsOption["series"] = [], titles: object[] = [];
  roles.forEach((r, k) => {
    const top = 14 + k * (rowH + 22);
    grids.push({ left: 52, right: 14, top, height: rowH });
    xs.push({ type: "category", gridIndex: k, data: s.months, axisLabel: { show: k === roles.length - 1, fontSize: 9 } });
    ys.push({ type: "value", gridIndex: k, name: "kWh", ...AX });
    titles.push({ text: label(r), left: 56, top: top - 8, textStyle: { fontSize: 11 } });
    series.push({ type: "bar", name: "baseline (modeled as DHW demand)", stack: r, xAxisIndex: k, yAxisIndex: k, itemStyle: { color: "#dd6b20" }, data: s.buildings[r].e_hp_baseline_kwh });
    series.push({ type: "bar", name: "space heating", stack: r, xAxisIndex: k, yAxisIndex: k, itemStyle: { color: "#2b6cb0" }, data: s.buildings[r].e_hp_space_heating_kwh });
  });
  const option: EChartsOption = { title: titles, grid: grids, xAxis: xs, yAxis: ys, series, tooltip: { trigger: "axis" }, legend: { ...LEG, data: ["baseline (modeled as DHW demand)", "space heating"] } };
  return <Chart option={option} height={roles.length * (rowH + 22) + 50} />;
}

export function HpSizing() {
  const r = useFigs()?.hp_sizing.rows;
  const label = useBuildingLabel();
  if (!r) return <Loading />;
  const x = r.map((q) => label(q.role));
  const option: EChartsOption = {
    grid: { left: 46, right: 14, top: 20, bottom: 90 }, tooltip: { trigger: "axis", formatter: axisTip({ head: Object.fromEntries(r.map((q) => [label(q.role), roleTip(q.role, q.building)])) }) }, legend: { bottom: 0, type: "scroll", textStyle: { fontSize: 10 } },
    xAxis: { type: "category", data: x, axisLabel: { fontSize: 9, rotate: 20 } }, yAxis: { type: "value", name: "kW (= kWh per hour)", ...AX },
    series: [
      { type: "bar", name: "peak measured HP electricity (kWh/h)", itemStyle: { color: "#a0aec0" }, data: r.map((q) => q.peak_measured_hp_kwh) },
      { type: "bar", name: "peak space-heating part", itemStyle: { color: "#90cdf4" }, data: r.map((q) => q.peak_sh_elec_kwh) },
      { type: "bar", name: "nominal power, heating device (kW)", itemStyle: { color: "#2b6cb0" }, data: r.map((q) => q.nominal_sh_kw) },
      { type: "bar", name: "peak baseline part", itemStyle: { color: "#fbd38d" }, data: r.map((q) => q.peak_baseline_elec_kwh) },
      { type: "bar", name: "nominal power, DHW device (kW)", itemStyle: { color: "#dd6b20" }, data: r.map((q) => q.nominal_dhw_kw) },
    ],
  };
  return <Chart option={option} height={340} />;
}

export function TankSizes() {
  const V = useFigs()?.tanks.variants;
  const label = useBuildingLabel();
  if (!V) return <Loading />;
  const names = Object.keys(V), plain = V[names[0]].map((q) => label(q.role));
  const heads = Object.fromEntries(V[names[0]].map((q) => [label(q.role), q.role]));
  const heat = ["#2b6cb0", "#90cdf4", "#1a365d", "#a0aec0", "#cbd5e0"], dhw = ["#c53030", "#feb2b2", "#742a2a", "#e2a0a0", "#fed7d7"];
  const series: EChartsOption["series"] = [];
  names.forEach((v, k) => {
    series.push({ type: "bar", name: `${v}: heating tank`, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: heat[k % 5] }, data: V[v].map((q) => q.heating_tank_kwh_th) });
    series.push({ type: "bar", name: `${v}: DHW tank`, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: dhw[k % 5] }, data: V[v].map((q) => q.dhw_tank_kwh_th) });
  });
  const option: EChartsOption = {
    grid: [{ left: 52, right: 14, top: 14, height: 120 }, { left: 52, right: 14, top: 180, height: 120 }], tooltip: { trigger: "axis", formatter: axisTip({ head: heads }) }, legend: { bottom: 0, type: "scroll", textStyle: { fontSize: 9 } },
    xAxis: [{ type: "category", gridIndex: 0, data: plain, axisLabel: { show: false } }, { type: "category", gridIndex: 1, data: plain, axisLabel: { fontSize: 9, interval: 0, width: 70, overflow: "break" } }],
    yAxis: [{ type: "value", gridIndex: 0, name: "heating kWh_th", ...AX }, { type: "value", gridIndex: 1, name: "DHW kWh_th", ...AX }], series,
  };
  return (
    <div>
      <Chart option={option} height={400} />
      <p className="text-xs text-muted-foreground">{names.map((v) => `${v}: efficiency ${V[v][0].tank_efficiency}, loss ${V[v][0].loss_coefficient}/h`).join(" · ")} (schema.json of each dataset). A DHW tank of 0 means no DHW tank.</p>
    </div>
  );
}

export function EnvInterface() {
  const e = useFigs()?.env_interface;
  if (!e) return <Loading />;
  const li = (a: string[]) => a.length ? a.map((x) => <code key={x} className="mr-1.5 inline-block">{x}</code>) : "none";
  const rows: [string, React.ReactNode][] = [
    [`active observations (${e.observations_active.length})`, li(e.observations_active)], ["shared in central agent", li(e.shared_in_central_agent)], ["inactive observations", li(e.observations_inactive)],
    ["active actions", li(e.actions_active)], ["inactive actions", li(e.actions_inactive)], ["central agent", String(e.central_agent)],
    ["time step", `${e.seconds_per_time_step} s, last step index ${e.simulation_end_time_step}`], ["building class", li(e.building_classes)], ["device classes", li(e.device_classes)],
  ];
  return <table className="w-full text-xs"><tbody>{rows.map(([k, v]) => <tr key={k} className="border-t align-top"><th className="w-40 py-1 pr-2 text-left font-medium text-muted-foreground">{k}</th><td className="py-1">{v}</td></tr>)}</tbody></table>;
}

export function ActionMap() {
  const A = useFigs()?.action_maps;
  if (!A) return <Loading />;
  const col = ["#90cdf4", "#2b6cb0", "#1a365d"];
  const option: EChartsOption = {
    grid: { left: 52, right: 14, top: 20, bottom: 56 }, tooltip: { trigger: "axis" }, legend: LEG,
    xAxis: { type: "category", data: Object.values(A)[0].local_hour.map(String), name: "local hour (CityLearn hour − 1)", nameLocation: "middle", nameGap: 24, ...AX },
    yAxis: { type: "value", name: "action (+ charge, − discharge)", ...AX },
    series: Object.entries(A).map(([k, m], i) => ({ type: "bar" as const, name: `${k} (r = ${m.rate})`, itemStyle: { color: col[i % 3] }, data: m.action })),
  };
  return <Chart option={option} height={290} />;
}

const REF_CTRL = "ALG-003_basic_rbc";
export function RewardYear() {
  const { nodes } = useBundle();
  const res = useBundleFile<Results & { reward_scales: Record<string, number> }>("results").data;
  const si = useSi();
  const [ctrl, setCtrl] = useState(REF_CTRL);
  const src = res?.traces[ctrl] ? (res.traces[ctrl].same_as ?? ctrl) : null;
  const T = useBundleFile<Trace>(src ? `trace_${src}` : null).data?.arrays;
  if (!res || !si || !T) return <Loading />;
  const w: Record<string, number> = {};
  for (const t of ((nodes["R-001"]?.fields.terms as unknown as Record<string, string>[]) ?? [])) w[t.Term] = parseFloat(t["Default weight"]);
  const ts = timestamps(si), days = Math.floor(T.reward.length / 24);
  const dayLab = Array.from({ length: days }, (_, d) => new Date(ts[d * 24]).toISOString().slice(0, 10));
  const colr: Record<string, string> = { cost: "#2b6cb0", peak: "#c53030", ramp: "#dd6b20", carbon: "#b7791f" };
  const series: EChartsOption["series"] = ["cost", "peak", "ramp", "carbon"].map((k) => ({
    type: "bar" as const, name: `${k} (weight ${w[k]})`, stack: "r", itemStyle: { color: colr[k] },
    data: dayLab.map((_, d) => { let s = 0; for (let h = 0; h < 24; h++) s += -(w[k] || 0) * ((T[`term_${k}`][d * 24 + h] as number) || 0) / res.reward_scales[k]; return +s.toFixed(4); }),
  }));
  const option: EChartsOption = { grid: { left: 52, right: 14, top: 20, bottom: 70 }, tooltip: { trigger: "axis" }, legend: LEG, dataZoom: [{ type: "inside" }, { type: "slider", height: 14, bottom: 22 }], xAxis: { type: "category", data: dayLab, ...AX }, yAxis: { type: "value", name: "reward per day", ...AX }, series };
  return (
    <div className="space-y-1">
      <label className="text-xs text-muted-foreground">Controller <select value={ctrl} onChange={(e) => setCtrl(e.target.value)} className="ml-1 h-7 rounded-md border bg-background px-1.5 text-xs">{res.rows.map((r) => <option key={r.controller}>{r.controller}</option>)}</select></label>
      <Chart option={option} height={300} />
      <p className="text-xs text-muted-foreground">Weights from the R-001 table; scales from reward_scales.json.</p>
    </div>
  );
}

const SENS_COLS: [string, string][] = [["cost_vs_zero_pct", "cost (%)"], ["import_vs_zero_pct", "import (%)"], ["peak_vs_zero_pct", "peak (%)"], ["high_tariff_share_pts_vs_zero", "high-tariff share (points)"]];
export function SensitivityBars() {
  const res = useBundleFile<{ sensitivity: Record<string, string | number>[] }>("results").data;
  if (!res) return <Loading />;
  const rows = res.sensitivity.filter((r) => r.controller !== "zero_action"), ctrls = [...new Set(rows.map((r) => r.controller as string))], variants = [...new Set(res.sensitivity.map((r) => r.variant as string))];
  const grids: object[] = [], xs: object[] = [], ys: object[] = [], series: EChartsOption["series"] = [], titles: object[] = [];
  SENS_COLS.forEach(([col, lab], k) => {
    const top = 28 + Math.floor(k / 2) * 230;
    grids.push({ left: `${k % 2 ? 56 : 7}%`, width: "40%", top, height: 160 });
    xs.push({ type: "category", gridIndex: k, data: variants, axisLabel: { fontSize: 9, rotate: 25 } });
    ys.push({ type: "value", gridIndex: k, ...AX });
    titles.push({ text: `${lab} vs uncontrolled`, left: `${k % 2 ? 56 : 7}%`, top: top - 24, textStyle: { fontSize: 11 } });
    ctrls.forEach((c, j) => series.push({ type: "bar", name: c, xAxisIndex: k, yAxisIndex: k, itemStyle: { color: ["#2b6cb0", "#dd6b20", "#2f855a"][j % 3] }, data: variants.map((v) => (rows.find((r) => r.variant === v && r.controller === c) ?? {})[col] as number) }));
  });
  const option: EChartsOption = { title: titles, grid: grids, xAxis: xs, yAxis: ys, series, tooltip: { trigger: "axis" }, legend: { ...LEG, data: ctrls } };
  return <Chart option={option} height={510} />;
}
