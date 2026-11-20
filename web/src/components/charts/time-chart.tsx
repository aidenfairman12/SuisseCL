"use client";
// Stacked panels on one shared time axis (zoom one, all follow), with the trust overlay: series in classification
// colours and flagged hours shaded and marked. Clicking the plot reports the hour index.
import { useCallback, useEffect, useMemo, useRef } from "react";
import type { EChartsOption } from "echarts";
import { Chart, type EChartInstance } from "./echarts";
import { FLAG_COLOURS, NEUTRAL, idxWhere, pairs, runs } from "./util";
import { PALETTE } from "@/lib/palette";

export type PSeries = { color?: string; name: string; values: (number | null)[]; cls: string; type?: "line" | "bar"; step?: boolean; stack?: string; area?: boolean; dash?: boolean };
export type PFlag = { label: string; values: number[]; colour: string; onSeries: number };
export type Panel = { title: string; unit: string; series: PSeries[]; flags?: PFlag[] };

const HOUR = 3600000;
const PANEL_H = 210, GAP = 52;

/** Sorted hour indices -> consecutive [start, end] pairs. */
function runsOf(idx: number[]): [number, number][] {
  const out: [number, number][] = [];
  for (const i of idx) { const last = out[out.length - 1]; if (last && i === last[1] + 1) last[1] = i; else out.push([i, i]); }
  return out;
}

export function flagColour(key: string) { return FLAG_COLOURS[key] ?? PALETTE.alert; }

export function TimeChart({ panels, ts, overlay, colours, onHour, highlight }: { panels: Panel[]; ts: number[]; overlay: boolean; colours: Record<string, string>; onHour?: (i: number) => void; highlight?: number[] }) {
  const cb = useRef(onHour);
  useEffect(() => { cb.current = onHour; }, [onHour]);
  const option = useMemo<EChartsOption>(() => {
    const grids: object[] = [], xs: object[] = [], ys: object[] = [], titles: object[] = [], series: object[] = [];
    panels.forEach((p, k) => {
      const top = 34 + k * (PANEL_H + GAP);
      grids.push({ left: 58, right: 18, top, height: PANEL_H });
      xs.push({ type: "time", gridIndex: k, axisLabel: { fontSize: 10 }, splitLine: { show: false } });
      ys.push({ type: "value", gridIndex: k, scale: true, axisLabel: { fontSize: 10 } });
      titles.push({ text: `${p.title} (${p.unit})`, left: 58, top: top - 26, textStyle: { fontSize: 12, fontWeight: 600 } });
      p.series.forEach((s, j) => {
        const colour = s.color ?? (overlay ? colours[s.cls] ?? NEUTRAL[j] : NEUTRAL[j % NEUTRAL.length]);
        const first = j === 0;
        const areas = first ? [
          ...(overlay ? (p.flags ?? []).flatMap((f) => runs(f.values).map(([a, b]) => [{ xAxis: ts[a], itemStyle: { color: f.colour, opacity: 0.2 } }, { xAxis: ts[b] + HOUR }])) : []),
          ...(highlight?.length ? runsOf(highlight).map(([a, b]) => [{ xAxis: ts[a], itemStyle: { color: PALETTE.highlight, opacity: 0.5 } }, { xAxis: ts[b] + HOUR }]) : []),
        ] : [];
        const hl = first && highlight?.length ? { markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: PALETTE.highlight, width: 1.5, type: "solid", opacity: 0.85 }, data: highlight.map((i) => ({ xAxis: ts[i] })) } } : {};
        const shade = areas.length ? { markArea: { silent: true, data: areas }, ...hl } : hl;
        series.push({
          type: s.type ?? "line", name: s.name, xAxisIndex: k, yAxisIndex: k, showSymbol: false, sampling: s.type === "bar" ? undefined : "lttb", step: s.step ? "end" : false,
          stack: s.stack, areaStyle: s.area ? { opacity: 0.55 } : undefined, lineStyle: { width: 1, type: s.dash ? "dotted" : "solid" }, itemStyle: { color: colour }, data: pairs(ts, s.values), ...shade,
        });
      });
      if (overlay) for (const f of p.flags ?? []) {
        const ser = p.series[f.onSeries], idx = idxWhere(f.values);
        series.push({ type: "scatter", name: `⚑ ${f.label} (${idx.length} h)`, xAxisIndex: k, yAxisIndex: k, symbol: "diamond", symbolSize: 8, itemStyle: { color: f.colour }, data: idx.map((i) => [ts[i], ser.values[i] ?? 0]) });
      }
    });
    const n = panels.length;
    return {
      title: titles, grid: grids, xAxis: xs, yAxis: ys, series: series as EChartsOption["series"], animation: false,
      tooltip: { trigger: "axis", axisPointer: { type: "cross", label: { fontSize: 10 } }, textStyle: { fontSize: 11 } },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      legend: { bottom: 28, type: "scroll", textStyle: { fontSize: 10 }, itemHeight: 8 },
      dataZoom: [{ type: "inside", xAxisIndex: Array.from({ length: n }, (_, i) => i) }, { type: "slider", xAxisIndex: Array.from({ length: n }, (_, i) => i), height: 16, bottom: 4 }],
    };
  }, [panels, ts, overlay, colours, highlight]);

  const ready = useCallback((c: EChartInstance) => {
    c.getZr().on("click", (e: { offsetX: number; offsetY: number }) => {
      const p: [number, number] = [e.offsetX, e.offsetY];
      for (let k = 0; k < panels.length; k++) {
        if (c.containPixel({ gridIndex: k }, p)) {
          const x = (c.convertFromPixel({ gridIndex: k }, p) as number[])[0];
          cb.current?.(Math.max(0, Math.min(ts.length - 1, Math.round((x - ts[0]) / HOUR))));
          return;
        }
      }
    });
  }, [panels.length, ts]);

  return <Chart option={option} height={panels.length * (PANEL_H + GAP) + 74} onReady={ready} />;
}
