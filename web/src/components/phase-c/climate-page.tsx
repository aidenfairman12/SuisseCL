"use client";
import type { EChartsOption } from "echarts";
import { Chart } from "@/components/charts/echarts";
import { Fold, Lead, Loading, Note, PB_COLOURS, Section, Table, fmt } from "@/components/phase-b/shared";
import { weekDay } from "@/components/phase-c/shared";
import { useBundleFile } from "@/lib/bundle";
import type { ClimateData } from "@/lib/types";

const AX = { axisLabel: { fontSize: 11 }, nameTextStyle: { fontSize: 11 } };
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const COL: Record<string, string> = { hist: PB_COLOURS.grey, "gwl2.0": PB_COLOURS.s3, "gwl3.0": PB_COLOURS.red, hist_hw99: PB_COLOURS.s1, "gwl2.0_hw99": PB_COLOURS.s3, "gwl3.0_hw99": PB_COLOURS.red };

function MonthlyChart({ d }: { d: ClimateData }) {
  const ids = ["hist", "gwl2.0", "gwl3.0"];
  const option: EChartsOption = {
    grid: { left: 52, right: 24, top: 64, bottom: 36 },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: MONTHS, ...AX },
    yAxis: { type: "value", name: "monthly mean temperature (°C)", ...AX },
    series: ids.map((id) => ({ type: "line", name: d.scenarios[id].label, symbolSize: 5, itemStyle: { color: COL[id] }, data: d.scenarios[id].monthly_mean_c.map((v) => Math.round(v * 10) / 10) })),
  };
  return <Chart option={option} height={300} />;
}

function WeekChart({ d }: { d: ClimateData }) {
  const ids = ["hist", "hist_hw99", "gwl2.0_hw99", "gwl3.0_hw99"];
  const start = d.inserted_rows[0];
  const option: EChartsOption = {
    grid: { left: 52, right: 24, top: 90, bottom: 48 },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: Array.from({ length: 168 }, (_, i) => i), axisLabel: { fontSize: 11, interval: 23, formatter: (v: string) => weekDay(start, Number(v)) }, ...{ nameTextStyle: { fontSize: 11 } } },
    yAxis: { type: "value", name: "hourly temperature (°C)", ...AX },
    series: ids.map((id) => ({ type: "line", name: d.scenarios[id].label, showSymbol: false, lineStyle: { width: id === "hist" ? 2.4 : 1.6, type: id === "hist" ? "dashed" : "solid" }, itemStyle: { color: COL[id] }, data: d.scenarios[id].week29_hourly_c ?? [] })),
  };
  return <Chart option={option} height={320} />;
}

export function ClimatePage() {
  const { data: d, error } = useBundleFile<ClimateData>("climate");
  if (error) return <p className="text-sm text-destructive">Could not load the climate bundle: {error}</p>;
  if (!d) return <Loading what="climate scenarios" />;
  const p = d.prose;
  const rows = (ids: string[]) => ids.map((id) => {
    const s = d.scenarios[id];
    return [<span key={id} className="block text-left">{s.label}</span>, fmt(s.annual_mean_c, 1), String(s.days_ge30), String(s.days_ge35), fmt(s.hottest_168h_c, 1), `${fmt(s.week29_mean_c, 1)} / ${fmt(s.week29_max_c, 1)}`, fmt(s.ghi_kwh_m2, 0), fmt(s.pv_kwh_kwp, 0)];
  });
  const head = ["Scenario", "Annual mean (°C)", "Days with a 30 °C hour", "Days with a 35 °C hour", "Hottest 168 h mean (°C)", "Inserted week mean / highest (°C)", "Solar radiation (kWh/m²)", "Solar yield (kWh/kWp)"];
  const spellRows = (pct: number) => d.spells.filter((s) => s.percentile === pct).map((s) => [
    <span key={s.level + s.percentile} className="block text-left">{s.level}</span>, s.chain, String(s.model_year), s.start, fmt(s.severity_c, 1),
    `${fmt(Math.max(...s.tasmax), 1)} / ${fmt(Math.min(...s.tasmin), 1)}`,
  ]);
  const spellHead = ["Level", "Model chain", "Model year", "Start (month-day)", "Mean daily maximum (°C)", "Highest / lowest day (°C)"];
  return (
    <div className="space-y-10">
      <Lead>{p.intro as string}</Lead>

      <Section title="The weather scenarios" classes={["measured", "modeled", "synthetic"]}>
        <p className="text-xs text-muted-foreground">Observed 2023 hours at Kloten with the climate-change signal added (typical warmer years), and the same years with a heat-wave week inserted. Hourly series are constructed; see below.</p>
        <Table head={head} rows={rows(d.order)} minWidth={900} />
        <Note>{p.stats as string}</Note>
        <Fold title="Sensitivity: milder spells and the lowest warming level" classes={["synthetic"]}>
          <Table head={head} rows={rows(d.sensitivity)} minWidth={900} />
          <Note>Not used in the cooling matrix: the milder spells are less hot than the hottest observed 2023 week.</Note>
        </Fold>
      </Section>

      <Section title="Monthly mean temperature" classes={["measured", "synthetic"]}>
        <MonthlyChart d={d} />
        <Note>Every month shifts by the middle change of all climate-model chains for that month.</Note>
      </Section>

      <Section title="The heat-wave week" classes={["synthetic"]}>
        <WeekChart d={d} />
        <Note>{p.heatwave as string}</Note>
      </Section>

      <Section title="How the hourly weather was built" classes={["derived", "synthetic"]}>
        <ul className="max-w-3xl list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground">
          {(p.construction as string[]).map((t, i) => <li key={i}>{t}</li>)}
        </ul>
        <p className="text-xs text-muted-foreground">Spell rule: {d.rule}.</p>
        <Table head={spellHead} rows={spellRows(99)} minWidth={760} />
        <Fold title="The milder (rank 95) spells, shown as a sensitivity">
          <Table head={spellHead} rows={spellRows(95)} minWidth={760} />
        </Fold>
      </Section>

      <Section title="Validation" classes={["derived"]}>
        <Note>{p.validation as string}</Note>
        <Fold title="Climate-model ensemble statistics for comparison">
          <Table
            head={["Level", "Days with a daily maximum of 30 °C or more per model year", "35 °C or more", "Highest humidity value (%)"]}
            rows={d.validation.ensemble.map((e) => [<span key={e.level} className="block text-left">{e.level}</span>, fmt(e.days_ge30, 1), fmt(e.days_ge35, 1), fmt(e.hurs_max, 1)])}
            minWidth={620}
          />
          <Note>Humidity values above one hundred percent are model output; they are capped when a spell is made hourly.</Note>
        </Fold>
      </Section>

      <Section title="What limits how far this weather can be read">
        <ul className="max-w-3xl list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground">
          {(p.limits as string[]).map((t, i) => <li key={i}>{t}</li>)}
        </ul>
      </Section>

      <Note>{p.citation_note as string} {d.citation}</Note>
      <Note>Sources: {d.sources.join(", ")}. Numbers are computed at build time from the committed weather files of the scenarios; the validation numbers come from the generated validation report.</Note>
    </div>
  );
}
