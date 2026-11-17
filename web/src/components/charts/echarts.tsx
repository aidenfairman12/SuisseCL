"use client";
// Tree-shaken ECharts: only the chart types and components the dashboard uses.
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import { AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TitleComponent, TooltipComponent, VisualMapComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import ReactEChartsCore from "echarts-for-react/lib/core";
import type { EChartsOption } from "echarts";

echarts.use([BarChart, HeatmapChart, LineChart, ScatterChart, AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TitleComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

export type EChartInstance = ReturnType<typeof echarts.init>;

export function Chart({ option, height = 300, onReady, className }: { option: EChartsOption; height?: number; onReady?: (c: EChartInstance) => void; className?: string }) {
  return (
    <ReactEChartsCore
      echarts={echarts}
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
