"use client";
// System map of all three phases (bundle file system_map.json, built by swiss/dashboard/system_map.py).
// Layout: inputs and the controller sit in a top row; their dashed lines run along a lane and drop down the gap left of
// each target, so they never cross a box. Energy flows run in two rows (space heating above, hot water below) around a
// middle row with the building connection, where grid, solar, battery and loads meet. Connectors are recomputed from
// the current box positions, so boxes can be dragged (pointer or arrow keys) and the lines follow.
import { useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { RotateCcw } from "lucide-react";
import { NodeLink } from "@/components/audit/bits";
import { useBundleFile } from "@/lib/bundle";
import { PALETTE } from "@/lib/palette";
import { cn } from "@/lib/utils";

type PhaseId = "A" | "B" | "C";
type Carrier = "electricity" | "heat" | "cooling" | "signal" | "control";
type MapComponent = { id: string; label: string; description: string; provenance: string | Record<string, string>; source_ids: string[]; present_in: string; tag: string | null; card: string | null };
type MapFlow = { id: string; from: string; to: string; carrier: Carrier; description: string; both: boolean };
type SystemMap = { phases: { id: PhaseId; label: string; title: string; summary: string }[]; views: Record<PhaseId, { components: MapComponent[]; flows: MapFlow[] }> };

type Pt = { x: number; y: number };
type Side = "l" | "r" | "t" | "b";
type Mode = "auto" | "over" | "under" | "under2" | "bus";

const W = 170, H = 58, VW = 1380;
const COL = [30, 260, 490, 720, 950, 1180];
const INPUT_Y = 34, TITLE_Y = 162;
const ROW = [180, 290, 400, 510, 620];
const START: Record<string, Pt> = {
  weather: { x: COL[0], y: INPUT_Y }, controller: { x: COL[3], y: INPUT_Y }, tariff: { x: COL[4], y: INPUT_Y }, carbon: { x: COL[5], y: INPUT_Y },
  pv: { x: COL[0], y: ROW[0] }, grid: { x: COL[0], y: ROW[1] }, battery: { x: COL[0], y: ROW[2] },
  meter: { x: COL[1], y: ROW[1] }, leg: { x: COL[1], y: ROW[2] },
  hp_sh: { x: COL[2], y: ROW[0] }, hp_hw: { x: COL[2], y: ROW[2] }, household: { x: COL[2], y: ROW[3] }, ev: { x: COL[2], y: ROW[4] },
  tank_sh: { x: COL[3], y: ROW[0] }, tank_hw: { x: COL[3], y: ROW[2] },
  demand_sh: { x: COL[4], y: ROW[0] }, demand_hw: { x: COL[4], y: ROW[2] },
  outcomes: { x: COL[5], y: ROW[1] },
};
const INPUTS = ["weather", "controller", "tariff", "carbon"];
const COLUMN_TITLES = ["Supply", "Connection", "Conversion and loads", "Storage", "Demand", "Results"];
// heat flows that would run through the tank are routed below (space heating) or above (hot water) their row
const MODE: Record<string, Mode> = { hp_sh_demand: "under", hp_sh_cooling: "under2", hp_hw_demand: "over" };

const CARRIER: Record<Carrier, { colour: string; dash?: string; width: number; label: string }> = {
  electricity: { colour: PALETTE.grid, width: 2, label: "Electricity" },
  heat: { colour: PALETTE.heat, width: 2, label: "Heat" },
  cooling: { colour: PALETTE.cool, width: 2, label: "Cooling" },
  signal: { colour: PALETTE.soft, dash: "5 4", width: 1.5, label: "Input signal" },
  control: { colour: PALETTE.export, dash: "5 4", width: 1.5, label: "Control" },
};

const provText = (v: MapComponent["provenance"]) =>
  typeof v === "string" ? v.replaceAll("_", " ") : Object.entries(v).map(([k, c]) => `${c.replaceAll("_", " ")} (${k === "SFH" ? "houses" : "apartment buildings"})`).join(", ");

function wrap(label: string, max = 21): string[] {
  const lines: string[] = [];
  let cur = "";
  for (const w of label.split(" ")) {
    if (cur && (cur + " " + w).length > max) { lines.push(cur); cur = w; } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 2);
}

function sides(a: Pt, b: Pt, mode: Mode): [Side, Side] {
  if (mode === "bus") return ["b", "l"];
  if (mode === "over") return ["t", "t"];
  if (mode === "under" || mode === "under2") return ["b", "b"];
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

function rounded(pts: Pt[], r = 8): string {
  const c = pts.filter((p, i) => i === 0 || Math.abs(p.x - pts[i - 1].x) > 0.01 || Math.abs(p.y - pts[i - 1].y) > 0.01);
  let d = `M ${c[0].x} ${c[0].y}`;
  for (let i = 1; i < c.length - 1; i++) {
    const p = c[i], a = c[i - 1], b = c[i + 1];
    const la = Math.hypot(p.x - a.x, p.y - a.y), lb = Math.hypot(b.x - p.x, b.y - p.y);
    const k = Math.min(r, la / 2, lb / 2);
    d += ` L ${p.x - ((p.x - a.x) / (la || 1)) * k} ${p.y - ((p.y - a.y) / (la || 1)) * k} Q ${p.x} ${p.y} ${p.x + ((b.x - p.x) / (lb || 1)) * k} ${p.y + ((b.y - p.y) / (lb || 1)) * k}`;
  }
  const last = c[c.length - 1];
  return `${d} L ${last.x} ${last.y}`;
}

export function SystemFlowDiagram() {
  const { data: map } = useBundleFile<SystemMap>("system_map");
  const [phase, setPhase] = useState<PhaseId>("C");
  const [selected, setSelected] = useState("meter");
  const [hover, setHover] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<Carrier>>(new Set());
  const [pos, setPos] = useState<Record<string, Pt>>(START);
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; dx: number; dy: number; start: Pt; moved: boolean } | null>(null);

  const view = map?.views[phase];
  const components = useMemo(() => (view?.components ?? []).filter((c) => START[c.id]), [view]);
  const flows = useMemo(() => (view?.flows ?? []).filter((f) => START[f.from] && START[f.to]), [view]);
  const shown = useMemo(() => flows.filter((f) => !hidden.has(f.carrier)), [flows, hidden]);
  const visibleIds = useMemo(() => new Set(components.map((c) => c.id)), [components]);

  const edges = useMemo(() => {
    const meta = shown.map((f) => {
      const mode: Mode = INPUTS.includes(f.from) && !INPUTS.includes(f.to) ? "bus" : MODE[f.id] ?? "auto";
      const [ss, es] = sides(pos[f.from], pos[f.to], mode);
      return { f, mode, ss, es };
    });
    // several connectors on one side of a box get separate attachment points, ordered by where their other end is
    const slots = new Map<string, { key: string; order: number }[]>();
    const add = (node: string, side: Side, key: string, other: Pt) => {
      const k = `${node}:${side}`;
      slots.set(k, [...(slots.get(k) ?? []), { key, order: side === "l" || side === "r" ? other.y : other.x }]);
    };
    for (const { f, ss, es } of meta) { add(f.from, ss, `${f.id}:s`, pos[f.to]); add(f.to, es, `${f.id}:e`, pos[f.from]); }
    const frac = new Map<string, number>();
    for (const list of slots.values()) list.sort((a, b) => a.order - b.order).forEach((x, i) => frac.set(x.key, (i + 1) / (list.length + 1)));
    return meta.map(({ f, mode, ss, es }) => {
      const a = pos[f.from], b = pos[f.to];
      const s = portPoint(a, ss, frac.get(`${f.id}:s`) ?? 0.5), e = portPoint(b, es, frac.get(`${f.id}:e`) ?? 0.5);
      let pts: Pt[];
      if (mode === "bus") {
        const lane = a.y + H + 12 + 8 * INPUTS.indexOf(f.from);
        const x = b.x - (f.carrier === "control" ? 18 : 9);
        pts = [s, { x: s.x, y: lane }, { x, y: lane }, { x, y: e.y }, e];
      } else if (mode === "over") {
        const y = Math.min(a.y, b.y) - 16;
        pts = [s, { x: s.x, y }, { x: e.x, y }, e];
      } else if (mode === "under" || mode === "under2") {
        const y = Math.max(a.y, b.y) + H + (mode === "under" ? 16 : 30);
        pts = [s, { x: s.x, y }, { x: e.x, y }, e];
      } else if (ss === "r" || ss === "l") {
        const mx = (s.x + e.x) / 2;
        pts = [s, { x: mx, y: s.y }, { x: mx, y: e.y }, e];
      } else {
        const my = (s.y + e.y) / 2;
        pts = [s, { x: s.x, y: my }, { x: e.x, y: my }, e];
      }
      return { f, d: rounded(pts) };
    });
  }, [shown, pos]);

  if (!map || !view) return <div className="rounded-xl border p-6 text-sm text-muted-foreground">Loading the system map…</div>;

  const vh = Math.max(...components.map((c) => pos[c.id].y)) + H + 34;
  const byId = new Map(components.map((c) => [c.id, c]));
  const active = byId.get(selected) ?? byId.get("meter");
  const moved = Object.keys(START).some((k) => pos[k].x !== START[k].x || pos[k].y !== START[k].y);
  const phaseInfo = map.phases.find((p) => p.id === phase)!;

  const toSvg = (e: PointerEvent): Pt => {
    const m = svg.current?.getScreenCTM();
    if (!m) return { x: 0, y: 0 };
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    return { x: p.x, y: p.y };
  };
  const clamp = (p: Pt): Pt => ({ x: Math.max(4, Math.min(VW - W - 4, p.x)), y: Math.max(4, Math.min(vh - H - 4, p.y)) });
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
    const dd = ({ ArrowLeft: { x: -step, y: 0 }, ArrowRight: { x: step, y: 0 }, ArrowUp: { x: 0, y: -step }, ArrowDown: { x: 0, y: step } } as Record<string, Pt>)[e.key];
    if (!dd) return;
    e.preventDefault();
    setPos((cur) => ({ ...cur, [id]: clamp({ x: cur[id].x + dd.x, y: cur[id].y + dd.y }) }));
  };
  const toggle = (c: Carrier) => setHidden((h) => { const n = new Set(h); if (n.has(c)) n.delete(c); else n.add(c); return n; });

  const linked = (f: MapFlow) => !hover || f.from === hover || f.to === hover;
  const neighbours = new Set(hover ? shown.filter(linked).flatMap((f) => [f.from, f.to]) : []);
  const carriers = (Object.keys(CARRIER) as Carrier[]).filter((c) => flows.some((f) => f.carrier === c));
  const activeFlows = active ? flows.filter((f) => f.from === active.id || f.to === active.id) : [];

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-zinc-100 px-4 py-3 lg:flex-row lg:items-start lg:justify-between">
          <div role="radiogroup" aria-label="Project phase" className="inline-flex w-fit rounded-lg border border-zinc-200 bg-zinc-50 p-0.5">
            {map.phases.map((p) => (
              <button key={p.id} type="button" role="radio" aria-checked={phase === p.id} onClick={() => setPhase(p.id)}
                className={cn("rounded-md px-3 py-1.5 text-left text-xs transition-colors", phase === p.id ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-600 hover:text-zinc-900")}>
                <span className="block font-semibold">{p.label}</span>
                <span className="block text-[11px] text-zinc-500">{p.title}</span>
              </button>
            ))}
          </div>
          <p className="max-w-xl text-xs leading-relaxed text-zinc-600">{phaseInfo.summary}</p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-2 text-xs text-zinc-600">
          <div className="flex flex-wrap items-center gap-1">
            {carriers.map((c) => (
              <button key={c} type="button" onClick={() => toggle(c)} aria-pressed={!hidden.has(c)} title={hidden.has(c) ? `Show ${CARRIER[c].label.toLowerCase()}` : `Hide ${CARRIER[c].label.toLowerCase()}`}
                className={cn("flex items-center gap-1.5 rounded-md px-2 py-1 hover:bg-zinc-50", hidden.has(c) && "opacity-40")}>
                <svg width="22" height="6" aria-hidden><path d="M1 3H21" stroke={CARRIER[c].colour} strokeWidth={CARRIER[c].width} strokeDasharray={CARRIER[c].dash} /></svg>{CARRIER[c].label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-zinc-500 md:inline">Click a line type to hide it · drag a box · hover to trace</span>
            <button type="button" onClick={() => setPos(START)} disabled={!moved} className="inline-flex h-7 items-center gap-1 rounded-md border border-zinc-200 px-2 font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-40">
              <RotateCcw className="size-3.5" />Reset layout
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <svg ref={svg} viewBox={`0 0 ${VW} ${vh}`} className="block w-full min-w-[960px] select-none bg-[radial-gradient(#e4e4e7_1px,transparent_1px)] [background-size:18px_18px]" role="group" aria-label={`Energy and information flows of the modeled district, ${phaseInfo.label}`}>
            <defs>
              {(Object.keys(CARRIER) as Carrier[]).map((k) => (
                <marker key={k} id={`sf-arrow-${k}`} viewBox="0 0 8 8" markerWidth="7" markerHeight="7" refX="7" refY="4" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
                  <path d="M0 0L8 4L0 8Z" fill={CARRIER[k].colour} />
                </marker>
              ))}
            </defs>
            <text x={COL[0]} y={22} fontSize="11" fontWeight={600} letterSpacing="0.06em" fill={PALETTE.soft}>INPUTS AND CONTROL</text>
            {COLUMN_TITLES.map((t, i) => (
              <text key={t} x={COL[i] + W / 2} y={TITLE_Y} textAnchor="middle" fontSize="11" fontWeight={600} letterSpacing="0.06em" fill={PALETTE.soft}>{t.toUpperCase()}</text>
            ))}
            <g fill="none">
              {edges.map(({ f, d }) => {
                const c = CARRIER[f.carrier];
                const on = linked(f);
                const end = `url(#sf-arrow-${f.carrier})`;
                return (
                  <path key={f.id} d={d} stroke={c.colour} strokeWidth={hover && on ? c.width + 1 : c.width} strokeDasharray={c.dash}
                    markerEnd={end} markerStart={f.both ? end : undefined} opacity={on ? 1 : 0.1} className="transition-opacity">
                    <title>{f.description}</title>
                  </path>
                );
              })}
            </g>
            {components.map((c) => {
              const p = pos[c.id], on = active?.id === c.id, dim = !!hover && !neighbours.has(c.id) && hover !== c.id;
              const lines = wrap(c.label);
              const rows = lines.length + (c.tag ? 1 : 0);
              const top = H / 2 - ((rows - 1) * 15) / 2 + 4.5;
              return (
                <g key={c.id} transform={`translate(${p.x} ${p.y})`} tabIndex={0} role="button" aria-pressed={on}
                  aria-label={`${c.label}. Press Enter for details; arrow keys move the box.`}
                  onPointerDown={onDown(c.id)} onPointerMove={onMove} onPointerUp={onUp(c.id)}
                  onPointerEnter={() => setHover(c.id)} onPointerLeave={() => setHover(null)}
                  onFocus={() => setHover(c.id)} onBlur={() => setHover(null)} onKeyDown={onKey(c.id)}
                  className="cursor-grab outline-none active:cursor-grabbing [touch-action:none]" opacity={dim ? 0.35 : 1}>
                  <rect width={W} height={H} rx="10" fill={on ? "#18181b" : "#ffffff"} stroke={on ? "#18181b" : hover === c.id ? "#71717a" : "#d4d4d8"} strokeWidth={on ? 1.5 : 1}
                    strokeDasharray={c.tag === "optimiser only" ? "4 3" : undefined} style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,.05))" }} />
                  {lines.map((l, i) => (
                    <text key={i} x="13" y={top + i * 15} fontSize="12.5" fontWeight={600} fill={on ? "#fafafa" : "#18181b"}>{l}</text>
                  ))}
                  {c.tag && <text x="13" y={top + lines.length * 15} fontSize="10.5" fill={on ? "#a1a1aa" : "#71717a"}>{c.tag}</text>}
                </g>
              );
            })}
          </svg>
        </div>
      </div>
      {active && (
        <section className="rounded-xl border border-zinc-200 bg-white p-4" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">{active.label}{active.tag && <span className="ml-2 text-xs font-normal text-zinc-500">{active.tag}</span>}</h3>
            <span className="flex items-center gap-3">
              {active.card && <NodeLink id={active.card} label="Open audit card →" className="font-sans text-xs" />}
              <span className="rounded-full border border-zinc-200 px-2 py-0.5 text-[11px] capitalize text-zinc-600">{provText(active.provenance)}</span>
            </span>
          </div>
          <p className="mt-2 max-w-4xl text-sm text-zinc-600">{active.description}</p>
          <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
            <span>{phaseInfo.label} · present in {active.present_in} · audit cards:</span>
            {active.source_ids.map((id) => <NodeLink key={id} id={id} />)}
          </p>
          {activeFlows.length > 0 && (
            <ul className="mt-3 grid gap-1 text-xs text-zinc-600 sm:grid-cols-2">
              {activeFlows.map((f) => (
                <li key={f.id} className="flex items-start gap-2">
                  <span className="mt-1.5 inline-block h-0.5 w-3 shrink-0" style={{ background: CARRIER[f.carrier].colour }} />
                  <span><b className="font-medium text-zinc-800">{f.from === active.id ? `${f.both ? "with" : "to"} ${byId.get(f.to)?.label}` : `${f.both ? "with" : "from"} ${byId.get(f.from)?.label}`}</b> · {f.description}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {!visibleIds.has(selected) && selected !== "meter" && <span className="sr-only">The selected component is not part of {phaseInfo.label}; showing the building connection.</span>}
    </div>
  );
}
