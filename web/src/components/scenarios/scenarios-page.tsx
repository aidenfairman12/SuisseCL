"use client";
import type { EChartsOption } from "echarts";
import { ClassBadge, NodeLink } from "@/components/audit/bits";
import { Chart } from "@/components/charts/echarts";
import { Fold, Lead, Loading, Note, PB_COLOURS, Section, Table, fmt } from "@/components/phase-b/shared";
import { useBundleFile } from "@/lib/bundle";
import type { ScenariosData } from "@/lib/types";
import { PALETTE } from "@/lib/palette";

const AX = { axisLabel: { fontSize: 11 }, nameTextStyle: { fontSize: 11 } };
const COLS = [PALETTE.soft, PALETTE.gridSoft, PALETTE.gridMid, PALETTE.grid];

function CeilingChart({ d }: { d: ScenariosData }) {
  const ids = ["s0", "s1", "s2", "s3"], names = ["S0", "S1", "S2", "S3"];
  const option: EChartsOption = {
    grid: { left: 48, right: 16, top: 36, bottom: 30 },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    tooltip: { trigger: "axis", valueFormatter: (v) => (v == null ? "not computed" : `${fmt(Number(v), 2)} %`) },
    xAxis: { type: "category", data: names, ...AX },
    yAxis: { type: "value", name: "share of the yearly bill saved (%)", ...AX },
    series: [
      { type: "bar", name: "Full year", data: ids.map((k) => d.ceilings[k].year), itemStyle: { color: PB_COLOURS.grey }, label: { show: true, position: "top", fontSize: 10, formatter: (p) => fmt(Number(p.value), 1) } },
      { type: "bar", name: "Eight test weeks (as for every controller)", data: ids.map((k) => d.ceilings[k].week), itemStyle: { color: PB_COLOURS.s2 }, label: { show: true, position: "top", fontSize: 10, formatter: (p) => (p.value == null ? "" : fmt(Number(p.value), 1)) } },
    ],
  };
  return <Chart option={option} height={280} />;
}

function ExportChart({ d }: { d: ScenariosData }) {
  const prices = Object.keys(d.export_sweep);
  const option: EChartsOption = {
    grid: { left: 48, right: 16, top: 36, bottom: 40 },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    tooltip: { trigger: "axis", valueFormatter: (v) => `${fmt(Number(v), 1)} %` },
    xAxis: { type: "category", data: prices, name: "assumed export price (Rp/kWh)", nameLocation: "middle", nameGap: 26, ...AX },
    yAxis: { type: "value", name: "ceiling (% of bill)", ...AX },
    series: (["S1", "S2", "S3"] as const).map((k, i) => ({ type: "line", name: k, symbolSize: 7, data: prices.map((p) => d.export_sweep[p][k]), itemStyle: { color: [PB_COLOURS.s1, PB_COLOURS.s2, PB_COLOURS.s3][i] }, label: { show: true, fontSize: 10, formatter: (q: { value?: unknown }) => fmt(Number(q.value), 1) } })),
  };
  return <Chart option={option} height={280} />;
}

export function ScenariosPage() {
  const { data: d, error } = useBundleFile<ScenariosData>("scenarios");
  if (error) return <p className="text-sm text-destructive">Could not load the scenarios bundle: {error}</p>;
  if (!d) return <Loading what="scenarios" />;
  const p = d.prose;
  return (
    <div className="space-y-10">
      <div className="space-y-3">
        <Lead>{p.intro}</Lead>
        <Note tone="warn">{p.gate}</Note>
      </div>

      <Section title="The ladder" classes={["assumption", "modeled"]}>
        <div className="grid gap-3 md:grid-cols-2">
          {d.ladder.map((s, i) => (
            <div key={s.id} className="space-y-2 rounded-xl border bg-card p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md px-2 py-0.5 text-sm font-semibold text-white" style={{ background: COLS[i] }}>{s.id}</span>
                <span className="font-medium">{s.name}</span>
                {s.classes.map((c) => <ClassBadge key={c} cls={c} />)}
              </div>
              <p className="text-sm text-muted-foreground">{s.adds}</p>
              <p className="text-xs text-muted-foreground">Yearly bill without control: {fmt(s.zero_bill_year_chf, 0)} CHF · ideal saving {fmt(s.saving_year_pct, 1)} % of the year{s.saving_week_pct != null && <> · {fmt(s.saving_week_pct, 1)} % of the test weeks</>}</p>
              <p className="flex flex-wrap gap-x-3 text-xs">{s.nodes.map((n) => <NodeLink key={n} id={n} />)}</p>
            </div>
          ))}
        </div>
        <Note>Solar size, battery size and rating, export price, thermal parameters and comfort band are assumed values; none is measured on these buildings. The reference for S3 is a thermostat at the setpoint, because zero heating would let the house cool down.</Note>
      </Section>

      <Section title="What an ideal controller could save" classes={["modeled", "assumption"]}>
        <Lead>{p.ceilings}</Lead>
        <CeilingChart d={d} />
        <Lead>{p.mass}</Lead>
        <Table head={["S3 comfort setting", "Ceiling (% of the yearly bill)"]} rows={[["Wide band (lower limit 20 °C)", fmt(d.bands.s3_band_20_24, 2)], ["Narrow band (21 to 24 °C), the default", fmt(d.bands.s3_band_21_24, 2)], ["No building flexibility (held at the thermostat path)", fmt(d.bands.s3_no_flex, 2)]]} minWidth={420} />
      </Section>

      <Section title="The export price" classes={["assumption"]}>
        <Lead>{p.export}</Lead>
        <ExportChart d={d} />
        <Note>The export price is a swept assumption (no producer price was available); the default is {fmt(d.export_price_rp, 0)} Rp/kWh. CityLearn itself credits no exports; the bill is computed outside it.</Note>
      </Section>

      <Section title="Other price structures" classes={["assumption", "synthetic"]}>
        <Lead>{p.tariffs}</Lead>
        <Table
          head={["Tariff variant", "Daily spread (Rp/kWh)", "Mean price (Rp/kWh)", "S0", "S1", "S2", "S3"]}
          rows={d.tariffs.map((t) => [t.label, fmt(t.spread_rp, 1), fmt(t.mean_rp, 1), `${fmt(t.S0, 1)} %`, `${fmt(t.S1, 1)} %`, `${fmt(t.S2, 1)} %`, `${fmt(t.S3, 1)} %`])}
          minWidth={820}
        />
        <Note>Cells show the ceiling as a share of the bill under that tariff. The standard two-tier tariff is the realistic baseline; the others are labelled scenarios.</Note>
      </Section>

      <Section title="Hours or quarter-hours" classes={["modeled"]}>
        <Lead>{p.resolution}</Lead>
        <Table head={["Rung", "Hourly ceiling (%)", "Quarter-hour ceiling (%)"]} rows={d.resolution.map((r) => [r.name, fmt(r.hourly_pct, 2), fmt(r.q15_pct, 2)])} minWidth={460} />
      </Section>

      <Section title="The ideal schedule and the grid" classes={["modeled"]}>
        <Lead>{p.peaks}</Lead>
        <Table
          head={["Case", "Grid import (MWh)", "Coincident peak (kW)", "Solar used on site", "Battery cycles", "Bill (CHF)"]}
          rows={d.metrics.map((m) => [m.name, fmt(m.import_kwh / 1000, 1), fmt(m.peak_kw, 0), m.pv_self_consumption == null ? "–" : `${fmt(100 * m.pv_self_consumption, 0)} %`, m.battery_cycles == null ? "–" : fmt(m.battery_cycles, 0), fmt(m.bill_chf, 0)])}
          minWidth={760}
        />
      </Section>

      <Section title="Electric vehicles and a local energy community" classes={["assumption", "synthetic"]}>
        <Lead>{p.evleg}</Lead>
        <Fold title="Details of the two what-ifs">
          <Table head={["Electric-vehicle case (on S2)", "Reference bill (CHF)", "Ideal saving (%)"]} rows={d.ev.map((e) => [e.name, fmt(e.zero_bill, 0), fmt(e.saving_pct, 2)])} minWidth={520} />
          <Table
            head={["Grid-fee discount on internal exchange", "Bill with community (CHF)", "Bill without the community credit (CHF)", "Energy exchanged inside (MWh)"]}
            rows={d.leg.map((l) => [`${fmt(100 * l.discount, 0)} %`, fmt(l.bill_with_leg, 0), fmt(l.bill_before_leg_credit, 0), fmt(l.internal_kwh / 1000, 1)])}
            minWidth={620}
          />
          <Note>One vehicle per housing unit of a measured charging station, plugged in overnight (assumed). All six buildings are treated as one community although they are a composite. Rules and fees come from one utility document.</Note>
        </Fold>
      </Section>

      <Note>Sources: {d.sources.join(", ")}. Every number on this page is read from those files at build time; classification badges say what kind of value each block shows.</Note>
    </div>
  );
}
