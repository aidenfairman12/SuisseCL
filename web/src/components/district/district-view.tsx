"use client";
import { useEffect, useMemo, useState } from "react";
import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useManifest, useBuildings, useConditions, useRun } from "@/lib/contract";
import type { BuildingInfo } from "@/lib/contract";
import { Scene, type SceneState } from "./scene";
import { BuildingCutaway } from "./building-cutaway";

const f = (v: number | null | undefined, d = 1) => v == null || !Number.isFinite(v) ? "—" : v.toFixed(d);
const maxOf = (a: number[]) => a.reduce((m, v) => Math.max(m, v), 0);
export const DEFAULT_CONTROLLER = "ALG-003_basic_rbc";

export function DistrictView({ controller: controllerProp, onController }: { controller: string; onController: (c: string) => void }) {
  const manifestFile = useManifest("full");
  const buildingsFile = useBuildings("full");
  const conditionsFile = useConditions("full");
  const runFile = useRun("base", controllerProp || DEFAULT_CONTROLLER, "full");
  const manifest = manifestFile.data;
  const buildings = buildingsFile.data?.buildings;
  const conditions = conditionsFile.data;
  const run = runFile.data;
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [playbackMs, setPlaybackMs] = useState(50);
  const [eventTag, setEventTag] = useState("district_daily_peak");
  const [selectedBuilding, setSelectedBuilding] = useState("");

  const buildingIds = manifest?.buildings ?? [];
  const districtBuildings = buildingIds.flatMap((id) => {
    const info = buildings?.[id];
    if (!info) return [];
    const area = info.attributes.floor_area_m2;
    const units = info.attributes.housing_units;
    return [{
      role: id,
      type: info.type,
      area_m2: area?.available && typeof area.value === "number" ? area.value : null,
      units: units?.available && typeof units.value === "number" ? units.value : null,
    }];
  });
  // The contract's scope is either a short sample window or the full simulated year.
  // All arrays are indexed locally within that scope; never hard-code the sample's 48 steps.
  const n = Math.min(
    run?.scope.n_steps ?? 0,
    conditions?.scope.n_steps ?? 0,
    run?.district.net_kwh_el.length ?? 0,
    conditions?.local_time.length ?? 0,
    conditions?.series.temp_c.length ?? 0,
  );
  const i = Math.min(step, Math.max(0, n - 1));
  useEffect(() => {
    if (!playing || n < 1) return;
    const timer = window.setInterval(() => setStep((current) => (current + 1) % n), playbackMs);
    return () => window.clearInterval(timer);
  }, [playing, n, playbackMs]);

  const buildingStates = useMemo(() => {
    if (!run) return [];
    return buildingIds.map((id) => {
      const series = run.buildings[id];
      if (!series) return { net: null, hp: null, socHeat: null, socDhw: null, actionHeat: null };
      return {
        net: series.net_kwh_el[i] ?? null,
        hp: (series.hp_sh_kwh_el[i] ?? 0) + (series.hp_hw_kwh_el[i] ?? 0),
        socHeat: series.sh_tank_soc[i] ?? null,
        socDhw: series.hw_tank_soc?.[i] ?? null,
        actionHeat: series.sh_tank_action[i] ?? null,
      };
    });
  }, [run, buildingIds, i]);

  if (!manifest || !buildings || !conditions || !run) {
    return <div className="flex aspect-[16/9] items-center justify-center rounded-2xl border bg-muted/30 text-sm text-muted-foreground">Loading the district simulation…</div>;
  }

  const stepSeconds = manifest.time_axis.step_seconds;
  const totalNet = run.district.net_kwh_el[i] ?? null;
  const maxNet = Math.max(1, ...buildingIds.map((id) => maxOf(run.buildings[id]?.net_kwh_el ?? [])));
  const maxHp = Math.max(1, ...buildingIds.map((id) => maxOf((run.buildings[id]?.hp_sh_kwh_el ?? []).map((v, j) => v + (run.buildings[id]?.hp_hw_kwh_el[j] ?? 0)))));
  const temp = conditions.series.temp_c[i] ?? null;
  const ghi = conditions.series.ghi_wm2[i] ?? 0;
  const price = conditions.series.price_chf_kwh[i] ?? null;
  const rank = conditions.series.carbon_relative_rank[i] ?? null;
  const localTime = conditions.local_time[i] ?? "Time unavailable";
  const eventSteps = run.situations.district[eventTag] ?? [];
  const previousEvent = [...eventSteps].reverse().find((eventStep) => eventStep < i);
  const nextEvent = eventSteps.find((eventStep) => eventStep > i);
  const eventLabel = manifest.situation_tags[eventTag] ?? eventTag.replaceAll("_", " ");
  const hour = conditions.local_hour[i] ?? 0;
  const night = hour < 6 || hour >= 20;
  const frac = Math.max(0, Math.min(1, (hour - 5) / 16));
  const statesById = new Map<string, (typeof buildingStates)[number]>();
  buildingIds.forEach((id, j) => statesById.set(id, buildingStates[j]));
  const sceneStates = districtBuildings.map((b) => statesById.get(b.role) ?? { net: null, hp: null, socHeat: null, socDhw: null, actionHeat: null });
  const sceneState: SceneState = {
    night, ghiK: Math.min(1, ghi / 700), sunX: 200 + frac * 900, sunY: 330 - Math.sin(frac * Math.PI) * 220,
    tariff: price == null ? "—" : `CHF ${f(price, 3)}/kWh`,
    tariffSub: conditions.series.tariff_tier[i] === "high" ? "High-price period" : "Low-price period",
    carbon: rank == null ? "—" : `Relative rank ${f(rank, 0)}`,
    carbonSub: "Modeled relative ranking only; no absolute emissions",
    weather: temp == null ? "—" : `${f(temp, 1)} °C`,
    weatherSub: "MeteoSwiss · measured",
    controller: manifest.controllers.find((c) => c.id === controllerProp)?.display_name ?? controllerProp,
    maxNet, maxHp, busFlow: totalNet ?? 0, buildings: sceneStates,
  };
  const selectedId = buildings[selectedBuilding] ? selectedBuilding : (manifest.buildings[0] ?? "");
  const selectedInfo: BuildingInfo | undefined = buildings[selectedId];
  const selectedSeries = run.buildings[selectedId];
  const selectedStep = selectedSeries ? {
    net: selectedSeries.net_kwh_el[i] ?? null,
    hpSh: selectedSeries.hp_sh_kwh_el[i] ?? null,
    hpHw: selectedSeries.hp_hw_kwh_el[i] ?? null,
    household: selectedSeries.household_kwh_el[i] ?? null,
    shDemand: selectedSeries.sh_demand_kwh_th[i] ?? null,
    hwDemand: selectedSeries.hw_demand_kwh_th[i] ?? null,
    hpShDirect: selectedSeries.hp_sh_direct_kwh_th[i] ?? null,
    hpShToTank: selectedSeries.hp_sh_to_tank_kwh_th[i] ?? null,
    shTankToDemand: selectedSeries.sh_tank_to_demand_kwh_th[i] ?? null,
    shTankLoss: selectedSeries.sh_tank_loss_kwh_th[i] ?? null,
    shSoc: selectedSeries.sh_tank_soc[i] ?? null,
    hpHwDirect: selectedSeries.hp_hw_direct_kwh_th[i] ?? null,
    hpHwToTank: selectedSeries.hp_hw_to_tank_kwh_th?.[i] ?? null,
    hwTankToDemand: selectedSeries.hw_tank_to_demand_kwh_th?.[i] ?? null,
    hwTankLoss: selectedSeries.hw_tank_loss_kwh_th?.[i] ?? null,
    hwSoc: selectedSeries.hw_tank_soc?.[i] ?? null,
  } : null;

  return (
    <div className="space-y-3">
      <Scene buildings={districtBuildings} names={districtBuildings.map((b) => buildings[b.role]?.display_name ?? "Building")} state={sceneState} selectedBuilding={selectedId} onSelect={setSelectedBuilding} />
      {selectedInfo && selectedStep && (
        <section aria-label="Selected building details" className="space-y-4 rounded-2xl border bg-card p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Selected building</p>
              <h3 className="text-xl font-semibold">{selectedInfo.display_name}</h3>
              <p className="text-sm text-muted-foreground">{selectedInfo.type === "SFH" ? "Single-family house" : "Apartment building"} · representative model</p>
            </div>
            <span className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground">Phase A · modeled system</span>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-xl bg-muted/50 p-3"><p className="text-xs text-muted-foreground">Grid electricity</p><p className="text-lg font-semibold tabular-nums">{f(selectedStep.net, 2)} <span className="text-xs font-normal text-muted-foreground">kWh_el/step</span></p></div>
            <div className="rounded-xl bg-muted/50 p-3"><p className="text-xs text-muted-foreground">Heat-pump electricity</p><p className="text-lg font-semibold tabular-nums">{f((selectedStep.hpSh ?? 0) + (selectedStep.hpHw ?? 0), 2)} <span className="text-xs font-normal text-muted-foreground">kWh_el/step</span></p></div>
            <div className="rounded-xl bg-muted/50 p-3"><p className="text-xs text-muted-foreground">Heating tank</p><p className="text-lg font-semibold tabular-nums">{selectedStep.shSoc == null ? "—" : `${f(selectedStep.shSoc * 100, 0)}%`}</p><p className="text-xs text-muted-foreground">Synthetic tank · assumed parameters</p></div>
          </div>
          <BuildingCutaway building={selectedInfo} state={selectedStep} stepSeconds={stepSeconds} />
        </section>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button size="icon" variant="outline" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "pause" : "play"}>{playing ? <Pause className="size-4" /> : <Play className="size-4" />}</Button>
        <select value={controllerProp} onChange={(e) => onController(e.target.value)} className="h-8 rounded-lg border bg-background px-2 text-sm" aria-label="control rule">
          {manifest.controllers.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
        </select>
        <input type="range" min={0} max={Math.max(n - 1, 0)} value={i} onChange={(e) => { setPlaying(false); setStep(+e.target.value); }} className="min-w-48 flex-1 accent-amber-500" aria-label="simulation timestep" />
        <select value={playbackMs} onChange={(e) => setPlaybackMs(Number(e.target.value))} className="h-8 rounded-lg border bg-background px-2 text-sm" aria-label="playback speed">
          <option value={25}>Fast · 25 ms/step</option>
          <option value={50}>1× · 50 ms/step</option>
          <option value={100}>½× · 100 ms/step</option>
          <option value={250}>¼× · 250 ms/step</option>
        </select>
        <Button size="sm" variant="outline" onClick={() => { setPlaying(false); setStep(0); }}>{run.scope.kind === "year" ? "Year start" : "Window start"}</Button>
        <Button size="sm" variant="outline" onClick={() => { setPlaying(false); setStep(Math.max(0, n - 1)); }}>{run.scope.kind === "year" ? "Year end" : "Window end"}</Button>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <label htmlFor="district-event" className="text-xs font-medium">Jump to event</label>
        <select id="district-event" value={eventTag} onChange={(e) => setEventTag(e.target.value)} className="h-8 rounded-lg border bg-background px-2 text-sm">
          {["district_daily_peak", "cold_hour", "high_tariff", "sh_tank_charging", "sh_tank_discharging"].map((tag) => <option key={tag} value={tag}>{manifest.situation_tags[tag] ?? tag}</option>)}
        </select>
        <Button size="sm" variant="outline" disabled={previousEvent == null} onClick={() => { setPlaying(false); setStep(previousEvent!); }}>Previous event</Button>
        <Button size="sm" variant="outline" disabled={nextEvent == null} onClick={() => { setPlaying(false); setStep(nextEvent!); }}>Next event</Button>
        <span className="text-xs">{eventSteps.length.toLocaleString()} tagged steps · {eventLabel}</span>
      </div>
      <p className="text-sm text-muted-foreground"><b className="text-foreground">{localTime}</b> · {f(totalNet, 2)} kWh_el drawn from the grid by all six building models in this step · {stepSeconds / 3600} h timestep</p>
      <p className="text-xs text-muted-foreground">{run.scope.kind === "year" ? "Full-year simulation" : "Sample window"} · {n.toLocaleString()} simulated steps · {conditions.local_time[0] ?? "—"} to {conditions.local_time[n - 1] ?? "—"} · {playbackMs} ms per step</p>
      <p className="text-xs text-muted-foreground">{manifest.description} {manifest.district_note}</p>
    </div>
  );
}

