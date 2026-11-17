"use client";
import { NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";

export function GlossaryPage() {
  const { story } = useBundle();
  if (!story) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const terms = [...story.glossary].sort((a, b) => a.term.localeCompare(b.term));
  return (
    <dl className="max-w-3xl divide-y">
      {terms.map((g) => (
        <div key={g.id} id={g.id} className="scroll-mt-20 py-4">
          <dt className="text-lg font-semibold">{g.term}</dt>
          <dd className="mt-1 text-[15px] leading-relaxed text-muted-foreground">{g.definition}</dd>
          {g.node && <dd className="mt-1 text-sm">See where it is used: <NodeLink id={g.node} className="font-sans text-sm" /></dd>}
        </div>
      ))}
    </dl>
  );
}
