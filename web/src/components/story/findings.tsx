"use client";
import { Rich } from "@/components/audit/term";
import { fmtKpi } from "@/components/results/results-utils";
import { useBundle } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";
import { cn } from "@/lib/utils";
import { DayChart } from "./day-chart";

export function Findings() {
  const { story } = useBundle();
  const { open } = useNodeParam();
  if (!story) return null;
  const f = story.story.findings;
  return (
    <section className="space-y-5">
      <h2 className="text-2xl font-semibold tracking-tight">{f.title}</h2>
      <div className="max-w-3xl space-y-2 rounded-xl border-l-4 border-sky-500 bg-sky-50 p-4 text-[17px] leading-relaxed">
        <p><Rich text={f.verdict} /></p>
        <p className="text-base text-muted-foreground">{f.rules_line}</p>
      </div>
      <div className="space-y-2">
        <h3 className="text-base font-semibold">{f.chart_title}</h3>
        <DayChart />
        <p className="max-w-3xl text-sm text-muted-foreground">{f.chart_caption}</p>
      </div>
      <div className="space-y-2">
        <div className="grid gap-3 sm:grid-cols-3">
          {f.tiles.map((t) => {
            const col = t.node.replace("kpi:", "");
            return (
              <button key={t.node} onClick={() => open(t.node)} className="rounded-xl border bg-card p-4 text-left shadow-sm transition hover:border-sky-300 hover:shadow">
                <div className="text-sm text-muted-foreground">{t.label}</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums">{fmtKpi(t.value, col)} <span className="text-sm font-normal text-muted-foreground">{t.unit}</span></div>
                <div className={cn("mt-1 text-sm font-medium", t.vs_none_pct < 0 ? "text-emerald-700" : "text-red-600")}>{t.vs_none_pct >= 0 ? "+" : ""}{t.vs_none_pct.toFixed(1)} % vs no control</div>
                <div className="text-xs text-muted-foreground">no control: {fmtKpi(t.reference, col)} {t.unit}</div>
              </button>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground">{f.tiles_caption}</p>
      </div>
      <p className="max-w-3xl text-lg font-medium leading-relaxed">{f.closing}</p>
    </section>
  );
}
