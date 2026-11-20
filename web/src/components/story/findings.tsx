"use client";
import Link from "next/link";
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { ArrowRight } from "lucide-react";
import { Chart } from "@/components/charts/echarts";
import { fmt, rng, type Landing, type Range } from "./landing-data";

const BLUE = "#2b6cb0", GREY = "#a0aec0", AMBER = "#dd6b20", GREEN = "#2f855a";

function Section({ n, title, lead, children }: { n: number; title: string; lead: string; children: React.ReactNode }) {
  return (
    <section className="space-y-5">
      <div className="space-y-2">
        <div className="text-xs font-medium uppercase tracking-wide text-sky-700">Finding {n}</div>
        <h2 className="max-w-4xl text-2xl font-semibold leading-snug tracking-tight">{title}</h2>
        <p className="max-w-3xl text-base leading-relaxed text-muted-foreground">{lead}</p>
      </div>
      {children}
    </section>
  );
}
const Loading = () => <div className="flex h-64 items-center justify-center rounded-xl border bg-muted/20 text-sm text-muted-foreground">Loading the numbers…</div>;
function Tile({ value, unit, label }: { value: string; unit?: string; label: string }) {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <div className="text-3xl font-semibold tabular-nums">{value}{unit && <span className="ml-1 text-base font-normal text-muted-foreground">{unit}</span>}</div>
      <div className="mt-1 text-sm text-muted-foreground">{label}</div>
    </div>
  );
}
const Caption = ({ children }: { children: React.ReactNode }) => <p className="max-w-3xl text-sm text-muted-foreground">{children}</p>;
const axis = { axisLabel: { fontSize: 12 }, nameTextStyle: { fontSize: 12 } };

/** A floating bar from lo to hi for each category (stacked: transparent base + visible span). */
function rangeOption(cats: string[], ranges: Range[], colours: string[], unit: string, d = 0): EChartsOption {
  return {
    grid: { left: 150, right: 24, top: 12, bottom: 36 }, animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: (p) => { const i = (p as { dataIndex: number }[])[0].dataIndex; return `${cats[i]}: ${rng(ranges[i], d)} ${unit}`; } },
    xAxis: { type: "value", name: unit, nameLocation: "middle", nameGap: 26, min: 0, ...axis },
    yAxis: { type: "category", data: cats, inverse: true, axisLabel: { fontSize: 13 } },
    series: [
      { type: "bar", stack: "r", silent: true, itemStyle: { color: "transparent" }, data: ranges.map((r) => r[0]) },
      { type: "bar", stack: "r", barMaxWidth: 28, data: ranges.map((r, i) => ({ value: Math.max(r[1] - r[0], r[1] * 0.012), itemStyle: { color: colours[i] } })),
        label: { show: true, position: "right", fontSize: 13, formatter: (p) => rng(ranges[p.dataIndex], d) } },
    ] as EChartsOption["series"],
  };
}

export function ClimateFinding({ d }: { d: Landing | null }) {
  const option = useMemo<EChartsOption | null>(() => d && ({
    grid: { left: 70, right: 16, top: 24, bottom: 56 }, animation: false,
    tooltip: { trigger: "axis", valueFormatter: (v) => `${fmt(+(v as number))} kWh` },
    xAxis: { type: "category", data: d.levels.map((l) => l.label), axisLabel: { fontSize: 12, interval: 0 } },
    yAxis: { type: "value", name: "heating electricity, kWh / year", nameTextStyle: { fontSize: 12 }, axisLabel: { fontSize: 12, formatter: (v: number) => fmt(v) } },
    series: [{ type: "bar", barMaxWidth: 64, data: d.levels.map((l, i) => ({ value: Math.round(l.heating), itemStyle: { color: i === 0 ? GREY : AMBER } })), label: { show: true, position: "top", fontSize: 13, formatter: (p: { value: number }) => fmt(p.value) } }],
  } as EChartsOption), [d]);
  return (
    <Section n={1} title={d ? `At +3 °C, heating electricity falls ${fmt(d.heatFallPct, 1)} % while cooling adds only ${rng(d.coolingRange)} kWh a year` : "Heating falls far more than cooling rises"}
      lead="A warmer climate shrinks the biggest load of a heat-pump district, winter heating. Cooling is new load, but it is small in comparison and mostly lands when the sun is up.">
      {!d || !option ? <Loading /> : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Tile value={`${fmt(d.heatNow)} → ${fmt(d.heatWarm)}`} unit="kWh" label={`heating electricity, today's weather to ${d.warmLabel}`} />
            <Tile value={rng(d.coolingRange)} unit="kWh / yr" label="electricity added by cooling at the low, medium and high adoption levels" />
            <Tile value={`${rng(d.pvCoverage)} %`} label="of that cooling electricity is covered directly by solar in the same hour" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-semibold">Heating electricity of the district by climate (no cooling installed)</h3>
            <Chart option={option} height={320} />
            <Caption>Weather is observed 2023 for today and a Swiss climate-scenario version of it for the warmer years. The thermostat is the reference control.</Caption>
          </div>
          <Link href="/houses/" className="inline-flex items-center gap-1.5 rounded-lg border bg-card px-4 py-2 text-sm font-medium shadow-sm hover:border-sky-300">
            See it building by building: heat, cooling and grid per house <ArrowRight className="size-4 text-sky-700" />
          </Link>
        </>
      )}
    </Section>
  );
}

export function FlexibilityFinding({ d }: { d: Landing | null }) {
  const option = useMemo<EChartsOption | null>(() => d && ({
    grid: { left: 190, right: 56, top: 12, bottom: 36 }, animation: false,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => `${(+(v as number)).toFixed(2)} %` },
    xAxis: { type: "value", name: "bill saved by the exact optimum, % per year", nameLocation: "middle", nameGap: 26, min: 0, ...axis },
    yAxis: { type: "category", inverse: true, data: d.ladder.map((r) => `${r.id} · ${r.name}`), axisLabel: { fontSize: 12, width: 175, overflow: "break" } },
    series: [{ type: "bar", barMaxWidth: 30, itemStyle: { color: BLUE }, data: d.ladder.map((r) => r.saving_year_pct), label: { show: true, position: "right", fontSize: 13, formatter: (p: { value: number }) => `${p.value.toFixed(2)} %` } }],
  } as EChartsOption), [d]);
  const [s0, s1, s2, s3] = d?.ladder.map((r) => r.saving_year_pct.toFixed(2)) ?? [];
  return (
    <Section n={2} title={d ? `Flexibility is worth almost nothing today (${s0} % of the bill) and about ${fmt(d.ladder[2].saving_year_pct)} % once solar, a battery and the building itself can shift load` : "What flexibility is worth"}
      lead="The exact optimum (a planner that knows the future perfectly) is the ceiling for any controller. It shows how much of the bill smart operation can ever remove, rung by rung.">
      {!d || !option ? <Loading /> : (
        <>
          <Chart option={option} height={260} />
          <Caption>
            Saving against doing nothing, over the simulated year: {s0} % with today&apos;s setup (S0), then {s1} / {s2} / {s3} % in S1 / S2 / S3. Each rung adds flexible equipment:
            S1 solar panels, S2 a battery, S3 the building&apos;s own thermal mass as heat storage. Details on the <Link href="/scenarios/" className="text-sky-700 hover:underline">Scenarios</Link> page.
          </Caption>
        </>
      )}
    </Section>
  );
}

export function ControlFinding({ d }: { d: Landing | null }) {
  const share = useMemo<EChartsOption | null>(() => d && rangeOption(["PV rule", "Planner (MPC)", "Exact optimum"], [d.ruleShare, d.mpcShare, [100, 100]], [GREY, BLUE, GREEN], "% of the exact optimum's saving"), [d]);
  const peak = useMemo<EChartsOption | null>(() => d && rangeOption(["Thermostat", "Planner, no peak term", "Planner, peak weight 0.1"], [d.peakThermostat, d.peakMpc, d.peakMpcWeighted], [GREY, AMBER, BLUE], "highest district grid draw, kW"), [d]);
  return (
    <Section n={3} title={d ? `A planner (MPC) reaches ${rng(d.mpcShare)} % of the optimum, a simple solar rule ${rng(d.ruleShare)} %, and a peak term keeps the grid peak in check` : "How close control gets to the optimum"}
      lead="Real controllers do not know the future. They plan with weather and demand forecasts, so the question is how much of the ceiling survives and what it does to the grid.">
      {!d || !share || !peak ? <Loading /> : (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-2"><h3 className="text-base font-semibold">Share of the optimum captured</h3><Chart option={share} height={210} /></div>
            <div className="space-y-2"><h3 className="text-base font-semibold">Highest hour of the district</h3><Chart option={peak} height={240} /></div>
          </div>
          <Caption>
            An MPC that only minimises the bill pushes the district peak to about {fmt(d.peakMpc[0], 0)} kW, against {rng(d.peakThermostat)} kW for the thermostat. A small peak weight (0.1) brings it back to {rng(d.peakMpcWeighted)} kW
            at the same or a slightly higher saving ({rng(d.savingMpcWeighted, 1)} % against {rng(d.savingMpc, 1)} %). Ranges span the warming levels and cooling adoption levels. Learning controllers (reinforcement learning) did not beat their reference.
            More on the <Link href="/controllers/" className="text-sky-700 hover:underline">Controllers</Link> page.
          </Caption>
        </>
      )}
    </Section>
  );
}
