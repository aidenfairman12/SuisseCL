"use client";
import { useEffect, useMemo, useState } from "react";
import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useBundleFile } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";
import type { Figures, Results, SeriesInputs, Trace } from "@/lib/types";
import { Scene, type SceneState } from "./scene";

const WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const f = (v: number | null | undefined, d: number) => (v == null || Number.isNaN(v) ? "–" : (+v).toFixed(d));
const argmax = (a: (number | null)[], sign: 1 | -1) => {
  let b = -1;
  for (let i = 0; i < a.length; i++) if (a[i] != null && (b < 0 || sign * (a[i] as number) > sign * (a[b] as number))) b = i;
  return Math.max(b, 0);
};
const maxOf = (a: (number | null)[]) => a.reduce<number>((m, v) => (v != null && v > m ? v : m), 0);

export const DEFAULT_CONTROLLER = "ALG-003_basic_rbc";

/** Illustrated district for one controller and one hour. Controlled from outside so other panels can share the controller. */
export function DistrictView({ controller, onController }: { controller: string; onController: (c: string) => void }) {
  const { open } = useNodeParam();
  const fig = useBundleFile<Figures>("figures").data;
  const si = useBundleFile<SeriesInputs>("series_inputs").data;
  const res = useBundleFile<Results>("results").data;
  const src = res?.traces[controller] ? (res.traces[controller].same_as ?? controller) : null;
  const tr = useBundleFile<Trace>(src ? `trace_${src}` : null).data;
  const [hour, setHour] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(3);
  const T = tr?.arrays ?? null;
  const n = T ? T.district_net_kwh.length : 0;

  // until the user picks an hour, show the district peak hour of the selected controller
  const peak = useMemo(() => (T ? argmax(T.district_net_kwh, 1) : 0), [T]);
  useEffect(() => {
    if (!playing || !n) return;
    const id = setInterval(() => setHour((h) => ((h ?? peak) + speed) % n), 140);
    return () => clearInterval(id);
  }, [playing, speed, n, peak]);

  const maxima = useMemo(() => {
    if (!T) return { net: 1, hp: 1 };
    let net = 1, hp = 1;
    for (let b = 1; b <= 6; b++) { net = Math.max(net, maxOf(T[`b${b}_net_kwh`])); hp = Math.max(hp, maxOf(T[`b${b}_hp_kwh_el`])); }
    return { net, hp };
  }, [T]);

  if (!fig || !si || !res) return <div className="flex aspect-[16/9] items-center justify-center rounded-2xl border bg-muted/30 text-sm text-muted-foreground">Loading the district…</div>;

  const i = Math.min(hour ?? peak, si.n - 1);
  const S = si.series;
  const ghi = S.ghi.values[i] ?? 0, night = ghi < 5, k = Math.min(1, ghi / 700);
  const lh = si.local_hour[i] + 0.5, frac = Math.max(0, Math.min(1, (lh - 5) / 16));
  const at = (name: string) => (T && i < n ? T[name]?.[i] ?? null : null);
  const fb = si.flags.neighbour_intensity_fallback_flag.values[i], ip = si.flags.gap_interpolated_flag.values[i];
  const bs = fig.district.buildings;
  const bstate = bs.map((_, j) => ({ net: at(`b${j + 1}_net_kwh`), hp: at(`b${j + 1}_hp_kwh_el`), socHeat: at(`b${j + 1}_heating_storage_soc`), socDhw: at(`b${j + 1}_dhw_storage_soc`), actionHeat: at(`b${j + 1}_action_heating_storage`) }));
  const dnet = bstate.reduce((a, b) => a + (b.net ?? 0), 0);
  const state: SceneState = {
    night, ghiK: k, sunX: 200 + frac * 900, sunY: 330 - Math.sin(frac * Math.PI) * 220,
    tariff: `${f(S.price.values[i], 2)} Rp/kWh · ${si.tier_high[i] ? "high" : "low"} tariff`, tariffSub: "EKZ standard 2023, excl. VAT",
    carbon: `${f(S.carbon.values[i], 1)} gCO2eq/kWh`, carbonSub: `${fb ? "⚑ neighbour fallback · " : ip ? "⚑ missing hour · " : ""}modeled, relative signal only`,
    weather: `${f(S.temp_c.values[i], 1)} °C · GHI ${f(S.ghi.values[i], 0)} W/m²`, weatherSub: "measured, MeteoSwiss KLO",
    controller, reward: T ? `${f(T.reward[i], 3)} this step` : "no trace",
    maxNet: maxima.net, maxHp: maxima.hp, busFlow: Math.max(dnet, 0), buildings: bstate,
  };
  const local = new Date(Date.parse(si.start_utc) + (i * si.step_s + si.utc_offset_h[i] * 3600) * 1000).toISOString().slice(0, 16).replace("T", " ");
  const observed = new Set(fig.env_interface.observations_active);
  const jump = (what: "peak" | "cold" | "sun" | "night") => {
    if (what === "peak" && T) setHour(argmax(T.district_net_kwh, 1));
    if (what === "cold") setHour(argmax(S.temp_c.values, -1));
    if (what === "sun") setHour(argmax(S.ghi.values, 1));
    if (what === "night") { const c = argmax(S.temp_c.values, -1); const h = c - si.local_hour[c] + 2; setHour(h > 0 ? h : c); }
  };
  return (
    <div className="space-y-2">
      <Scene buildings={bs} state={state} observed={observed} open={open} />
      <div className="flex flex-wrap items-center gap-2">
        <Button size="icon" variant="outline" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "pause" : "play"}>{playing ? <Pause className="size-4" /> : <Play className="size-4" />}</Button>
        <select value={speed} onChange={(e) => setSpeed(+e.target.value)} className="h-8 rounded-lg border bg-background px-2 text-sm" aria-label="speed">
          <option value={1}>1 h per step</option><option value={3}>3 h per step</option><option value={24}>1 day per step</option>
        </select>
        <select value={controller} onChange={(e) => onController(e.target.value)} className="h-8 rounded-lg border bg-background px-2 text-sm" aria-label="controller">
          {res.rows.map((r) => <option key={r.controller} value={r.controller}>{r.controller}</option>)}
        </select>
        <input type="range" min={0} max={Math.max(n - 1, 0)} value={i} onChange={(e) => setHour(+e.target.value)} className="min-w-48 flex-1 accent-amber-500" aria-label="hour of the year" />
        <div className="flex flex-wrap gap-1">
          {([["peak", "district peak hour"], ["cold", "coldest hour"], ["sun", "sunniest hour"], ["night", "a winter night"]] as const).map(([k2, label]) => (
            <Button key={k2} size="sm" variant="outline" onClick={() => jump(k2)}>{label}</Button>
          ))}
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        <b className="text-foreground">{local}</b> local · {WD[si.weekday[i]]} · step {i} · district net <b className="text-foreground">{T ? `${f(dnet, 2)} kWh` : "–"}</b> · {controller}
      </p>
    </div>
  );
}
