"use client";
// Glossary terms: dotted underline plus a one-sentence tooltip (single source: _glossary in ui_map.yaml).
import Link from "next/link";
import { Fragment, type ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useBundle } from "@/lib/bundle";

export function Term({ id, children }: { id: string; children?: ReactNode }) {
  const { story } = useBundle();
  const g = story?.glossary.find((x) => x.id === id);
  if (!g) return <>{children ?? id}</>;
  return (
    <Tooltip>
      <TooltipTrigger render={<span tabIndex={0} />} className="cursor-help underline decoration-dotted decoration-muted-foreground underline-offset-4">
        {children ?? g.term}
      </TooltipTrigger>
      <TooltipContent className="max-w-sm flex-col items-start">
        <span className="font-semibold">{g.term}</span>
        <span>{g.definition}</span>
        <Link href={`/glossary/#${g.id}`} className="underline">All terms</Link>
      </TooltipContent>
    </Tooltip>
  );
}

const TERM_RE = /\[\[([^\]|]+)\|([a-z0-9_]+)\]\]/g;

/** Plain text with [[words|term_id]] markup turned into glossary terms. */
export function Rich({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(TERM_RE)) {
    const i = m.index ?? 0;
    parts.push(text.slice(last, i), <Term key={i} id={m[2]}>{m[1]}</Term>);
    last = i + m[0].length;
  }
  parts.push(text.slice(last));
  return <>{parts.map((p, i) => <Fragment key={i}>{p}</Fragment>)}</>;
}
