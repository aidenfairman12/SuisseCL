"use client";
import { NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";
import { useNames } from "@/lib/names";
import { cn } from "@/lib/utils";
import { REF, fmtKpi, lowerBetter, pctVs, type ResultsFull } from "./results-utils";

/** Every column of the results file for the selected controller, grouped by where the number comes from. */
export function AllKpis({ res, controller }: { res: ResultsFull; controller: string }) {
  const { nodes } = useBundle();
  const names = useNames();
  const r = res.rows.find((x) => x.controller === controller)!, r0 = res.rows.find((x) => x.controller === REF)!;
  const cols = res.columns.filter((c) => c !== "controller" && c !== "steps");
  const group = (c: string) => (!c.startsWith("kpi_") ? "own" : r[c] == null ? "na" : "cl");
  const groups: [string, string, string][] = [
    ["own", "Our own computations", "Computed in run_baselines.py from the CityLearn building series and the R-001 reward."],
    ["cl", "CityLearn KPIs, normalised to CityLearn's conventional counterfactual", "1.0 = the same buildings without storage control; lower is better."],
    ["na", "Not applicable", "The dataset has no thermal dynamics (constant indoor-temperature placeholder, D-018), so CityLearn's comfort and resilience KPIs are empty by design."],
  ];
  return (
    <div className="space-y-5">
      {groups.map(([g, title, note]) => {
        const list = cols.filter((c) => group(c) === g);
        if (!list.length) return null;
        return (
          <section key={g} className="space-y-1">
            <h3 className="text-sm font-semibold">{title} <span className="font-normal text-muted-foreground">({list.length})</span></h3>
            <p className="text-xs text-muted-foreground">{note}</p>
            <table className="w-full text-sm">
              <tbody>
                {list.map((c) => {
                  const n = nodes[`kpi:${c}`], d = controller === REF || g === "na" ? null : pctVs(r, r0, c);
                  const good = d == null || d === 0 ? "" : (lowerBetter(c) ? d < 0 : d > 0) ? "text-emerald-700" : "text-red-600";
                  return (
                    <tr key={c} className="border-t">
                      <td className="py-1 pr-3"><NodeLink id={`kpi:${c}`} label={names.kpi(c) === c ? (n?.title ?? c).replace(" (CityLearn KPI)", "") : names.kpi(c)} className="font-sans text-sm" /></td>
                      <td className="py-1 pr-3 text-right tabular-nums">{g === "na" ? <span className="text-muted-foreground">n/a</span> : n?.fields.relative_only ? <span className="text-xs text-muted-foreground">{controller === REF ? "reference" : "change vs no control"}</span> : <>{fmtKpi(r[c], c)} <span className="text-xs text-muted-foreground">{String(n?.fields.unit ?? "")}</span></>}</td>
                      <td className={cn("w-32 py-1 text-right text-xs", good || "text-muted-foreground")}>{d == null ? "" : `${d >= 0 ? "+" : ""}${d.toFixed(2)} %`}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        );
      })}
    </div>
  );
}
