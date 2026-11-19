"use client";
import { useState } from "react";
import { Lead, Loading, Note, Section, Table, fmt, signed } from "@/components/phase-b/shared";
import { dataKey } from "@/components/phase-c/explorer-page";
import { ArchetypeSelector, Pills, cellId, useArchetype } from "@/components/phase-c/shared";
import { useBundleFile } from "@/lib/bundle";
import type { HouseBlock, HousesData } from "@/lib/types";

type Cell = { archetype: string } & Record<string, { buildings: Record<string, HouseBlock>; district: { summer_peak_kw: number; peak_kw: number } }>;

export function HousesPage() {
  const { data: d, error } = useBundleFile<HousesData>("houses");
  const [scen, setScen] = useState("gwl3.0_hw99");
  const [adopt, setAdopt] = useState("high");
  const [ctrl, setCtrl] = useState<"thermostat" | "optimum">("thermostat");
  const arch = useArchetype(d?.archetypes ?? []);
  if (error) return <p className="text-sm text-destructive">Could not load the houses bundle: {error}</p>;
  if (!d) return <Loading what="house-level results" />;
  const p = d.prose;
  const get = (s: string, a: string) => d.cells[dataKey(arch.current, cellId(s, a))] as Cell | undefined;
  const cell = get(scen, adopt), none = get(scen, "none"), histNone = get("hist", "none");
  const adoptions = d.adoption.filter((a) => a !== "none" && d.scenarios.some((s) => get(s, a)));
  const rows = cell && none && histNone ? d.buildings.map((b) => {
    const c = cell[ctrl].buildings[b], n = none[ctrl].buildings[b], h = histNone[ctrl].buildings[b];
    const cooled = c.annual.cool > 1e-6;
    return [
      <span key={b} className="block text-left">{b}{cooled && <span className="text-xs text-muted-foreground"> · cooled</span>}</span>,
      fmt(c.annual.cool, 0), fmt(h.annual.heat - n.annual.heat, 0),
      cooled && c.annual.pv_share_of_cooling != null ? `${fmt(100 * c.annual.pv_share_of_cooling, 0)} %` : "–",
      cooled && c.pv_share_of_cooling_hp_first != null ? `${fmt(100 * c.pv_share_of_cooling_hp_first, 0)} %` : "–",
      signed(c.annual.import - n.annual.import, 0), signed(c.annual.export - n.annual.export, 0), signed(c.summer.import - n.summer.import, 0), fmt(c.dh26, 0),
    ];
  }) : [];
  const dsp = cell && none ? cell[ctrl].district.summer_peak_kw - none[ctrl].district.summer_peak_kw : null;
  const dpk = cell && none ? cell[ctrl].district.peak_kw - none[ctrl].district.peak_kw : null;
  return (
    <div className="space-y-10">
      <Lead>{p.intro as string}</Lead>
      <div className="space-y-3">
        <ArchetypeSelector list={d.archetypes} current={arch.current} onChange={arch.setSel} />
        <Pills value={scen} onChange={setScen} label="Weather scenario" options={d.scenarios.map((s) => ({ id: s, label: d.scenario_labels[s] }))} />
        <Pills value={adopt} onChange={setAdopt} label="Cooling level" options={adoptions.map((a) => ({ id: a, label: d.adoption_labels[a].split(":")[0] }))} />
        <Pills value={ctrl} onChange={setCtrl} label="Controller" options={[{ id: "thermostat", label: "Thermostat (reference)" }, { id: "optimum", label: "Exact optimum" }]} />
      </div>

      <Section title="Per building" classes={["modeled", "assumption"]}>
        <Table
          head={["Building", "Cooling added (kWh per year)", "Heating saved by warming (kWh per year)", "Cooling covered by solar", "… with the heat pump first", "Grid import change (kWh)", "Export change (kWh)", "Summer import change (kWh)", "Degree-hours above the cooling setpoint"]}
          rows={rows}
          minWidth={980}
        />
        <p className="text-xs text-muted-foreground">
          Cell: {d.scenario_labels[scen]}; {d.adoption_labels[adopt]}. Import, export and summer import changes compare the cell with the heating-only cell of the same weather; heating saved by warming compares the heating-only cell of this weather with the heating-only cell of 2023 weather. A positive export change means more exported.
        </p>
        {dsp != null && dpk != null && <p className="text-sm">District: summer peak {signed(dsp, 1)} kW and highest hour of the year {signed(dpk, 1)} kW against the heating-only district of the same weather.</p>}
        <Note>{p.rule_note as string}</Note>
      </Section>
      <Note>Sources: {d.sources.join(", ")}. Every number is read from committed result files at build time.</Note>
    </div>
  );
}
