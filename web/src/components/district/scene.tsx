"use client";
// The illustrated district: pure drawing, driven by `hour` values passed in. Every number drawn comes from the bundle;
// building height only reflects housing units, the rest of the geometry is illustrative.
import type { ReactNode } from "react";
import type { DistrictBuilding } from "@/lib/types";

export const W = 1280, H = 720, GROUND = 530, BUS_Y = 572, TH = 58;
const C = { elec: "#f59f00", heat: "#e8590c", dhw: "#1098ad", ctrl: "#7048e8", feed: "#868e96", synth: "#e03131" };

// ui keys of clickable parts (all exist in ui_map.yaml; lint checks them)
export const UI = {
  district: "card:district", house: "series:building_electricity", hp: "card:cop_model", hpsize: "card:hp_nominal_power",
  tank: "card:tanks", meter: "kpi:district_import_kwh", grid: "card:environment", controller: "card:controllers",
  weather: "series:outdoor_temperature", tariff: "series:price", carbon: "series:carbon_intensity", selection: "card:building_selection",
  reward: "card:reward",
} as const;

export type BuildingState = {
  net: number | null; hp: number | null; socHeat: number | null; socDhw: number | null; actionHeat: number | null;
};
export type SceneState = {
  night: boolean; ghiK: number; sunX: number; sunY: number;
  tariff: string; tariffSub: string; carbon: string; carbonSub: string; weather: string; weatherSub: string;
  controller: string; reward: string;
  maxNet: number; maxHp: number; busFlow: number;
  buildings: BuildingState[];
};

export const slotX = (i: number) => 160 + i * 185;
const floorsOf = (b: DistrictBuilding) => (b.type === "SFH" ? 1 : Math.max(3, Math.round(Math.sqrt(b.units) * 1.25)));
const f = (v: number | null | undefined, d: number) => (v == null || Number.isNaN(v) ? "–" : (+v).toFixed(d));

function Flow({ d, color, v, vmax, wmin, wmax, className, opacity }: { d: string; color: string; v: number; vmax: number; wmin: number; wmax?: number; className?: string; opacity?: number }) {
  const dur = v > 1e-6 ? Math.max(0.35, 2.6 - 2.2 * Math.min(1, v / vmax)) : 0;
  const w = wmax && dur ? wmin + (wmax - wmin) * Math.min(1, v / vmax) : wmin;
  return <path d={d} className={`dflow ${dur ? "" : "dstill"} ${className ?? ""}`} stroke={color} strokeWidth={w} fill="none" style={{ animationDuration: dur ? `${dur}s` : "0s" }} opacity={opacity} />;
}

function Defs() {
  return (
    <defs>
      <linearGradient id="dwallS" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#fffaf0" /><stop offset="1" stopColor="#f3e7d3" /></linearGradient>
      <linearGradient id="dwallM" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#f1f3f5" /><stop offset="1" stopColor="#dee2e6" /></linearGradient>
      <linearGradient id="dgrass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b7dfa1" /><stop offset="1" stopColor="#8cc47a" /></linearGradient>
      <linearGradient id="dheat" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor="#d9480f" /><stop offset="1" stopColor="#ff922b" /></linearGradient>
      <linearGradient id="ddhw" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor="#0b7285" /><stop offset="1" stopColor="#3bc9db" /></linearGradient>
      <linearGradient id="dtankbody" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#ced4da" /><stop offset=".45" stopColor="#f8f9fa" /><stop offset="1" stopColor="#adb5bd" /></linearGradient>
      <radialGradient id="dsun"><stop offset="0" stopColor="#fff3bf" /><stop offset=".6" stopColor="#ffd43b" /><stop offset="1" stopColor="#fab005" stopOpacity="0" /></radialGradient>
      <filter id="dshadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="2.5" floodOpacity=".18" /></filter>
      <filter id="dglow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      <pattern id="dsynth" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff5f5" /><line x1="0" y1="0" x2="0" y2="6" stroke="#ffc9c9" strokeWidth="3" /></pattern>
    </defs>
  );
}

function Sky({ s }: { s: SceneState }) {
  const k = s.ghiK;
  const mix = (a: number[], b: number[]) => a.map((x, j) => Math.round(x + (b[j] - x) * k));
  const top = s.night ? [16, 28, 58] : mix([150, 180, 210], [120, 190, 255]);
  const bot = s.night ? [44, 62, 100] : mix([215, 225, 235], [235, 247, 255]);
  return (
    <>
      <defs>
        <linearGradient id="dsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={`rgb(${top})`} /><stop offset="1" stopColor={`rgb(${bot})`} /></linearGradient>
      </defs>
      <rect width={W} height={GROUND} fill="url(#dsky)" />
      <g opacity={s.night ? 0.8 : 0}>
        {Array.from({ length: 40 }, (_, i) => <circle key={i} cx={(i * 263) % W} cy={12 + ((i * 97) % 300)} r={(i % 3) * 0.5 + 0.6} fill="#fff" />)}
      </g>
      <circle cx={s.sunX} cy={s.night ? 600 : s.sunY} r={22 + 26 * k} fill="url(#dsun)" />
      <g opacity={s.night ? 1 : 0}><circle cx="1000" cy="80" r="16" fill="#f1f3f5" /><circle cx="1007" cy="75" r="14" fill={`rgb(${top})`} /></g>
      <path d={`M0,${GROUND} L120,400 L260,440 L420,380 L560,430 L720,370 L900,425 L1060,385 L1280,430 L1280,${GROUND} Z`} fill="#a5c8a0" opacity=".55" />
      <rect y={GROUND} width={W} height={H - GROUND} fill="url(#dgrass)" />
      <rect y={BUS_Y - 16} width={W} height="24" fill="#e9ecef" />
      <line x1="0" x2={W} y1={BUS_Y - 16} y2={BUS_Y - 16} stroke="#ced4da" />
      <rect y={BUS_Y + 8} width={W} height="58" fill="#495057" />
      <rect y={BUS_Y + 66} width={W} height={H - BUS_Y - 66} fill="#ced4da" />
      <line x1="0" x2={W} y1={BUS_Y + 37} y2={BUS_Y + 37} stroke="#f8f9fa" strokeWidth="2.5" strokeDasharray="26 22" />
    </>
  );
}

const ICON: Record<string, ReactNode> = {
  weather: <g><circle r="9" fill="#fcc419" /><path d="M-2,4 a8,8 0 0 1 14,-2 a6,6 0 0 1 2,12 h-14 a6,6 0 0 1 -2,-10z" fill="#e9ecef" stroke="#adb5bd" /></g>,
  tariff: <g><circle r="13" fill="#fff4e6" stroke="#f59f00" strokeWidth="2" /><text y="5" textAnchor="middle" fontSize="13" fontWeight="700" fill="#e67700">Rp</text></g>,
  carbon: <g><path d="M-10,8 C-14,-2 -4,-12 2,-8 C6,-14 16,-8 12,0 C18,4 12,12 6,10 Z" fill="#e9ecef" stroke="#b7791f" strokeWidth="1.6" /><text x="1" y="4" textAnchor="middle" fontSize="8" fontWeight="700" fill="#b7791f">CO₂</text></g>,
  ctrl: <g><rect x="-12" y="-12" width="24" height="24" rx="4" fill="#f3f0ff" stroke="#7048e8" strokeWidth="2" /><rect x="-5" y="-5" width="10" height="10" fill="#7048e8" /><path d="M-12,-6h-4M-12,0h-4M-12,6h-4M12,-6h4M12,0h4M12,6h4M-6,-12v-4M0,-12v-4M6,-12v-4M-6,12v4M0,12v4M6,12v4" stroke="#7048e8" strokeWidth="1.6" /></g>,
};

function FeedCard({ x, y, w, h, ui, icon, title, line, sub, open }: { x: number; y: number; w: number; h: number; ui: string; icon: string; title: string; line: string; sub: string; open: (id: string) => void }) {
  return (
    <g className="dclick" transform={`translate(${x},${y})`} filter="url(#dshadow)" onClick={() => open(ui)}>
      <rect width={w} height={h} rx="12" fill="#fff" fillOpacity=".94" stroke="#dee2e6" />
      <g transform={`translate(14,${h / 2})`}>{ICON[icon]}</g>
      <text x="52" y="22" fontSize="12.5" fontWeight="700" fill="#212529">{title}</text>
      <text x="52" y="38" fontSize="12" fill="#343a40">{line}</text>
      <text x="52" y="53" fontSize="9.5" fill="#868e96">{sub}</text>
    </g>
  );
}

function Substation({ open }: { open: (id: string) => void }) {
  return (
    <g className="dclick" transform={`translate(18,${GROUND - 130})`} onClick={() => open(UI.grid)}>
      <path d="M30,0 L18,130 M30,0 L42,130 M21,95 L39,95 M23,70 L37,70 M25,45 L35,45 M10,18 L50,18 M14,34 L46,34" stroke="#495057" strokeWidth="2.4" fill="none" />
      <circle cx="10" cy="18" r="2.5" fill="#495057" /><circle cx="50" cy="18" r="2.5" fill="#495057" />
      <g transform="translate(52,82)" filter="url(#dshadow)"><rect width="66" height="48" rx="6" fill="#e9ecef" stroke="#868e96" /><path d="M14,24 l6,-9 l6,18 l6,-18 l6,18 l6,-18 l6,9" stroke={C.elec} strokeWidth="2.4" fill="none" /></g>
      <text x="68" y="148" fontSize="10.5" fontWeight="700" fill="#343a40" textAnchor="middle">Grid · EKZ area</text>
    </g>
  );
}

function Building({ b, i, st, maxNet, maxHp, open }: { b: DistrictBuilding; i: number; st: BuildingState; maxNet: number; maxHp: number; open: (id: string) => void }) {
  const x = slotX(i), sfh = b.type === "SFH";
  const w = sfh ? 128 : 144, fl = floorsOf(b), fh = 34;
  const h = sfh ? 122 : fl * fh + 32, top = GROUND - h;
  const cy = GROUND - 80, lx = x + w - 32, ly = cy + 8;
  const t1 = x + 14, t2 = x + 42, ex = x + 72, ew = w - 112;
  const hx = x + w + 6, hy = GROUND - 36, mx = x + w / 2 + 6;
  const hp = st.hp ?? 0, net = Math.max(st.net ?? 0, 0);
  const hpDur = hp > 1e-6 ? Math.max(0.35, 2.6 - 2.2 * Math.min(1, hp / maxHp)) : 0;
  const wins: [number, number, number, number][] = [];
  if (sfh) wins.push([x + 16, top + 8, 28, 24], [x + w - 44, top + 8, 28, 24]);
  else for (let r = 0; r < fl - 1; r++) for (let k = 0; k < 4; k++) wins.push([x + 13 + k * 33, top + 10 + r * fh, 21, 20]);
  let wave = `M${ex},${GROUND - 8}`;
  for (let k = 0; k <= ew; k += 8) wave += ` L${ex + k},${GROUND - 8 - ((k / 8) % 2 ? 6 : 0)}`;
  const label = sfh ? `${b.source} household${b.area_m2 ? ` · ${f(b.area_m2, 0)} m²` : ""}` : `${b.source} · ${b.units} housing units`;
  const nameY = sfh ? top - 84 : top - 30;

  const tank = (tx: number, kind: "heat" | "dhw", cap: number, soc: number | null) => {
    const tw = 22;
    if (!cap) return (
      <g className="dclick" onClick={() => open(UI.tank)}>
        <rect x={tx} y={cy + 6} width={tw} height={TH} rx="9" fill="none" stroke="#ced4da" strokeDasharray="3 3" />
        <text x={tx + tw / 2} y={cy + 38} textAnchor="middle" fontSize="8" fill="#adb5bd">none</text>
        <title>No {kind === "dhw" ? "hot-water" : "heating"} tank in this building (D-017a rule).</title>
      </g>
    );
    const fill = (TH - 4) * Math.max(0, Math.min(1, soc ?? 0));
    const id = `dclip${kind}${i}`;
    return (
      <g className="dclick" onClick={() => open(UI.tank)}>
        <rect x={tx} y={cy + 6} width={tw} height={TH} rx="9" fill="url(#dtankbody)" stroke="#868e96" />
        <clipPath id={id}><rect x={tx + 2} y={cy + 8} width={tw - 4} height={TH - 4} rx="7" /></clipPath>
        <rect clipPath={`url(#${id})`} x={tx + 2} y={cy + 8 + TH - 4 - fill} width={tw - 4} height={fill} fill={`url(#${kind === "dhw" ? "ddhw" : "dheat"})`} />
        <rect x={tx} y={cy + 6} width={tw} height={TH} rx="9" fill="none" stroke={C.synth} strokeWidth="1.2" strokeDasharray="4 2" opacity=".75" />
        <text x={tx + tw / 2} y={cy + TH + 15} textAnchor="middle" fontSize="8.5" fontWeight="600" fill="#495057">{kind === "dhw" ? "DHW" : "heat"}</text>
        <title>{`${kind === "dhw" ? "Hot-water" : "Heating buffer"} tank ${f(cap, 2)} kWh_th, state of charge ${f(soc, 3)} (SYNTHETIC, D-017a)`}</title>
      </g>
    );
  };

  const ah = st.actionHeat ?? 0;
  return (
    <g>
      {sfh ? (
        <>
          <path d={`M${x - 10},${top + 2} L${x + w / 2},${top - 62} L${x + w + 10},${top + 2} Z`} fill="#c92a2a" opacity=".88" />
          <path d={`M${x - 10},${top + 2} L${x + w / 2},${top - 62} L${x + w + 10},${top + 2}`} fill="none" stroke="#862e2e" strokeWidth="3" strokeLinejoin="round" />
          <rect x={x + w - 34} y={top - 40} width="14" height="26" fill="#a61e4d" opacity=".9" />
        </>
      ) : <rect x={x - 6} y={top - 10} width={w + 12} height="12" rx="2" fill="#495057" />}
      <rect className="dclick" onClick={() => open(UI.house)} x={x} y={top} width={w} height={h} fill={`url(#${sfh ? "dwallS" : "dwallM"})`} stroke="#adb5bd" strokeWidth="1.5" filter="url(#dshadow)" />
      <g>{wins.map(([a, c, d, e], k) => <rect key={k} className="dwin" x={a} y={c} width={d} height={e} rx="2" />)}</g>
      <rect x={x + 6} y={cy - 4} width={w - 12} height="80" rx="5" fill="#fff" fillOpacity=".86" stroke="#ced4da" strokeDasharray="3 2" />
      {b.apartments_synthetic ? (
        <g className="dclick" onClick={() => open(UI.house)}>
          <rect x={lx - 10} y={ly - 2} width="30" height="26" rx="4" fill="url(#dsynth)" stroke={C.synth} strokeDasharray="3 2" />
          <text x={lx + 5} y={ly + 10} textAnchor="middle" fontSize="7.5" fontWeight="700" fill={C.synth}>apts</text>
          <text x={lx + 5} y={ly + 19} textAnchor="middle" fontSize="6.5" fill={C.synth}>synthetic</text>
          <title>Apartment load is SYNTHETIC: drawn from other EKZ apartment meters, not this building (D-006, D-015).</title>
        </g>
      ) : (
        <g className="dclick" onClick={() => open(UI.house)}>
          <circle cx={lx + 5} cy={ly + 10} r="9" fill="#fff9db" stroke="#fab005" /><path d={`M${lx + 2},${ly + 13} v4 h6 v-4`} stroke="#868e96" fill="none" /><circle cx={lx + 5} cy={ly + 8} r="4" fill="#ffe066" />
          <title>Household electricity (HEAPO, measured)</title>
        </g>
      )}
      {tank(t1, "heat", b.heating_tank_kwh_th, st.socHeat)}
      {tank(t2, "dhw", b.dhw_tank_kwh_th, st.socDhw)}
      <Flow d={wave} color={C.heat} v={hp} vmax={maxHp} wmin={2.4} className="" />
      <Flow d={`M${t1 + 10},${cy + 6} V${cy - 1} H${ex} V${GROUND - 8}`} color={C.heat} v={hp + Math.max(-ah, 0)} vmax={maxHp} wmin={2.2} />
      {b.dhw_tank_kwh_th > 0 && (
        <>
          <Flow d={`M${t2 + 10},${cy + 6} V${cy + 1} H${lx - 16} V${cy + 18}`} color={C.dhw} v={st.socDhw != null ? 0.3 : 0} vmax={1} wmin={2} />
          <path d={`M${lx - 20},${cy + 18} h8 v5`} stroke="#495057" strokeWidth="2" fill="none" />
        </>
      )}
      <g className="dclick" filter="url(#dshadow)" onClick={() => open(UI.hp)}>
        <rect x={hx} y={hy} width="30" height="32" rx="4" fill="#f8f9fa" stroke="#868e96" />
        <circle cx={hx + 15} cy={hy + 14} r="10" fill="#e9ecef" stroke="#adb5bd" />
        <g className={`dfan ${hpDur ? "" : "dstill"}`} style={{ transformOrigin: `${hx + 15}px ${hy + 14}px`, animationDuration: hpDur ? `${hpDur * 0.6}s` : "0s" }}>
          <path d={`M${hx + 15},${hy + 14} l0,-9 a4,4 0 0 1 4,4z M${hx + 15},${hy + 14} l9,0 a4,4 0 0 1 -4,4z M${hx + 15},${hy + 14} l0,9 a4,4 0 0 1 -4,-4z M${hx + 15},${hy + 14} l-9,0 a4,4 0 0 1 4,-4z`} fill="#495057" />
        </g>
        <rect x={hx + 4} y={hy + 27} width="22" height="3" rx="1.5" fill="#dee2e6" />
        <rect x={hx + 4} y={hy + 27} width={22 * Math.min(1, hp / (b.hp_sh_nominal_kw + b.hp_dhw_nominal_kw))} height="3" rx="1.5" fill={C.elec} />
        <title>{`${b.role} heat pump: ${f(st.hp, 3)} kWh electricity this hour; nominal ${f(b.hp_sh_nominal_kw, 2)} kW (heating) + ${f(b.hp_dhw_nominal_kw, 2)} kW (DHW); T_sup ${b.T_sup_sh_c} °C, η ${f(b.eta_sh, 3)}`}</title>
      </g>
      <text className="dclick" onClick={() => open(UI.hpsize)} x={hx + 15} y={hy - 5} textAnchor="middle" fontSize="9.5" fontWeight="700" fill="#495057">{f(b.hp_sh_nominal_kw, 1)} kW</text>
      <Flow d={`M${hx},${hy + 8} H${x + w + 2} H${t1 + 10} V${cy + 6}`} color={C.heat} v={hp} vmax={maxHp} wmin={1.6} wmax={5} opacity={0.95} />
      {b.dhw_tank_kwh_th > 0 && <Flow d={`M${hx},${hy + 18} H${t2 + 11} V${cy + TH + 4}`} color={C.dhw} v={hp} vmax={maxHp} wmin={1.4} wmax={3.6} />}
      <Flow d={`M${mx},${BUS_Y} V${GROUND + 6}`} color={C.elec} v={net} vmax={maxNet} wmin={2} wmax={7} />
      <g className="dclick" onClick={() => open(UI.meter)}>
        <rect x={mx - 11} y={GROUND - 4} width="22" height="16" rx="3" fill="#212529" /><rect x={mx - 8} y={GROUND - 1} width="16" height="7" rx="1" fill={net > 0.01 ? "#69db7c" : "#2b8a3e"} />
        <title>{`${b.role} net electricity this hour: ${f(st.net, 3)} kWh`}</title>
      </g>
      <g className="dclick" onClick={() => open(UI.selection)}>
        <text x={x + w / 2} y={nameY} textAnchor="middle" fontSize="14" fontWeight="800" fill="#212529" stroke="#fff" strokeWidth="3" paintOrder="stroke">{b.role}</text>
        <text x={x + w / 2} y={nameY + 14} textAnchor="middle" fontSize="9.5" fill="#495057" stroke="#fff" strokeWidth="3" paintOrder="stroke">{b.building} · {label}</text>
      </g>
      <g transform={`translate(${mx},${BUS_Y + 30})`}>
        <rect x="-38" y="-11" width="76" height="20" rx="10" fill="#fff" fillOpacity=".95" stroke={C.elec} />
        <text y="3" textAnchor="middle" fontSize="10.5" fontWeight="700" fill="#5c3d00">{st.net == null ? "no trace" : `${f(st.net, 2)} kWh`}</text>
      </g>
    </g>
  );
}

function Legend() {
  const items: [string, string, string?][] = [[C.elec, "electricity (import)"], [C.heat, "space-heating water"], [C.dhw, "hot water"], [C.ctrl, "controller action", "6 4"], [C.feed, "data feed", "2 4"]];
  let x = 18;
  return (
    <>
      <rect y={H - 58} width={W} height="58" fill="#212529" />
      {items.map(([c, t, d]) => {
        const g = <g key={t} transform={`translate(${x},${H - 28})`}><line x2="26" stroke={c} strokeWidth="3" strokeDasharray={d} /><text x="32" y="4" fontSize="11" fill="#f8f9fa">{t}</text></g>;
        x += 32 + t.length * 6.2 + 18;
        return g;
      })}
      <g transform={`translate(${x},${H - 36})`}><rect width="22" height="14" rx="3" fill="url(#dsynth)" stroke={C.synth} strokeDasharray="3 2" /><text x="28" y="11" fontSize="11" fill="#f8f9fa">synthetic (tanks, apartment loads)</text></g>
    </>
  );
}

export function Scene({ buildings, state: s, observed, open }: { buildings: DistrictBuilding[]; state: SceneState; observed: Set<string>; open: (id: string) => void }) {
  const yrail = 150;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={`dsvg block h-auto w-full rounded-2xl shadow-lg ${s.night ? "dnight" : ""}`} role="img" aria-label="Six-building district, one hour at a time">
      <Defs />
      <Sky s={s} />
      <Substation open={open} />
      <g>
        <path className="dfeed" d={`M1150,104 V${yrail} H${slotX(0) + 150}`} stroke={C.feed} />
        {buildings.map((b, i) => <path key={b.building} className="dfeed" d={`M${slotX(i) + (b.type === "SFH" ? 128 : 144) + 21},${yrail} V${GROUND - 36}`} stroke={C.feed} />)}
        <text x={slotX(0) + 160} y={yrail - 5} fontSize="10" fontStyle="italic" fill={s.night ? "#dee2e6" : "#495057"}>outdoor temperature → heat-pump COP (M-001)</text>
        {observed.has("outdoor_dry_bulb_temperature") && <path className="dfeed dobs" d="M1090,64 H780" stroke={C.ctrl} />}
        <path className="dfeed" d={`M48,104 V${GROUND - 128}`} stroke={C.feed} />
        <path className="dfeed" d={`M100,188 V${GROUND - 48}`} stroke={C.feed} />
        {observed.has("electricity_pricing") && <path className="dfeed dobs" d="M250,62 H500" stroke={C.ctrl} />}
        {observed.has("carbon_intensity") && <path className="dfeed dobs" d="M250,148 C400,148 450,80 500,70" stroke={C.ctrl} />}
        {buildings.map((b, i) => {
          const x = slotX(i), sfh = b.type === "SFH", top = GROUND - (sfh ? 122 : floorsOf(b) * 34 + 32);
          const a = s.buildings[i].actionHeat ?? 0, on = Math.abs(a) > 1e-6;
          return <path key={b.building} className={`dflow ${on ? "" : "dstill"} ${a < 0 ? "drev" : ""}`} d={`M640,98 C640,${150 + i * 6} ${x + 24},${top - 20} ${x + 24},${GROUND - 78}`} stroke={C.ctrl} strokeWidth={on ? 2 : 1.2} fill="none" opacity={on ? 0.85 : 0.15} style={{ animationDuration: on ? "1.2s" : "0s" }} />;
        })}
        <path className="dfeed dobs" d={`M${slotX(5) + 70},${GROUND - 8} C1240,300 900,90 780,70`} stroke={C.ctrl} opacity=".35" />
        <Flow d={`M136,${GROUND - 25} V${BUS_Y} H${W - 10}`} color={C.elec} v={s.busFlow} vmax={s.maxNet * buildings.length} wmin={3} wmax={8} />
      </g>
      {buildings.map((b, i) => <Building key={b.building} b={b} i={i} st={s.buildings[i]} maxNet={s.maxNet} maxHp={s.maxHp} open={open} />)}
      <FeedCard x={18} y={30} w={232} h={74} ui={UI.tariff} icon="tariff" title="Electricity price" line={s.tariff} sub={s.tariffSub} open={open} />
      <FeedCard x={18} y={114} w={232} h={74} ui={UI.carbon} icon="carbon" title="Grid carbon (modeled)" line={s.carbon} sub={s.carbonSub} open={open} />
      <FeedCard x={1030} y={30} w={232} h={74} ui={UI.weather} icon="weather" title="Weather · Zurich/Kloten" line={s.weather} sub={s.weatherSub} open={open} />
      <FeedCard x={500} y={30} w={280} h={68} ui={UI.controller} icon="ctrl" title="Controller" line={s.controller} sub="" open={open} />
      <g className="dclick" transform="translate(790,44)" onClick={() => open(UI.reward)}>
        <rect width="150" height="40" rx="10" fill="#fff" fillOpacity=".9" stroke="#d0bfff" />
        <text x="12" y="17" fontSize="11" fontWeight="700" fill="#212529">Reward R-001</text>
        <text x="12" y="32" fontSize="12" fill="#343a40">{s.reward}</text>
      </g>
      <Legend />
      <text className="dclick" onClick={() => open(UI.district)} x={W - 18} y={H - 24} textAnchor="end" fontSize="13" fontWeight="700" fill="#f1f3f5">Six-building district · 2023 · about this view ⓘ</text>
    </svg>
  );
}
