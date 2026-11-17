"use client";
import { useMemo } from "react";
import { NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";

/** Data sources the dashboard actually shows, with each licence/attribution text exactly as recorded in the registry. */
export function SiteFooter() {
  const { nodes, meta } = useBundle();
  const sources = useMemo(() => {
    const used = new Set<string>();
    for (const n of Object.values(nodes)) {
      if (!n.ui) continue;
      for (const id of [...n.lineage, ...n.edges.filter((e) => e.rel === "shows").map((e) => e.to)]) if (id.startsWith("SRC-") && nodes[id]) used.add(id);
    }
    return [...used].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).map((id) => nodes[id]);
  }, [nodes]);
  if (!sources.length) return null;
  return (
    <footer className="border-t bg-muted/20">
      <div className="mx-auto max-w-[1400px] space-y-3 px-4 py-6 text-xs text-muted-foreground">
        <h2 className="text-sm font-semibold text-foreground">Data sources and licences</h2>
        <ul className="grid gap-x-8 gap-y-2 md:grid-cols-2">
          {sources.map((s) => (
            <li key={s.id}>
              <NodeLink id={s.id} /> <span className="text-foreground">{String(s.fields.name)}</span> — {String(s.fields.publisher)}.{" "}
              <span>Licence: {String(s.fields.licence)}.</span>
            </li>
          ))}
        </ul>
        <p>
          Shown as recorded in this project’s data-source registry (<code>docs/data/data_source_registry.csv</code>); open an ID for the full entry.
          Series marked modeled, derived or synthetic were produced by this project from these sources.
          {meta ? <> Build <code>{meta.git.commit}</code>.</> : null}
        </p>
      </div>
    </footer>
  );
}
