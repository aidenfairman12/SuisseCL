"use client";
import Link from "next/link";
import { useBundle } from "@/lib/bundle";

export function Next() {
  const { story } = useBundle();
  if (!story) return null;
  const n = story.story.next;
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">{n.title}</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {n.phases.map((p) => (
          <div key={p.letter} className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Phase {p.letter}</div>
            <div className="mt-0.5 text-lg font-semibold">{p.focus}</div>
            <p className="mt-1 text-sm text-muted-foreground">{p.objective}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{n.source_note}.</p>
      <p className="text-sm">Want the details? <Link href="/results/" className="text-sky-700 hover:underline">Results</Link> · <Link href="/inputs/" className="text-sky-700 hover:underline">Inputs</Link> · <Link href="/model/" className="text-sky-700 hover:underline">Model</Link> · <Link href="/audit/" className="text-sky-700 hover:underline">Sources &amp; audit</Link> · <Link href="/glossary/" className="text-sky-700 hover:underline">Glossary</Link></p>
    </section>
  );
}
