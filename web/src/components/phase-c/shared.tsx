"use client";
// Helpers shared by the Phase C pages: archetype selector (built from the archetypes present in the data), scenario labels and the colour scale of the heat maps.
import { useState } from "react";
import type { PcArchetype } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Archetype state: shown as a selector only when the data hold more than one archetype. */
export function useArchetype(list: PcArchetype[]) {
  const [sel, setSel] = useState<string | null>(null);
  const current = sel && list.some((a) => a.id === sel) ? sel : list[0]?.id ?? "central";
  return { current, setSel };
}

export function ArchetypeSelector({ list, current, onChange }: { list: PcArchetype[]; current: string; onChange: (id: string) => void }) {
  const label = list.find((a) => a.id === current)?.label ?? current;
  if (list.length <= 1) return <p className="text-xs text-muted-foreground">Cooling system archetype: {label}.</p>;
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Cooling system archetype">
      <span className="text-xs text-muted-foreground">Cooling system archetype</span>
      {list.map((a) => (
        <button key={a.id} type="button" onClick={() => onChange(a.id)} aria-pressed={a.id === current}
          className={cn("rounded-md border px-2.5 py-1 text-xs transition-colors hover:bg-muted", a.id === current && "bg-muted font-medium")}>{a.label}</button>
      ))}
    </div>
  );
}

export function Pills<T extends string>({ value, options, onChange, label }: { value: T; options: { id: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" onClick={() => onChange(o.id)} aria-pressed={o.id === value}
          className={cn("rounded-md border px-2.5 py-1 text-xs transition-colors hover:bg-muted", o.id === value && "bg-muted font-medium")}>{o.label}</button>
      ))}
    </div>
  );
}

/** Colour of a heat-map cell: white to green by position of v between lo and hi. */
export function heat(v: number | null | undefined, lo: number, hi: number, reverse = false) {
  if (v == null || !Number.isFinite(v) || hi <= lo) return "transparent";
  let t = (v - lo) / (hi - lo);
  t = Math.max(0, Math.min(1, reverse ? 1 - t : t));
  return `rgba(47,133,90,${(0.08 + 0.55 * t).toFixed(2)})`;
}

export const weekDay = (startStep: number, hour: number) => {
  const d = new Date(Date.UTC(2023, 0, 1) + (startStep + hour) * 3600_000);
  const wd = d.toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" });
  const dm = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  return `${wd}\n${dm}`;                                     // two short lines so that seven labels fit on a phone
};

/** Splits a "<scenario>_<adoption>" id as in the data. */
export const cellId = (scenario: string, adoption: string) => `${scenario}_${adoption}`;
