"use client";
import { useState } from "react";
import type { EChartsOption } from "echarts";
import { NodeLink } from "@/components/audit/bits";
import { Chart } from "@/components/charts/echarts";
import { Fold, Lead, Loading, Note, PB_COLOURS, Section, Table, fmt, signed } from "@/components/phase-b/shared";
import { useBundleFile } from "@/lib/bundle";
import type { ControllersData, PbRow } from "@/lib/types";
import { cn } from "@/lib/utils";

const AX = { axisLabel: { fontSize: 11 }, nameTextStyle: { fontSize: 11 } };
const SC_IDS = ["s1", "s2", "s3"] as const;
const SC_COL: Record<string, string> = { s1: PB_COLOURS.s1, s2: PB_COLOURS.s2, s3: PB_COLOURS.s3 };
const GROUP_TITLE: Record<string, string> = {
  optimum: "Upper reference",
  pv_rule: "Hand-set solar rule",
  rl: "Reinforcement learning (mean over seeds, spread = standard deviation)",
  mpc_forecast: "Receding-horizon planner: how good the forecast is",
  mpc_peak: "Receding-horizon planner: with a peak weight",
};
const MAIN_GROUPS = ["optimum", "pv_rule", "rl", "mpc_forecast", "mpc_peak"];

function SavingCell({ r, ceiling }: { r: PbRow; ceiling: number }) {
  if (r.saving_pct == null) return <span className="text-muted-foreground">{r.note ?? "–"}</span>;
  const w = Math.max(0, Math.min(100, (100 * Math.abs(r.saving_pct)) / Math.max(ceiling, Math.abs(r.saving_pct), 1e-9)));
  const neg = r.saving_pct < 0;
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="hidden h-2 w-24 overflow-hidden rounded-full bg-muted sm:block"><div className="h-full rounded-full" style={{ width: `${w}%`, background: neg ? PB_COLOURS.red : PB_COLOURS.s2 }} /></div>
      <span className={cn("w-24 text-right", neg && "text-red-700")}>
        {signed(r.saving_pct, 2)} %{r.spread_pct != null && <span className="text-xs text-muted-foreground"> ± {fmt(r.spread_pct, 2)}</span>}
      </span>
    </div>
  );
}

function ComparisonTable({ d, sc }: { d: ControllersData; sc: string }) {
  const s = d.scenarios[sc];
  const rows = MAIN_GROUPS.flatMap((g) => {
    const rs = s.rows.filter((r) => r.group === g && (g !== "mpc_forecast" || r.horizon === 48));
    return rs.length ? [{ g, rs }] : [];
  });
  const body: React.ReactNode[][] = [];
  rows.forEach(({ g, rs }) => {
    body.push([<span key={g} className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{GROUP_TITLE[g]}</span>, "", "", "", ""]);
    rs.forEach((r) => body.push([
      <span key={r.id} className="block max-w-[34rem] text-left">{r.label}{r.n != null && r.n > 0 && <span className="text-xs text-muted-foreground"> · {r.n} seeds</span>}</span>,
      <SavingCell key="s" r={r} ceiling={s.ceiling_pct} />,
      r.share_of_ceiling_pct == null ? "–" : `${fmt(r.share_of_ceiling_pct, 0)} %`,
      r.peak_kw != null ? `${fmt(r.peak_kw, 0)} kW (${signed(r.peak_vs_zero_pct, 0)} %)` : r.peak_vs_zero_pct != null ? `${signed(r.peak_vs_zero_pct, 0)} %` : "–",
      r.comfort_kh == null ? "–" : fmt(r.comfort_kh, 0),
    ]));
  });
  return (
    <Table
      head={["Controller", "Bill saved against the reference", "Share of the ideal saving", "Highest hour (change vs reference)", "Hours too cold (K·h)"]}
      rows={body}
      minWidth={860}
    />
  );
}

function ForecastChart({ d }: { d: ControllersData }) {
  const f = d.forecast_quality;
  const option: EChartsOption = {
    grid: { left: 52, right: 24, top: 40, bottom: 48 },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    tooltip: { trigger: "item" },
    xAxis: { type: "value", name: "forecast error (multiple of the standard deviation of each series)", nameLocation: "middle", nameGap: 28, min: 0, ...AX },
    yAxis: { type: "value", name: "bill saved (%)", ...AX },
    series: [
      {
        type: "line", name: "Perfect forecast plus synthetic error", symbolSize: 8, itemStyle: { color: PB_COLOURS.s2 }, data: f.synthetic.map((p) => ({ value: [p.x, p.saving_pct], name: p.label })),
        label: { show: true, fontSize: 10, position: "top", formatter: (q: { value?: unknown }) => fmt((q.value as number[])[1], 1) },
        markLine: { symbol: "none", lineStyle: { type: "dashed" }, data: [
          { yAxis: f.ceiling_pct, name: "Exact optimum", lineStyle: { color: PB_COLOURS.purple }, label: { formatter: "Exact optimum", fontSize: 10, position: "insideEndTop" } },
        ] },
      },
      { type: "scatter", name: "Weather-conditioned forecast (measured load error)", symbolSize: 12, itemStyle: { color: PB_COLOURS.s3 }, data: [{ value: [f.weather_conditioned.x, f.weather_conditioned.saving_pct], name: f.weather_conditioned.label }], label: { show: true, fontSize: 10, position: "right", formatter: (q: { value?: unknown }) => fmt((q.value as number[])[1], 1) } },
      { type: "scatter", name: "History-only forecast (measured error)", symbolSize: 12, itemStyle: { color: PB_COLOURS.red }, data: [{ value: [f.history_only.x, f.history_only.saving_pct], name: f.history_only.label }], label: { show: true, fontSize: 10, position: "right", formatter: (q: { value?: unknown }) => fmt((q.value as number[])[1], 1) } },
    ],
  };
  return <Chart option={option} height={320} />;
}

function TradeoffChart({ d, sc }: { d: ControllersData; sc: string }) {
  const t = d.peak_tradeoff[sc];
  const mk = (mode: string, name: string, colour: string) => {
    const pts = t.series[mode];
    if (!pts) return null;
    return { type: "line" as const, name, symbolSize: 9, itemStyle: { color: colour }, data: pts.map((p) => ({ value: [p.peak_kw, p.saving_pct], w: p.peak_w })), label: { show: true, fontSize: 10, position: "top" as const, formatter: (q: { data?: unknown }) => `w ${(q.data as { w: number }).w}` } };
  };
  const series = [mk("perfect", "Perfect forecast", PB_COLOURS.s2), mk("weather", "Weather-conditioned forecast", PB_COLOURS.s3)].filter((x) => x !== null) as NonNullable<EChartsOption["series"]>;
  const option: EChartsOption = {
    grid: { left: 52, right: 24, top: 64, bottom: 48 },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    tooltip: { trigger: "item" },
    xAxis: { type: "value", name: "highest hour of the district in the test weeks (kW)", nameLocation: "middle", nameGap: 28, scale: true, ...AX },
    yAxis: { type: "value", name: "bill saved (%)", ...AX },
    series: [
      ...(series as object[]),
      { type: "scatter", name: "Hand-set solar rule", symbolSize: 12, itemStyle: { color: PB_COLOURS.grey }, data: [[t.pv_rule.peak_kw, t.pv_rule.saving_pct]] },
      { type: "scatter", name: "Reference (no control)", symbolSize: 12, itemStyle: { color: PB_COLOURS.red }, symbol: "diamond", data: [[t.zero_peak_kw, 0]] },
    ] as EChartsOption["series"],
  };
  return <Chart option={option} height={300} />;
}

function CurvesChart({ d, sc }: { d: ControllersData; sc: string }) {
  const runs = d.rl_curves.filter((c) => c.scenario === sc);
  const kinds = [...new Set(runs.map((r) => r.kind))];
  const colour: Record<string, string> = { sac_central: PB_COLOURS.s1, sac_decentral: PB_COLOURS.s3 };
  const option: EChartsOption = {
    grid: { left: 52, right: 24, top: 40, bottom: 48 },
    legend: { top: 0, textStyle: { fontSize: 11 }, data: kinds.map((k) => (k === "sac_central" ? "Central SAC" : "SAC per building")) },
    tooltip: { trigger: "axis" },
    xAxis: { type: "value", name: "training steps", nameLocation: "middle", nameGap: 28, ...AX },
    yAxis: { type: "value", name: "bill change on the test weeks (%, positive = loss)", ...AX },
    series: runs.map((r) => ({
      type: "line", name: r.kind === "sac_central" ? "Central SAC" : "SAC per building", symbolSize: 4, lineStyle: { width: 1.2 }, itemStyle: { color: colour[r.kind] ?? PB_COLOURS.grey },
      data: r.steps.map((x, i) => [x, r.bill_change_pct[i]]), markLine: { symbol: "none", silent: true, data: [{ yAxis: 0 }], lineStyle: { color: PB_COLOURS.s2, type: "dashed" }, label: { show: false } },
    })),
  };
  return <Chart option={option} height={300} />;
}

export function ControllersPage() {
  const { data: d, error } = useBundleFile<ControllersData>("controllers");
  const [sc, setSc] = useState<string>("s2");
  if (error) return <p className="text-sm text-destructive">Could not load the controllers bundle: {error}</p>;
  if (!d) return <Loading what="controller comparison" />;
  const p = d.prose;
  const s = d.scenarios[sc];
  const findings = (p.findings as string[]) ?? [];
  const folds = {
    ablation: s.rows.filter((r) => r.group === "mpc_ablation"),
    other: s.rows.filter((r) => r.group === "mpc_forecast" && r.horizon !== 48),
  };
  return (
    <div className="space-y-10">
      <Lead>{p.intro as string}</Lead>
      <Section title="What the comparison shows" classes={["modeled"]}>
        <ul className="max-w-3xl list-disc space-y-2 pl-5 text-sm leading-relaxed">{findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
        <Note>Every number in these sentences is read from the result files.</Note>
      </Section>

      <Section title="Controllers on the held-out weeks" classes={["modeled", "synthetic"]}>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Scenario">
          {SC_IDS.map((k) => (
            <button key={k} type="button" role="tab" aria-selected={sc === k} onClick={() => setSc(k)} className={cn("rounded-md border px-3 py-1.5 text-sm transition-colors", sc === k ? "font-medium text-white" : "hover:bg-muted")} style={sc === k ? { background: SC_COL[k] } : undefined}>
              {d.scenarios[k].name}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Reference: {s.reference.label.toLowerCase()}, bill {fmt(s.reference.bill_chf, 0)} CHF over the eight test weeks, highest hour {fmt(s.reference.peak_kw, 0)} kW. The exact optimum saves {fmt(s.ceiling_pct, 1)} % on these weeks.
        </p>
        <ComparisonTable d={d} sc={sc} />
        <Note>{p.rl_note as string}</Note>
        {(folds.other.length > 0 || folds.ablation.length > 0) && (
          <Fold title="More planner variants: other horizons and ablations">
            <Table
              head={["Variant", "Bill saved (%)", "Share of the ideal saving", "Highest hour (kW)", "Hours too cold (K·h)"]}
              rows={[...folds.other, ...folds.ablation].map((r) => [<span key={r.id} className="block max-w-[34rem] text-left">{r.label}</span>, signed(r.saving_pct, 2), r.share_of_ceiling_pct == null ? "–" : `${fmt(r.share_of_ceiling_pct, 0)} %`, fmt(r.peak_kw, 0), fmt(r.comfort_kh, 0)])}
              minWidth={780}
            />
          </Fold>
        )}
      </Section>

      <Section title="How good the forecast has to be" classes={["synthetic", "modeled"]}>
        <p className="text-xs text-muted-foreground">S2: solar and battery. The sweep adds random error to the true future; the two real forecasters are placed by their measured load error on the eight test weeks.</p>
        <ForecastChart d={d} />
        <Note>{p.forecast_note as string}</Note>
      </Section>

      <Section title="Bill against highest hour" classes={["modeled"]}>
        <div className="grid gap-4 lg:grid-cols-2">
          {(["s2", "s3"] as const).filter((k) => d.peak_tradeoff[k]).map((k) => (
            <div key={k} className="space-y-1">
              <h3 className="text-sm font-medium">{d.scenarios[k].name}</h3>
              <TradeoffChart d={d} sc={k} />
            </div>
          ))}
        </div>
        <Note>{p.tradeoff_note as string}</Note>
      </Section>

      <Section title="S3: comfort when the planner's room model is wrong" classes={["modeled", "assumption"]}>
        <Table
          head={["Planner", "Model error (heat loss and capacity)", "Comfort margin (K)", "Online correction", "Bill saved (%)", "Hours too cold (K·h)"]}
          rows={d.model_error_s3.map((m) => [
            <span key={m.label} className="block max-w-[26rem] text-left">{m.label}</span>,
            m.rc_perturb === 1 ? "none" : `x${fmt(m.rc_perturb, 2)}`, fmt(m.rc_margin, 1), m.rc_correct ? "yes" : "no", signed(m.saving_pct, 2), fmt(m.comfort_kh, 0),
          ])}
          minWidth={820}
        />
        <Note>{p.model_error_note as string}</Note>
      </Section>

      <Section title="Details" >
        <Fold title="Reinforcement-learning learning curves" classes={["modeled"]}>
          <p className="text-xs text-muted-foreground">Scenario shown: {s.name} (use the tabs above). Central and per-building SAC; MARLISA was evaluated at the end only.</p>
          <CurvesChart d={d} sc={sc} />
          <Note>{p.curves_note as string}</Note>
        </Fold>
        <Fold title="Stochastic planner: a negative result" classes={["modeled"]}>
          <Note>{p.stochastic_note as string}</Note>
          <Table
            head={["Variant", "Error scenarios", "Shared steps", "Errors scaled by", "Bill saved (%)", "Highest hour (kW)"]}
            rows={[...d.stochastic].sort((a, b) => b.saving_pct - a.saving_pct).map((r) => [<span key={r.label} className="block max-w-[24rem] text-left">{r.label}</span>, String(r.scenarios), String(r.share), fmt(r.err_scale, 2), signed(r.saving_pct, 2), fmt(r.peak_kw, 0)])}
            minWidth={760}
          />
          <p className="text-xs text-muted-foreground">Single-forecast planner with the same horizon: {signed(d.deterministic_reference.saving_pct, 2)} % saved, highest hour {fmt(d.deterministic_reference.peak_kw, 0)} kW.</p>
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

      <Note>Sources: {d.sources.join(", ")}. Every number is read from committed result files at build time. Savings are changes of the bill on the eight test weeks; the exact optimum is a perfect-foresight upper reference, not a controller.</Note>
    </div>
  );
}
