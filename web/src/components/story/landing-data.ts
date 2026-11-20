"use client";
// Every number on the story page is computed here from the bundle files (cooling.json, scenarios.json); nothing is typed by hand.
import { useMemo } from "react";
import { useBundleFile } from "@/lib/bundle";

type Ctl = { saving_pct: number; share_of_ceiling_pct: number; highest_hour_kw: number };
type Cell = {
  id: string; archetype: string; scenario: string; adoption: string;
  heating_kwh: { baseline: number };
  cooling_kwh: { baseline: number };
  pv_cooling_share: { thermostat: { pv: number } | null };
  controllers: Record<string, Ctl>;
};
type Cooling = { cells: Cell[]; scenario_labels: Record<string, string> };
type Rung = { id: string; name: string; adds: string; saving_year_pct: number };
type Scenarios = { ladder: Rung[] };
export type Range = [number, number];

const range = (v: number[]): Range => [Math.min(...v), Math.max(...v)];

export function useLanding() {
  const cooling = useBundleFile<Cooling>("cooling").data;
  const scen = useBundleFile<Scenarios>("scenarios").data;
  const houses = useBundleFile<{ buildings: string[] }>("houses").data;
  return useMemo(() => {
    if (!cooling || !scen) return null;
    const central = cooling.cells.filter((c) => c.archetype === "central");
    const cell = (id: string) => central.find((c) => c.id === id)!;
    const levels = ["hist", "gwl2.0", "gwl3.0"].map((s) => ({ id: s, label: cooling.scenario_labels[s], heating: cell(`${s}_none`).heating_kwh.baseline }));
    const heatNow = levels[0].heating, heatWarm = levels[levels.length - 1].heating;
    const warm = "gwl3.0";
    const adoption = ["low", "medium", "high"].map((a) => ({ id: a, kwh: cell(`${warm}_${a}`).cooling_kwh.baseline }));
    const cooled = central.filter((c) => ["low", "medium", "high"].includes(c.adoption));
    const of = (key: string, f: (c: Ctl) => number) => range(central.map((c) => f(c.controllers[key])));
    return {
      buildings: houses?.buildings.length ?? null,
      levels, heatNow, heatWarm, heatFallPct: (1 - heatWarm / heatNow) * 100, warmLabel: cooling.scenario_labels[warm],
      adoption, coolingRange: range(cooled.map((c) => c.cooling_kwh.baseline)),
      pvCoverage: range(cooled.map((c) => c.pv_cooling_share.thermostat!.pv * 100)),
      ladder: scen.ladder,
      mpcShare: of("mpc", (c) => c.share_of_ceiling_pct), ruleShare: of("pv_rule", (c) => c.share_of_ceiling_pct),
      peakThermostat: of("thermostat", (c) => c.highest_hour_kw), peakMpc: of("mpc", (c) => c.highest_hour_kw), peakMpcWeighted: of("mpc_peak0.1", (c) => c.highest_hour_kw),
      savingMpc: of("mpc", (c) => c.saving_pct), savingMpcWeighted: of("mpc_peak0.1", (c) => c.saving_pct),
    };
  }, [cooling, scen, houses]);
}
export type Landing = NonNullable<ReturnType<typeof useLanding>>;

const nf = (v: number, d = 0) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmt = nf;
/** "75–78" style range, rounded to whole numbers (or d decimals); a single value if both ends round the same. */
export const rng = ([lo, hi]: Range, d = 0) => (nf(lo, d) === nf(hi, d) ? nf(lo, d) : `${nf(lo, d)}–${nf(hi, d)}`);
