"use client";
import { useState } from "react";
import { DEFAULT_CONTROLLER, DistrictView } from "@/components/district/district-view";
import { Hero } from "./hero";
import { ClimateFinding, ControlFinding, FlexibilityFinding } from "./findings";
import { DeepDive, How, Trust } from "./sections";
import { useLanding } from "./landing-data";
import { HeatPeakSection } from "./heat-peaks-section";

export function StoryPage() {
  const [controller, setController] = useState(DEFAULT_CONTROLLER);
  const d = useLanding();
  return (
    <div className="space-y-16">
      <Hero buildings={d?.buildings ?? null} />
      <section aria-label="Live district view" className="-mt-8">
        <DistrictView controller={controller} onController={setController} variant="sample" />
      </section>
      <ClimateFinding d={d} />
      <HeatPeakSection />
      <FlexibilityFinding d={d} />
      <ControlFinding d={d} />
      <How />
      <Trust />
      <DeepDive />
    </div>
  );
}
