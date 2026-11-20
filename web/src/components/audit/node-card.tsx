"use client";
// One audit card for any node. Always visible: title, class, summary, key numbers, where it comes from.
// Everything else sits in closed accordion sections (progressive disclosure). Ported from dashboard/app.js.
import { useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useBundle } from "@/lib/bundle";
import { REL_LABEL, type NodeT } from "@/lib/types";
import { FigureView } from "@/components/charts/registry";
import { CsvButton, hasCsv } from "./csv-button";
import { ClassBadge, Linkified, NodeLink, cleanTitle, kindLabel, short } from "./bits";
import { flatten, fmtJson } from "./flatten";

function Chip({ children, tone }: { children: React.ReactNode; tone?: "ok" | "warn" | "bad" }) {
  const t = tone === "ok" ? "border-emerald-300 text-emerald-700" : tone === "warn" ? "border-amber-300 text-amber-700" : tone === "bad" ? "border-red-300 text-red-600" : "border-border text-muted-foreground";
  return <span className={`rounded border px-1.5 py-0.5 text-xs ${t}`}>{children}</span>;
}

function Head({ n }: { n: NodeT }) {
  const origin = n.fields?.origin as string | undefined;
  return (
    <header className="space-y-2">
      <div className="text-xs text-muted-foreground">
        {kindLabel(n.kind)} · <code>{n.id}</code>
      </div>
      <h2 className="flex flex-wrap items-center gap-2 text-xl font-semibold leading-tight">
        {n.display_name || cleanTitle(n.title)} <ClassBadge cls={n.classification} />
      </h2>
      {n.classification_raw && n.classification_raw !== n.classification && (
        <div className="text-xs text-muted-foreground">classification in registry: {n.classification_raw}</div>
      )}
      <div className="flex flex-wrap gap-1.5">
        {n.kind === "issue" && <Chip tone={n.open ? "bad" : undefined}>{n.open ? "open" : "closed"}: {short(n.status ?? "", 80)}</Chip>}
        {n.kind === "validation_check" && <Chip tone={n.passed ? "ok" : "warn"}>{short(n.status ?? "", 100)}</Chip>}
        {n.status && n.kind !== "issue" && n.kind !== "validation_check" && <Chip>{short(n.status, 100)}</Chip>}
        {origin && <Chip>{origin === "own" ? "our own computation" : "CityLearn KPI, normalised to the conventional counterfactual (1.0 = counterfactual, lower is better)"}</Chip>}
        {n.fields?.not_applicable ? <Chip tone="warn">not applicable by design</Chip> : null}
      </div>
      {n.summary && <p className="text-[15px] leading-relaxed"><Linkified text={n.summary} /></p>}
      {(n.caveats ?? []).map((c, i) => (
        <div key={i} className="flex gap-2 rounded-r-lg border-l-2 border-zinc-400 bg-zinc-50 px-3 py-2 text-sm text-zinc-700">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span><Linkified text={c} /></span>
        </div>
      ))}
    </header>
  );
}

function Numbers({ n }: { n: NodeT }) {
  if (!n.numbers?.length) return null;
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {n.numbers.map((x, i) => (
        <div key={i} className="rounded-lg border p-2.5">
          <div className="text-lg font-semibold tabular-nums">
            {x.value} {x.unit && x.unit !== "-" && <span className="text-xs font-normal text-muted-foreground">{x.unit}</span>}
          </div>
          <div className="text-xs text-muted-foreground">{x.label}</div>
          {x.note && <div className="text-xs text-amber-800">{x.note}</div>}
        </div>
      ))}
    </div>
  );
}

/** Shortest upstream chain from this node to each SRC-* (or to the last node when no source is reached). */
function Breadcrumbs({ n }: { n: NodeT }) {
  const { nodes } = useBundle();
  const chains = useMemo(() => {
    const tree = n.lineage_tree ?? {};
    const parent: Record<string, string | null> = { [n.id]: null };
    const q = [n.id];
    while (q.length) {
      const x = q.shift()!;
      for (const u of tree[x] ?? []) if (!(u in parent)) { parent[u] = x; q.push(u); }
    }
    const ends = n.lineage.filter((x) => x.startsWith("SRC-"));
    const targets = ends.length ? ends : n.lineage.length ? [n.lineage[n.lineage.length - 1]] : [];
    return { ends: ends.length > 0, list: targets.map((t) => { const c: string[] = []; for (let x: string | null = t; x != null; x = parent[x]) c.unshift(x); return c; }) };
  }, [n]);
  if (!chains.list.length) return null;
  return (
    <section className="space-y-1.5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Where it comes from</h3>
      {chains.list.map((c, i) => (
        <div key={i} className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
          {c.map((x, j) => (
            <span key={x} className="inline-flex items-center gap-1.5">
              {j > 0 && <span className="text-muted-foreground">←</span>}
              {x === n.id ? <b>{n.ui ? n.title : x}</b> : <NodeLink id={x} />}
              {x !== n.id && nodes[x]?.classification && <ClassBadge cls={nodes[x].classification} />}
            </span>
          ))}
        </div>
      ))}
      {!chains.ends && <p className="text-xs text-amber-700">No measured source upstream: the chain ends in a decision or assumption.</p>}
    </section>
  );
}

function LineageTree({ n }: { n: NodeT }) {
  const { nodes } = useBundle();
  const seen = new Set<string>();
  const render = (id: string, depth: number): React.ReactNode => {
    const ups = n.lineage_tree?.[id] ?? [];
    const again = seen.has(id);
    seen.add(id);
    const nd = nodes[id];
    return (
      <li key={id + depth} className="my-0.5">
        {id === n.id ? <b>{n.ui ? n.title : id}</b> : <NodeLink id={id} />}{" "}
        {nd && id !== n.id && <span className="text-[11px] text-muted-foreground">{kindLabel(nd.kind)}</span>} <ClassBadge cls={nd?.classification} />
        {again && ups.length > 0 && <span className="text-xs text-muted-foreground"> (see above)</span>}
        {!again && ups.length > 0 && depth < 12 && <ul className="ml-3 border-l border-dashed pl-3">{ups.map((u) => render(u, depth + 1))}</ul>}
      </li>
    );
  };
  return <ul className="text-sm">{render(n.id, 0)}</ul>;
}

function Code({ n }: { n: NodeT }) {
  const rewardTerms = n.kind === "reward" ? (n.fields.terms as unknown as Record<string, string>[] | undefined) : undefined;
  return (
    <div className="space-y-3">
      {n.formula && <pre className="rounded-md border bg-muted p-2 font-mono text-[13px] whitespace-pre-wrap">{n.formula}</pre>}
      {n.kind === "reward" && n.fields.formula ? <pre className="rounded-md border bg-muted p-2 font-mono text-[13px] whitespace-pre-wrap">{String(n.fields.formula)}</pre> : null}
      {rewardTerms && (
        <table className="w-full text-xs">
          <thead><tr className="text-left"><th>Term</th><th>Definition</th><th>Unit</th><th>Weight</th><th>Scale</th></tr></thead>
          <tbody>{rewardTerms.map((t, i) => <tr key={i} className="border-t align-top"><td className="pr-2">{t.Term}</td><td className="pr-2">{t.Definition}</td><td className="pr-2">{t.Unit}</td><td className="pr-2">{t["Default weight"]}</td><td>{t.Scale}</td></tr>)}</tbody>
        </table>
      )}
      {n.code.map((c, i) => (
        <details key={i} open={n.code.length === 1} className="rounded-md border">
          <summary className="cursor-pointer p-2 text-xs">
            <code>{c.file}{c.symbol ? `::${c.symbol}` : ""}</code> · {c.kind} · {c.commit ? <>commit <code>{c.commit}</code></> : <span className="text-amber-700">not committed</span>}
            {c.uncommitted_changes && <span className="text-amber-700"> (file has uncommitted changes; excerpt is the working copy)</span>}
          </summary>
          {c.defines?.length ? <div className="px-2 text-xs text-muted-foreground">defines: {c.defines.join(", ")}</div> : null}
          <pre className="max-h-[420px] overflow-auto bg-zinc-900 p-2 text-[11.5px] leading-snug text-zinc-200">
            {c.source.split("\n").map((l, j) => `${String(c.line + j).padStart(4)}  ${l}`).join("\n")}
          </pre>
        </details>
      ))}
    </div>
  );
}

function Parameters({ n, ids }: { n: NodeT; ids: string[] }) {
  const { nodes } = useBundle();
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="text-left"><th>Name</th><th>Parameter</th><th>Value</th><th>Unit</th><th>Source / citation</th><th>Class</th></tr></thead>
        <tbody>
          {ids.map((p) => {
            const f = nodes[p].fields as Record<string, string>;
            const proxy = /PROXY|judgement/i.test(f.source ?? "");
            return (
              <tr key={p} className={`border-t align-top ${proxy ? "bg-amber-50" : ""}`} title={proxy ? "proxy or judgement, not a direct literature value" : undefined}>
                <td className="pr-2"><NodeLink id={p} label={f.name} className="font-sans" /></td>
                <td className="pr-2"><code>{f.parameter}</code></td>
                <td className="pr-2 tabular-nums">{f.value}</td>
                <td className="pr-2">{f.unit}</td>
                <td className="pr-2"><Linkified text={f.source_resolved || f.source} />{f.source_resolved && <div className="text-muted-foreground">registry text: “{f.source}” (resolved to the row above)</div>}</td>
                <td>{f.classification}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-1 text-xs text-muted-foreground">Parameters of {n.kind === "parameter" ? String(n.fields.model_id) : "the model(s) this item uses"}.</p>
    </div>
  );
}

function KV({ rows }: { rows: [string, unknown][] }) {
  return (
    <table className="w-full text-xs">
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k} className="border-t align-top">
            <th className="w-2/5 py-0.5 pr-2 text-left font-medium text-muted-foreground">{k}</th>
            <td className="py-0.5 font-mono text-[11.5px]">{typeof v === "string" ? <Linkified text={v} /> : fmtJson(v as never)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Qc({ n }: { n: NodeT }) {
  const { nodes } = useBundle();
  const qcs = [...new Set([...(n.qc ?? []), ...n.edges.filter((e) => nodes[e.to]?.kind === "qc_report").map((e) => e.to)])];
  const vs = n.kind === "validation_check" ? [n.id] : n.edges.filter((e) => nodes[e.to]?.kind === "validation_check").map((e) => e.to);
  return (
    <div className="space-y-2">
      {n.kind === "qc_report" && <KV rows={flatten(n.results)} />}
      {qcs.map((q) => (
        <details key={q} className="rounded-md border p-2">
          <summary className="cursor-pointer text-xs"><NodeLink id={q} /> {nodes[q].title}</summary>
          <div className="mt-1"><KV rows={flatten(nodes[q].results)} /></div>
        </details>
      ))}
      {vs.map((v) => {
        const c = nodes[v];
        return (
          <div key={v} className="text-sm">
            {v !== n.id && <NodeLink id={v} />} <b>{v}</b> {c.title} — <span className={c.passed ? "text-emerald-700" : "text-amber-700"}>{c.status}</span>
            <div className="text-xs"><Linkified text={String(c.fields.Result)} /></div>
            {v === n.id && (c.results ? <details><summary className="cursor-pointer text-xs">numbers ({c.results_key})</summary><KV rows={flatten(c.results)} /></details> : <p className="text-xs text-muted-foreground">no machine-readable numbers for this check in validation_phase_a.json</p>)}
          </div>
        );
      })}
    </div>
  );
}

function Related({ n }: { n: NodeT }) {
  const { nodes } = useBundle();
  const groups: Record<string, [string, string, "in" | "out"][]> = { decision: [], assumption: [], issue: [], other: [], used_by: [] };
  const seen = new Set<string>();
  const add = (id: string, rel: string, dir: "in" | "out") => {
    const key = id + dir;
    const t = nodes[id];
    if (!t || seen.has(key) || id === n.id) return;
    seen.add(key);
    if (dir === "in" && t.ui) groups.used_by.push([id, rel, dir]);
    else if (t.kind in groups) groups[t.kind].push([id, rel, dir]);
    else if (t.kind !== "qc_report" && t.kind !== "parameter") groups.other.push([id, rel, dir]);
  };
  n.edges.forEach((e) => add(e.to, e.rel, "out"));
  (n.backlinks ?? []).forEach((b) => add(b.from, b.rel, "in"));
  groups.issue.sort((a, b) => Number(!!nodes[b[0]].open) - Number(!!nodes[a[0]].open));
  const sect = (title: string, rows: [string, string, "in" | "out"][]) =>
    rows.length ? (
      <div key={title}>
        <h5 className="mt-2 text-xs font-semibold">{title}</h5>
        <ul className="ml-4 list-disc text-sm">
          {rows.map(([id, rel, dir]) => (
            <li key={id + dir}><NodeLink id={id} title /> <span className="text-[11px] text-muted-foreground">{dir === "in" ? "← " : ""}{REL_LABEL[rel] ?? rel}</span></li>
          ))}
        </ul>
      </div>
    ) : null;
  return <div>{sect("Decisions", groups.decision)}{sect("Assumptions", groups.assumption)}{sect("Issues (open issues in red)", groups.issue)}{sect("Other links", groups.other)}{sect("Shown in the dashboard as", groups.used_by)}</div>;
}

function Registry({ n }: { n: NodeT }) {
  return (
    <div className="space-y-2">
      {n.kind === "issue" && n.history ? (
        <>
          <table className="w-full text-xs">
            <thead><tr className="text-left"><th>Date</th><th>Entry</th><th>Status</th></tr></thead>
            <tbody>{n.history.map((h, i) => <tr key={i} className="border-t align-top"><td className="pr-2">{h.date}</td><td className="pr-2"><Linkified text={h.text} />{h.affects && <div className="text-muted-foreground">affects: {h.affects}</div>}{h.needs_user_approval && <div className="text-muted-foreground">needs user approval: {h.needs_user_approval}</div>}</td><td>{h.status}</td></tr>)}</tbody>
          </table>
          <p className="text-xs text-muted-foreground">Open/closed is derived from the last non-empty Status cell; an update row starting with RESOLVED, Closed or Superseded closes the issue.</p>
        </>
      ) : n.fields && !n.ui && n.kind !== "reward" ? (
        <KV rows={Object.entries(n.fields).filter(([, v]) => v !== "" && v != null)} />
      ) : null}
      {n.source_ref && <p className="text-xs">Registry row: <code>{n.source_ref.file}</code> line {n.source_ref.line}</p>}
      {n.parse_warnings.length > 0 && (
        <>
          <div className="rounded-r-lg border-l-2 border-zinc-400 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">This registry row did not parse cleanly: {n.parse_warnings.join("; ")}. Raw line:</div>
          <pre className="max-h-24 overflow-auto rounded bg-muted p-1.5 text-[11px] whitespace-pre-wrap">{n.source_ref?.raw}</pre>
        </>
      )}
    </div>
  );
}

function Files({ n }: { n: NodeT }) {
  const { meta } = useBundle();
  const docs = [...new Set(n.docs ?? [])];
  return (
    <ul className="space-y-1 text-sm">
      {docs.map((d) => (
        <li key={d}>
          {meta?.repo_url ? <a className="font-mono text-xs text-blue-700 hover:underline" href={`${meta.repo_url}/blob/${meta.git.commit_full}/${d}`} target="_blank" rel="noreferrer">{d}</a> : <code className="text-xs">{d}</code>}
        </li>
      ))}
    </ul>
  );
}

export function NodeCard({ id }: { id: string }) {
  const { nodes } = useBundle();
  const n = nodes[id];
  if (!n) return <div><h2 className="text-lg font-semibold">Not found: {id}</h2><p className="text-sm text-muted-foreground">No node with this ID exists in the bundle.</p></div>;

  const modelIds = [...(n.kind === "model" ? [n.id] : []), ...n.edges.map((e) => e.to).filter((t) => t.startsWith("M-") && nodes[t])];
  const params = [...new Set([...(n.kind === "parameter" ? [n.id] : []), ...modelIds.flatMap((m) => nodes[m].edges.filter((e) => e.rel === "has_parameter").map((e) => e.to))])].filter((p) => nodes[p]);
  const hasQc = n.kind === "qc_report" || n.kind === "validation_check" || (n.qc ?? []).length > 0 || n.edges.some((e) => nodes[e.to]?.kind === "qc_report" || nodes[e.to]?.kind === "validation_check");
  const hasMethod = !!n.formula || n.code.length > 0 || n.kind === "reward";
  const hasRegistry = !!n.source_ref || (n.history?.length ?? 0) > 0 || (!n.ui && Object.keys(n.fields ?? {}).length > 0);
  const sections: { key: string; title: string; hint?: string; body: React.ReactNode }[] = [
    n.figures.length > 1 && { key: "figs", title: "More figures", hint: `${n.figures.length - 1}`, body: <div className="space-y-6">{n.figures.slice(1).map((f) => <FigureView key={f} name={f} />)}</div> },
    hasMethod && { key: "method", title: "Method and code", hint: n.code.length ? `${n.code.length} code excerpt${n.code.length > 1 ? "s" : ""}` : undefined, body: <Code n={n} /> },
    params.length > 0 && { key: "params", title: "Parameters and citations", hint: `${params.length}`, body: <Parameters n={n} ids={params} /> },
    hasQc && { key: "qc", title: "QC and validation", body: <Qc n={n} /> },
    { key: "related", title: "Decisions, assumptions and issues", body: <Related n={n} /> },
    n.lineage.length > 0 && { key: "tree", title: "Full lineage", hint: `${n.lineage.length} nodes`, body: <LineageTree n={n} /> },
    hasRegistry && { key: "registry", title: n.kind === "issue" ? "Issue history (verbatim)" : "Registry entry (verbatim)", body: <Registry n={n} /> },
    (n.docs ?? []).length > 0 && { key: "files", title: "Reports and files", hint: `${new Set(n.docs).size}`, body: <Files n={n} /> },
  ].filter(Boolean) as { key: string; title: string; hint?: string; body: React.ReactNode }[];

  return (
    <div className="space-y-5">
      <Head n={n} />
      <Numbers n={n} />
      {n.figures.length > 0 && <FigureView name={n.figures[0]} />}
      {hasCsv(n) && <CsvButton n={n} />}
      <Breadcrumbs n={n} />
      <Accordion multiple className="rounded-lg border px-3">
        {sections.map((s) => (
          <AccordionItem key={s.key} value={s.key}>
            <AccordionTrigger>
              <span>{s.title} {s.hint && <span className="ml-1 text-xs font-normal text-muted-foreground">{s.hint}</span>}</span>
            </AccordionTrigger>
            <AccordionContent>{s.body}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
