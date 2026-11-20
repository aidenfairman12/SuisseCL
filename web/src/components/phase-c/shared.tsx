"use client";
// Helpers shared by the Phase C pages: archetype selector (built from the archetypes present in the data), scenario labels and the colour scale of the heat maps.
import { useState, type ReactNode } from "react";
import type { PcArchetype } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Archetype state: shown as a selector only when the data hold more than one archetype. */
export function useArchetype(list: PcArchetype[]) {
  const [sel, setSel] = useState<string | null>(null);
  const current = sel && list.some((a) => a.id === sel) ? sel : list[0]?.id ?? "central";
  return { current, setSel };
}

/** One labelled row of choices: the label (and an optional one-line hint) in a fixed column on wide screens, above the buttons on phones. */
export function ChoiceRow({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5 sm:grid-cols-[10rem_1fr] sm:items-start" role="group" aria-label={label}>
      <div className="pt-1 text-xs font-medium leading-tight">
        {label}
        {hint && <div className="mt-0.5 font-normal text-muted-foreground">{hint}</div>}
      </div>
      <div className="flex flex-wrap items-center gap-1.5">{children}</div>
    </div>
  );
}

const pill = (active: boolean, disabled?: boolean) =>
  cn("rounded-md border px-2.5 py-1 text-xs transition-colors", disabled ? "cursor-not-allowed border-dashed text-muted-foreground/60" : "hover:bg-muted", active && "bg-muted font-medium");

export function ArchetypeSelector({ list, current, onChange }: { list: PcArchetype[]; current: string; onChange: (id: string) => void }) {
  const label = list.find((a) => a.id === current)?.label ?? current;
  if (list.length <= 1) return <p className="text-xs text-muted-foreground">Cooling system: {label}.</p>;
  return (
    <ChoiceRow label="Cooling system" hint="how the cooled buildings are cooled">
      {list.map((a) => (
        <button key={a.id} type="button" onClick={() => onChange(a.id)} aria-pressed={a.id === current} className={pill(a.id === current)}>{a.label}</button>
      ))}
    </ChoiceRow>
  );
}

export type PillOption<T extends string> = { id: T; label: string; disabled?: boolean; title?: string };

export function Pills<T extends string>({ value, options, onChange, label, hint }: { value: T; options: PillOption<T>[]; onChange: (v: T) => void; label: string; hint?: string }) {
  return (
    <ChoiceRow label={label} hint={hint}>
      {options.map((o) => (
        <button key={o.id} type="button" disabled={o.disabled} title={o.title} onClick={() => onChange(o.id)} aria-pressed={o.id === value} className={pill(o.id === value, o.disabled)}>{o.label}</button>
      ))}
    </ChoiceRow>
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

/** Key of a cell in the hourly and house data: the archetype prefix for room units; the cells without cooling are the same district in every archetype and carry the plain key. */
export const cellKey = (archetype: string, scenario: string, adoption: string) =>
  archetype === "central" || adoption === "none" ? cellId(scenario, adoption) : `${archetype}__${cellId(scenario, adoption)}`;
