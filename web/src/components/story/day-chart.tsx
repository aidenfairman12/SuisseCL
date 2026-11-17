"use client";
// A cold winter weekday: grid draw of all buildings, with and without the night-charging rule, expensive tariff hours shaded.
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { Chart } from "@/components/charts/echarts";
import { useSi } from "@/components/charts/figures-inputs";
import { runs } from "@/components/charts/util";
import { useResults, useTrace } from "@/components/results/results-utils";
import { useBundle } from "@/lib/bundle";

export function DayChart() {
  const { story } = useBundle();
  const si = useSi();
  const res = useResults();
  const f = story?.story.findings;
  const T0 = useTrace(res, f?.reference.controller ?? "");
  const T1 = useTrace(res, f?.rule.controller ?? "");
  const option = useMemo<EChartsOption | null>(() => {
    if (!f || !si || !T0 || !T1) return null;
    const { index, hours } = f.day;
    const slice = (a: (number | null)[]) => a.slice(index, index + hours);
    const labels = Array.from({ length: hours }, (_, h) => `${String(h).padStart(2, "0")}:00`);
    const high = si.tier_high.slice(index, index + hours);
    const areas = runs(high).map(([a, b]) => [{ xAxis: labels[a] }, { xAxis: labels[Math.min(b + 1, hours - 1)] }]);
    return {
      grid: { left: 58, right: 18, top: 28, bottom: 72 }, animation: false,
      tooltip: { trigger: "axis", valueFormatter: (v) => `${(+(v as number)).toFixed(1)} kWh` },
      legend: { bottom: 4, textStyle: { fontSize: 13 }, itemWidth: 22 },
      xAxis: { type: "category", data: labels, boundaryGap: false, axisLabel: { fontSize: 12, interval: 2 }, name: "local hour of the day", nameLocation: "middle", nameGap: 30, nameTextStyle: { fontSize: 12 } },
      yAxis: { type: "value", name: "kWh per hour", nameTextStyle: { fontSize: 12 }, axisLabel: { fontSize: 12 } },
      series: [
        { type: "line", name: f.reference.name, step: "end", showSymbol: false, lineStyle: { width: 3, color: "#a0aec0" }, itemStyle: { color: "#a0aec0" }, data: slice(T0.district_net_kwh),
          markArea: { silent: true, itemStyle: { color: "rgba(246, 173, 85, 0.22)" }, label: { show: true, formatter: "expensive tariff", color: "#975a16", fontSize: 12, position: "insideTop" }, data: areas } },
        { type: "line", name: f.rule.name, step: "end", showSymbol: false, lineStyle: { width: 3, color: "#2b6cb0" }, itemStyle: { color: "#2b6cb0" }, data: slice(T1.district_net_kwh) },
      ] as EChartsOption["series"],
    };
  }, [f, si, T0, T1]);
  if (!option) return <div className="flex h-72 items-center justify-center rounded-xl border bg-muted/20 text-sm text-muted-foreground">Loading the chart…</div>;
  return <Chart option={option} height={340} />;
}
