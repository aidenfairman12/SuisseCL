"use client";
import { Rich } from "@/components/audit/term";
import { useBundle } from "@/lib/bundle";

export function Hero() {
  const { story } = useBundle();
  if (!story) return <div className="h-64" />;
  const h = story.story.hero;
  return (
    <section className="space-y-6 py-4">
      <span className="inline-flex rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground">{h.status}</span>
      <h1 className="max-w-4xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">{h.question}</h1>
      <p className="max-w-3xl text-lg leading-relaxed text-muted-foreground"><Rich text={h.context} /></p>
      <div className="grid gap-3 sm:grid-cols-3">
        {h.tiles.map((t) => (
          <div key={t.label} className="rounded-xl border bg-card p-4 shadow-sm">
            <div className="text-3xl font-semibold tabular-nums">{t.value}</div>
            <div className="mt-1 text-sm text-muted-foreground">{t.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
