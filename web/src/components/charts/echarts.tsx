"use client";
// Tree-shaken ECharts: only the chart types and components the dashboard uses.
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import { AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TitleComponent, TooltipComponent, VisualMapComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";
import type { EChartsOption } from "echarts";
import { CATEGORICAL, PALETTE } from "@/lib/palette";

echarts.use([BarChart, HeatmapChart, LineChart, ScatterChart, AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TitleComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

// Site-wide chart look: zinc text and hairline axes, the shared categorical palette, a white tooltip card.
const axisStyle = {
  axisLine: { lineStyle: { color: PALETTE.faint } },
  axisTick: { lineStyle: { color: PALETTE.faint } },
  axisLabel: { color: PALETTE.muted },
  nameTextStyle: { color: PALETTE.muted },
  splitLine: { lineStyle: { color: PALETTE.wash } },
};
echarts.registerTheme("site", {
  color: CATEGORICAL,
  textStyle: { fontFamily: "inherit", color: PALETTE.text },
  title: { textStyle: { color: PALETTE.ink, fontWeight: 600 }, subtextStyle: { color: PALETTE.muted } },
  legend: { textStyle: { color: PALETTE.text }, icon: "roundRect", itemWidth: 10, itemHeight: 10 },
  tooltip: { backgroundColor: "#ffffff", borderColor: PALETTE.hair, borderWidth: 1, textStyle: { color: PALETTE.ink, fontSize: 12 }, extraCssText: "border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.06);" },
  categoryAxis: axisStyle,
  valueAxis: { ...axisStyle, axisLine: { show: false }, axisTick: { show: false } },
  timeAxis: axisStyle,
  logAxis: axisStyle,
  markLine: { lineStyle: { color: PALETTE.soft } },
});

export type EChartInstance = ReturnType<typeof echarts.init>;

export function Chart({ option, height = 300, onReady, className }: { option: EChartsOption; height?: number; onReady?: (c: EChartInstance) => void; className?: string }) {
  return (
    <ReactEChartsCore
      echarts={echarts}
      theme="site"
      option={option}
      notMerge
      lazyUpdate
      className={className}
      style={{ height, width: "100%" }}
      opts={{ renderer: "canvas" }}
      onChartReady={onReady as ((c: unknown) => void) | undefined}
    />
  );
}
