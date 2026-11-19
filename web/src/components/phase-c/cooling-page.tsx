"use client";
import { useState } from "react";
import { NodeLink } from "@/components/audit/bits";
import { Fold, Lead, Loading, Note, Section, Table, fmt, signed } from "@/components/phase-b/shared";
import { ArchetypeSelector, Pills, heat, useArchetype } from "@/components/phase-c/shared";
import { useBundleFile } from "@/lib/bundle";
import type { CoolingCell, CoolingData } from "@/lib/types";

type Metric = { id: string; label: string; unit: string; get: (c: CoolingCell) => number | null; digits: number; note: string };
const METRICS: Metric[] = [
  { id: "ceiling", label: "Exact optimum saving", unit: "% of the yearly bill", get: (c) => c.ceiling_year_pct, digits: 1, note: "Best possible bill saving over the year with perfect foresight, against the thermostat." },
  { id: "mass", label: "Value of building thermal mass", unit: "percentage points", get: (c) => c.mass_value_pts, digits: 1, note: "Exact optimum with the comfort band against the same optimum with the room held at the thermostat path." },
  { id: "cool", label: "Cooling electricity (thermostat)", unit: "MWh per year", get: (c) => c.cooling_kwh.baseline / 1000, digits: 1, note: "Electricity the district uses for cooling with the thermostat reference." },
  { id: "peak_t", label: "Summer peak (thermostat)", unit: "kW", get: (c) => c.peak_kw.summer_baseline, digits: 0, note: "Largest district grid draw in June to August." },
  { id: "peak_o", label: "Summer peak (exact optimum)", unit: "kW", get: (c) => c.peak_kw.summer_optimum, digits: 0, note: "The bill-optimal schedule charges storage together, which raises the peak." },
  { id: "pv_t", label: "Solar share of cooling electricity (thermostat)", unit: "%", get: (c) => (c.pv_cooling_share.thermostat ? 100 * c.pv_cooling_share.thermostat.pv : null), digits: 0, note: "Bookkeeping rule: solar serves base load and hot water first, then the heat pump. Only cells with cooling." },
  { id: "pv_o", label: "Solar and battery share of cooling electricity (optimum)", unit: "%", get: (c) => (c.pv_cooling_share.optimum ? 100 * (c.pv_cooling_share.optimum.pv + c.pv_cooling_share.optimum.battery) : null), digits: 0, note: "Same rule; battery energy of any origin." },
  { id: "mpc", label: "Planner: share of the optimum", unit: "% on the eight test weeks", get: (c) => c.controllers.mpc.share_of_ceiling_pct, digits: 0, note: "Planner saving divided by the exact optimum saving on the same weeks." },
  { id: "rule", label: "Hand-set solar rule: share of the optimum", unit: "% on the eight test weeks", get: (c) => c.controllers.pv_rule.share_of_ceiling_pct, digits: 0, note: "Same division for the hand-set rule." },
  { id: "dh", label: "Overheating without cooling (thermostat)", unit: "thousand degree-hours above the cooling setpoint", get: (c) => c.dh26.baseline / 1000, digits: 0, note: "A limit of the thermal model (no shading or ventilation); an indicator only." },
];

function HeatMap({ d, cells, metric }: { d: CoolingData; cells: CoolingCell[]; metric: Metric }) {
  const byId = new Map(cells.map((c) => [`${c.scenario}|${c.adoption}`, c]));
  const vals = cells.map(metric.get).filter((v): v is number => v != null);
  const lo = vals.length ? Math.min(...vals) : 0, hi = vals.length ? Math.max(...vals) : 1;
  const adoption = d.adoption.filter((a) => cells.some((c) => c.adoption === a));
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm" style={{ minWidth: 640 }}>
        <thead className="bg-muted/40 text-left text-xs">
          <tr><th className="p-2.5 font-medium">Weather scenario</th>{adoption.map((a) => <th key={a} className="p-2.5 text-right font-medium" title={d.adoption_labels[a]}>{d.adoption_short[a]}</th>)}</tr>
        </thead>
        <tbody>
          {d.scenarios.map((s) => (
            <tr key={s} className="border-t">
              <td className="p-2.5">{d.scenario_labels[s]}</td>
              {adoption.map((a) => {
                const c = byId.get(`${s}|${a}`);
                const v = c ? metric.get(c) : null;
                return <td key={a} className="p-2.5 text-right tabular-nums" style={{ background: heat(v, lo, hi) }}>{v == null ? "–" : fmt(v, metric.digits)}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CoolingPage() {
  const { data: d, error } = useBundleFile<CoolingData>("cooling");
  const [metricId, setMetricId] = useState("ceiling");
  const [scen, setScen] = useState("gwl3.0_hw99");
  const [rcell, setRcell] = useState("gwl3.0_hw99_high");
  const arch = useArchetype(d?.archetypes ?? []);
  if (error) return <p className="text-sm text-destructive">Could not load the cooling bundle: {error}</p>;
  if (!d) return <Loading what="cooling scenarios" />;
  const p = d.prose;
  const cells = d.cells.filter((c) => c.archetype === arch.current);
  const metric = METRICS.find((m) => m.id === metricId) ?? METRICS[0];
  const adoptionHere = d.adoption.filter((a) => cells.some((c) => c.adoption === a));
  const scCells = adoptionHere.map((a) => cells.find((c) => c.scenario === scen && c.adoption === a)).filter((c): c is CoolingCell => !!c);
  const rob = d.robustness.filter((r) => r.cell === rcell);
  const findings = (p.findings as string[]) ?? [];
  return (
    <div className="space-y-10">
      <Lead>{p.intro as string}</Lead>
      <div className="space-y-1"><ArchetypeSelector list={d.archetypes} current={arch.current} onChange={arch.setSel} /><Note>{p.archetype_note as string}</Note></div>
      <Note>{p.model_note as string}</Note>

      <Section title="What the results say" classes={["modeled", "assumption"]}>
        <ul className="max-w-3xl list-disc space-y-2 pl-5 text-sm leading-relaxed">
          {findings.map((f, i) => <li key={i}>{f}</li>)}
        </ul>
        <Note tone="warn">Agent&apos;s draft wording for the owner&apos;s review: the sentences above state what the numbers show; any reading beyond that is interpretation.</Note>
      </Section>

      <Section title="Climate and cooling level" classes={["modeled", "assumption"]}>
        <Pills value={metricId} onChange={setMetricId} label="Metric" options={METRICS.map((m) => ({ id: m.id, label: m.label }))} />
        <p className="text-sm font-medium">{metric.label} <span className="text-xs font-normal text-muted-foreground">({metric.unit})</span></p>
        <HeatMap d={d} cells={cells} metric={metric} />
        <Note>{metric.note} {p.heatmap_note as string}</Note>
      </Section>

      <Section title="Controllers in each cell" classes={["modeled"]}>
        <Pills value={scen} onChange={setScen} label="Weather scenario" options={d.scenarios.map((s) => ({ id: s, label: d.scenario_labels[s] }))} />
        <Table
          head={["Cooling level", "Exact optimum, test weeks (%)", "Solar rule saving (%)", "Planner saving (%)", "Planner + peak weight saving (%)", "Planner share of optimum (%)", "Thermostat highest hour (kW)", "Planner highest hour (kW)", "Planner + peak weight highest hour (kW)"]}
          rows={scCells.map((c) => [
            <span key={c.id} className="block max-w-[22rem] text-left">{d.adoption_short[c.adoption]}{c.cooled.length ? ` (${c.cooled.join(", ")})` : ""}</span>,
            fmt(c.ceiling_weeks_pct, 1), signed(c.controllers.pv_rule.saving_pct, 1), signed(c.controllers.mpc.saving_pct, 1), signed(c.controllers["mpc_peak0.1"].saving_pct, 1),
            fmt(c.controllers.mpc.share_of_ceiling_pct, 0), fmt(c.controllers.thermostat.highest_hour_kw, 0), fmt(c.controllers.mpc.highest_hour_kw, 0), fmt(c.controllers["mpc_peak0.1"].highest_hour_kw, 0),
          ])}
          minWidth={980}
        />
        <Note>{p.controllers_note as string} The highest hour is the largest district grid draw in the eight test weeks.</Note>
      </Section>

      <Section title="Details" >
        <Fold title="Robustness of the planner on the heat-wave cells (high cooling)" classes={["synthetic", "modeled"]}>
          <Pills value={rcell} onChange={setRcell} label="Cell" options={[...new Set(d.robustness.map((r) => r.cell))].map((c) => ({ id: c, label: c }))} />
          <Table
            head={["Case", "Bill saved (%)", "Share of optimum (%)", "Hours too cold (K·h)", "Cooling electricity (kWh)", "Highest hour (kW)"]}
            rows={rob.map((r) => [<span key={r.case} className="block max-w-[26rem] text-left">{r.label}{r.synthetic && <span className="text-xs text-muted-foreground"> · synthetic error</span>}</span>, signed(r.saving_pct, 1), fmt(r.share_of_ceiling_pct, 0), fmt(r.comfort_cold_kh, 0), fmt(r.cooling_kwh, 0), fmt(r.highest_hour_kw, 0)])}
            minWidth={760}
          />
          <Note>{p.robustness_note as string}</Note>
        </Fold>
        <Fold title="Phase C assumptions that are written in drafts and not yet in the registers" classes={["assumption"]}>
          <ul className="space-y-2">
            {d.pending_register.map((x) => (
              <li key={x.title} className="rounded-xl border bg-card p-3 text-sm"><div className="font-medium">{x.title}</div><p className="text-xs text-muted-foreground">{x.text}</p></li>
            ))}
          </ul>
        </Fold>
      </Section>

      <Section title={p.limitations_title as string}>
        <Lead>{p.limitations_intro as string}</Lead>
        <ul className="grid gap-2 md:grid-cols-2">
          {d.limitations.map((l) => (
            <li key={l.id} className="space-y-1 rounded-xl border bg-card p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2"><NodeLink id={l.id} /><span className="text-xs text-muted-foreground">{l.status}</span></div>
              <p className="text-sm">{l.title}</p>
            </li>
          ))}
        </ul>
      </Section>
      <Note>Sources: {d.sources.join(", ")}. Every number is read from committed result files at build time; the export price is {fmt(d.meta.export_price_rp, 0)} Rp/kWh. Savings are changes of the bill against the thermostat.</Note>
    </div>
  );
}
