"use client";
// Small building blocks shared by the Phase B pages (Scenarios, Controllers); Phase C pages can reuse them.
import type { ReactNode } from "react";
import { ClassBadge } from "@/components/audit/bits";
import { cn } from "@/lib/utils";

export const fmt = (v: number | null | undefined, d = 1) => (v == null || !Number.isFinite(v) ? "–" : v.toLocaleString("en-CH", { minimumFractionDigits: d, maximumFractionDigits: d }));
export const signed = (v: number | null | undefined, d = 1) => (v == null || !Number.isFinite(v) ? "–" : `${v > 0 ? "+" : ""}${fmt(v, d)}`);

export const PB_COLOURS = { s1: "#2b6cb0", s2: "#2f855a", s3: "#b7791f", grey: "#718096", red: "#c53030", purple: "#6b46c1", light: "#a0aec0" };

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
  return <p className={cn("max-w-3xl text-xs leading-relaxed", tone === "warn" ? "rounded-lg border border-amber-200 bg-amber-50/60 p-3 text-amber-950" : "text-muted-foreground")}>{children}</p>;
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
