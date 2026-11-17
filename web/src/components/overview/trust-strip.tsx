"use client";
import { ClassBadge, NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";

// Plain-language meaning of each classification (UI copy; which items fall in which class comes from the data).
const MEANING: Record<string, string> = {
  measured: "recorded by a sensor or meter",
  derived: "calculated from measured data with a stated formula",
  modeled: "produced by a model, not observed",
  synthetic: "constructed for this study, not recorded in these buildings",
  assumption: "a chosen value with no direct data behind it",
  mixed: "contains several of the above",
};
const ORDER = ["measured", "derived", "modeled", "synthetic", "assumption", "mixed"];

export function TrustStrip() {
  const { nodes } = useBundle();
  const items = Object.values(nodes).filter((n) => n.ui && n.classification && (n.kind === "series" || n.kind === "card") && n.id !== "card:district");
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">What is real, and what is not</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ORDER.map((cls) => {
          const mine = items.filter((n) => n.classification === cls);
          if (!mine.length) return null;
          return (
            <div key={cls} className="rounded-xl border p-3">
              <div className="mb-1 flex items-center gap-2"><ClassBadge cls={cls} /><span className="text-xs text-muted-foreground">{MEANING[cls]}</span></div>
              <ul className="space-y-0.5 text-sm">
                {mine.map((n) => <li key={n.id}><NodeLink id={n.id} label={n.title} className="font-sans text-sm" /></li>)}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
