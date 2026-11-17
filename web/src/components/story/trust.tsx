"use client";
import { ArrowRight } from "lucide-react";
import { NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";

const ORDER = ["measured", "derived", "modeled", "synthetic", "assumption", "mixed"];

export function Trust() {
  const { story, nodes, colours } = useBundle();
  const { open } = useNodeParam();
  if (!story) return null;
  const t = story.story.trust;
  const items = Object.values(nodes).filter((n) => n.ui && n.classification && (n.kind === "series" || n.kind === "card") && n.id !== "card:district");
  return (
    <section className="space-y-5">
      <h2 className="text-2xl font-semibold tracking-tight">{t.title}</h2>
      <button onClick={() => open("panel:validation")} className="inline-flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-left text-base shadow-sm hover:border-sky-300">
        <span>{t.validation}</span><ArrowRight className="size-4 shrink-0 text-sky-700" />
      </button>
      <div className="space-y-2">
        <h3 className="text-base font-semibold">{t.classes_title}</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {ORDER.map((cls) => {
            const mine = items.filter((n) => n.classification === cls), c = t.classes[cls];
            if (!mine.length || !c) return null;
            return (
              <div key={cls} className="rounded-xl border p-3">
                <div className="mb-1 flex items-center gap-2"><span className="size-3 rounded-full" style={{ background: colours[cls] }} /><span className="font-medium">{c.label}</span></div>
                <p className="mb-1 text-xs text-muted-foreground">{c.meaning}</p>
                <ul className="space-y-0.5 text-sm">{mine.map((n) => <li key={n.id}><NodeLink id={n.id} label={n.display_name || n.title} className="font-sans text-sm" /></li>)}</ul>
              </div>
            );
          })}
        </div>
      </div>
      <div className="space-y-2">
        <h3 className="text-base font-semibold">{t.limitations_title}</h3>
        <div className="grid gap-3 md:grid-cols-3">
          {t.limitations.map((l) => (
            <button key={l.title} onClick={() => open(l.node)} className="rounded-xl border border-amber-300 bg-amber-50/60 p-4 text-left transition hover:border-amber-500">
              <div className="font-medium text-amber-950">{l.title}</div>
              <p className="mt-1 text-sm text-amber-950/80">{l.text}</p>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
