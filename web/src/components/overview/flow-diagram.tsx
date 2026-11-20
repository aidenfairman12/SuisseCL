"use client";
import { useBundle } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";

type Box = { ui: string; x: number; y: number; w?: number; h?: number; title: string; sub?: string };
const BOXES: Box[] = [
  { ui: "series:outdoor_temperature", x: 20, y: 20, title: "Weather", sub: "DER-007 · Zurich/Kloten" },
  { ui: "series:price", x: 20, y: 90, title: "Tariff", sub: "DER-008 · EKZ standard" },
  { ui: "series:carbon_intensity", x: 20, y: 160, title: "Carbon intensity", sub: "DER-011 · M-002" },
  { ui: "series:building_electricity", x: 20, y: 230, title: "Building loads", sub: "DER-005 · six buildings" },
  { ui: "card:building_selection", x: 20, y: 290, h: 32, title: "Building selection" },
  { ui: "card:cop_model", x: 230, y: 30, title: "Heat-pump model", sub: "M-001 · DER-009" },
  { ui: "card:hp_nominal_power", x: 230, y: 100, h: 40, title: "Heat-pump size", sub: "TR-009" },
  { ui: "card:tanks", x: 430, y: 60, title: "Thermal tanks", sub: "D-017a · synthetic" },
  { ui: "card:environment", x: 430, y: 180, h: 55, title: "CityLearn + grid", sub: "DER-010 · D-018" },
  { ui: "card:controllers", x: 640, y: 60, title: "Controller", sub: "ALG-001..004" },
  { ui: "card:reward", x: 640, y: 185, title: "Reward", sub: "R-001 · D-019" },
  { ui: "panel:kpis", x: 850, y: 185, title: "KPIs", sub: "EXP-007..012" },
  { ui: "panel:validation", x: 850, y: 60, title: "Validation", sub: "V1..V9" },
  { ui: "panel:sensitivity", x: 850, y: 265, title: "Sensitivity", sub: "variants" },
  { ui: "panel:open_issues", x: 640, y: 285, h: 32, title: "Open issues" },
];
const LINKS = [
  "M170,45 C200,45 200,52 228,52", "M170,255 C205,255 200,68 228,68", "M380,55 C405,55 405,82 428,82", "M380,120 C410,120 405,192 428,192",
  "M505,110 L505,178", "M170,125 C210,125 210,178 260,178 L428,200", "M170,185 C260,185 330,208 428,208", "M170,262 C300,262 330,222 428,222",
  "M638,85 L582,85", "M582,190 C610,190 610,110 638,100", "M582,210 L638,210", "M790,210 L848,210", "M582,228 C700,262 760,242 848,224",
];
const LABELS: [number, number, string][] = [
  [590, 78, "actions"], [614, 150, "observations"], [796, 203, "per step"], [300, 183, "tariff"], [300, 203, "carbon"], [282, 256, "non-shiftable load"],
  [180, 38, "T_out"], [206, 232, "HP electricity"], [390, 50, "heat"], [408, 150, "size"],
];

export function FlowDiagram() {
  const { nodes, colours } = useBundle();
  const { open } = useNodeParam();
  return (
    <svg viewBox="0 0 1080 330" className="h-auto w-full max-w-[1180px]" role="img" aria-label="How the simulation fits together">
      <defs><marker id="farr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#71717a" /></marker></defs>
      <g stroke="#a1a1aa" strokeWidth="1.5" fill="none" markerEnd="url(#farr)">{LINKS.map((d) => <path key={d} d={d} />)}</g>
      <g fontSize="10" fill="#71717a">{LABELS.map(([x, y, t]) => <text key={t} x={x} y={y}>{t}</text>)}</g>
      {BOXES.map((b) => {
        const n = nodes[b.ui], c = n?.classification ? colours[n.classification] : null, w = b.w ?? 150, h = b.h ?? 50;
        return (
          <g key={b.ui} transform={`translate(${b.x},${b.y})`} className="cursor-pointer" onClick={() => open(b.ui)}>
            <rect width={w} height={h} rx="7" fill={c ? `${c}22` : "#fafafa"} stroke={c ?? "#71717a"} strokeWidth="1.5" />
            <text x={w / 2} y={b.sub ? (h < 45 ? 18 : 22) : 20} textAnchor="middle" fontSize="13" fontWeight="600" fill="#1a202c">{b.title}</text>
            {b.sub && <text x={w / 2} y={h < 45 ? 32 : 38} textAnchor="middle" fontSize="10.5" fill="#52525b">{b.sub}</text>}
            <title>{n ? `${n.title}${n.classification ? ` — ${n.classification}` : ""}${n.summary ? `: ${n.summary}` : ""}` : b.ui}</title>
          </g>
        );
      })}
    </svg>
  );
}
