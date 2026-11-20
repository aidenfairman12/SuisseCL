"use client";
// System diagram of the modeled components and flows from the v1 contract.
// Layout: one row per heating chain (grid → heat pump → tank → demand); the signals that act on a column
// (weather, controller, tariff) sit between the two rows so their arrows stay short. Connectors are right-angled
// and recomputed from the current box positions, so boxes can be dragged (mouse, touch or arrow keys).
import { useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { RotateCcw } from "lucide-react";
import { useComponents } from "@/lib/contract";
import type { SystemComponent } from "@/lib/contract";
import { PALETTE } from "@/lib/palette";
import { cn } from "@/lib/utils";

type Pt = { x: number; y: number };
type Side = "l" | "r" | "t" | "b";
type Mode = "auto" | "over" | "under" | "floor";

const VW = 1280, VH = 590, W = 180, H = 56;
const COL = [30, 290, 550, 810, 1070];
const ROW = { top: 44, sh: 150, mid: 262, hw: 374, house: 486 };
const START: Record<string, Pt> = {
  grid: { x: COL[0], y: ROW.mid },
  weather: { x: COL[1], y: ROW.mid },
  hp_sh: { x: COL[1], y: ROW.sh },
  hp_hw: { x: COL[1], y: ROW.hw },
  household: { x: COL[1], y: ROW.house },
  controller: { x: COL[2], y: ROW.mid },
  tank_sh: { x: COL[2], y: ROW.sh },
  tank_hw: { x: COL[2], y: ROW.hw },
  tariff: { x: COL[3], y: ROW.mid },
  demand_sh: { x: COL[3], y: ROW.sh },
  demand_hw: { x: COL[3], y: ROW.hw },
  carbon: { x: COL[4], y: ROW.top },
  district_outcomes: { x: COL[4], y: ROW.mid },
};
const COLUMN_TITLES = ["Supply", "Heat pumps", "Storage", "Demand", "Results"];
// Flows that would otherwise run straight through a box are routed above or below the row.
const MODE: Record<string, Mode> = { hp_sh_demand: "over", hp_hw_demand: "under", grid_outcomes: "floor" };

const CARRIER = {
  electricity: { colour: PALETTE.grid, dash: undefined, width: 2, label: "Electricity" },
  heat: { colour: PALETTE.heat, dash: undefined, width: 2, label: "Heat" },
  signal: { colour: PALETTE.soft, dash: "5 4", width: 1.5, label: "Input signal" },
  control: { colour: PALETTE.export, dash: "5 4", width: 1.5, label: "Control signal" },
} as const;

const prov = (v: SystemComponent["provenance"]) => (typeof v === "string" ? v.replaceAll("_", " ") : "measured / synthetic by building type");

function wrap(label: string, max = 22): string[] {
  const words = label.split(" ");
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    if (cur && (cur + " " + w).length > max) { lines.push(cur); cur = w; } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 2);
}

/** Pick the sides an edge leaves and enters from the two box positions. */
function sides(a: Pt, b: Pt, mode: Mode): [Side, Side] {
  if (mode === "over") return ["t", "t"];
  if (mode === "under" || mode === "floor") return ["b", "b"];
  if (b.x >= a.x + W + 20) return ["r", "l"];
  if (b.x + W + 20 <= a.x) return ["l", "r"];
  return b.y > a.y ? ["b", "t"] : ["t", "b"];
}

function portPoint(p: Pt, side: Side, frac: number): Pt {
  if (side === "l") return { x: p.x, y: p.y + H * frac };
  if (side === "r") return { x: p.x + W, y: p.y + H * frac };
  if (side === "t") return { x: p.x + W * frac, y: p.y };
  return { x: p.x + W * frac, y: p.y + H };
}

/** Polyline through the points with rounded corners. */
function rounded(pts: Pt[], r = 8): string {
  const clean = pts.filter((p, i) => i === 0 || p.x !== pts[i - 1].x || p.y !== pts[i - 1].y);
  let d = `M ${clean[0].x} ${clean[0].y}`;
  for (let i = 1; i < clean.length - 1; i++) {
    const p = clean[i], a = clean[i - 1], b = clean[i + 1];
    const la = Math.hypot(p.x - a.x, p.y - a.y), lb = Math.hypot(b.x - p.x, b.y - p.y);
    const k = Math.min(r, la / 2, lb / 2);
    const s = { x: p.x - ((p.x - a.x) / (la || 1)) * k, y: p.y - ((p.y - a.y) / (la || 1)) * k };
    const e = { x: p.x + ((b.x - p.x) / (lb || 1)) * k, y: p.y + ((b.y - p.y) / (lb || 1)) * k };
    d += ` L ${s.x} ${s.y} Q ${p.x} ${p.y} ${e.x} ${e.y}`;
  }
  const last = clean[clean.length - 1];
  return `${d} L ${last.x} ${last.y}`;
}

function route(s: Pt, e: Pt, ss: Side, es: Side, a: Pt, b: Pt, floor?: number): Pt[] {
  if (floor != null) return [s, { x: s.x, y: floor }, { x: e.x, y: floor }, e];
  if (ss === "t" && es === "t") { const y = Math.min(a.y, b.y) - 22; return [s, { x: s.x, y }, { x: e.x, y }, e]; }
  if (ss === "b" && es === "b") { const y = Math.max(a.y, b.y) + H + 22; return [s, { x: s.x, y }, { x: e.x, y }, e]; }
  if (ss === "r" || ss === "l") { const mx = (s.x + e.x) / 2; return [s, { x: mx, y: s.y }, { x: mx, y: e.y }, e]; }
  const my = (s.y + e.y) / 2;
  return [s, { x: s.x, y: my }, { x: e.x, y: my }, e];
}

export function SystemFlowDiagram() {
  const file = useComponents("full");
  const [selected, setSelected] = useState("grid");
  const [hover, setHover] = useState<string | null>(null);
  const [pos, setPos] = useState<Record<string, Pt>>(START);
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; dx: number; dy: number; start: Pt; moved: boolean } | null>(null);

  const components = useMemo(() => (file.data?.components ?? []).filter((c) => START[c.id]), [file.data]);
  const flows = useMemo(() => (file.data?.flows ?? []).filter((f) => START[f.from] && START[f.to]), [file.data]);
  const byId = new Map((file.data?.components ?? []).map((c) => [c.id, c]));
  const active = byId.get(selected);
  const moved = Object.keys(START).some((k) => pos[k].x !== START[k].x || pos[k].y !== START[k].y);

  const edges = useMemo(() => {
    const meta = flows.map((f) => {
      const [ss, es] = sides(pos[f.from], pos[f.to], MODE[f.id] ?? "auto");
      return { f, ss, es };
    });
    // spread several connectors on one side of a box, ordered by where their other end is
    const slots = new Map<string, { key: string; order: number }[]>();
    const add = (node: string, side: Side, key: string, other: Pt) => {
      const k = `${node}:${side}`;
      const order = side === "l" || side === "r" ? other.y : other.x;
      slots.set(k, [...(slots.get(k) ?? []), { key, order }]);
    };
    for (const { f, ss, es } of meta) {
      add(f.from, ss, `${f.id}:s`, pos[f.to]);
      add(f.to, es, `${f.id}:e`, pos[f.from]);
    }
    // the "floor" lane runs below every box
    const floor = Math.min(VH - 6, Math.max(...Object.values(pos).map((p) => p.y)) + H + 24);
    const frac = new Map<string, number>();
    for (const list of slots.values()) {
      list.sort((a, b) => a.order - b.order).forEach((x, i) => frac.set(x.key, (i + 1) / (list.length + 1)));
    }
    return meta.map(({ f, ss, es }) => {
      const a = pos[f.from], b = pos[f.to];
      const s = portPoint(a, ss, frac.get(`${f.id}:s`) ?? 0.5), e = portPoint(b, es, frac.get(`${f.id}:e`) ?? 0.5);
      return { f, d: rounded(route(s, e, ss, es, a, b, MODE[f.id] === "floor" ? floor : undefined)) };
    });
  }, [flows, pos]);

  if (!file.data) return <div className="rounded-xl border p-6 text-sm text-muted-foreground">Loading system contract…</div>;

  const toSvg = (e: PointerEvent): Pt => {
    const m = svg.current?.getScreenCTM();
    if (!m) return { x: 0, y: 0 };
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    return { x: p.x, y: p.y };
  };
  const clamp = (p: Pt): Pt => ({ x: Math.max(4, Math.min(VW - W - 4, p.x)), y: Math.max(28, Math.min(VH - H - 4, p.y)) });
  const onDown = (id: string) => (e: PointerEvent<SVGGElement>) => {
    const p = toSvg(e);
    drag.current = { id, dx: p.x - pos[id].x, dy: p.y - pos[id].y, start: p, moved: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onMove = (e: PointerEvent<SVGGElement>) => {
    const d = drag.current;
    if (!d) return;
    const p = toSvg(e);
    if (!d.moved && Math.hypot(p.x - d.start.x, p.y - d.start.y) < 4) return;
    d.moved = true;
    setPos((cur) => ({ ...cur, [d.id]: clamp({ x: p.x - d.dx, y: p.y - d.dy }) }));
  };
  const onUp = (id: string) => () => {
    if (drag.current && !drag.current.moved) setSelected(id);
    drag.current = null;
  };
  const onKey = (id: string) => (e: KeyboardEvent<SVGGElement>) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(id); return; }
    const step = e.shiftKey ? 40 : 10;
    const delta: Record<string, Pt> = { ArrowLeft: { x: -step, y: 0 }, ArrowRight: { x: step, y: 0 }, ArrowUp: { x: 0, y: -step }, ArrowDown: { x: 0, y: step } };
    const dd = delta[e.key];
    if (!dd) return;
    e.preventDefault();
    setPos((cur) => ({ ...cur, [id]: clamp({ x: cur[id].x + dd.x, y: cur[id].y + dd.y }) }));
  };

  const focus = hover;
  const linked = (f: { from: string; to: string }) => !focus || f.from === focus || f.to === focus;
  const neighbours = new Set(focus ? flows.filter(linked).flatMap((f) => [f.from, f.to]) : []);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-2.5 text-xs text-zinc-600">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            {Object.values(CARRIER).map((c) => (
              <span key={c.label} className="flex items-center gap-1.5">
                <svg width="22" height="6" aria-hidden><path d="M1 3H21" stroke={c.colour} strokeWidth={c.width} strokeDasharray={c.dash} /></svg>{c.label}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-zinc-500 sm:inline">Drag a box to move it · hover to trace its connections</span>
            <button type="button" onClick={() => setPos(START)} disabled={!moved} className="inline-flex h-7 items-center gap-1 rounded-md border border-zinc-200 px-2 font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-40">
              <RotateCcw className="size-3.5" />Reset layout
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <svg ref={svg} viewBox={`0 0 ${VW} ${VH}`} className="block w-full min-w-[900px] select-none bg-[radial-gradient(#e4e4e7_1px,transparent_1px)] [background-size:18px_18px]" role="group" aria-label="Energy and information flows of the modeled district, from the simulation contract">
            <defs>
              {Object.entries(CARRIER).map(([k, c]) => (
                <marker key={k} id={`sf-arrow-${k}`} viewBox="0 0 8 8" markerWidth="7" markerHeight="7" refX="7" refY="4" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
                  <path d="M0 0L8 4L0 8Z" fill={c.colour} />
                </marker>
              ))}
            </defs>
            {COLUMN_TITLES.map((t, i) => (
              <text key={t} x={COL[i] + W / 2} y={20} textAnchor="middle" fontSize="11" fontWeight={600} letterSpacing="0.06em" fill={PALETTE.soft}>{t.toUpperCase()}</text>
            ))}
            <g fill="none">
              {edges.map(({ f, d }) => {
                const c = CARRIER[f.carrier as keyof typeof CARRIER] ?? CARRIER.signal;
                const on = linked(f);
                return (
                  <path key={f.id} d={d} stroke={c.colour} strokeWidth={focus && on ? c.width + 1 : c.width} strokeDasharray={c.dash}
                    markerEnd={`url(#sf-arrow-${f.carrier})`} opacity={on ? 1 : 0.12} className="transition-opacity">
                    <title>{f.description}</title>
                  </path>
                );
              })}
            </g>
            {components.map((c) => {
              const p = pos[c.id], on = selected === c.id, dim = !!focus && !neighbours.has(c.id);
              const lines = wrap(c.label);
              return (
                <g key={c.id} transform={`translate(${p.x} ${p.y})`} tabIndex={0} role="button" aria-pressed={on}
                  aria-label={`${c.label}. Press Enter for details; arrow keys move the box.`}
                  onPointerDown={onDown(c.id)} onPointerMove={onMove} onPointerUp={onUp(c.id)}
                  onPointerEnter={() => setHover(c.id)} onPointerLeave={() => setHover(null)}
                  onFocus={() => setHover(c.id)} onBlur={() => setHover(null)} onKeyDown={onKey(c.id)}
                  className="cursor-grab outline-none active:cursor-grabbing [touch-action:none]" opacity={dim ? 0.35 : 1}>
                  <rect width={W} height={H} rx="10" fill={on ? "#18181b" : "#ffffff"} stroke={on ? "#18181b" : hover === c.id ? "#71717a" : "#d4d4d8"} strokeWidth={on ? 1.5 : 1}
                    style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,.05))" }} />
                  {lines.map((l, i) => (
                    <text key={i} x="14" y={H / 2 + (i - (lines.length - 1) / 2) * 16 + 4.5} fontSize="12.5" fontWeight={600} fill={on ? "#fafafa" : "#18181b"}>{l}</text>
                  ))}
                </g>
              );
            })}
          </svg>
        </div>
      </div>
      {active && (
        <section className="rounded-xl border bg-card p-4" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">{active.label}</h3>
            <div className="flex items-center gap-2">
              <span className="rounded-full border px-2 py-0.5 text-[10px] capitalize text-muted-foreground">{prov(active.provenance)}</span>
              <span className="text-xs text-muted-foreground">Phase {active.phase_available} · {active.status.replaceAll("_", " ")}</span>
            </div>
          </div>
          <p className="mt-2 max-w-4xl text-sm text-muted-foreground">{active.description}</p>
          <p className="mt-2 text-xs text-muted-foreground">Present in: {active.present_in}{active.source_ids.length ? ` · Sources: ${active.source_ids.join(", ")}` : ""}</p>
          {active.variables.length > 0 && <p className="mt-1 text-xs text-muted-foreground">Contract variables: {active.variables.join(", ")}</p>}
          {flows.some((f) => f.from === active.id || f.to === active.id) && (
            <ul className="mt-3 grid gap-1 text-xs text-zinc-600 sm:grid-cols-2">
              {flows.filter((f) => f.from === active.id || f.to === active.id).map((f) => (
                <li key={f.id} className="flex items-start gap-2">
                  <span className="mt-1.5 inline-block h-0.5 w-3 shrink-0" style={{ background: (CARRIER[f.carrier as keyof typeof CARRIER] ?? CARRIER.signal).colour }} />
                  <span><b className="font-medium text-zinc-800">{f.from === active.id ? `to ${byId.get(f.to)?.label}` : `from ${byId.get(f.from)?.label}`}</b> · {f.description}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      <section className="space-y-2">
        <div>
          <h3 className="font-semibold">Planned beyond Phase A</h3>
          <p className="text-sm text-muted-foreground">Not modeled in the Phase A simulation shown here. Phase B examines some of them as labelled scenarios (see the Scenarios and Controllers pages) and Phase C examines future climates and cooling (see the Climate, Cooling, Explorer and Houses pages).</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {(file.data.components ?? []).filter((c) => c.status === "not_modeled").map((c) => (
            <button key={c.id} onClick={() => setSelected(c.id)} className={cn("rounded-xl border p-3 text-left hover:bg-muted/50", selected === c.id ? "border-foreground/50 bg-muted/40" : "bg-card")}>
              <div className="flex items-center justify-between gap-2"><span className="text-sm font-medium">{c.label}</span><span className="text-[10px] text-muted-foreground">Phase {c.phase_available}</span></div>
              <p className="mt-1 text-xs text-muted-foreground">{c.description}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
