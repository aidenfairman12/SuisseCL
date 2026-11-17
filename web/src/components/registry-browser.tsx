"use client";
import { useMemo, useState } from "react";
import { ClassBadge, NodeLink, cleanTitle, kindLabel, short } from "@/components/audit/bits";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useBundle } from "@/lib/bundle";

const ORDER = ["series", "card", "kpi", "panel", "source", "derived_dataset", "transform", "model", "parameter", "decision", "assumption", "issue", "controller", "reward", "experiment", "validation_check", "qc_report"];

export function RegistryBrowser() {
  const { nodes, meta } = useBundle();
  const [kind, setKind] = useState("issue");
  const [q, setQ] = useState("");
  const [onlyOpen, setOnlyOpen] = useState(true);
  const rows = useMemo(() => {
    const f = q.trim().toLowerCase();
    return Object.values(nodes)
      .filter((n) => n.kind === kind && (!f || `${n.id} ${n.title} ${n.summary ?? ""}`.toLowerCase().includes(f)) && !(kind === "issue" && onlyOpen && !n.open))
      .sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
  }, [nodes, kind, q, onlyOpen]);
  if (!meta) return <p className="text-sm text-muted-foreground">Loading bundle…</p>;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <select value={kind} onChange={(e) => setKind(e.target.value)} className="h-8 rounded-lg border bg-background px-2 text-sm">
          {ORDER.filter((k) => meta.node_counts[k]).map((k) => <option key={k} value={k}>{kindLabel(k)} ({meta.node_counts[k]})</option>)}
        </select>
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="filter" className="h-8 w-64" />
        {kind === "issue" && <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} /> open issues only</label>}
        <span className="text-xs text-muted-foreground">{rows.length} shown</span>
      </div>
      <Table>
        <TableHeader><TableRow><TableHead className="w-40">ID</TableHead><TableHead>Title</TableHead><TableHead className="w-48">Class / status</TableHead></TableRow></TableHeader>
        <TableBody>
          {rows.map((n) => (
            <TableRow key={n.id}>
              <TableCell><NodeLink id={n.id} label={n.id} /></TableCell>
              <TableCell>{short(cleanTitle(n.title), 160)}</TableCell>
              <TableCell>
                <ClassBadge cls={n.classification} />{" "}
                {n.kind === "issue" ? <span className={n.open ? "text-red-600" : "text-muted-foreground"}>{n.open ? "open" : "closed"}</span> : <span className="text-xs text-muted-foreground">{short(n.status ?? "", 40)}</span>}
                {n.parse_warnings.length > 0 && <span className="ml-1 text-xs text-amber-700" title="registry row did not parse cleanly">⚠ row</span>}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
