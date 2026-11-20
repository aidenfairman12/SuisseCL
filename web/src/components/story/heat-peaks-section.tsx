"use client";
import Link from "next/link";
import { HeatPeakSummary, HeatPeakTable, LoadDurationChart, useHeatPeaks } from "./heat-peaks";

/** Short subsection right after Finding 1: load-duration curves and the per-building peak table. */
export function HeatPeakSection() {
  const d = useHeatPeaks();
  return (
    <section className="space-y-4">
      <h3 className="max-w-4xl text-xl font-semibold leading-snug tracking-tight">Warming lowers the yearly heat peak much less than the yearly heat</h3>
      {!d ? <div className="flex h-64 items-center justify-center rounded-xl border bg-muted/20 text-sm text-muted-foreground">Loading the numbers…</div> : (
        <>
          <p className="max-w-3xl text-base leading-relaxed text-muted-foreground"><HeatPeakSummary d={d} /></p>
          <div className="space-y-2">
            <h4 className="text-base font-semibold">Load-duration curve of the district&apos;s heating electricity</h4>
            <LoadDurationChart d={d} />
          </div>
          <HeatPeakTable d={d} />
          <p className="max-w-3xl text-sm text-muted-foreground">
            Modeled values for the thermostat reference: a composite district, an RC building model and synthetic heat timing. The district peak is the highest hour of all six buildings together, not the sum of their own peaks.
            Per-building curves are on the <Link href="/houses/" className="text-sky-700 hover:underline">Houses</Link> page.
          </p>
        </>
      )}
    </section>
  );
}
