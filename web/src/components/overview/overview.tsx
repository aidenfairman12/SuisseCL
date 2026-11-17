"use client";
import { useState } from "react";
import { DEFAULT_CONTROLLER, DistrictView } from "@/components/district/district-view";
import { useBundleFile } from "@/lib/bundle";
import type { Figures } from "@/lib/types";
import { FlowDiagram } from "./flow-diagram";
import { Headline } from "./headline";
import { TrustStrip } from "./trust-strip";

export function Overview() {
  const [controller, setController] = useState(DEFAULT_CONTROLLER);
  const fig = useBundleFile<Figures>("figures").data;
  const bs = fig?.district.buildings ?? [];
  const sfh = bs.filter((b) => b.type === "SFH"), mfh = bs.filter((b) => b.type === "MFH");
  const src = (a: typeof bs) => [...new Set(a.map((b) => b.source))].join(" / ");
  return (
    <div className="space-y-8">
      <div className="max-w-3xl space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">The simulated district</h1>
        <p className="text-muted-foreground">
          {fig ? `A simulation of a ${bs.length}-building Swiss district for 2023: ${sfh.length} single-family houses (${src(sfh)}) and ${mfh.length} apartment buildings (${src(mfh)}), each with an air-source heat pump and storage tanks. ` : "Loading… "}
          Move the slider to watch one hour at a time, or switch controller to see how it charges and discharges the tanks. Every part is labelled measured, derived, modeled or synthetic, and every item opens an audit card showing where it comes from.
        </p>
      </div>
      <DistrictView controller={controller} onController={setController} />
      <Headline controller={controller} />
      <TrustStrip />
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">How it fits together <span className="text-sm font-normal text-muted-foreground">click any box; colours show the classification</span></h2>
        <FlowDiagram />
      </section>
    </div>
  );
}
