"use client";
import { useMemo, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimeChart, flagColour, type Panel } from "@/components/charts/time-chart";
import { useSi } from "@/components/charts/figures-inputs";
import { count, timestamps } from "@/components/charts/util";
import { ClassBadge } from "@/components/audit/bits";
import { TopicHeader } from "@/components/topic-header";
import { MoreViews } from "@/components/topic-more";
import { useBundle } from "@/lib/bundle";
import { useNames } from "@/lib/names";
import type { SeriesInputs } from "@/lib/types";
import { HourPanel } from "./hour-panel";

type TabDef = { id: string; label: string; node: string; more: string[]; panels: (si: SeriesInputs, role: string, nm: (r: string) => string) => Panel[] };

const flag = (si: SeriesInputs, key: string, onSeries: number) => ({ label: si.flags[key].label, values: si.flags[key].values, colour: flagColour(key), onSeries });
const S = (si: SeriesInputs, k: string) => ({ name: si.series[k].label, values: si.series[k].values, cls: si.series[k].classification });

const TABS: TabDef[] = [
  { id: "weather", label: "Weather", node: "series:outdoor_temperature", more: ["klo_vs_heapo", "ghi_vs_diffuse"],
    panels: (si) => [
      { title: "Outdoor temperature — Zurich/Kloten", unit: "°C", series: [S(si, "temp_c")] },
      { title: "Solar irradiance — Zurich/Kloten (beam = global − diffuse)", unit: "W/m²", series: [S(si, "ghi"), { ...S(si, "diffuse") }, S(si, "beam")], flags: [flag(si, "weather_missing", 1), flag(si, "beam_negative", 2)] },
    ] },
  { id: "price", label: "Price", node: "series:price", more: ["price_heatmap"],
    panels: (si) => [{ title: "Electricity price — EKZ standard tariff, excl. VAT", unit: "Rp/kWh", series: [{ ...S(si, "price"), step: true }] }] },
  { id: "carbon", label: "Carbon", node: "series:carbon_intensity", more: ["carbon_import_stack", "epfl_monthly", "epfl_diurnal", "epfl_table"],
    panels: (si) => [{ title: "Grid carbon intensity — MODELED: read the shape, not the level (see the notes above)", unit: "gCO2eq/kWh", series: [S(si, "carbon"), { ...S(si, "carbon_domestic"), dash: true }], flags: [flag(si, "neighbour_intensity_fallback_flag", 0), flag(si, "gap_interpolated_flag", 1)] }] },
  { id: "buildings", label: "Buildings", node: "series:building_electricity", more: ["building_daily", "selection_pools", "backtest"],
    panels: (si, role, nm) => {
      const b = si.buildings[role];
      return [{ title: `Electricity — ${nm(role)} (kWh per hour, stacked)`, unit: "kWh", series: b.components.map((c) => ({ name: c.label, values: c.values, cls: c.classification, stack: "e", area: true })),
        flags: b.gap_filled_flag.some(Boolean) ? [{ label: `${nm(role)} gap-filled (constructed)`, values: b.gap_filled_flag, colour: flagColour("gap_filled_flag"), onSeries: 0 }] : [] }];
    } },
];

function Legend({ si, overlay, panels }: { si: SeriesInputs; overlay: boolean; panels: Panel[] }) {
  const { colours } = useBundle();
  if (!overlay) return <p className="text-xs text-muted-foreground">Trust overlay off: series in neutral colours, flagged hours hidden.</p>;
  const flags = panels.flatMap((p) => p.flags ?? []);
  const classes = [...new Set(panels.flatMap((p) => p.series.map((s) => s.cls)))];
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
      <span>Series coloured by classification:</span>{classes.map((c) => <ClassBadge key={c} cls={c} />)}
      {flags.length > 0 && <span>· flagged hours shaded and marked ⚑:</span>}
      {flags.map((f) => <span key={f.label} className="inline-flex items-center gap-1"><i className="inline-block size-2.5 rounded-sm" style={{ background: f.colour }} />{f.label}: <b>{count(f.values)}</b> h</span>)}
      <span className="hidden" aria-hidden>{si.n}{Object.keys(colours).length}</span>
    </div>
  );
}

function InputTab({ def, si }: { def: TabDef; si: SeriesInputs }) {
  const { colours } = useBundle();
  const names = useNames();
  const [overlay, setOverlay] = useState(true);
  const [picked, setRole] = useState<string | null>(null);
  const role = picked ?? Object.keys(si.buildings)[0];
  const [hour, setHour] = useState<number | null>(null);
  const ts = useMemo(() => timestamps(si), [si]);
  const panels = useMemo(() => def.panels(si, role, names.building), [def, si, role, names]);
  return (
    <div className="space-y-4">
      <TopicHeader nodeId={def.node} />
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={overlay} onChange={(e) => setOverlay(e.target.checked)} /> Trust overlay</label>
        {def.id === "buildings" && (
          <label className="text-sm">Building <select value={role} onChange={(e) => setRole(e.target.value)} className="ml-1 h-8 rounded-lg border bg-background px-2 text-sm">{Object.keys(si.buildings).map((r) => <option key={r} value={r}>{names.building(r)}</option>)}</select></label>
        )}
        <span className="text-xs text-muted-foreground">Drag to zoom (panels follow) · click the plot for every input at that hour</span>
      </div>
      <Legend si={si} overlay={overlay} panels={panels} />
      <TimeChart panels={panels} ts={ts} overlay={overlay} colours={colours} onHour={setHour} />
      {hour != null && <HourPanel si={si} i={hour} />}
      <MoreViews figs={def.more} />
    </div>
  );
}

export function InputsPage() {
  const si = useSi();
  if (!si) return <p className="text-sm text-muted-foreground">Loading inputs…</p>;
  return (
    <Tabs defaultValue="weather">
      <TabsList>{TABS.map((t) => <TabsTrigger key={t.id} value={t.id}>{t.label}</TabsTrigger>)}</TabsList>
      {TABS.map((t) => <TabsContent key={t.id} value={t.id} className="pt-4"><InputTab def={t} si={si} /></TabsContent>)}
    </Tabs>
  );
}
