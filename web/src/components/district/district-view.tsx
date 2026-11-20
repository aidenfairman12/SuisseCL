"use client";
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useManifest, useBuildings, useConditions, useRun } from "@/lib/contract";
import type { BuildingInfo } from "@/lib/contract";
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

function Stat({ label, value, tone }: { label: string; value: string; tone?: "blue" }) {
  return (
    <div className={cn("flex flex-col rounded-lg border px-3 py-1.5", tone === "blue" ? "border-blue-200 bg-blue-50" : "border-zinc-200 bg-white")}>
      <span className={cn("text-[11px]", tone === "blue" ? "text-blue-800" : "text-zinc-500")}>{label}</span>
      <span className={cn("text-sm font-semibold tabular-nums", tone === "blue" && "text-blue-700")}>{value}</span>
    </div>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-zinc-100 py-2">
      <span className="text-[13px] text-zinc-600">{label}</span>
      <span className={cn("text-[13px] tabular-nums", strong && "text-sm font-semibold text-orange-700")}>{value}</span>
    </div>
  );
}

function Level({ label, soc, colour }: { label: string; soc: number | null; colour: string }) {
  const v = soc == null ? null : Math.max(0, Math.min(1, soc));
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs"><span className="text-zinc-600">{label}</span><span className="tabular-nums">{v == null ? "not modeled" : `${f(v * 100, 0)} %`}</span></div>
      <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100"><div className={cn("h-1.5 rounded-full", colour)} style={{ width: `${(v ?? 0) * 100}%` }} /></div>
    </div>
  );
}

export function DistrictView({ controller: controllerProp, onController, variant = "full" }: { controller: string; onController: (c: string) => void; variant?: "sample" | "full" }) {
  const manifestFile = useManifest(variant);
  const buildingsFile = useBuildings(variant);
  const conditionsFile = useConditions(variant);
  const runFile = useRun("base", controllerProp || DEFAULT_CONTROLLER, variant);
  const manifest = manifestFile.data;
  const buildings = buildingsFile.data?.buildings;
  const conditions = conditionsFile.data;
  const run = runFile.data;
  const [step, setStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [playbackMs, setPlaybackMs] = useState(250);
  const [eventTag, setEventTag] = useState("district_daily_peak");
  const [selectedBuilding, setSelectedBuilding] = useState("");

  const buildingIds = useMemo(() => manifest?.buildings ?? [], [manifest]);
  // The contract's scope is either a short sample window or the full simulated year.
  // All arrays are indexed locally within that scope; never hard-code the sample's 48 steps.
  const n = Math.min(
    run?.scope.n_steps ?? 0,
    conditions?.scope.n_steps ?? 0,
    run?.district.net_kwh_el.length ?? 0,
    conditions?.local_time.length ?? 0,
    conditions?.series.temp_c.length ?? 0,
  );
  // open on the first evening peak of the window (the hour the story is about) until the visitor moves the time
  const firstPeak = run?.situations.district.district_daily_peak?.[0] ?? 0;
  const i = Math.min(step ?? firstPeak, Math.max(0, n - 1));
  useEffect(() => {
    if (!playing || n < 1) return;
    const timer = window.setInterval(() => setStep((current) => ((current ?? firstPeak) + 1) % n), playbackMs);
    return () => window.clearInterval(timer);
  }, [playing, n, playbackMs, firstPeak]);

  if (!manifest || !buildings || !conditions || !run) {
    return <div className="flex aspect-[16/9] items-center justify-center rounded-2xl border bg-muted/30 text-sm text-muted-foreground">Loading the district simulation…</div>;
  }

  const stepSeconds = manifest.time_axis.step_seconds;
  const toKw = (kwh: number | null | undefined) => kwh == null || !Number.isFinite(kwh) ? null : kwh / (stepSeconds / 3600);
  const jump = (s: number) => { setPlaying(false); setStep(Math.max(0, Math.min(n - 1, s))); };

  const sceneBuildings: SceneBuilding[] = buildingIds.flatMap((id) => {
    const info = buildings[id];
    const series = run.buildings[id];
    if (!info) return [];
    return [{
      role: id, type: info.type, short: shortName(info), sub: subLine(info),
      gridKw: toKw(series?.net_kwh_el[i]),
      hpKw: series ? toKw((series.hp_sh_kwh_el[i] ?? 0) + (series.hp_hw_kwh_el[i] ?? 0)) : null,
    }];
  });

  const temp = conditions.series.temp_c[i] ?? null;
  const price = conditions.series.price_chf_kwh[i] ?? null;
  const tier = conditions.series.tariff_tier[i];
  const when = localParts(conditions.local_time[i]);
  const totalKw = toKw(run.district.net_kwh_el[i]);
  const controllerName = manifest.controllers.find((c) => c.id === controllerProp)?.display_name ?? controllerProp;

  const eventSteps = run.situations.district[eventTag] ?? [];
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

  // 48-hour strip around the current hour, starting at midnight
  const stripStart = Math.max(0, Math.min(Math.floor(i / 24) * 24, n - STRIP));
  const stripLen = Math.min(STRIP, n);
  const stripNet = Array.from({ length: stripLen }, (_, k) => toKw(run.district.net_kwh_el[stripStart + k]) ?? 0);
  const stripMax = Math.max(1, ...stripNet);
  const bands: { from: number; to: number }[] = [];
  for (let k = 0; k < stripLen; k++) {
    if (conditions.series.tariff_tier[stripStart + k] !== "high") continue;
    const last = bands[bands.length - 1];
    if (last && last.to === k) last.to = k + 1; else bands.push({ from: k, to: k + 1 });
  }
  const ticks = Array.from({ length: Math.ceil(stripLen / 12) }, (_, k) => k * 12).map((k) => {
    const p = localParts(conditions.local_time[stripStart + k]);
    return { k, label: p.time === "00:00" ? p.short : p.time };
  });

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white text-zinc-900 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 px-4 pt-4 sm:px-6 sm:pt-5">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">The district, hour by hour</p>
          <p className="text-lg font-semibold tracking-tight sm:text-xl">Six heat-pump buildings on Swiss weather and tariffs</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Stat label={when.day} value={when.time} />
          <Stat label="Outside" value={temp == null ? "—" : `${f(temp, 1).replace("-", "−")} °C`} />
          <Stat label="Tariff" value={price == null ? "—" : `${tier === "high" ? "High" : "Low"} · ${f(price * 100, 2)} Rp/kWh`} />
          <Stat label="District grid draw" value={totalKw == null ? "—" : `${f(totalKw, 1)} kW`} tone="blue" />
        </div>
      </div>

      <div className="mt-4 flex flex-col border-y border-zinc-100 xl:flex-row">
        <div className="min-w-0 flex-1 p-3 sm:p-4">
          <Scene buildings={sceneBuildings} selected={selectedId} onSelect={setSelectedBuilding} />
        </div>
        {selectedInfo && selectedStep && (
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
      {selectedInfo && selectedStep && (
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
          <div className="relative h-14" role="group" aria-label="District grid draw by hour; select an hour">
            {bands.map((b) => (
              <div key={b.from} className="absolute inset-y-0 border-x border-dashed border-zinc-200 bg-zinc-50" style={{ left: `${(b.from / stripLen) * 100}%`, width: `${((b.to - b.from) / stripLen) * 100}%` }} />
            ))}
            <div className="absolute inset-0 flex items-end">
              {stripNet.map((v, k) => {
                const s = stripStart + k;
                const p = localParts(conditions.local_time[s]);
                return (
                  <button key={s} type="button" onClick={() => jump(s)} aria-label={`${p.short} ${p.time}, ${f(v, 1)} kW`} aria-current={s === i ? "true" : undefined}
                    className="group flex h-full flex-1 items-end px-[1px] sm:px-0.5">
                    <span className={cn("block w-full rounded-t-[2px] transition-colors", s === i ? "bg-blue-600" : "bg-blue-200 group-hover:bg-blue-300")} style={{ height: `${Math.max(2, (v / stripMax) * 100)}%` }} />
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
        <span className="flex items-center gap-1.5"><span className="size-2.5 border border-dashed border-zinc-300 bg-zinc-50" />High-tariff hours</span>
        <span className="mx-1 hidden h-4 w-px bg-zinc-200 sm:block" />
        <label className="flex items-center gap-1.5">Controller
          <select value={controllerProp} onChange={(e) => onController(e.target.value)} className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-xs text-zinc-900">
            {manifest.controllers.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}
          </select>
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
          <select id={`district-event-${variant}`} value={eventTag} onChange={(e) => setEventTag(e.target.value)} className="h-8 rounded-md border border-zinc-200 bg-white px-2 text-xs text-zinc-900">
            {Object.entries(EVENTS).filter(([tag]) => run.situations.district[tag]).map(([tag, label]) => <option key={tag} value={tag} title={manifest.situation_tags[tag]}>{label}</option>)}
          </select>
          <Button size="icon" variant="outline" className="size-8" disabled={previousEvent == null} onClick={() => jump(previousEvent!)} aria-label="Previous event"><ChevronLeft className="size-4" /></Button>
          <Button size="icon" variant="outline" className="size-8" disabled={nextEvent == null} onClick={() => jump(nextEvent!)} aria-label="Next event"><ChevronRight className="size-4" /></Button>
        </span>
        {n > STRIP && (
          <input type="range" min={0} max={n - 1} value={i} onChange={(e) => jump(+e.target.value)} className="min-w-40 flex-1 accent-zinc-900" aria-label="Hour of the year" />
        )}
      </div>

      <p className="border-t border-zinc-100 px-4 py-3 text-[11px] leading-relaxed text-zinc-500 sm:px-6">
        {controllerName}. Illustrative layout and massing: the buildings come from two Swiss datasets and are not neighbours; no shared grid or heat network is modeled.
        {" "}{run.scope.kind === "year" ? "Full-year simulation" : "Sample window"}, {n.toLocaleString()} hourly steps.
      </p>
    </div>
  );
}
