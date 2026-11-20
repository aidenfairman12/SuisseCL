"use client";
import Link from "next/link";
import { ArrowDown, ArrowRight } from "lucide-react";
import { useBundleFile } from "@/lib/bundle";

type Dataset = { id: string; name: string; publisher: string; licence: string; kind: "source" | "derived" };
type Stage = { id: string; title: string; text: string; datasets: Dataset[] };
type Pipeline = { stages: Stage[] };
const short = (s: string, n = 90) => (s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s);

export function MethodsPage() {
  const p = useBundleFile<Pipeline>("pipeline").data;
  return (
    <div className="space-y-12">
      <header className="max-w-3xl space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">How it was built</p>
        <h1 className="text-3xl font-semibold tracking-tight">Data &amp; methods</h1>
        <p className="text-base leading-relaxed text-zinc-600">Where the numbers come from, how they are turned into a simulation, and how the project was built.</p>
      </header>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">From raw data to the dashboard</h2>
        {!p ? <div className="h-40 rounded-xl border bg-muted/20" /> : (
          <>
            <ol className="grid items-stretch gap-2 md:grid-cols-6" aria-label="Pipeline">
              {p.stages.map((s, i) => (
                <li key={s.id} className="flex flex-col items-stretch gap-2 md:flex-row md:items-center">
                  <div className="flex-1 rounded-xl border bg-card p-3 shadow-sm">
                    <div className="text-xs font-medium text-zinc-500">Step {i + 1}</div>
                    <div className="font-medium leading-snug">{s.title}</div>
                    <p className="mt-1 text-xs text-muted-foreground">{s.text}</p>
                  </div>
                  {i < p.stages.length - 1 && <><ArrowRight className="hidden size-4 shrink-0 text-muted-foreground md:block" /><ArrowDown className="mx-auto size-4 text-muted-foreground md:hidden" /></>}
                </li>
              ))}
            </ol>
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="bg-muted/40 text-left text-xs"><tr>{["Step", "Dataset", "Source or origin", "Licence"].map((h) => <th key={h} className="p-2.5 font-medium">{h}</th>)}</tr></thead>
                <tbody>
                  {p.stages.flatMap((s) => s.datasets.map((d, j) => (
                    <tr key={d.id} className="border-t align-top">
                      <td className="p-2.5 text-muted-foreground">{j === 0 ? s.title : ""}</td>
                      <td className="p-2.5">{short(d.name)}</td>
                      <td className="p-2.5">{d.kind === "source" ? d.publisher : "derived in this project"}</td>
                      <td className="p-2.5">{short(d.licence, 60)}</td>
                    </tr>
                  )))}
                </tbody>
              </table>
            </div>
            <p className="max-w-3xl text-sm text-muted-foreground">Names and licences are copied from the project&apos;s source registry. The full list, with versions, checksums and access dates, is on the <Link href="/audit/" className="text-blue-700 hover:underline">Audit</Link> page.</p>
          </>
        )}
      </section>

      <section className="max-w-3xl space-y-2">
        <h2 className="text-xl font-semibold tracking-tight">Built with AI agents, under a decision log</h2>
        <p className="leading-relaxed">
          The project was built with Claude Code agents. Every choice went into a decision log, with separate registers for assumptions and open issues; simulations are replayed to check that results reproduce exactly;
          a lint guards the dashboard against numbers that do not trace back to a generated file; work moved through phase gates that the owner approved; and the owner approved every commit.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold tracking-tight">Go deeper</h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[["/model/", "Model", "devices, assumptions and control"], ["/inputs/", "Inputs", "weather, price, carbon and demand"], ["/scenarios/", "Scenarios", "solar, battery, building and price assumptions"], ["/audit/", "Audit", "registry, validation and open issues"]].map(([h, l, t]) => (
            <li key={h}><Link href={h} className="block rounded-xl border p-4 hover:border-blue-300"><div className="font-medium text-blue-700">{l}</div><div className="text-sm text-muted-foreground">{t}</div></Link></li>
          ))}
        </ul>
      </section>
    </div>
  );
}
