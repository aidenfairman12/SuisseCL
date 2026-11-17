"use client";

import type { DistrictBuilding } from "@/lib/types";

export type BuildingState = {
  net: number | null;
  hp: number | null;
  socHeat: number | null;
  socDhw: number | null;
  actionHeat: number | null;
};

export type SceneState = {
  night: boolean;
  ghiK: number;
  sunX: number;
  sunY: number;
  tariff: string;
  tariffSub: string;
  carbon: string;
  carbonSub: string;
  weather: string;
  weatherSub: string;
  controller: string;
  maxNet: number;
  maxHp: number;
  busFlow: number;
  buildings: BuildingState[];
};

const W = 1200;
const H = 650;
const positions = [
  // Three detached houses are dispersed across the left and centre.
  { x: 155, y: 340, scale: 0.9 },
  { x: 405, y: 275, scale: 0.82 },
  { x: 675, y: 350, scale: 1.0 },
  // Apartment buildings sit more loosely together along the access road.
  { x: 865, y: 320, scale: 0.78 },
  { x: 1010, y: 405, scale: 0.9 },
  { x: 1080, y: 265, scale: 0.96 },
];
const fmt = (v: number | null, d = 1) => v == null || !Number.isFinite(v) ? "—" : v.toFixed(d);

function Tree({ x, y, scale = 1 }: { x: number; y: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx="0" cy="28" rx="19" ry="6" fill="#315d3b" opacity=".18" />
      <path d="M-3 8h6v20h-6z" fill="#795548" />
      <circle cx="0" cy="-3" r="17" fill="#4f8b55" />
      <circle cx="-11" cy="5" r="10" fill="#6aa66b" />
      <circle cx="11" cy="6" r="11" fill="#3e7548" />
    </g>
  );
}

function Garden({ x, y, scale = 1 }: { x: number; y: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx="0" cy="0" rx="72" ry="25" fill="#6f9d60" opacity=".25" />
      <path d="M-54 -5Q-25 -24 12 -14T55 -5" fill="none" stroke="#e4d6b8" strokeWidth="3" />
      <path d="M-45 7Q-20 -3 5 7T42 7" fill="none" stroke="#789d5c" strokeWidth="2" />
      <circle cx="-42" cy="-7" r="5" fill="#e7c1a1" /><circle cx="-28" cy="-12" r="4" fill="#f0d7a0" />
      <circle cx="34" cy="-10" r="5" fill="#d99a91" /><circle cx="46" cy="-4" r="4" fill="#f0d7a0" />
      <path d="M-63 18h126" stroke="#e7e0cf" strokeWidth="2" strokeDasharray="3 4" />
    </g>
  );
}

function House({ b, name, selected, onSelect, x, y, scale, state }: {
  b: DistrictBuilding; name: string; selected: boolean; onSelect: () => void;
  x: number; y: number; scale: number; state: BuildingState;
}) {
  const sfh = b.type === "SFH";
  const width = sfh ? 118 * Math.sqrt((b.area_m2 ?? 180) / 180) : 112 + Math.sqrt(b.units) * 8;
  const height = sfh ? 78 : 68 + Math.sqrt(b.units) * 9;
  const depth = sfh ? 48 : 42;
  const roof = sfh ? "#a64b3c" : "#64748b";
  const front = selected ? "#fff5df" : "#f1e8d9";
  const side = selected ? "#e8d6b9" : "#d8cbb9";
  const soc = state.socHeat == null ? null : Math.max(0, Math.min(1, state.socHeat));
  const detailStart = name.indexOf("(");
  const primaryLabel = detailStart > 0 ? name.slice(0, detailStart).trim() : name;
  const secondaryLabel = detailStart > 0 ? name.slice(detailStart + 1, -1) : "";
  return (
    <g
      transform={`translate(${x} ${y}) scale(${scale})`}
      role="button"
      tabIndex={0}
      aria-label={`Select ${name}`}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(); } }}
      style={{ cursor: "pointer", outline: "none" }}
      className="transition-[filter] hover:brightness-105"
    >
      {selected && <ellipse cx="0" cy="8" rx={width * 0.82} ry="35" fill="#d97706" opacity=".14" />}
      <ellipse cx="0" cy="10" rx={width * 0.78} ry="25" fill="#315d3b" opacity=".16" />
      {sfh ? (
        <>
          <path d={`M${-width / 2} ${-height} L0 ${-height - 48} L${width / 2} ${-height} L${width / 2 + depth} ${-height + 20} L${depth} ${-height + 68} Z`} fill={roof} stroke="#713b32" strokeWidth="2" />
          <path d={`M${-width / 2} ${-height} L0 ${-height - 48} L0 ${-height + 1} L${-width / 2} ${-height + 30} Z`} fill="#bd6550" />
        </>
      ) : (
        <>
          <path d={`M${-width / 2} ${-height} L${-width / 2 + depth} ${-height - 20} L${width / 2 + depth} ${-height - 20} L${width / 2} ${-height} Z`} fill="#64748b" />
          <path d={`M${-width / 2} ${-height} L${width / 2} ${-height} L${width / 2} 0 L${-width / 2} 0 Z`} fill={front} stroke={selected ? "#b45309" : "#b9aa98"} strokeWidth={selected ? 3 : 1.5} />
          <path d={`M${width / 2} ${-height} L${width / 2 + depth} ${-height - 20} L${width / 2 + depth} ${-20} L${width / 2} 0 Z`} fill={side} stroke="#b9aa98" />
          {Array.from({ length: Math.max(2, Math.min(5, Math.round(Math.sqrt(b.units)))) }, (_, floor) =>
            <g key={floor}>
              {[-1, 0, 1].map((col) => <rect key={col} x={col * 28 - 12} y={-height + 12 + floor * ((height - 18) / Math.max(2, Math.min(5, Math.round(Math.sqrt(b.units)))))} width="15" height="13" rx="2" fill="#8db7c8" stroke="#6b8793" strokeWidth=".8" />)}
            </g>
          )}
        </>
      )}
      {sfh && (
        <>
          <path d={`M${-width / 2} ${-height} L${width / 2} ${-height} L${width / 2} 0 L${-width / 2} 0 Z`} fill={front} stroke={selected ? "#b45309" : "#b9aa98"} strokeWidth={selected ? 3 : 1.5} />
          <path d={`M${width / 2} ${-height} L${width / 2 + depth} ${-height + 20} L${width / 2 + depth} 20 L${width / 2} 0 Z`} fill={side} stroke="#b9aa98" />
          <rect x="-36" y={-height + 23} width="23" height="23" rx="2" fill="#8db7c8" stroke="#6b8793" />
          <rect x="13" y={-height + 23} width="23" height="23" rx="2" fill="#8db7c8" stroke="#6b8793" />
          <rect x="-8" y={-34} width="22" height="34" fill="#8b6651" />
        </>
      )}
      <path d={`M${-width / 2} 0 L${width / 2} 0 L${width / 2 + depth} 20 L${depth} 20 Z`} fill="#b9a98e" opacity=".8" />
      <g transform={`translate(${width / 2 + depth + 14} ${-18})`}>
        <rect x="-7" y="-35" width="14" height="35" rx="6" fill="#e5e7eb" stroke="#64748b" />
        {soc != null && <rect x="-5" y={-3 - 29 * soc} width="10" height={29 * soc} rx="4" fill="#ea580c" />}
      </g>
      {selected && <path d={`M${-width / 2 - 8} 8 L${width / 2 + depth + 8} 28`} stroke="#d97706" strokeWidth="3" strokeDasharray="5 5" />}
      <rect x={-width / 2 - 5} y={25} width={width + depth + 10} height="30" rx="15" fill={selected ? "#92400e" : "#334155"} opacity=".95" />
      <text x={depth / 2} y={secondaryLabel ? "40" : "45"} textAnchor="middle" fontSize="10.5" fontWeight="700" fill="#fff">{primaryLabel}</text>
      {secondaryLabel && <text x={depth / 2} y="52" textAnchor="middle" fontSize="9" fill="#fff">{secondaryLabel}</text>}
      <text x={depth / 2} y="75" textAnchor="middle" fontSize="10" fill="#334155">{sfh ? `${fmt(b.area_m2, 0)} m²` : `${b.units} homes`}</text>
      <title>{name}. Select to inspect the building.</title>
    </g>
  );
}

export function Scene({ buildings, names, state, selectedBuilding, onSelect }: {
  buildings: DistrictBuilding[];
  names: string[];
  state: SceneState;
  selectedBuilding: string;
  onSelect: (role: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border bg-[#e8f0e3] shadow-sm">
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="group" aria-label="Illustrated representative Swiss residential development">
          <defs>
            <linearGradient id="neighborhood-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#dceaf0" /><stop offset="1" stopColor="#f4f1e7" /></linearGradient>
            <linearGradient id="neighborhood-ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b8d3a7" /><stop offset="1" stopColor="#8fb783" /></linearGradient>
            <filter id="building-shadow" x="-30%" y="-30%" width="160%" height="180%"><feDropShadow dx="0" dy="8" stdDeviation="7" floodColor="#263b2b" floodOpacity=".18" /></filter>
          </defs>
          <rect width={W} height={H} fill="url(#neighborhood-sky)" />
          <path d="M0 310 L130 205 L250 282 L390 180 L520 275 L660 190 L790 270 L950 175 L1100 255 L1200 210 L1200 650 L0 650Z" fill="#c6d8cf" opacity=".55" />
          <path d="M0 395 Q250 330 460 400 T900 380 T1200 395 L1200 650 L0 650Z" fill="url(#neighborhood-ground)" />
          <path d="M-40 520 Q260 450 480 510 T920 500 T1240 525" fill="none" stroke="#d8d2c4" strokeWidth="58" />
          <path d="M-40 520 Q260 450 480 510 T920 500 T1240 525" fill="none" stroke="#f8f5ed" strokeWidth="3" strokeDasharray="18 16" />
          <path d="M40 430 Q250 360 440 425 T830 420 T1160 430" fill="none" stroke="#e8dfca" strokeWidth="22" opacity=".9" />
          <path d="M40 430 Q250 360 440 425 T830 420 T1160 430" fill="none" stroke="#fffaf0" strokeWidth="2" strokeDasharray="6 9" />
          <g opacity=".96">
            <Garden x={175} y={425} scale={0.9} /><Garden x={430} y={365} scale={0.82} /><Garden x={690} y={445} scale={0.9} /><Garden x={865} y={390} scale={0.72} /><Garden x={1000} y={465} scale={0.8} />
            <Tree x={55} y={375} scale={1.2} /><Tree x={290} y={445} /><Tree x={575} y={445} scale={1.1} /><Tree x={755} y={260} scale={1.15} /><Tree x={945} y={255} /><Tree x={1160} y={445} scale={1.15} />
          </g>
          <g filter="url(#building-shadow)">
            {buildings.map((b, i) => <House key={b.building} b={b} name={names[i]} selected={selectedBuilding === b.role} onSelect={() => onSelect(b.role)} {...positions[i]} state={state.buildings[i]} />)}
          </g>
          <g transform="translate(30 28)">
            <rect width="285" height="68" rx="14" fill="#ffffff" fillOpacity=".88" stroke="#d8dfd6" />
            <text x="18" y="27" fontSize="15" fontWeight="700" fill="#294332">Representative Swiss residential development</text>
            <text x="18" y="49" fontSize="12" fill="#52675a">Six modeled building archetypes · not a real street</text>
          </g>
          <g transform="translate(925 28)">
            <rect width="245" height="68" rx="14" fill="#ffffff" fillOpacity=".88" stroke="#d8dfd6" />
            <text x="16" y="26" fontSize="12" fontWeight="700" fill="#334155">Current conditions</text>
            <text x="16" y="47" fontSize="13" fill="#334155">{state.weather} · {state.tariff}</text>
          </g>
        </svg>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#d0ddca] bg-[#f8faf6] px-4 py-3 text-xs text-slate-600">
        <span>Illustrative architecture and storeys · no shared grid, heat network, or energy exchange is modeled</span>
        <span>Choose a building to inspect its heating system</span>
      </div>
    </div>
  );
}
