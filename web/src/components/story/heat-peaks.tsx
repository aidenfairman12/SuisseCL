"use client";
// Peak heat demand and load-duration curves (heat_peaks.json): how much warming lowers the yearly peak compared with the yearly energy.
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { Chart } from "@/components/charts/echarts";
import { useBuildingLabel } from "@/components/charts/util";
import { Table } from "@/components/phase-b/shared";
import { useBundleFile } from "@/lib/bundle";
import { fmt, rng } from "./landing-data";

type Stat = { annual_kwh: number; peak_kw: number; full_load_hours: number; ldc: { rank_hour: number[]; kw: number[] } };
type Row = Record<"heat_el" | "heat_th", Stat>;
type Change = { annual_pct: number; peak_pct: number };
export type HeatPeaksData = {
  roles: string[]; cell_order: string[]; labels: Record<string, string>;
  cells: Record<string, Record<string, Row>>;
  changes: Record<string, Record<string, Record<"heat_el" | "heat_th", Change>>>;
  capped?: Record<string, Record<string, { rated_kw: number; hours_at_cap: number; kh_below_setpoint: number; hours_below_comfort_lower: number }>>;
};
const WARM = "gwl3.0_none", NOW = "hist_none";
const pct = (v: number, d = 1) => (Math.abs(v) < 0.5 * 10 ** -d ? `${fmt(0, d)} %` : `${v > 0 ? "+" : "−"}${fmt(Math.abs(v), d)} %`);
const COLOURS: Record<string, string> = { hist_none: "#a0aec0", "gwl2.0_none": "#ed8936", "gwl3.0_none": "#c05621" };

export function useHeatPeaks() {
  return useBundleFile<HeatPeaksData>("heat_peaks").data;
}

export function LoadDurationChart({ d, height = 320 }: { d: HeatPeaksData; height?: number }) {
  const option = useMemo<EChartsOption>(() => ({
    grid: { left: 60, right: 18, top: 28, bottom: 72 }, animation: false,
    tooltip: { trigger: "axis", valueFormatter: (v) => `${fmt(+(v as number), 1)} kW` },
    legend: { bottom: 4, textStyle: { fontSize: 13 } },
    xAxis: { type: "value", name: "hours of the year, highest hour first", nameLocation: "middle", nameGap: 30, min: 0, max: Math.max(...d.cells[NOW].district.heat_el.ldc.rank_hour), nameTextStyle: { fontSize: 12 }, axisLabel: { fontSize: 12, formatter: (v: number) => fmt(v, 0) } },
    yAxis: { type: "value", name: "district heating electricity, kW", nameTextStyle: { fontSize: 12 }, axisLabel: { fontSize: 12 } },
    series: d.cell_order.map((c) => ({
      type: "line", name: d.labels[c], showSymbol: false, lineStyle: { width: 3, color: COLOURS[c] }, itemStyle: { color: COLOURS[c] },
      data: d.cells[c].district.heat_el.ldc.rank_hour.map((h, i) => [h, d.cells[c].district.heat_el.ldc.kw[i]]),
    })) as EChartsOption["series"],
  }), [d]);
  return <Chart option={option} height={height} />;
}

/** Per building and district: annual heating electricity, highest hour and full-load hours today and at +3 °C, with the changes. */
export function HeatPeakTable({ d }: { d: HeatPeaksData }) {
  const label = useBuildingLabel();
  const rows = [...d.roles, "district"].map((r) => {
    const a = d.cells[NOW][r].heat_el, b = d.cells[WARM][r].heat_el, ch = d.changes[WARM][r].heat_el;
    return [
      <span key={r} className={r === "district" ? "font-medium" : ""}>{r === "district" ? "District (coincident)" : label(r)}{d.capped?.[r] ? " *" : ""}</span>,
      `${fmt(a.annual_kwh / 1e3, 1)} → ${fmt(b.annual_kwh / 1e3, 1)}`, pct(ch.annual_pct),
      `${fmt(a.peak_kw, 1)} → ${fmt(b.peak_kw, 1)}`, pct(ch.peak_pct),
      `${fmt(a.full_load_hours, 0)} → ${fmt(b.full_load_hours, 0)}`,
    ];
  });
  const notes = Object.entries(d.capped ?? {}).map(([r, c]) => `${label(r)}: ${d.cell_order.map((k) => c[k].hours_at_cap).join(" / ")} h`);
  const comfort = Object.values(d.capped ?? {}).every((c) => Object.values(c).every((x) => x.hours_below_comfort_lower === 0));
  return (
    <div className="space-y-1">
      <Table minWidth={680} head={["Building", "Annual MWh, 2023 → +3 °C", "Change", "Highest hour kW", "Change", "Full-load hours"]} rows={rows} />
      {notes.length > 0 && <p className="text-xs text-muted-foreground">* Capped at heat-pump capacity (hours at the cap, 2023 / +2.0 °C / +3.0 °C): {notes.join("; ")}, so these peaks cannot fall{comfort ? "; room temperature stays above the comfort limit" : ""}.</p>}
    </div>
  );
}

export function HeatPeakSummary({ d }: { d: HeatPeaksData }) {
  const dist = d.changes[WARM].district.heat_el;
  const per = d.roles.map((r) => Math.abs(d.changes[WARM][r].heat_el.peak_pct));
  return (
    <>
      The district&apos;s yearly heating electricity falls {fmt(-dist.annual_pct, 1)} % at +3 °C but its highest hour falls only {fmt(-dist.peak_pct, 1)} %, so the full-load hours drop from {fmt(d.cells[NOW].district.heat_el.full_load_hours, 0)} to {fmt(d.cells[WARM].district.heat_el.full_load_hours, 0)}.
      Per building the highest hour falls by {rng([Math.min(...per), Math.max(...per)], 1)} %; where it does not fall, the heat pump already runs at its rated power in the peak hour. Heat pumps and networks are sized for the peak, so warming helps sizing much less than it helps energy.
    </>
  );
}
