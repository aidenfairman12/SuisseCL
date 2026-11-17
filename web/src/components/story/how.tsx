"use client";
import { ArrowRight } from "lucide-react";
import { useBundle } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";

export function How() {
  const { story } = useBundle();
  const { open } = useNodeParam();
  if (!story) return null;
  const h = story.story.how;
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">{h.title}</h2>
      <ol className="grid gap-3 md:grid-cols-4">
        {h.steps.map((s, i) => (
          <li key={s.title} className="relative">
            <button onClick={() => open(s.node)} className="group h-full w-full rounded-xl border bg-card p-4 text-left shadow-sm transition hover:border-sky-300 hover:shadow">
              <div className="mb-2 flex size-7 items-center justify-center rounded-full bg-sky-100 text-sm font-semibold text-sky-800">{i + 1}</div>
              <div className="font-medium">{s.title}</div>
              <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
              <span className="mt-2 inline-flex items-center gap-1 text-xs text-sky-700 opacity-80 group-hover:opacity-100">Where this comes from <ArrowRight className="size-3" /></span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
