"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useBundle, useBundleFile } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";
import type { Results } from "@/lib/types";
import { cn } from "@/lib/utils";

const REF = "ALG-001_zero_action";
// own computations from baselines_2023.csv (lower is better); carbon is Σ import × the MODELED intensity series
const KPIS = ["cost_chf_excl_vat", "district_peak_kw", "district_import_kwh", "term_carbon_sum"] as const;
const SHORT: Record<string, string> = { cost_chf_excl_vat: "Electricity cost", district_peak_kw: "District peak", district_import_kwh: "Grid import", term_carbon_sum: "Carbon (modeled series)" };

const fmt = (v: number) => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString("en-US").replace(/,/g, " ") : v.toFixed(2));

export function Headline({ controller }: { controller: string }) {
  const res = useBundleFile<Results>("results").data;
  const { nodes } = useBundle();
  const { open } = useNodeParam();
  if (!res) return <div className="h-28 rounded-xl border bg-muted/30" />;
  const r = res.rows.find((x) => x.controller === controller), r0 = res.rows.find((x) => x.controller === REF);
  if (!r || !r0) return null;
  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">Headline results <span className="text-sm font-normal text-muted-foreground">full year 2023, <code>{controller}</code> vs no control (ALG-001)</span></h2>
        <Link href="/results/" className="inline-flex items-center gap-1 text-sm text-sky-700 hover:underline">All results <ArrowRight className="size-3.5" /></Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {KPIS.map((col) => {
          const v = r[col] as number, v0 = r0[col] as number;
          const d = v0 ? ((v - v0) / Math.abs(v0)) * 100 : null;
          const same = controller === REF;
          const good = d == null || same || d === 0 ? "" : d < 0 ? "text-emerald-700" : "text-red-600";
          const unit = (nodes[`kpi:${col}`]?.fields?.unit as string | undefined) ?? "";
          return (
            <button key={col} onClick={() => open(`kpi:${col}`)} className="rounded-xl border bg-card p-4 text-left shadow-sm transition hover:border-sky-300 hover:shadow">
              <div className="text-xs text-muted-foreground">{SHORT[col]}</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums">{fmt(v)} <span className="text-xs font-normal text-muted-foreground">{unit}</span></div>
              <div className={cn("mt-1 text-sm", good)}>{same ? "reference (no control)" : d == null ? "" : `${d >= 0 ? "+" : ""}${d.toFixed(2)} % vs no control`}</div>
            </button>
          );
        })}
      </div>
      <p className="text-xs text-muted-foreground">Lower is better. Each tile opens its audit card with the formula, the experiment row and the trace check.</p>
    </section>
  );
}
