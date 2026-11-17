"use client";
import { useMemo, useState } from "react";
import { TimeChart, type Panel } from "@/components/charts/time-chart";
import { useSi } from "@/components/charts/figures-inputs";
import { WD, fmt, timestamps } from "@/components/charts/util";
import { NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";
import { DRILL, REF, drillHours, useTrace, type ResultsFull } from "./results-utils";

const ROLES = ["SFH-low", "SFH-mid", "SFH-high", "MFH-small", "MFH-medium", "MFH-large"];

export function HourlyView({ res, controller }: { res: ResultsFull; controller: string }) {
  const { nodes } = useBundle();
  const si = useSi();
  const T = useTrace(res, controller), T0 = useTrace(res, REF);
  const [building, setBuilding] = useState(1);
  const [kpi, setKpi] = useState("district_peak_kw");
  const [hour, setHour] = useState<number | null>(null);
  const highlight = useMemo(() => (T ? drillHours(T, kpi) : []), [T, kpi]);
  const panels = useMemo<Panel[]>(() => {
    if (!T || !T0) return [];
    const w: Record<string, number> = {};
    for (const t of ((nodes["R-001"]?.fields.terms as unknown as Record<string, string>[]) ?? [])) w[t.Term] = parseFloat(t["Default weight"]);
    const term = (k: string) => T[`term_${k}`].map((v) => (v == null ? null : (-w[k] * v) / res.reward_scales[k]));
    return [
      { title: `District net electricity — ${controller}${controller === REF ? "" : ` vs ${REF}`}`, unit: "kWh per hour", series: [...(controller === REF ? [] : [{ name: `${REF} (no control)`, values: T0.district_net_kwh, cls: "", color: "#a0aec0" }]), { name: controller, values: T.district_net_kwh, cls: "", color: "#2b6cb0" }] },
      { title: `Tank state of charge — ${ROLES[building - 1]}, ${controller} (SYNTHETIC tanks, D-017a)`, unit: "0–1", series: [{ name: "heating tank", values: T[`b${building}_heating_storage_soc`], cls: "", color: "#e8590c" }, { name: "hot-water tank", values: T[`b${building}_dhw_storage_soc`], cls: "", color: "#1098ad" }] },
      { title: `Reward R-001 terms — ${controller} (−weight × term ÷ scale per step)`, unit: "reward", series: ["cost", "peak", "ramp", "carbon"].filter((k) => w[k]).map((k) => ({ name: `${k} (weight ${w[k]})`, values: term(k), cls: "", color: ({ cost: "#2b6cb0", peak: "#c53030", ramp: "#dd6b20", carbon: "#b7791f" } as Record<string, string>)[k] })) },
    ];
  }, [T, T0, controller, building, res.reward_scales, nodes]);
  if (!si) return null;
  const ts = timestamps(si).slice(0, T?.district_net_kwh.length ?? si.n);
  const drillable = res.columns.filter((c) => DRILL[c]);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <label>Highlight the hours that drive <select value={kpi} onChange={(e) => setKpi(e.target.value)} className="ml-1 h-8 rounded-lg border bg-background px-2 text-sm">{drillable.map((c) => <option key={c} value={c}>{(nodes[`kpi:${c}`]?.title ?? c).replace(" (R-001)", "")}</option>)}</select></label>
        <span className="text-xs text-muted-foreground">gold = {DRILL[kpi]?.label} for {controller} ({highlight.length} h)</span>
        <label>Tank of <select value={building} onChange={(e) => setBuilding(+e.target.value)} className="ml-1 h-8 rounded-lg border bg-background px-2 text-sm">{ROLES.map((r, i) => <option key={r} value={i + 1}>{r}</option>)}</select></label>
      </div>
      {T && T0 ? <TimeChart panels={panels} ts={ts} overlay={false} colours={{}} highlight={highlight} onHour={setHour} /> : <p className="py-8 text-sm text-muted-foreground">Loading the run trace…</p>}
      {T && hour != null && hour < T.district_net_kwh.length && (
        <div className="space-y-1 rounded-xl border bg-muted/20 p-3 text-sm">
          <div><b>{new Date(ts[hour]).toISOString().slice(0, 16).replace("T", " ")} UTC</b> · {WD[si.weekday[hour]]} · step {hour} · district net <b>{fmt(T.district_net_kwh[hour], 2)} kWh</b>{T0 && controller !== REF ? <> (no control {fmt(T0.district_net_kwh[hour], 2)})</> : null} · reward <b>{fmt(T.reward[hour], 3)}</b> · terms {["cost", "peak", "ramp", "carbon"].map((k) => `${k} ${fmt(T[`term_${k}`][hour], 2)}`).join(", ")} (unscaled; see <NodeLink id="card:reward" />)</div>
          <div className="grid gap-x-6 text-xs md:grid-cols-3">
            {ROLES.map((r, i) => (
              <div key={r}><b>{r}</b> net {fmt(T[`b${i + 1}_net_kwh`][hour], 2)} kWh · SOC {fmt(T[`b${i + 1}_heating_storage_soc`][hour], 2)} / {fmt(T[`b${i + 1}_dhw_storage_soc`][hour], 2)} · action {fmt(T[`b${i + 1}_action_heating_storage`]?.[hour], 3)} / {fmt(T[`b${i + 1}_action_dhw_storage`]?.[hour], 3)}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
