"use client";
// Small building blocks shared by the Phase B pages (Scenarios, Controllers); Phase C pages can reuse them.
import type { ReactNode } from "react";
import { ClassBadge } from "@/components/audit/bits";
import { cn } from "@/lib/utils";
import { PALETTE } from "@/lib/palette";

export const fmt = (v: number | null | undefined, d = 1) => (v == null || !Number.isFinite(v) ? "–" : v.toLocaleString("en-CH", { minimumFractionDigits: d, maximumFractionDigits: d }));
export const signed = (v: number | null | undefined, d = 1) => (v == null || !Number.isFinite(v) ? "–" : `${v > 0 ? "+" : ""}${fmt(v, d)}`);

/** Generic categorical colours for the Phase B/C charts, drawn from the site palette. */
export const PB_COLOURS = { s1: PALETTE.grid, s2: PALETTE.battery, s3: PALETTE.solar, grey: PALETTE.muted, red: PALETTE.alert, purple: PALETTE.export, light: PALETTE.soft };

/** A titled block with the classification of what it shows (measured / derived / modeled / synthetic / assumption). */
export function Section({ title, classes, children, id }: { title: string; classes?: string[]; children: ReactNode; id?: string }) {
  return (
    <section id={id} className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {classes?.map((c) => <ClassBadge key={c} cls={c} />)}
      </div>
      {children}
    </section>
  );
}

export function Lead({ children }: { children: ReactNode }) {
  return <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">{children}</p>;
}

export function Note({ children, tone = "muted" }: { children: ReactNode; tone?: "muted" | "warn" }) {
  return <p className={cn("max-w-3xl text-xs leading-relaxed", tone === "warn" ? "rounded-r-lg border-l-2 border-zinc-400 bg-zinc-50 px-3 py-2.5 text-zinc-700" : "text-muted-foreground")}>{children}</p>;
}

export function Table({ head, rows, className, minWidth = 640 }: { head: ReactNode[]; rows: ReactNode[][]; className?: string; minWidth?: number }) {
  return (
    <div className={cn("overflow-x-auto rounded-xl border", className)}>
      <table className="w-full text-sm" style={{ minWidth }}>
        <thead className="bg-muted/40 text-left text-xs">
          <tr>{head.map((h, i) => <th key={i} className={cn("p-2.5 font-medium", i > 0 && "text-right")}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t">{r.map((c, j) => <td key={j} className={cn("p-2.5 align-top", j > 0 && "text-right tabular-nums")}>{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Native collapsible: closed by default, keyboard accessible. */
export function Fold({ title, children, classes }: { title: string; children: ReactNode; classes?: string[] }) {
  return (
    <details className="group rounded-xl border bg-card">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 p-3 text-sm font-medium marker:hidden">
        <span className="inline-block w-3 text-muted-foreground transition-transform group-open:rotate-90">›</span>
        {title}
        {classes?.map((c) => <ClassBadge key={c} cls={c} />)}
      </summary>
      <div className="space-y-3 border-t p-3">{children}</div>
    </details>
  );
}

export function Loading({ what }: { what: string }) {
  return <p className="text-sm text-muted-foreground">Loading {what}…</p>;
}
