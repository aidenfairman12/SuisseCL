"use client";
import { useState } from "react";
import { DEFAULT_CONTROLLER, DistrictView } from "@/components/district/district-view";
import { useBundle } from "@/lib/bundle";
import { Findings } from "./findings";
import { Hero } from "./hero";
import { How } from "./how";
import { Next } from "./next";
import { Trust } from "./trust";

export function StoryPage() {
  const [controller, setController] = useState(DEFAULT_CONTROLLER);
  const { story } = useBundle();
  return (
    <div className="space-y-14">
      <Hero />
      <section className="space-y-3">
        <h2 className="text-2xl font-semibold tracking-tight">{story?.story.district.title}</h2>
        <DistrictView controller={controller} onController={setController} />
        <p className="max-w-3xl text-sm text-muted-foreground">{story?.story.district.caption}</p>
      </section>
      <How />
      <Findings />
      <Trust />
      <Next />
    </div>
  );
}
