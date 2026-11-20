"use client";
import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Linkified, NodeLink, cleanTitle, short } from "@/components/audit/bits";
import { RegistryBrowser } from "@/components/registry-browser";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useBundle } from "@/lib/bundle";
import { cn } from "@/lib/utils";

const byId = (a: { id: string }, b: { id: string }) => a.id.localeCompare(b.id, undefined, { numeric: true });

function Validation() {
  const { nodes } = useBundle();
  const vs = Object.values(nodes).filter((n) => n.kind === "validation_check").sort(byId);
  return (
    <div className="space-y-2">
      <p className="max-w-3xl text-sm text-muted-foreground">Internal-consistency and plausibility checks, not calibration against observations. Each row opens its card with the numbers from validation_phase_a.json.</p>
      <Table>
        <TableHeader><TableRow><TableHead className="w-16">ID</TableHead><TableHead>Check</TableHead><TableHead>Result</TableHead><TableHead className="w-48">Status</TableHead></TableRow></TableHeader>
        <TableBody>
          {vs.map((n) => (
            <TableRow key={n.id} className="align-top">
              <TableCell><NodeLink id={n.id} label={n.id} /></TableCell>
              <TableCell className="whitespace-normal">{String(n.fields.Check)}</TableCell>
              <TableCell className="whitespace-normal text-xs"><Linkified text={String(n.fields.Result)} /></TableCell>
              <TableCell className={cn("whitespace-normal text-xs font-medium", n.passed ? "text-emerald-700" : "text-amber-700")}>{n.status}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function OpenIssues() {
  const { nodes } = useBundle();
  const [q, setQ] = useState("");
  const all = Object.values(nodes).filter((n) => n.kind === "issue");
  const open = all.filter((n) => n.open).sort(byId);
  const rows = open.filter((n) => !q.trim() || `${n.id} ${n.summary} ${n.fields.Affects}`.toLowerCase().includes(q.trim().toLowerCase()));
  const shownOn = (id: string) => (nodes[id].backlinks ?? []).filter((b) => nodes[b.from]?.ui && b.from !== "panel:open_issues");
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-3">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="filter open issues" className="h-8 w-64" />
        <span className="text-xs text-muted-foreground">{open.length} open of {all.length}. Open = last non-empty Status is “Open…” and no later update row closes it (shown on each issue card).</span>
      </div>
      <Table>
        <TableHeader><TableRow><TableHead className="w-20">ID</TableHead><TableHead>Issue (first clause)</TableHead><TableHead className="w-32">Affects</TableHead><TableHead className="w-40">Status</TableHead><TableHead className="w-56">Shown on</TableHead></TableRow></TableHeader>
        <TableBody>
          {rows.map((n) => (
            <TableRow key={n.id} className="align-top">
              <TableCell><NodeLink id={n.id} label={n.id} /></TableCell>
              <TableCell className="whitespace-normal">{cleanTitle(n.summary ?? n.title)}</TableCell>
              <TableCell className="whitespace-normal text-xs">{String(n.fields.Affects)}</TableCell>
              <TableCell className="whitespace-normal text-xs">{short(n.status ?? "", 60)}</TableCell>
              <TableCell className="whitespace-normal text-xs">{shownOn(n.id).map((b) => <span key={b.from} className="mr-2 inline-block"><NodeLink id={b.from} className="font-sans text-xs" /></span>)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function Reports() {
  const { nodes, meta } = useBundle();
  const qcs = Object.values(nodes).filter((n) => n.kind === "qc_report").sort(byId);
  return (
    <div className="space-y-2">
      <p className="max-w-3xl text-sm text-muted-foreground">Machine-readable QC reports behind the cards. Open one to see every number; the files are in the repository.</p>
      <ul className="space-y-1.5 text-sm">
        {qcs.map((n) => (
          <li key={n.id}>
            <NodeLink id={n.id} title />
            <span className="ml-2 text-xs">{n.docs.map((d) => meta?.repo_url ? <a key={d} className="mr-2 font-mono text-blue-700 hover:underline" href={`${meta.repo_url}/blob/${meta.git.commit_full}/${d}`} target="_blank" rel="noreferrer">{d.split("/").pop()}</a> : <code key={d} className="mr-2">{d}</code>)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Snapshot() {
  const { meta, nodes } = useBundle();
  const warned = useMemo(() => Object.values(nodes).filter((n) => n.parse_warnings.length).sort(byId), [nodes]);
  if (!meta) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const g = meta.git, m = meta.manifest;
  const row = (k: string, v: React.ReactNode) => <tr className="border-t align-top"><th className="w-56 py-1.5 pr-3 text-left font-medium text-muted-foreground">{k}</th><td className="py-1.5">{v}</td></tr>;
  const ok = (t: string) => <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="size-4" />{t}</span>;
  const bad = (t: string) => <span className="inline-flex items-center gap-1 font-medium text-red-600"><AlertTriangle className="size-4" />{t}</span>;
  return (
    <div className="space-y-4">
      <p className="max-w-3xl text-sm text-muted-foreground">Which version of the repository this page was built from, and whether the inputs have changed since. The same checks run as <code>lint.py --check-fresh</code> in the Python test suite.</p>
      <table className="w-full max-w-4xl text-sm">
        <tbody>
          {row("Built from commit", <><code>{g.commit_full}</code>{meta.repo_url && <> · <a className="text-blue-700 hover:underline" href={`${meta.repo_url}/commit/${g.commit_full}`} target="_blank" rel="noreferrer">view</a></>}</>)}
          {row("Built (UTC)", meta.built_utc)}
          {row("Git working tree", g.dirty ? <div>{bad(`built from uncommitted changes (${g.dirty_paths.length} paths)`)}<ul className="ml-6 list-disc text-xs">{g.dirty_paths.map((p) => <li key={p}><code>{p}</code></li>)}</ul></div> : ok("clean when built"))}
          {row("Canonical data MANIFEST", m.verified ? ok(`all ${m.files_listed} files in data/canonical/MANIFEST.sha256 match`) : <div>{bad("does not verify")}<ul className="text-xs">{m.failures.map((f) => <li key={f.file}><code>{f.file}</code>: {f.problem}</li>)}</ul></div>)}
          {row("Input files hashed", <details><summary className="cursor-pointer">{Object.keys(meta.inputs).length} files (sha256 recorded at build time)</summary><table className="mt-1 text-[11px]"><tbody>{Object.entries(meta.inputs).map(([f, h]) => <tr key={f}><td className="pr-3"><code>{f}</code></td><td className="font-mono text-muted-foreground">{h.slice(0, 16)}…</td></tr>)}</tbody></table></details>)}
          {row("Build errors", meta.build_errors.length ? bad(`${meta.build_errors.length}: ${meta.build_errors.join("; ")}`) : ok("none (all placeholders resolved)"))}
          {row("Nodes", <span>{Object.entries(meta.node_counts).map(([k, v]) => `${k} ${v}`).join(" · ")}</span>)}
        </tbody>
      </table>
      <div>
        <h3 className="mb-1 text-sm font-semibold">Registry rows that did not parse cleanly ({warned.length})</h3>
        <p className="mb-1 text-xs text-muted-foreground">The registries are read-only here; these rows are repaired or aligned by the parser and shown with their raw line on their cards. Fixing them at the source would remove the warnings.</p>
        <ul className="grid gap-x-6 text-sm sm:grid-cols-2 lg:grid-cols-3">{warned.map((n) => <li key={n.id}><NodeLink id={n.id} /> <span className="text-xs text-muted-foreground">{n.source_ref?.file.split("/").pop()}:{n.source_ref?.line}</span></li>)}</ul>
      </div>
    </div>
  );
}

export function AuditPage() {
  return (
    <Tabs defaultValue="registry">
      <TabsList>
        <TabsTrigger value="registry">Registry</TabsTrigger>
        <TabsTrigger value="validation">Validation</TabsTrigger>
        <TabsTrigger value="issues">Open issues</TabsTrigger>
        <TabsTrigger value="reports">Quality reports</TabsTrigger>
        <TabsTrigger value="snapshot">Snapshot</TabsTrigger>
      </TabsList>
      <TabsContent value="registry" className="pt-4"><RegistryBrowser /></TabsContent>
      <TabsContent value="validation" className="pt-4"><Validation /></TabsContent>
      <TabsContent value="issues" className="pt-4"><OpenIssues /></TabsContent>
      <TabsContent value="reports" className="pt-4"><Reports /></TabsContent>
      <TabsContent value="snapshot" className="pt-4"><Snapshot /></TabsContent>
    </Tabs>
  );
}
