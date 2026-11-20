"use client";
// Axonometric drawing of the six modeled buildings. Massing and layout are illustrative (floor counts and site geometry are not in the data);
// what is live is each building's grid draw (label) and whether its heat pump runs (orange unit beside the building).
import { cn } from "@/lib/utils";
import { PALETTE } from "@/lib/palette";

/** Live values that exist only in the Phase B and Phase C scenarios (solar panels, battery, export, room temperature, cooling). */
export type SceneExtras = {
  solarKw: number | null; solarKwp: number | null;
  batterySoc: number | null; batteryKw: number | null;   // kw: positive = charging, negative = discharging
  exportKw: number | null; tempIn: number | null;
  coolKw: number | null;                                   // null = no cooling device in this building
};

export type SceneBuilding = {
  role: string;
  type: "SFH" | "MFH";
  short: string;
  sub: string;
  gridKw: number | null;
  hpKw: number | null;
  extras?: SceneExtras;
};

const W = 840;
const H = 560;
const S = 5.5;
const OX = 321;
const OY = 160;
const C = 0.866;
const ROOF = 4;
type Lot = { x: number; y: number; w: number; d: number; h: number };
// Plan positions in drawing units, per type in manifest order (houses: low → high use; apartments: small → large).
// Role codes are deliberately not used here; extra buildings beyond these lots are not drawn.
const LOTS: Record<SceneBuilding["type"], Lot[]> = {
  SFH: [{ x: 66, y: 46, w: 12, d: 10, h: 7 }, { x: 38, y: 44, w: 12, d: 10, h: 7 }, { x: 4, y: 38, w: 12, d: 10, h: 7 }],
  MFH: [{ x: 76, y: -4, w: 16, d: 12, h: 12 }, { x: 38, y: -4, w: 22, d: 14, h: 18 }, { x: 0, y: 0, w: 26, d: 16, h: 21 }],
};
const TREES: [number, number][] = [[100, 10], [104, 30], [14, 70], [30, 72], [-20, 0]];
const RUNNING_KW = 0.5;

const P = (x: number, y: number, z: number) => [OX + (x - y) * C * S, OY + (x + y) * 0.5 * S - z * S] as const;
const poly = (pts: [number, number, number][]) => "M" + pts.map((p) => P(...p).map((v) => v.toFixed(1)).join(" ")).join(" L") + " Z";
const quadX = (x0: number, x1: number, y: number, z0: number, z1: number) => poly([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]]);
const quadY = (x: number, y0: number, y1: number, z0: number, z1: number) => poly([[x, y0, z0], [x, y1, z0], [x, y1, z1], [x, y0, z1]]);

function geometry(lot: Lot, sfh: boolean) {
  const { x, y, w, d, h } = lot;
  const xw = x + w, yd = y + d, m = y + d / 2;
  let winL = "", winR = "", door = "";
  if (sfh) {
    winL = quadX(x + 2.2, x + 3.8, yd, 3.2, 4.8) + quadX(xw - 3.8, xw - 2.2, yd, 3.2, 4.8);
    door = quadX(x + w / 2 - 0.9, x + w / 2 + 0.9, yd, 0, 2.8);
    winR = quadY(xw, m - 0.8, m + 0.8, 3.2, 4.8);
  } else {
    const floors = Math.floor((h - 2) / 3);
    for (let f = 0; f < floors; f++) {
      const z = 1.6 + f * 3;
      for (let cx = x + 2; cx + 1.6 <= xw - 1.5; cx += 3.6) winL += quadX(cx, cx + 1.6, yd, z, z + 1.5);
      for (let cy = y + 2; cy + 1.6 <= yd - 1.5; cy += 3.6) winR += quadY(xw, cy, cy + 1.6, z, z + 1.5);
    }
  }
  const hx = xw + 1, hy = yd - 3.4, hw = 2.2, hd = 2.4, hh = 1.8;
  // rooftop solar array: an inset quad on the south roof plane of a house, on the flat roof of an apartment building, with cell lines
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
  const roofPt = (u: number, t: number): [number, number, number] => sfh ? [lerp(x, xw, u), lerp(m, yd, t), lerp(h + ROOF, h, t)] : [lerp(x, xw, u), lerp(y, yd, t), h];
  const u0 = sfh ? 0.12 : 0.1, u1 = sfh ? 0.88 : 0.9, t0 = sfh ? 0.14 : 0.12, t1 = sfh ? 0.86 : 0.88;
  const cols = sfh ? 4 : 6, rows = sfh ? 2 : 3;
  let cells = "";
  for (let c = 1; c < cols; c++) cells += poly([roofPt(lerp(u0, u1, c / cols), t0), roofPt(lerp(u0, u1, c / cols), t1), roofPt(lerp(u0, u1, c / cols), t1), roofPt(lerp(u0, u1, c / cols), t0)]);
  for (let r = 1; r < rows; r++) cells += poly([roofPt(u0, lerp(t0, t1, r / rows)), roofPt(u1, lerp(t0, t1, r / rows)), roofPt(u1, lerp(t0, t1, r / rows)), roofPt(u0, lerp(t0, t1, r / rows))]);
  // battery cabinet on the street side of the building
  const bw = 2.0, bd = 2.2, bh = 3.2, bx = x - 3.4, by = yd - 3.4;
  return {
    solar: poly([roofPt(u0, t0), roofPt(u1, t0), roofPt(u1, t1), roofPt(u0, t1)]), solarCells: cells,
    batL: quadX(bx, bx + bw, by + bd, 0, bh), batR: quadY(bx + bw, by, by + bd, 0, bh), batT: poly([[bx, by, bh], [bx + bw, by, bh], [bx + bw, by + bd, bh], [bx, by + bd, bh]]),
    batFill: (soc: number) => quadX(bx, bx + bw, by + bd, 0, Math.max(0.05, bh * Math.max(0, Math.min(1, soc)))),
    batFillR: (soc: number) => quadY(bx + bw, by, by + bd, 0, Math.max(0.05, bh * Math.max(0, Math.min(1, soc)))),
    back: sfh ? poly([[x, y, h], [xw, y, h], [xw, m, h + ROOF], [x, m, h + ROOF]]) : "",
    left: poly([[x, yd, 0], [xw, yd, 0], [xw, yd, h], [x, yd, h]]),
    right: poly([[xw, y, 0], [xw, yd, 0], [xw, yd, h], [xw, y, h]]),
    top: sfh ? poly([[x, m, h + ROOF], [xw, m, h + ROOF], [xw, yd, h], [x, yd, h]]) : poly([[x, y, h], [xw, y, h], [xw, yd, h], [x, yd, h]]),
    gable: sfh ? poly([[xw, y, h], [xw, yd, h], [xw, m, h + ROOF]]) : "",
    shadow: poly([[x + 1.5, y + 1.5, 0], [xw + 3, y + 1.5, 0], [xw + 3, yd + 3, 0], [x + 1.5, yd + 3, 0]]),
    winL, winR, door,
    hpL: quadX(hx, hx + hw, hy + hd, 0, hh),
    hpR: quadY(hx + hw, hy, hy + hd, 0, hh),
    hpT: poly([[hx, hy, hh], [hx + hw, hy, hh], [hx + hw, hy + hd, hh], [hx, hy + hd, hh]]),
    anchor: P(x + w / 2, y + d / 2, h + (sfh ? ROOF : 0)),
  };
}

const kw = (v: number | null) => (v == null || !Number.isFinite(v) ? "—" : `${v.toFixed(1)} kW`);
const pct = (v: number) => `${((v / W) * 100).toFixed(3)}%`;
const pctY = (v: number) => `${((v / H) * 100).toFixed(3)}%`;
const SOLAR_ON = 0.1;   // kW of generation from which the panels are drawn as producing
const rgba = (hex: string, a: number) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };

export function Scene({ buildings, selected, onSelect }: { buildings: SceneBuilding[]; selected: string; onSelect: (role: string) => void }) {
  const placed = (["SFH", "MFH"] as const).flatMap((t) => buildings.filter((b) => b.type === t).slice(0, LOTS[t].length).map((b, k) => ({ b, lot: LOTS[t][k] })));
  placed.sort((a, b) => (a.lot.x + a.lot.y) - (b.lot.x + b.lot.y));
  const drawn = placed.map(({ b, lot }) => ({ b, g: geometry(lot, b.type === "SFH") }));
  const scenario = buildings.some((b) => b.extras);
  const cooling = buildings.some((b) => b.extras?.coolKw != null);
  return (
    <div className="space-y-3">
      <div className="relative aspect-[3/2] w-full overflow-hidden rounded-xl bg-[#fcfcfc] bg-[radial-gradient(#e4e4e7_1px,transparent_1px)] [background-size:18px_18px]">
        <svg viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 h-full w-full" role="img" aria-label="Illustrative axonometric drawing of the six modeled buildings">
          <path d={drawn.map((x) => x.g.shadow).join(" ")} fill="#18181b" opacity={0.05} />
          <path d={TREES.map(([tx, ty]) => { const [cx, cy] = P(tx, ty, 2.4); return `M${(cx - 11).toFixed(1)} ${cy.toFixed(1)} a11 11 0 1 0 22 0 a11 11 0 1 0 -22 0 Z`; }).join(" ")} fill="#eef2ee" stroke="#c8d3c8" strokeWidth={0.8} />
          {drawn.map(({ b, g }) => {
            const on = b.role === selected;
            const x = b.extras;
            const cooling = (x?.coolKw ?? 0) >= RUNNING_KW;
            const run = (b.hpKw ?? 0) >= RUNNING_KW;
            const face = { stroke: on ? "#18181b" : "#a1a1aa", strokeWidth: on ? 1.4 : 0.8, strokeLinejoin: "round" as const };
            const hpc = cooling ? { s: "#0e7490", l: PALETTE.cool, r: "#0e7490", t: "#67e8f9" } : { s: "#9a3412", l: "#f97316", r: "#c2410c", t: "#fdba74" };
            const sun = x?.solarKw != null && x.solarKw >= SOLAR_ON ? Math.min(1, x.solarKw / Math.max(1, (x.solarKwp ?? 1) * 0.8)) : 0;
            return (
              <g key={b.role} className="cursor-pointer" onClick={() => onSelect(b.role)}>
                {g.back && <path d={g.back} fill="#d4d4d8" {...face} />}
                <path d={g.left} fill="#f4f4f5" {...face} />
                <path d={g.right} fill="#e4e4e7" {...face} />
                <path d={g.top} fill="#ffffff" {...face} />
                {g.gable && <path d={g.gable} fill="#e4e4e7" {...face} />}
                <path d={g.winL} fill="#d4d4d8" />
                <path d={g.winR} fill="#c4c4ca" />
                {g.door && <path d={g.door} fill="#a1a1aa" />}
                {x && x.solarKwp != null && (
                  <g className="transition-colors">
                    <path d={g.solar} fill={sun > 0 ? PALETTE.solar : "#52525b"} fillOpacity={sun > 0 ? 0.35 + 0.65 * sun : 0.85} stroke={sun > 0 ? "#854d0e" : "#27272a"} strokeWidth={0.8} strokeLinejoin="round" />
                    <path d={g.solarCells} fill="none" stroke={sun > 0 ? "#fef3c7" : "#71717a"} strokeWidth={0.5} />
                  </g>
                )}
                <g stroke={run ? hpc.s : "#a1a1aa"} strokeWidth={0.6} className="transition-colors">
                  <path d={g.hpL} fill={run ? hpc.l : "#f4f4f5"} />
                  <path d={g.hpR} fill={run ? hpc.r : "#e4e4e7"} />
                  <path d={g.hpT} fill={run ? hpc.t : "#ffffff"} />
                </g>
                {x && x.batterySoc != null && (
                  <g stroke="#52525b" strokeWidth={0.6}>
                    <path d={g.batL} fill="#f4f4f5" />
                    <path d={g.batR} fill="#e4e4e7" />
                    <path d={g.batT} fill="#ffffff" />
                    <path d={g.batFill(x.batterySoc)} fill={PALETTE.battery} stroke="none" />
                    <path d={g.batFillR(x.batterySoc)} fill="#0f766e" stroke="none" />
                  </g>
                )}
              </g>
            );
          })}
          <g className="hidden md:inline">
            {drawn.map(({ b, g }) => (
              <g key={b.role}>
                <path d={`M${g.anchor[0].toFixed(1)} ${(g.anchor[1] - 10).toFixed(1)} V${g.anchor[1].toFixed(1)}`} stroke="#a1a1aa" strokeWidth={1} />
                <circle cx={g.anchor[0]} cy={g.anchor[1]} r={2.5} fill="#18181b" />
              </g>
            ))}
          </g>
        </svg>
        <div className="hidden md:block">
          {drawn.map(({ b, g }) => {
            const on = b.role === selected;
            const x = b.extras;
            const exporting = x?.exportKw != null && x.exportKw >= 0.05 && (b.gridKw ?? 0) < 0.05;
            const muted = on ? "text-zinc-300" : "text-zinc-500";
            return (
              <button
                key={b.role}
                type="button"
                onClick={() => onSelect(b.role)}
                aria-pressed={on}
                style={{ left: pct(g.anchor[0]), top: pctY(g.anchor[1] - 10) }}
                className={cn(
                  "absolute w-max whitespace-nowrap -translate-x-1/2 -translate-y-full rounded-lg border px-2.5 py-1.5 text-left shadow-[0_1px_2px_rgba(0,0,0,.05),0_4px_12px_rgba(0,0,0,.04)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600",
                  on ? "border-zinc-900 bg-zinc-900 text-zinc-50" : "border-zinc-200 bg-white text-zinc-900 hover:border-zinc-400",
                )}
              >
                <span className="block text-xs font-semibold leading-4">{b.short}</span>
                <span className={cn("block text-[11px] leading-4", muted)}>{b.sub}</span>
                <span className="mt-0.5 flex items-center gap-1.5 text-xs leading-4 tabular-nums">
                  <span className="size-[7px] rounded-[2px]" style={{ background: exporting ? PALETTE.export : PALETTE.grid }} />
                  <span className="font-semibold" style={{ color: exporting ? (on ? "#c4b5fd" : PALETTE.export) : on ? "#93c5fd" : "#1d4ed8" }}>{kw(exporting ? x!.exportKw : b.gridKw)}</span>
                  <span className={cn("text-[11px]", muted)}>{exporting ? "to grid" : "from grid"}</span>
                </span>
                {x && x.solarKwp != null && (
                  <span className="flex items-center gap-1.5 text-[11px] leading-4 tabular-nums">
                    <span className="size-[7px] rounded-[2px]" style={{ background: PALETTE.solar }} />
                    <span className={on ? "text-zinc-100" : "text-zinc-700"}>{kw(x.solarKw)}</span>
                    {x.batterySoc != null && <>
                      <span className="size-[7px] rounded-[2px]" style={{ background: PALETTE.battery }} />
                      <span className={on ? "text-zinc-100" : "text-zinc-700"}>{(x.batterySoc * 100).toFixed(0)} %</span>
                    </>}
                  </span>
                )}
                {x && x.coolKw != null && (
                  <span className="flex items-center gap-1.5 text-[11px] leading-4 tabular-nums">
                    <span className="size-[7px] rounded-[2px]" style={{ background: PALETTE.cool }} />
                    <span className={on ? "text-zinc-100" : "text-zinc-700"}>cooling {kw(x.coolKw)}</span>
                  </span>
                )}
                {x && x.tempIn != null && (
                  <span className={cn("block text-[11px] leading-4 tabular-nums", x.tempIn > 26 ? (on ? "text-red-300" : "text-red-600") : muted)}>indoor {x.tempIn.toFixed(1).replace("-", "−")} °C</span>
                )}
              </button>
            );
          })}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1 px-1 text-[11px] text-zinc-600">
        <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px] bg-orange-600" />Heat pump running</span>
        {cooling && <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px]" style={{ background: PALETTE.cool }} />Cooling</span>}
        <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px] border border-zinc-400 bg-zinc-200" />Heat pump idle</span>
        {scenario && <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px]" style={{ background: rgba(PALETTE.solar, 0.8) }} />Solar panels producing</span>}
        {scenario && <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-[2px]" style={{ background: PALETTE.battery }} />Battery level</span>}
        <span className="text-zinc-500">Select a building for details</span>
      </div>
      <div className="grid grid-cols-2 gap-2 md:hidden" role="group" aria-label="Choose a building">
        {buildings.map((b) => {
          const on = b.role === selected;
          const exporting = b.extras?.exportKw != null && b.extras.exportKw >= 0.05 && (b.gridKw ?? 0) < 0.05;
          return (
            <button key={b.role} type="button" onClick={() => onSelect(b.role)} aria-pressed={on}
              className={cn("min-h-11 rounded-lg border px-3 py-2 text-left", on ? "border-zinc-900 bg-zinc-900 text-zinc-50" : "border-zinc-200 bg-white")}>
              <span className="block text-xs font-semibold">{b.short}</span>
              <span className={cn("block text-xs tabular-nums", exporting ? (on ? "text-violet-300" : "text-violet-700") : on ? "text-blue-300" : "text-blue-700")}>{kw(exporting ? b.extras!.exportKw : b.gridKw)} {exporting ? "to grid" : "from grid"}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
