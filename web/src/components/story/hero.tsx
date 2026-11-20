"use client";
const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];

export function Hero({ buildings }: { buildings: number | null }) {
  const w = buildings == null ? "a few" : WORDS[buildings] ?? String(buildings);
  const n = w.charAt(0).toUpperCase() + w.slice(1);
  return (
    <section className="space-y-5 pt-2">
      <h1 className="max-w-4xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
        What does a Swiss heat-pump district need from the grid, today and in a warmer climate, and how much can smart operation save?
      </h1>
      <p className="max-w-3xl text-lg leading-relaxed text-muted-foreground">
        {n} buildings (houses and apartment blocks) heated by heat pumps with hot-water tanks, on Swiss weather, a Swiss time-of-use tariff and measured household heat-pump data.
        Later steps add solar panels, a battery and cooling. Below, a live two-day view of the simulated district: drag the slider or press play.
      </p>
    </section>
  );
}
