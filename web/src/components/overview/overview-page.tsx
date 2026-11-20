"use client";
import Link from "next/link";
import { SystemFlowDiagram } from "@/components/overview/system-flow-diagram";
import { useManifest } from "@/lib/contract";

const PHASES = [
  { id: "Phase A", title: "Today's district", body: "Grid electricity only: heat pumps, hot-water and space-heating tanks, household loads. Hourly CityLearn simulation.", links: [{ href: "/district/", label: "District" }, { href: "/results/", label: "Results" }] },
  { id: "Phase B", title: "Solar, battery, building mass", body: "Adds assumed rooftop solar with an export price, a home battery, a building thermal model, other tariffs, EV charging and an energy community.", links: [{ href: "/scenarios/", label: "Scenarios" }, { href: "/controllers/", label: "Controllers" }] },
  { id: "Phase C", title: "Warmer climate and cooling", body: "Keeps solar, battery and the building model; adds warmer weather years, a heat-wave week and cooling by reversible heat pumps or room units.", links: [{ href: "/climate/", label: "Climate" }, { href: "/cooling/", label: "Cooling" }, { href: "/explorer/", label: "Explorer" }] },
];

export function OverviewPage() {
  const m = useManifest("full").data;
  return (
    <div className="space-y-8">
      <header className="max-w-4xl space-y-3">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Deep dive · Explore</p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">A district energy system, made inspectable.</h1>
        <p className="max-w-3xl text-base leading-relaxed text-muted-foreground">How weather, prices, heat pumps, thermal storage, rooftop solar, a battery, building mass and cooling combine across six representative Swiss buildings. The project grows in three phases; the map below shows each one.</p>
      </header>
      <div className="grid gap-3 md:grid-cols-3">
        {PHASES.map((p) => (
          <div key={p.id} className="rounded-xl border bg-card p-4">
            <p className="text-xs font-medium text-zinc-500">{p.id}</p>
            <p className="mt-1 font-semibold">{p.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{p.body}</p>
            <p className="mt-2 flex flex-wrap gap-x-3 text-xs">{p.links.map((l) => <Link key={l.href} href={l.href} className="text-blue-700 hover:underline">{l.label} →</Link>)}</p>
          </div>
        ))}
      </div>
      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">How the modeled system fits together</h2>
          <p className="text-sm text-muted-foreground">Pick a phase to see which devices and connections it adds. Select a component for its description, provenance and audit cards. {m && <>Weather and prices are for {m.year}; the district has {m.buildings.length} buildings.</>}</p>
        </div>
        <SystemFlowDiagram />
      </section>
      <div className="rounded-r-lg border-l-2 border-zinc-400 bg-zinc-50 p-4 text-sm text-zinc-700">
        <p className="font-semibold">Important scope boundary</p>
        <p className="mt-1">The six buildings form a representative composite, not a physically adjacent neighbourhood; outside the energy-community scenario they do not share a connection or exchange energy. Solar, battery and EV charging are assumptions, not measured installations, and cooling is modeled. The hourly CityLearn simulation behind the <Link href="/district/" className="underline">District</Link> and <Link href="/results/" className="underline">Results</Link> pages is the Phase A setup; Phase B and C results come from the scenario runs on their own pages.</p>
      </div>
      <p className="text-xs text-muted-foreground">Measured values are not interchangeable with derived, modeled, synthetic or assumed values. Unavailable attributes remain unavailable, not zero.</p>
    </div>
  );
}
