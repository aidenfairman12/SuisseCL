"use client";
import Link from "next/link";
import { DEEP_DIVE } from "@/lib/nav";
import { useBundleFile } from "@/lib/bundle";
import { fmt } from "./landing-data";

const STEPS = [
  { title: "Real data", text: "Hourly electricity of heat pumps and households recorded in homes around Zurich, plus Swiss weather, prices and climate scenarios." },
  { title: "A physical model", text: "Heat demand is calculated from heat-pump electricity and outdoor temperature, then run through heat pumps, tanks, solar, a battery and building thermal mass in CityLearn." },
  { title: "Controllers", text: "A thermostat, simple rules, a planner (MPC) and learning controllers are all compared against the exact optimum on the same weeks." },
  { title: "Checks", text: "Every number carries its provenance, runs are replayed exactly, and a data contract and lint keep the dashboard in step with the results." },
];

export function How() {
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">How it was built</h2>
      <ol className="grid gap-3 md:grid-cols-4">
        {STEPS.map((s, i) => (
          <li key={s.title} className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="mb-2 flex size-7 items-center justify-center rounded-full bg-zinc-900 text-sm font-semibold text-white">{i + 1}</div>
            <div className="font-medium">{s.title}</div>
            <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
          </li>
        ))}
      </ol>
      <p className="max-w-3xl text-sm text-muted-foreground">Built with Claude Code agents under a documented decision log, with assumption and issue registers, replay-exact validation, dashboard lint guards and owner-approved phase gates and commits. More on <Link href="/methods/" className="text-blue-700 hover:underline">Data &amp; methods</Link>.</p>
    </section>
  );
}

const LIMITS = [
  { title: "A composite district", text: "The buildings are a composite of separate homes, not neighbours on one street. That is why there is no map." },
  { title: "Synthetic storage", text: "No home has a documented tank or battery. Their sizes follow a stated sizing rule, and storage results depend on those assumptions." },
  { title: "Modeled cooling", text: "Cooling is a model: the cooling device is the heat pump run in reverse, and several of its parameters have no source." },
  { title: "Synthetic household load", text: "The non-heating household load is constructed, and it is the forecast that limits what a planner can do." },
];

export function Trust() {
  const cap = useBundleFile<{ capacity_check?: { sfh_low_model_over_real: number } }>("heat_peaks").data?.capacity_check;
  const limits = cap ? [...LIMITS, { title: "Heat-pump capacity", text: `The model's heat pumps can deliver about ${fmt(cap.sfh_low_model_over_real, 1)} times the rated heat of the one installed unit we could check (a HEAPO site visit), so the savings may be somewhat optimistic.` }] : LIMITS;
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">How far to trust it</h2>
      <p className="max-w-3xl text-base text-muted-foreground">Read the results as a controlled experiment on a realistic district, not as a forecast for a real one. These limits matter most.</p>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {limits.map((l) => (
          <div key={l.title} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="font-medium text-zinc-900">{l.title}</div>
            <p className="mt-1 text-sm text-zinc-600">{l.text}</p>
          </div>
        ))}
      </div>
      <p className="text-sm">Sources, assumptions and validation: <Link href="/methods/" className="text-blue-700 hover:underline">Data &amp; methods</Link> · <Link href="/audit/" className="text-blue-700 hover:underline">Audit</Link></p>
    </section>
  );
}

export function DeepDive() {
  return (
    <section className="space-y-4" id="deep-dive">
      <h2 className="text-2xl font-semibold tracking-tight">Deep dive</h2>
      <div className="rounded-xl border border-dashed bg-muted/20 p-4">
        <div className="font-medium">Technical summary <span className="text-sm font-normal text-muted-foreground">(coming soon)</span></div>
        <p className="text-sm text-muted-foreground">A two-page write-up of the method, the three findings, the limits and how to reproduce them.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {DEEP_DIVE.map((g) => (
          <div key={g.group} className="rounded-xl border p-4">
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{g.group}</div>
            <ul className="space-y-2">
              {g.items.map((p) => (
                <li key={p.href}><Link href={p.href} className="font-medium text-blue-700 hover:underline">{p.label}</Link><div className="text-sm text-muted-foreground">{p.hint}</div></li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
