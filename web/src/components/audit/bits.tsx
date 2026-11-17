"use client";
import Link from "next/link";
import { Fragment, type ReactNode } from "react";
import { useBundle } from "@/lib/bundle";
import { nodeHref, useNodeParam } from "@/lib/deeplink";
import { KIND_LABEL } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ClassBadge({ cls, className }: { cls: string | null | undefined; className?: string }) {
  const { colours } = useBundle();
  if (!cls) return null;
  const c = colours[cls] ?? "#4a5568";
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white", className)}
      style={{ background: c }}
    >
      {cls}
    </span>
  );
}

/** Link that opens the audit card for `id` on the current page. */
export function NodeLink({ id, label, title, className }: { id: string; label?: ReactNode; title?: boolean; className?: string }) {
  const { nodes } = useBundle();
  const { pathname } = useNodeParam();
  const n = nodes[id];
  if (!n) return <span className="text-destructive line-through" title="not in any registry">{id}</span>;
  const open = n.kind === "issue" && n.open;
  return (
    <Link
      href={nodeHref(pathname, id)}
      scroll={false}
      title={n.title}
      className={cn("font-mono text-[12.5px] text-sky-700 hover:underline", open && "font-bold text-red-600", className)}
    >
      {label ?? (n.ui ? n.display_name || n.title : id)}
      {title && <span className="ml-1 font-sans text-xs font-normal text-foreground/80">{short(n.title, 90)}</span>}
    </Link>
  );
}

const ID_RE = /\b((?:SRC|DER|TR|ISS|ALG|EXP|R|M|D|A)-\d{3}[a-z]?|V\d{1,2})\b/g;

/** Text with registry IDs turned into links (only IDs that exist in the bundle). */
export function Linkified({ text }: { text: string }) {
  const { nodes } = useBundle();
  const parts: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(ID_RE)) {
    const i = m.index ?? 0;
    parts.push(text.slice(last, i));
    parts.push(nodes[m[0]] ? <NodeLink key={i} id={m[0]} /> : m[0]);
    last = i + m[0].length;
  }
  parts.push(text.slice(last));
  return (
    <>
      {parts.map((p, i) => (
        <Fragment key={i}>{p}</Fragment>
      ))}
    </>
  );
}

export const short = (s: string, k: number) => (s.length > k ? s.slice(0, k - 1) + "…" : s);
/** Titles are cut at the first sentence/clause; drop the dangling punctuation. */
export const cleanTitle = (s: string) => s.replace(/[;:,\s]+$/, "");
export const kindLabel = (k: string) => KIND_LABEL[k] ?? k;
