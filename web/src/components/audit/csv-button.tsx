"use client";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useBundleFile } from "@/lib/bundle";
import type { NodeT, SeriesInputs } from "@/lib/types";

/** All hours of the series an audit card shows (values as stored in the bundle, with flags and source columns named). */
function buildCsv(si: SeriesInputs, n: NodeT): string | null {
  const iso = (i: number) => new Date(Date.parse(si.start_utc) + i * si.step_s * 1000).toISOString().replace(".000Z", "Z");
  const cols: [string, (number | null)[]][] = [["timestamp_utc", Array.from({ length: si.n }, (_, i) => iso(i) as unknown as number)]];
  for (const s of Object.values(si.series)) if (s.ui === n.id) cols.push([s.label, s.values]);
  for (const [k, f] of Object.entries(si.flags)) if (f.ui === n.id) cols.push([k, f.values]);
  if (n.id === "series:building_electricity") for (const [role, b] of Object.entries(si.buildings)) {
    for (const c of b.components) cols.push([`${role}: ${c.label}`, c.values]);
    cols.push([`${role}: gap_filled_flag`, b.gap_filled_flag]);
  }
  if (cols.length === 1) return null;
  const lines = [cols.map((c) => `"${c[0]}"`).join(",")];
  for (let i = 0; i < si.n; i++) lines.push(cols.map((c) => (c[1][i] == null ? "" : c[1][i])).join(","));
  return lines.join("\n");
}

export function hasCsv(n: NodeT) {
  return n.kind === "series";
}

export function CsvButton({ n }: { n: NodeT }) {
  const si = useBundleFile<SeriesInputs>("series_inputs").data;
  if (!si) return null;
  const go = () => {
    const csv = buildCsv(si, n);
    if (!csv) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `${n.id.replace(/[^a-z0-9_]+/gi, "_")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  return <Button variant="outline" size="sm" onClick={go}><Download className="size-3.5" /> Download CSV of the series shown (all hours, with flags)</Button>;
}
