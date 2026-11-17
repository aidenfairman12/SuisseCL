"use client";
import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { useBundle } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";
import { cleanTitle, kindLabel } from "@/components/audit/bits";
import type { NodeT } from "@/lib/types";

const ORDER = ["series", "card", "kpi", "panel", "source", "derived_dataset", "transform", "model", "parameter", "decision", "assumption", "issue", "controller", "reward", "experiment", "validation_check", "qc_report"];

const shortId = (n: NodeT) => (n.ui ? n.id.split(":")[1] : n.id);

/** Exact ID first, then ID prefix, then words in the title, then words in the summary (0 = no match). */
function rank(n: NodeT, q: string): number {
  const id = n.id.toLowerCase(), sid = shortId(n).toLowerCase();
  if (id === q || sid === q) return 1;
  if (id.startsWith(q) || sid.startsWith(q)) return 0.9;
  const words = q.split(/\s+/);
  const title = `${id} ${n.title}`.toLowerCase();
  if (words.every((w) => title.includes(w))) return 0.6;
  return words.every((w) => `${title} ${(n.summary ?? "").toLowerCase()}`.includes(w)) ? 0.3 : 0;
}

export function SearchButton() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { nodes } = useBundle();
  const { open: openNode } = useNodeParam();
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const typing = /input|textarea|select/i.test((e.target as HTMLElement).tagName);
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, []);

  const q = query.trim().toLowerCase();
  const ranked = useMemo(() => {
    if (!q) return [];
    return Object.values(nodes)
      .map((n) => [n, rank(n, q)] as const)
      .filter(([, s]) => s > 0)
      .sort((a, b) => b[1] - a[1] || a[0].id.localeCompare(b[0].id, undefined, { numeric: true }))
      .slice(0, 40)
      .map(([n]) => n);
  }, [nodes, q]);
  const groups = useMemo(() => {
    const g: Record<string, NodeT[]> = {};
    for (const n of Object.values(nodes)) (g[n.kind] ??= []).push(n);
    for (const k of Object.keys(g)) g[k].sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
    return g;
  }, [nodes]);

  const go = (id: string) => {
    setOpen(false);
    setQuery("");
    openNode(id);
  };
  const item = (n: NodeT, withKind: boolean) => (
    <CommandItem key={n.id} value={n.id} onSelect={() => go(n.id)}>
      <code className="mr-2 w-28 shrink-0 text-xs">{shortId(n)}</code>
      <span className="truncate text-sm">{cleanTitle(n.title)}</span>
      {withKind && <span className="ml-auto shrink-0 pl-2 text-[11px] text-muted-foreground">{kindLabel(n.kind)}</span>}
    </CommandItem>
  );

  return (
    <>
      <Button variant="outline" size="sm" className="gap-2 text-muted-foreground" onClick={() => setOpen(true)}>
        <Search className="size-3.5" /> Search IDs and topics <kbd className="rounded border px-1 text-[10px]">⌘K</kbd>
      </Button>
      <CommandDialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setQuery(""); }} title="Search" description="Type an ID such as D-017a, or a word">
        <Command shouldFilter={false}>
          <CommandInput value={query} onValueChange={setQuery} placeholder="D-017a, carbon, tank, ISS-033…" />
          <CommandList>
            {q && ranked.length === 0 && <CommandEmpty>No match.</CommandEmpty>}
            {q
              ? ranked.map((n) => item(n, true))
              : ORDER.filter((k) => groups[k]).map((k) => (
                  <CommandGroup key={k} heading={kindLabel(k)}>
                    {groups[k].map((n) => item(n, false))}
                  </CommandGroup>
                ))}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
