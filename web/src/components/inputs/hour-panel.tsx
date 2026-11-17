"use client";
import { ClassBadge, NodeLink } from "@/components/audit/bits";
import { WD, carbonRelative, fmt, useBuildingLabel } from "@/components/charts/util";
import { useBundle } from "@/lib/bundle";
import type { SeriesInputs } from "@/lib/types";

/** Every input for one hour, with classification and flags (the hour you clicked in the chart). */
export function HourPanel({ si, i }: { si: SeriesInputs; i: number }) {
  const { story } = useBundle();
  const label = useBuildingLabel();
  const rel = carbonRelative(si, story, i);
  const local = new Date(Date.parse(si.start_utc) + (i * si.step_s + si.utc_offset_h[i] * 3600) * 1000).toISOString().slice(0, 16).replace("T", " ");
  const utc = new Date(Date.parse(si.start_utc) + i * si.step_s * 1000).toISOString().slice(0, 16).replace("T", " ");
  const flagsFor = (ui: string) => Object.values(si.flags).filter((f) => f.ui === ui && f.values[i]).map((f) => `⚑ ${f.label}`);
  const rows = Object.entries(si.series).filter(([k, s]) => !s.relative_only || k === "carbon").map(([k, s]) => ({ k, label: s.label, v: s.values[i], unit: s.unit, cls: s.classification, ui: s.ui, rel: s.relative_only ? rel : null, flags: flagsFor(s.ui).concat(k === "price" ? [si.tier_high[i] ? "high tariff" : "low tariff"] : []) }));
  return (
    <div className="space-y-2 rounded-xl border bg-muted/20 p-3">
      <div className="text-sm"><b>{utc} UTC</b> · local {local} (UTC+{si.utc_offset_h[i]}) · {WD[si.weekday[i]]} · step {i}</div>
      <div className="grid gap-x-6 gap-y-0.5 text-sm md:grid-cols-2">
        {rows.map((r) => (
          <div key={r.k} className="flex items-baseline gap-2 border-b py-0.5">
            <NodeLink id={r.ui} label={r.label} className="font-sans text-sm" />
            <span className="ml-auto tabular-nums">{r.rel ? <>{r.rel.line} <span className="text-xs text-muted-foreground">({r.rel.sub})</span></> : <>{r.v == null ? <span className="text-amber-700">missing</span> : fmt(r.v, 2)} <span className="text-xs text-muted-foreground">{r.unit}</span></>}</span>
            <ClassBadge cls={r.cls} />
            {r.flags.length > 0 && <span className="text-xs text-amber-700">{r.flags.join(", ")}</span>}
          </div>
        ))}
      </div>
      <details>
        <summary className="cursor-pointer text-xs text-muted-foreground">Building electricity this hour (kWh)</summary>
        <div className="mt-1 grid gap-x-6 text-xs md:grid-cols-3">
          {Object.entries(si.buildings).map(([role, b]) => (
            <div key={role} className="py-0.5"><b>{label(role)}</b>{b.gap_filled_flag[i] ? <span className="text-red-600"> ⚑ gap-filled: synthetic</span> : null}
              {b.components.map((c) => <div key={c.key} className="flex gap-2"><span className="text-muted-foreground">{c.label}</span><span className="ml-auto tabular-nums">{c.values[i] == null ? "missing" : fmt(c.values[i], 3)}</span></div>)}
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
