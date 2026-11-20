"use client";
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useManifest, useBuildings, useConditions, useRun, useScenarioIndex, useScenarioManifest, useScenarioConditions, useScenarioRun } from "@/lib/contract";
import type { BuildingInfo, ScenarioBuildingSeries } from "@/lib/contract";
import { PALETTE } from "@/lib/palette";
import { cn } from "@/lib/utils";
import { Scene, type SceneBuilding } from "./scene";
import { BuildingCutaway } from "./building-cutaway";

const f = (v: number | null | undefined, d = 1) => v == null || !Number.isFinite(v) ? "—" : v.toFixed(d);
export const DEFAULT_CONTROLLER = "ALG-003_basic_rbc";
const STRIP = 48;
const EVENTS: Record<string, string> = {
  district_daily_peak: "Daily peak", cold_hour: "Cold hour", high_tariff: "High-tariff hour",
  sh_tank_charging: "Heating tank charging", sh_tank_discharging: "Heating tank discharging",
};

/** Jump entries that come from the per-hour tags of a run; the Phase B and Phase C scenarios add their own targets from their manifest. */
const SCENARIO_EVENTS: Record<string, string> = { ...EVENTS, district_exporting: "Export hour" };
const PHASE_A = "phase_a";
const PHASE_A_LABEL = "Phase A (today)";

const num = (b: BuildingInfo, key: string) => { const a = b.attributes[key]; return a?.available && typeof a.value === "number" ? a.value : null; };
/** "Single-family house (low use)" → "House, low use"; "Apartment building (large)" → "Apartments, large". */
function shortName(b: BuildingInfo) {
  const m = /\(([^)]+)\)/.exec(b.display_name);
  return `${b.type === "SFH" ? "House" : "Apartments"}${m ? `, ${m[1]}` : ""}`;
}
function subLine(b: BuildingInfo) {
  if (b.type === "SFH") {
    const area = num(b, "floor_area_m2"), res = num(b, "residents");
    return [area == null ? null : `${area.toFixed(0)} m²`, res == null ? null : `${res.toFixed(0)} residents`].filter(Boolean).join(" · ") || "Single-family house";
  }
  const units = num(b, "housing_units");
  return units == null ? "Apartment building" : `${units} homes`;
}
/** "2023-12-04T19:00+0100" → { day: "Mon 4 Dec 2023", time: "19:00" } without time-zone conversion. */
function localParts(s: string | undefined) {
  const m = s ? /^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})/.exec(s) : null;
  if (!m) return { day: "—", short: "—", time: "—" };
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  const wd = d.toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" });
  const dm = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  return { day: `${wd} ${dm} ${m[1]}`, short: `${wd} ${dm}`, time: m[4] };
}

const TONES = {
  blue: { box: "border-blue-200 bg-blue-50", label: "text-blue-800", value: "text-blue-700" },
  solar: { box: "border-yellow-200 bg-yellow-50", label: "text-yellow-800", value: "text-yellow-700" },
  export: { box: "border-violet-200 bg-violet-50", label: "text-violet-800", value: "text-violet-700" },
} as const;
function Stat({ label, value, tone }: { label: string; value: string; tone?: keyof typeof TONES }) {
  const t = tone ? TONES[tone] : null;
  return (
    <div className={cn("flex flex-col rounded-lg border px-3 py-1.5", t ? t.box : "border-zinc-200 bg-white")}>
      <span className={cn("text-[11px]", t ? t.label : "text-zinc-500")}>{label}</span>
      <span className={cn("text-sm font-semibold tabular-nums", t?.value)}>{value}</span>
    </div>
  );
}

function Row({ label, value, strong, colour }: { label: string; value: string; strong?: boolean; colour?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-zinc-100 py-2">
      <span className="text-[13px] text-zinc-600">{label}</span>
      <span className={cn("text-[13px] tabular-nums", strong && "text-sm font-semibold", strong && !colour && "text-orange-700")} style={colour ? { color: colour } : undefined}>{value}</span>
    </div>
  );
}

function Level({ label, soc, colour, hex }: { label: string; soc: number | null; colour?: string; hex?: string }) {
  const v = soc == null ? null : Math.max(0, Math.min(1, soc));
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs"><span className="text-zinc-600">{label}</span><span className="tabular-nums">{v == null ? "not modeled" : `${f(v * 100, 0)} %`}</span></div>
      <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100"><div className={cn("h-1.5 rounded-full", colour)} style={{ width: `${(v ?? 0) * 100}%`, background: hex }} /></div>
    </div>
  );
}

/** The scenario choice: Phase A is built in, every other entry comes from sim_scenarios/index.json (a list, not a code path per scenario). */
function ScenarioSwitch({ options, value, onChange }: { options: { id: string; label: string; title?: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div role="radiogroup" aria-label="Scenario" className="inline-flex flex-wrap overflow-hidden rounded-md border border-zinc-200 bg-white text-xs">
      {options.map((o) => (
        <button key={o.id} type="button" role="radio" aria-checked={o.id === value} title={o.title} onClick={() => onChange(o.id)}
          className={cn("h-8 border-r border-zinc-200 px-2.5 last:border-r-0", o.id === value ? "bg-zinc-900 font-medium text-zinc-50" : "text-zinc-700 hover:bg-zinc-50")}>{o.label}</button>
      ))}
    </div>
  );
}

const kwOf = (kwh: number | null | undefined, stepSeconds: number) => kwh == null || !Number.isFinite(kwh) ? null : kwh / (stepSeconds / 3600);

export function DistrictView({ controller: controllerProp, onController, variant = "full" }: { controller: string; onController: (c: string) => void; variant?: "sample" | "full" }) {
  const manifestFile = useManifest(variant);
  const buildingsFile = useBuildings(variant);
  const conditionsFile = useConditions(variant);
  const runFile = useRun("base", controllerProp || DEFAULT_CONTROLLER, variant);
  const manifest = manifestFile.data;
  const buildings = buildingsFile.data?.buildings;
  const conditions = conditionsFile.data;
  const run = runFile.data;
  // Scenarios (Phase B and Phase C): the list is small and always loaded; the data of a scenario is fetched only once it is selected.
  const scenarioIndex = useScenarioIndex().data;
  const [scenarioId, setScenarioId] = useState(PHASE_A);
  const [scnController, setScnController] = useState("");
  const entry = scenarioIndex?.scenarios.find((e) => e.id === scenarioId) ?? null;
  const scnId = entry?.id ?? null;
  const scnCtrl = entry ? (entry.controllers.includes(scnController) ? scnController : entry.default_controller) : null;
  const scnManifest = useScenarioManifest(scnId).data;
  const scnConditions = useScenarioConditions(scnId).data;
  const scnRun = useScenarioRun(scnId, scnCtrl).data;
  const scn = scnId && scnManifest && scnConditions && scnRun && scnRun.scenario === scnId ? { manifest: scnManifest, cond: scnConditions, run: scnRun } : null;

  const [step, setStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [playbackMs, setPlaybackMs] = useState(250);
  const [eventTag, setEventTag] = useState("district_daily_peak");
  const [selectedBuilding, setSelectedBuilding] = useState("");

  const buildingIds = useMemo(() => manifest?.buildings ?? [], [manifest]);
  // The contract's scope is either a short sample window or the full simulated year.
  // All arrays are indexed locally within that scope; never hard-code the sample's 48 steps.
  const n = scn
    ? Math.min(scn.run.scope.n_steps, scn.cond.local_time.length, scn.run.district.import_kwh_el.length)
    : Math.min(
      run?.scope.n_steps ?? 0,
      conditions?.scope.n_steps ?? 0,
      run?.district.net_kwh_el.length ?? 0,
      conditions?.local_time.length ?? 0,
      conditions?.series.temp_c.length ?? 0,
    );
  // open on the first evening peak of the window (the hour the story is about) until the visitor moves the time;
  // a scenario opens at noon of its first jump target (the heat wave) or at its largest export hour
  const scnDefault = useMemo(() => {
    if (!scnManifest || !scnRun) return 0;
    const target = scnManifest.jump_targets[0]?.steps[0];
    if (target != null) return target + 13;
    const ex = scnRun.district.export_kwh_el;
    return ex.reduce((best, v, k) => (v > ex[best] ? k : best), 0);
  }, [scnManifest, scnRun]);
  const firstPeak = scn ? scnDefault : (run?.situations.district.district_daily_peak?.[0] ?? 0);
  const i = Math.min(step ?? firstPeak, Math.max(0, n - 1));
  useEffect(() => {
    if (!playing || n < 1) return;
    const timer = window.setInterval(() => setStep((current) => ((current ?? firstPeak) + 1) % n), playbackMs);
    return () => window.clearInterval(timer);
  }, [playing, n, playbackMs, firstPeak]);

  const chooseScenario = (id: string) => {
    setScenarioId(id); setStep(null); setPlaying(false); setSelectedBuilding("");
    setEventTag(scenarioIndex?.scenarios.find((e) => e.id === id)?.jump_targets[0]?.id ?? "district_daily_peak");   // a scenario with a heat wave offers it first
  };
  const switchOptions = [{ id: PHASE_A, label: PHASE_A_LABEL }, ...(scenarioIndex?.scenarios ?? []).map((e) => ({ id: e.id, label: e.label, title: e.description }))];
  const switchEl = scenarioIndex && scenarioIndex.scenarios.length > 0 ? <ScenarioSwitch options={switchOptions} value={scenarioId} onChange={chooseScenario} /> : null;

  if (!manifest || !buildings || !conditions || !run || (scnId && !scn)) {
    return (
      <div className="space-y-3">
        {switchEl}
        <div className="flex aspect-[16/9] items-center justify-center rounded-2xl border bg-muted/30 text-sm text-muted-foreground">{scnId && manifest ? "Loading the full-year scenario…" : "Loading the district simulation…"}</div>
      </div>
    );
  }

  const stepSeconds = (scn ? scn.manifest.time_axis : manifest.time_axis).step_seconds;
  const toKw = (kwh: number | null | undefined) => kwOf(kwh, stepSeconds);
  const jump = (s: number) => { setPlaying(false); setStep(Math.max(0, Math.min(n - 1, s))); };

  const localTime = scn ? scn.cond.local_time : conditions.local_time;
  const tierArr = scn ? scn.cond.series.tariff_tier : conditions.series.tariff_tier;
  const features = scn?.manifest.features;
  const drawAt = (k: number) => (scn ? scn.run.district.import_kwh_el[k] : run.district.net_kwh_el[k]);
  const exportAt = (k: number) => (scn ? scn.run.district.export_kwh_el[k] ?? 0 : 0);

  const sceneBuildings: SceneBuilding[] = buildingIds.flatMap((id) => {
    const info = buildings[id];
    if (!info) return [];
    const base = { role: id, type: info.type, short: shortName(info), sub: subLine(info) };
    if (scn) {
      const sr: ScenarioBuildingSeries | undefined = scn.run.buildings[id];
      const eq = scn.manifest.equipment[id];
      if (!sr) return [];
      const cool = sr.hp_cool_kwh_el ? toKw(sr.hp_cool_kwh_el[i]) : null;
      return [{
        ...base, gridKw: toKw(sr.import_kwh_el[i]), hpKw: toKw(sr.hp_sh_kwh_el[i] + sr.hp_hw_kwh_el[i] + (sr.hp_cool_kwh_el?.[i] ?? 0)),
        extras: {
          solarKw: toKw(sr.pv_kwh_el[i]), solarKwp: typeof eq?.pv_kwp.value === "number" ? eq.pv_kwp.value : null,
          batterySoc: sr.battery_soc[i] ?? null, batteryKw: toKw(sr.battery_charge_kwh_el[i] - sr.battery_discharge_kwh_el[i]),
          exportKw: toKw(sr.export_kwh_el[i]), tempIn: sr.temp_in_c[i] ?? null, coolKw: cool,
        },
      }];
    }
    const series = run.buildings[id];
    return [{ ...base, gridKw: toKw(series?.net_kwh_el[i]), hpKw: series ? toKw((series.hp_sh_kwh_el[i] ?? 0) + (series.hp_hw_kwh_el[i] ?? 0)) : null }];
  });

  const temp = (scn ? scn.cond.series.temp_c : conditions.series.temp_c)[i] ?? null;
  const price = (scn ? scn.cond.series.price_chf_kwh : conditions.series.price_chf_kwh)[i] ?? null;
  const tier = tierArr[i];
  const when = localParts(localTime[i]);
  const totalKw = toKw(drawAt(i));
  const controllerName = scn ? (scn.manifest.controllers.find((c) => c.id === scnCtrl)?.display_name ?? scnCtrl) : (manifest.controllers.find((c) => c.id === controllerProp)?.display_name ?? controllerProp);

  type JumpOption = { id: string; label: string; title?: string; steps: number[] };
  const tagOptions = (events: Record<string, string>, tags: Record<string, number[]>, texts: Record<string, string>): JumpOption[] =>
    Object.entries(events).filter(([tag]) => tags[tag]).map(([tag, label]) => ({ id: tag, label, title: texts[tag], steps: tags[tag] }));
  const jumpOptions: JumpOption[] = scn
    ? [...scn.manifest.jump_targets.map((j) => ({ id: j.id, label: j.label, title: j.description, steps: j.steps })),
       ...tagOptions(SCENARIO_EVENTS, scn.run.situations.district, scn.manifest.situation_tags)]
    : tagOptions(EVENTS, run.situations.district, manifest.situation_tags);
  const activeEvent = jumpOptions.find((o) => o.id === eventTag) ?? jumpOptions[0];
  const eventSteps = activeEvent?.steps ?? [];
  const previousEvent = [...eventSteps].reverse().find((s) => s < i);
  const nextEvent = eventSteps.find((s) => s > i);

  const selectedId = buildings[selectedBuilding] ? selectedBuilding : (buildingIds.filter((id) => buildings[id]?.type === "MFH")[1] ?? buildingIds[0] ?? "");
  const selectedInfo: BuildingInfo | undefined = buildings[selectedId];
  const sel = run.buildings[selectedId];
  const selectedStep = sel ? {
    net: sel.net_kwh_el[i] ?? null, hpSh: sel.hp_sh_kwh_el[i] ?? null, hpHw: sel.hp_hw_kwh_el[i] ?? null, household: sel.household_kwh_el[i] ?? null,
    shDemand: sel.sh_demand_kwh_th[i] ?? null, hwDemand: sel.hw_demand_kwh_th[i] ?? null, hpShDirect: sel.hp_sh_direct_kwh_th[i] ?? null,
    hpShToTank: sel.hp_sh_to_tank_kwh_th[i] ?? null, shTankToDemand: sel.sh_tank_to_demand_kwh_th[i] ?? null, shTankLoss: sel.sh_tank_loss_kwh_th[i] ?? null,
    shSoc: sel.sh_tank_soc[i] ?? null, hpHwDirect: sel.hp_hw_direct_kwh_th[i] ?? null, hpHwToTank: sel.hp_hw_to_tank_kwh_th?.[i] ?? null,
    hwTankToDemand: sel.hw_tank_to_demand_kwh_th?.[i] ?? null, hwTankLoss: sel.hw_tank_loss_kwh_th?.[i] ?? null, hwSoc: sel.hw_tank_soc?.[i] ?? null,
  } : null;
  const cop = sel?.cop_sh?.[i] ?? null;
  const hasHwTank = selectedInfo?.components.tank_hw.present ?? false;
  const sc = scn?.run.buildings[selectedId];
  const scStep = sc ? {
    imp: sc.import_kwh_el[i], exp: sc.export_kwh_el[i], pv: sc.pv_kwh_el[i], household: sc.household_kwh_el[i], hpSh: sc.hp_sh_kwh_el[i], hpHw: sc.hp_hw_kwh_el[i],
    cool: sc.hp_cool_kwh_el ? sc.hp_cool_kwh_el[i] : null, charge: sc.battery_charge_kwh_el[i], discharge: sc.battery_discharge_kwh_el[i], soc: sc.battery_soc[i], tempIn: sc.temp_in_c[i],
  } : null;
  const equipment = scn?.manifest.equipment[selectedId];

  // 48-hour strip around the current hour, starting at midnight: grid purchase upwards, export (scenarios) downwards from the zero line
  const stripStart = Math.max(0, Math.min(Math.floor(i / 24) * 24, n - STRIP));
  const stripLen = Math.min(STRIP, n);
  const stripImp = Array.from({ length: stripLen }, (_, k) => toKw(drawAt(stripStart + k)) ?? 0);
  const stripExp = Array.from({ length: stripLen }, (_, k) => toKw(exportAt(stripStart + k)) ?? 0);
  const maxImp = Math.max(1, ...stripImp), maxExp = Math.max(0, ...stripExp);
  const stripTotal = maxImp + maxExp;
  const zero = maxExp / stripTotal;    // fraction of the strip height below the zero line (0 in Phase A)
  const bands: { from: number; to: number }[] = [];
  for (let k = 0; k < stripLen; k++) {
    if (tierArr[stripStart + k] !== "high") continue;
    const last = bands[bands.length - 1];
    if (last && last.to === k) last.to = k + 1; else bands.push({ from: k, to: k + 1 });
  }
  const ticks = Array.from({ length: Math.ceil(stripLen / 12) }, (_, k) => k * 12).map((k) => {
    const p = localParts(localTime[stripStart + k]);
    return { k, label: p.time === "00:00" ? p.short : p.time };
  });
  const batteryState = scStep ? (scStep.charge > 0.005 ? "charging" : scStep.discharge > 0.005 ? "discharging" : "idle") : "";
  const exportPrice = scn && typeof scn.manifest.export_price_chf_kwh.value === "number" ? scn.manifest.export_price_chf_kwh.value : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white text-zinc-900 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 px-4 pt-4 sm:px-6 sm:pt-5">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">The district, hour by hour{scn ? ` · ${scn.manifest.scenario.short_label}` : ""}</p>
          <p className="text-lg font-semibold tracking-tight sm:text-xl">Six heat-pump buildings on Swiss weather and tariffs</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Stat label={when.day} value={when.time} />
          <Stat label="Outside" value={temp == null ? "—" : `${f(temp, 1).replace("-", "−")} °C`} />
          <Stat label="Tariff" value={price == null ? "—" : `${tier === "high" ? "High" : "Low"} · ${f(price * 100, 2)} Rp/kWh`} />
          {scn && <Stat label="Solar" value={`${f(toKw(scn.run.district.pv_kwh_el[i]), 1)} kW`} tone="solar" />}
          {scn && <Stat label="To grid" value={`${f(toKw(scn.run.district.export_kwh_el[i]), 1)} kW`} tone="export" />}
          <Stat label="District grid draw" value={totalKw == null ? "—" : `${f(totalKw, 1)} kW`} tone="blue" />
        </div>
      </div>

      <div className="mt-4 flex flex-col border-y border-zinc-100 xl:flex-row">
        <div className="min-w-0 flex-1 p-3 sm:p-4">
          <Scene buildings={sceneBuildings} selected={selectedId} onSelect={setSelectedBuilding} />
        </div>
        {selectedInfo && scn && scStep && (
          <section aria-label="Selected building" className="flex w-full flex-col gap-4 border-t border-zinc-100 p-5 md:grid md:grid-cols-2 md:gap-x-8 xl:flex xl:w-[340px] xl:border-l xl:border-t-0">
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Selected building</p>
              <h3 className="text-lg font-semibold">{selectedInfo.display_name}</h3>
              <p className="text-xs leading-relaxed text-zinc-500">{subLine(selectedInfo)} · {selectedInfo.type === "SFH" ? "metered household load" : "household load built from sampled apartment meters"}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-xl bg-blue-50 px-3 py-3">
                <p className="text-xs text-blue-800">From the grid</p>
                <p className="text-2xl font-semibold tracking-tight text-blue-700 tabular-nums">{f(toKw(scStep.imp), 1)} <span className="text-sm font-medium">kW</span></p>
              </div>
              <div className="rounded-xl bg-violet-50 px-3 py-3">
                <p className="text-xs text-violet-800">To the grid</p>
                <p className="text-2xl font-semibold tracking-tight text-violet-700 tabular-nums">{f(toKw(scStep.exp), 1)} <span className="text-sm font-medium">kW</span></p>
              </div>
            </div>
            <div>
              <Row label={`Solar panels${typeof equipment?.pv_kwp.value === "number" ? ` (${f(equipment.pv_kwp.value, 1)} kWp, assumed)` : ""}`} value={`${f(toKw(scStep.pv), 1)} kW`} strong colour={PALETTE.solar} />
              <Row label={`Battery ${batteryState}`} value={`${f(toKw(scStep.charge - scStep.discharge), 1).replace("-", "−")} kW`} strong colour={PALETTE.battery} />
              <Row label="Heat pump, heating" value={`${f(toKw(scStep.hpSh), 1)} kW`} strong />
              <Row label="Heat pump, hot water" value={`${f(toKw(scStep.hpHw), 1)} kW`} />
              {features?.cooling && <Row label="Cooling" value={scStep.cool == null ? "no cooling device" : `${f(toKw(scStep.cool), 1)} kW`} strong={scStep.cool != null} colour={scStep.cool != null ? PALETTE.cool : undefined} />}
              <Row label="Household appliances" value={`${f(toKw(scStep.household), 1)} kW`} />
              <Row label="Indoor temperature (modeled)" value={`${f(scStep.tempIn, 1).replace("-", "−")} °C`} colour={scStep.tempIn > 26 ? PALETTE.alert : undefined} strong={scStep.tempIn > 26} />
            </div>
            <div className="space-y-2.5">
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Stored electricity · assumed battery{typeof equipment?.battery_kwh.value === "number" ? `, ${f(equipment.battery_kwh.value, 0)} kWh` : ""}</p>
              <Level label="Battery" soc={scStep.soc} hex={PALETTE.battery} />
            </div>
          </section>
        )}
        {selectedInfo && !scn && selectedStep && (
          <section aria-label="Selected building" className="flex w-full flex-col gap-4 border-t border-zinc-100 p-5 md:grid md:grid-cols-2 md:gap-x-8 xl:flex xl:w-[340px] xl:border-l xl:border-t-0">
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Selected building</p>
              <h3 className="text-lg font-semibold">{selectedInfo.display_name}</h3>
              <p className="text-xs leading-relaxed text-zinc-500">{subLine(selectedInfo)} · {selectedInfo.type === "SFH" ? "metered household load" : "household load built from sampled apartment meters"}</p>
            </div>
            <div className="rounded-xl bg-blue-50 px-4 py-3">
              <p className="text-xs text-blue-800">Electricity from the grid</p>
              <p className="text-3xl font-semibold tracking-tight text-blue-700 tabular-nums">{f(toKw(selectedStep.net), 1)} <span className="text-base font-medium">kW</span></p>
            </div>
            <div>
              <Row label="Heat pump" value={`${f(toKw((selectedStep.hpSh ?? 0) + (selectedStep.hpHw ?? 0)), 1)} kW`} strong />
              <Row label="space heating · hot water" value={`${f(toKw(selectedStep.hpSh), 1)} · ${f(toKw(selectedStep.hpHw), 1)} kW`} />
              <Row label="Heat per unit of electricity (COP)" value={f(cop, 1)} />
              <Row label="Household appliances" value={`${f(toKw(selectedStep.household), 1)} kW`} />
            </div>
            <div className="space-y-2.5">
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Stored heat · assumed tank sizes</p>
              <Level label="Heating tank" soc={selectedStep.shSoc} colour="bg-orange-600" />
              <Level label="Hot-water tank" soc={hasHwTank ? selectedStep.hwSoc : null} colour="bg-orange-400" />
            </div>
          </section>
        )}
      </div>
      {selectedInfo && selectedStep && !scn && (
        <details className="group border-b border-zinc-100 px-4 py-3 text-xs text-zinc-600 sm:px-6">
          <summary className="cursor-pointer select-none font-medium text-zinc-700 hover:text-zinc-900">How heat moves inside {selectedInfo.display_name.toLowerCase()}</summary>
          <div className="mt-3"><BuildingCutaway building={selectedInfo} state={selectedStep} stepSeconds={stepSeconds} /></div>
        </details>
      )}

      <div className="flex gap-3 px-4 pt-4 sm:gap-4 sm:px-6">
        <Button size="icon" variant="outline" className="mt-2 size-11 shrink-0 rounded-full" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "Pause" : "Play"}>
          {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
        </Button>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="relative h-14" role="group" aria-label={scn ? "District grid draw and export by hour; select an hour" : "District grid draw by hour; select an hour"}>
            {bands.map((b) => (
              <div key={b.from} className="absolute inset-y-0 border-x border-dashed border-zinc-200 bg-zinc-50" style={{ left: `${(b.from / stripLen) * 100}%`, width: `${((b.to - b.from) / stripLen) * 100}%` }} />
            ))}
            {scn && <div className="absolute inset-x-0 h-px bg-zinc-300" style={{ bottom: `${zero * 100}%` }} />}
            <div className="absolute inset-0 flex">
              {stripImp.map((v, k) => {
                const s = stripStart + k;
                const p = localParts(localTime[s]);
                const e = stripExp[k];
                return (
                  <button key={s} type="button" onClick={() => jump(s)} aria-label={`${p.short} ${p.time}, ${f(v, 1)} kW from the grid${scn ? `, ${f(e, 1)} kW to the grid` : ""}`} aria-current={s === i ? "true" : undefined}
                    className="group relative h-full flex-1 px-[1px] sm:px-0.5">
                    <span className={cn("absolute inset-x-[1px] block rounded-t-[2px] transition-colors sm:inset-x-0.5", s === i ? "bg-blue-600" : "bg-blue-200 group-hover:bg-blue-300")}
                      style={{ bottom: `${zero * 100}%`, height: `${Math.max(2, (v / stripTotal) * 100)}%` }} />
                    {e > 0.005 && (
                      <span className="absolute inset-x-[1px] block rounded-b-[2px] sm:inset-x-0.5" style={{ top: `${(1 - zero) * 100}%`, height: `${Math.max(2, (e / stripTotal) * 100)}%`, background: PALETTE.export, opacity: s === i ? 1 : 0.55 }} />
                    )}
                  </button>
                );
              })}
            </div>
            {i >= stripStart && i < stripStart + stripLen && (
              <div className="pointer-events-none absolute -top-1 bottom-0 w-0.5 -translate-x-1/2 rounded bg-zinc-900" style={{ left: `${((i - stripStart + 0.5) / stripLen) * 100}%` }} />
            )}
          </div>
          <div className="relative h-4 text-[11px] text-zinc-500">
            {ticks.map((t) => <span key={t.k} className="absolute" style={{ left: `${(t.k / stripLen) * 100}%` }}>{t.label}</span>)}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 pb-4 pt-3 text-xs text-zinc-600 sm:px-6">
        <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px] bg-blue-300" />District grid draw</span>
        {scn && <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px]" style={{ background: PALETTE.export, opacity: 0.55 }} />Export to the grid</span>}
        <span className="flex items-center gap-1.5"><span className="size-2.5 border border-dashed border-zinc-300 bg-zinc-50" />High-tariff hours</span>
        <span className="mx-1 hidden h-4 w-px bg-zinc-200 sm:block" />
        {switchEl}
        <label className="flex items-center gap-1.5">Controller
          {scn ? (
            <select value={scnCtrl ?? ""} onChange={(e) => setScnController(e.target.value)} className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-xs text-zinc-900">
              {scn.manifest.controllers.map((c) => <option key={c.id} value={c.id} title={c.note}>{c.display_name}</option>)}
            </select>
          ) : (
            <select value={controllerProp} onChange={(e) => onController(e.target.value)} className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-xs text-zinc-900">
              {manifest.controllers.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
            </select>
          )}
        </label>
        <label className="flex items-center gap-1.5">Speed
          <select value={playbackMs} onChange={(e) => setPlaybackMs(Number(e.target.value))} className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-xs text-zinc-900">
            <option value={500}>Slow</option>
            <option value={250}>Normal</option>
            <option value={60}>Fast</option>
          </select>
        </label>
        <span className="flex items-center gap-1">
          <label htmlFor={`district-event-${variant}`}>Jump to</label>
          <select id={`district-event-${variant}`} value={activeEvent?.id ?? ""} onChange={(e) => setEventTag(e.target.value)} className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-xs text-zinc-900">
            {jumpOptions.map((o) => <option key={o.id} value={o.id} title={o.title}>{o.label}</option>)}
          </select>
          <Button size="icon" variant="outline" className="size-8" disabled={previousEvent == null} onClick={() => jump(previousEvent!)} aria-label="Previous event"><ChevronLeft className="size-4" /></Button>
          <Button size="icon" variant="outline" className="size-8" disabled={nextEvent == null} onClick={() => jump(nextEvent!)} aria-label="Next event"><ChevronRight className="size-4" /></Button>
          {activeEvent && scn && scn.manifest.jump_targets.some((j) => j.id === activeEvent.id) && (
            <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => jump(activeEvent.steps[0])}>Go</Button>
          )}
        </span>
        {n > STRIP && (
          <input type="range" min={0} max={n - 1} value={i} onChange={(e) => jump(+e.target.value)} className="min-w-40 flex-1 accent-zinc-900" aria-label="Hour of the year" />
        )}
      </div>

      <p className="border-t border-zinc-100 px-4 py-3 text-[11px] leading-relaxed text-zinc-500 sm:px-6">
        {controllerName}. Illustrative layout and massing: the buildings come from two Swiss datasets and are not neighbours; no shared grid or heat network is modeled.
        {scn && <> {scn.manifest.scenario.description} Solar panels and batteries have assumed sizes (one kWh of battery per kWp of panels), room temperature is modeled{exportPrice != null ? `, and export is paid at an assumed ${f(exportPrice * 100, 0)} Rp/kWh` : ""}.</>}
        {" "}{(scn ? "year" : run.scope.kind) === "year" ? "Full-year simulation" : "Sample window"}, {n.toLocaleString()} hourly steps.
      </p>
    </div>
  );
}
