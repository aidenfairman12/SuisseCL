"use client";
import { Linkified, NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";
import { useNames } from "@/lib/names";
import { cn } from "@/lib/utils";
import { HEADLINE, REF, fmtKpi, lowerBetter, pctVs, type ResultsFull } from "./results-utils";

export function CompareTable({ res, controller, onController }: { res: ResultsFull; controller: string; onController: (c: string) => void }) {
  const { nodes } = useBundle();
  const names = useNames();
  const ref = res.rows.find((r) => r.controller === REF)!;
  // controllers whose results are identical in every column (computed from the data, not stated by hand)
  const twins = res.rows.filter((a) => a.controller !== REF && res.columns.every((c) => c === "controller" || a[c] === ref[c])).map((a) => a.controller);
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-xs">
            <tr>
              <th className="p-2">Controller</th>
              {HEADLINE.map((c) => <th key={c} className="p-2 text-right"><NodeLink id={`kpi:${c}`} label={names.kpi(c)} className="font-sans text-xs" />{nodes[`kpi:${c}`]?.fields.unit ? <div className="font-normal text-muted-foreground">{String(nodes[`kpi:${c}`].fields.unit)}</div> : null}</th>)}
              <th className="p-2">Experiment</th>
            </tr>
          </thead>
          <tbody>
            {res.rows.map((r) => {
              const alg = r.controller.split("_")[0], sel = r.controller === controller;
              return (
                <tr key={r.controller} className={cn("cursor-pointer border-t hover:bg-muted/30", sel && "bg-sky-50")} onClick={() => onController(r.controller)}>
                  <td className="p-2"><NodeLink id={alg} label={names.ctrl(r.controller)} className="font-sans text-sm font-medium" /> <span className="text-xs text-muted-foreground">{alg} · {r.controller.slice(alg.length + 1)}</span>{sel && <span className="ml-1 text-xs text-sky-700">selected</span>}</td>
                  {HEADLINE.map((c) => {
                    const d = r.controller === REF ? null : pctVs(r, ref, c);
                    const good = d == null || d === 0 ? "" : (lowerBetter(c) ? d < 0 : d > 0) ? "text-emerald-700" : "text-red-600";
                    return <td key={c} className="p-2 text-right tabular-nums"><div>{fmtKpi(r[c], c)}</div><div className={cn("text-xs", good || "text-muted-foreground")}>{r.controller === REF ? "reference" : d == null ? "" : `${d >= 0 ? "+" : ""}${d.toFixed(2)} %`}</div></td>;
                  })}
                  <td className="p-2 text-xs">{(res.experiment_of[r.controller] ?? []).map((e) => <NodeLink key={e} id={e} />)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">Full-year 2023 totals from {res.files[0]} (git {res.meta.git_head}). Lower is better, except reward return. Percentages are against {names.ctrl(REF)}. Click a row to select it for the hour-by-hour view below.</p>
      {twins.map((t) => {
        const alg = t.split("_")[0];
        return (
          <p key={t} className="rounded-md border-l-4 border-sky-500 bg-sky-50 p-2 text-sm">
            <b>{names.ctrl(t)}</b> gives results identical to <b>{names.ctrl(REF)}</b> in every column of the results file. Registry note for <NodeLink id={alg} />: <Linkified text={String(nodes[alg]?.fields.Limitations ?? "")} />
          </p>
        );
      })}
    </div>
  );
}
