"use client";
import { useState } from "react";
import type { EChartsOption } from "echarts";
import { Chart } from "@/components/charts/echarts";
import { Lead, Loading, Note, PB_COLOURS, Section, Table, fmt, signed } from "@/components/phase-b/shared";
import { ArchetypeSelector, Pills, cellId, useArchetype, weekDay } from "@/components/phase-c/shared";
import { useBundleFile } from "@/lib/bundle";
import type { CoolingCell, CoolingData, ExplorerData, HouseBlock, HoursSeries, HousesData } from "@/lib/types";

const AX = { axisLabel: { fontSize: 11 }, nameTextStyle: { fontSize: 11 } };
const LOAD_COL = { base: "#718096", dhw: "#4299e1", heat: "#dd6b20", cool: "#2b6cb0" };
/** Data key of a cell: the central archetype uses the plain cell id, other archetypes are prefixed with their id. */
export const dataKey = (arch: string, cell: string) => (arch === "central" ? cell : `${arch}__${cell}`);

function AnnualChart({ blocks, buildings }: { blocks: Record<string, HouseBlock>; buildings: string[] }) {
  const g = (f: (b: HouseBlock) => number) => buildings.map((b) => Math.round((f(blocks[b]) / 1000) * 10) / 10);
  const bar = (name: string, stack: string, colour: string, data: number[]) => ({ type: "bar" as const, name, stack, itemStyle: { color: colour }, data, barMaxWidth: 26 });
  const option: EChartsOption = {
    grid: { left: 56, right: 16, top: 100, bottom: 56 },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: buildings, axisLabel: { fontSize: 11, interval: 0, rotate: 30 } },
    yAxis: { type: "value", name: "electricity (MWh per year)", ...AX },
    series: [
      bar("Household load", "use", LOAD_COL.base, g((b) => b.annual.base)), bar("Hot water", "use", LOAD_COL.dhw, g((b) => b.annual.dhw)),
      bar("Heating", "use", LOAD_COL.heat, g((b) => b.annual.heat)), bar("Cooling", "use", LOAD_COL.cool, g((b) => b.annual.cool)),
      bar("Solar used on site", "source", PB_COLOURS.s2, g((b) => b.annual.pv_used_onsite)), bar("Bought from the grid", "source", PB_COLOURS.red, g((b) => b.annual.import)),
      bar("Exported", "export", PB_COLOURS.purple, g((b) => b.annual.export)),
    ],
  };
  return <Chart option={option} height={340} />;
}

function WeekChart({ h, start }: { h: HoursSeries; start: number }) {
  const peak = Math.max(...h.net);
  const at = h.net.indexOf(peak);
  const area = (name: string, key: keyof typeof LOAD_COL, data: number[]) => ({ type: "line" as const, name, stack: "load", areaStyle: { opacity: 0.55 }, showSymbol: false, lineStyle: { width: 0 }, itemStyle: { color: LOAD_COL[key] }, data });
  const option: EChartsOption = {
    grid: { left: 56, right: 16, top: 100, bottom: 48 },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: Array.from({ length: h.net.length }, (_, i) => i), axisLabel: { fontSize: 11, interval: 23, formatter: (v: string) => weekDay(start, Number(v)) } },
    yAxis: { type: "value", name: "district energy per hour (kWh)", ...AX },
    series: [
      area("Household load", "base", h.base), area("Hot water", "dhw", h.dhw), area("Heating", "heat", h.heat), area("Cooling", "cool", h.cool),
      { type: "line", name: "Solar generation", showSymbol: false, lineStyle: { width: 1.6, color: PB_COLOURS.s3 }, itemStyle: { color: PB_COLOURS.s3 }, data: h.pv },
      { type: "line", name: "Battery (charging positive)", showSymbol: false, lineStyle: { width: 1.2, color: PB_COLOURS.s1, type: "dashed" }, itemStyle: { color: PB_COLOURS.s1 }, data: h.batt },
      { type: "line", name: "Grid (import positive)", showSymbol: false, lineStyle: { width: 2.2, color: PB_COLOURS.red }, itemStyle: { color: PB_COLOURS.red }, data: h.net,
        markPoint: { symbolSize: 46, label: { fontSize: 10, formatter: () => `highest ${fmt(peak, 1)}` }, data: [{ coord: [at, peak] }] } },
    ] as EChartsOption["series"],
  };
  return <Chart option={option} height={380} />;
}

export function ExplorerPage() {
  const { data: d, error } = useBundleFile<ExplorerData>("explorer");
  const { data: hs } = useBundleFile<HousesData>("houses");
  const { data: cd } = useBundleFile<CoolingData>("cooling");
  const [scen, setScen] = useState("gwl3.0_hw99");
  const [adopt, setAdopt] = useState("high");
  const [ctrl, setCtrl] = useState("thermostat");
  const arch = useArchetype(d?.archetypes ?? []);
  if (error) return <p className="text-sm text-destructive">Could not load the explorer bundle: {error}</p>;
  if (!d || !hs || !cd) return <Loading what="scenario explorer" />;
  const p = d.prose;
  const adoptions = d.adoption.filter((a) => d.scenarios.some((s) => dataKey(arch.current, cellId(s, a)) in d.hourly));
  const key = dataKey(arch.current, cellId(scen, adopt));
  const hours = (d.hourly[key]?.[ctrl] as HoursSeries | undefined) ?? null;
  const annualCell = hs.cells[key] as ({ archetype: string } & Record<string, { buildings: Record<string, HouseBlock>; district: { annual: Record<string, number>; summer_peak_kw: number; peak_kw: number } }>) | undefined;
  const annual = annualCell && (ctrl === "thermostat" || ctrl === "optimum") ? annualCell[ctrl] : null;
  const cell: CoolingCell | undefined = cd.cells.find((c) => c.archetype === arch.current && c.id === cellId(scen, adopt));
  const ctrlRow = cell && ctrl !== "optimum" ? cell.controllers[ctrl] : null;
  return (
    <div className="space-y-10">
      <Lead>{p.intro as string}</Lead>
      <div className="space-y-3">
        <ArchetypeSelector list={d.archetypes} current={arch.current} onChange={arch.setSel} />
        <Pills value={scen} onChange={setScen} label="Weather scenario" options={d.scenarios.map((s) => ({ id: s, label: d.scenario_labels[s] }))} />
        <Pills value={adopt} onChange={setAdopt} label="Cooling level" options={adoptions.map((a) => ({ id: a, label: d.adoption_labels[a].split(":")[0] }))} />
        <Pills value={ctrl} onChange={setCtrl} label="Controller" options={d.controllers.map((c) => ({ id: c, label: d.controller_labels[c] }))} />
      </div>

      <Section title="Energy over the year, per building" classes={["modeled", "assumption"]}>
        {annual ? (
          <>
            <AnnualChart blocks={annual.buildings} buildings={hs.buildings} />
            <Note>Full-year simulation of the {d.controller_labels[ctrl].toLowerCase()}. The first stack is electricity use, the second is where it came from, the third is solar power exported. The solar-used and grid parts also cover battery losses, so they do not add up exactly to the use.</Note>
          </>
        ) : (
          <Note>The yearly stack is only available for the thermostat and the exact optimum, which were simulated for the whole year. The {d.controller_labels[ctrl].toLowerCase()} was simulated for the eight test weeks; see the numbers below and the heat-wave week.</Note>
        )}
      </Section>

      <Section title="The heat-wave week, hour by hour" classes={["modeled", "synthetic"]}>
        {hours ? <WeekChart h={hours} start={d.week.steps[0]} /> : <Note tone="warn">{p.missing_note as string}</Note>}
        <Note>{p.week_note as string}</Note>
      </Section>

      <Section title="The numbers" classes={["modeled"]}>
        {cell ? (
          <Table
            head={["Quantity", "Value"]}
            rows={[
              ["Weather scenario and cooling level", `${d.scenario_labels[scen]}; ${d.adoption_labels[adopt]}`],
              ["Exact optimum saving over the year (%)", fmt(cell.ceiling_year_pct, 1)],
              ["Exact optimum saving on the eight test weeks (%)", fmt(cell.ceiling_weeks_pct, 1)],
              ["Thermostat bill (CHF per year)", fmt(cell.zero_bill_chf, 0)],
              ["Cooling electricity with the thermostat (kWh per year)", fmt(cell.cooling_kwh.baseline, 0)],
              ["Summer peak, thermostat / exact optimum (kW)", `${fmt(cell.peak_kw.summer_baseline, 0)} / ${fmt(cell.peak_kw.summer_optimum, 0)}`],
              ...(ctrlRow ? [
                [`${d.controller_labels[ctrl]}: bill saved on the test weeks (%)`, signed(ctrlRow.saving_pct, 1)],
                [`${d.controller_labels[ctrl]}: share of the optimum (%)`, fmt(ctrlRow.share_of_ceiling_pct, 0)],
                [`${d.controller_labels[ctrl]}: highest hour in the test weeks (kW)`, fmt(ctrlRow.highest_hour_kw, 0)],
                [`${d.controller_labels[ctrl]}: cooling electricity in the test weeks (kWh)`, fmt(ctrlRow.cooling_kwh, 0)],
              ] : []),
              ...(annual ? [[`Highest hour of the year, ${d.controller_labels[ctrl].toLowerCase()} (kW)`, fmt(annual.district.peak_kw, 0)]] : []),
            ]}
            minWidth={520}
          />
        ) : <Note>No data for this combination.</Note>}
      </Section>
      <Note>Sources: {d.sources.join(", ")}. Every curve and number is read from committed result files at build time. Hours with the rule and the planner exist only for the cells of the heat-wave scenarios with no cooling and with high cooling.</Note>
    </div>
  );
}
