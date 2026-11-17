"use client";

type DistrictBuilding = {
  role: string;
  type: "SFH" | "MFH";
  units: number | null;
  area_m2: number | null;
};

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
  { x: 185, y: 330, scale: 0.88 },
  { x: 405, y: 250, scale: 0.82 },
  { x: 640, y: 345, scale: 0.96 },
  { x: 825, y: 260, scale: 0.82 },
  { x: 980, y: 375, scale: 0.92 },
  { x: 1050, y: 205, scale: 0.9 },
];
const fmt = (v: number | null, d = 1) => v == null || !Number.isFinite(v) ? "—" : v.toFixed(d);

function Tree({ x, y, scale = 1, tone = 0 }: { x: number; y: number; scale?: number; tone?: number }) {
  const greens = ["#477b53", "#5e925d", "#3f704a"];
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <ellipse cx="0" cy="22" rx="18" ry="6" fill="#314c39" opacity=".16" />
      <path d="M-3 4h6v20h-6z" fill="#80634a" />
      <circle cx="0" cy="-8" r="17" fill={greens[tone % 3]} />
      <circle cx="-11" cy="0" r="11" fill="#6b9c67" />
      <circle cx="10" cy="1" r="12" fill={greens[(tone + 1) % 3]} />
      <circle cx="-3" cy="-16" r="9" fill="#79a96d" opacity=".8" />
    </g>
  );
}

function House({ b, name, selected, onSelect, x, y, scale, state }: {
  b: DistrictBuilding; name: string; selected: boolean; onSelect: () => void;
  x: number; y: number; scale: number; state: BuildingState;
}) {
  const sfh = b.type === "SFH";
  const width = sfh ? 106 : 126;
  const height = sfh ? 72 : 88;
  const depth = sfh ? 43 : 42;
  const wall = selected ? "#fff8e9" : "#f2eadc";
  const side = selected ? "#e8d7bc" : "#d8c9b3";
  const roof = sfh ? "#a94f40" : "#65747a";
  const soc = state.socHeat == null ? null : Math.max(0, Math.min(1, state.socHeat));
  const floors = 3; // Illustrative façade detail only; apartment floor counts are unavailable.
  const detailStart = name.indexOf("(");
  const primaryLabel = detailStart > 0 ? name.slice(0, detailStart).trim() : name;
  const secondaryLabel = detailStart > 0 ? name.slice(detailStart + 1, -1) : "";
  return (
    <g
      transform={`translate(${x} ${y}) scale(${scale})`}
      role="button" tabIndex={0} aria-label={`Select ${name}`} aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(); } }}
      style={{ cursor: "pointer", outline: "none" }}
      className="transition-[filter] duration-200 hover:brightness-105"
    >
      {selected && <ellipse cx="5" cy="8" rx={width * 0.9} ry="30" fill="#d58b36" opacity=".2" />}
      <ellipse cx="5" cy="12" rx={width * .82} ry="22" fill="#344d3a" opacity=".16" />
      {sfh ? (
        <>
          <path d={`M${-width/2} ${-height} L0 ${-height-43} L${width/2} ${-height} L${width/2+depth} ${-height+17} L${depth} ${-height+60} Z`} fill={roof} stroke="#754239" strokeWidth="2" />
          <path d={`M${-width/2} ${-height} L0 ${-height-43} L0 ${-height+2} L${-width/2} ${-height+27} Z`} fill="#c36b55" />
          <path d={`M0 ${-height-43} L${width/2} ${-height} L${width/2+depth} ${-height+17} L${depth} ${-height+60} Z`} fill="#984638" opacity=".55" />
        </>
      ) : (
        <>
          <path d={`M${-width/2} ${-height} L${-width/2+depth} ${-height-19} L${width/2+depth} ${-height-19} L${width/2} ${-height} Z`} fill="#89979a" stroke="#68777b" strokeWidth="2" />
          <path d={`M${-width/2+depth} ${-height-19} L${width/2+depth} ${-height-19} L${width/2+depth} ${-height-3} L${-width/2+depth} ${-height-3} Z`} fill="#53676d" />
        </>
      )}
      <path d={`M${-width/2} ${-height} L${width/2} ${-height} L${width/2} 0 L${-width/2} 0 Z`} fill={wall} stroke={selected ? "#b97732" : "#b9aa98"} strokeWidth={selected ? 3 : 1.5} />
      <path d={`M${width/2} ${-height} L${width/2+depth} ${-height+17} L${width/2+depth} 17 L${width/2} 0 Z`} fill={side} stroke="#b6a68f" strokeWidth="1.5" />
      {sfh ? (
        <>
          <rect x="-34" y={-height+22} width="22" height="24" rx="2" fill="#a9cbd5" stroke="#718f99" />
          <rect x="12" y={-height+22} width="22" height="24" rx="2" fill="#a9cbd5" stroke="#718f99" />
          <path d={`M-8 ${-height+22}h22v24H-8z`} fill="#a9cbd5" stroke="#718f99" />
          <rect x="-7" y="-34" width="20" height="34" fill="#87634d" />
          <circle cx="8" cy="-17" r="1.5" fill="#e9d3a6" />
        </>
      ) : (
        <>
          {Array.from({ length: floors }, (_, floor) => (
            <g key={floor}>
              {[-1, 0, 1].map((col) => (
                <g key={col}>
                  <rect x={col*27-11} y={-height+10+floor*((height-14)/floors)} width="16" height="14" rx="1.5" fill="#a9cbd5" stroke="#78949b" strokeWidth=".8" />
                  <path d={`M${col*27-13} ${-height+25+floor*((height-14)/floors)}h20`} stroke="#b69a79" strokeWidth="2" />
                </g>
              ))}
            </g>
          ))}
          <rect x="-8" y="-28" width="17" height="28" fill="#87634d" />
        </>
      )}
      <path d={`M${-width/2} 0 L${width/2} 0 L${width/2+depth} 17 L${depth} 17 Z`} fill="#c0ad91" />
      <g transform={`translate(${width/2+depth+12} -16)`}>
        <rect x="-6" y="-31" width="12" height="31" rx="5" fill="#e3e8e7" stroke="#87979a" />
        {soc != null && <rect x="-4" y={-3-25*soc} width="8" height={25*soc} rx="3" fill="#e17a36" />}
      </g>
      {selected && <path d={`M${-width/2-9} 9 L${width/2+depth+10} 26`} stroke="#d58b36" strokeWidth="3" strokeDasharray="5 5" />}
      <rect x={-width/2-8} y="27" width={width+depth+16} height="28" rx="14" fill={selected ? "#80502d" : "#3e5546"} opacity=".96" />
      <text x={depth/2} y={secondaryLabel ? "39" : "45"} textAnchor="middle" fontSize="10.5" fontWeight="700" fill="#fff">{primaryLabel}</text>
      {secondaryLabel && <text x={depth/2} y="51" textAnchor="middle" fontSize="8.5" fill="#fff">{secondaryLabel}</text>}
      <text x={depth/2} y="73" textAnchor="middle" fontSize="10" fill="#45594a">{sfh ? (b.area_m2 == null ? "Area unavailable" : `${fmt(b.area_m2, 0)} m²`) : (b.units == null ? "Unit count unavailable" : `${b.units} homes`)}</text>
      <title>{name}. Select to inspect the building.</title>
    </g>
  );
}

function Pathway({ d, width = 14 }: { d: string; width?: number }) {
  return <g fill="none" strokeLinecap="round"><path d={d} stroke="#c8bda7" strokeWidth={width+5}/><path d={d} stroke="#f4eddf" strokeWidth={width}/></g>;
}

export function Scene({ buildings, names, state, selectedBuilding, onSelect }: {
  buildings: DistrictBuilding[];
  names: string[];
  state: SceneState;
  selectedBuilding: string;
  onSelect: (role: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#d9dfd4] bg-[#e9eee7] shadow-sm">
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="group" aria-label="Illustrated representative Swiss residential development">
          <defs>
            <linearGradient id="district-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#dce9e9"/><stop offset="1" stopColor="#f5f0e5"/></linearGradient>
            <linearGradient id="district-meadow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b9d0a9"/><stop offset="1" stopColor="#8eaf83"/></linearGradient>
            <filter id="district-shadow" x="-30%" y="-30%" width="170%" height="190%"><feDropShadow dx="0" dy="10" stdDeviation="8" floodColor="#314b3b" floodOpacity=".2"/></filter>
            <filter id="soft-shadow" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#314b3b" floodOpacity=".13"/></filter>
          </defs>
          <rect width={W} height={H} fill="url(#district-sky)"/>
          <path d="M0 300L120 210 245 275 370 168 510 270 650 175 785 270 930 165 1080 260 1200 195V650H0Z" fill="#c7d8d1" opacity=".62"/>
          <path d="M0 365Q240 310 430 370T820 355T1200 370V650H0Z" fill="#b5cba8"/>
          <path d="M0 415Q230 355 440 420T850 405T1200 420V650H0Z" fill="url(#district-meadow)"/>
          <path d="M70 530L340 420 575 500 840 390 1110 490" fill="none" stroke="#d2c8b4" strokeWidth="72" strokeLinecap="round"/>
          <path d="M70 530L340 420 575 500 840 390 1110 490" fill="none" stroke="#f7f1e6" strokeWidth="3" strokeDasharray="15 18" strokeLinecap="round"/>
          <Pathway d="M70 390Q250 330 400 390T720 390T1120 350" width={12}/>
          <Pathway d="M185 405L185 490M405 330L405 420M640 420L640 490M825 340L825 410M980 440L980 500M1050 285L1050 360" width={9}/>
          <g opacity=".92">
            <ellipse cx="185" cy="437" rx="76" ry="29" fill="#729b68" opacity=".4"/>
            <ellipse cx="405" cy="360" rx="72" ry="26" fill="#729b68" opacity=".38"/>
            <ellipse cx="640" cy="455" rx="82" ry="29" fill="#729b68" opacity=".4"/>
            <ellipse cx="825" cy="370" rx="70" ry="25" fill="#729b68" opacity=".38"/>
            <ellipse cx="980" cy="480" rx="75" ry="27" fill="#729b68" opacity=".4"/>
            <Tree x={70} y={380} scale={1.25} tone={0}/><Tree x={300} y={450} scale={.95} tone={1}/><Tree x={535} y={390} scale={1.05} tone={2}/><Tree x={735} y={465} scale={1.1} tone={0}/><Tree x={915} y={290} scale={1.0} tone={1}/><Tree x={1150} y={430} scale={1.2} tone={2}/>
            <Tree x={255} y={300} scale={.75} tone={2}/><Tree x={570} y={250} scale={.8} tone={1}/><Tree x={1110} y={315} scale={.8} tone={0}/>
          </g>
          <g filter="url(#district-shadow)">
            {buildings.map((b, i) => <House key={b.building} b={b} name={names[i]} selected={selectedBuilding === b.role} onSelect={() => onSelect(b.role)} {...positions[i]} state={state.buildings[i]}/>)}
          </g>
          <g transform="translate(28 26)" filter="url(#soft-shadow)">
            <rect width="340" height="68" rx="15" fill="#fffdf8" fillOpacity=".94" stroke="#d9dfd4"/>
            <text x="17" y="27" fontSize="14" fontWeight="700" fill="#344d3c">A Swiss residential neighborhood</text>
            <text x="17" y="49" fontSize="11.5" fill="#66766a">Six modeled building archetypes · illustrative composite</text>
          </g>
          <g transform="translate(955 26)" filter="url(#soft-shadow)">
            <rect width="215" height="68" rx="15" fill="#fffdf8" fillOpacity=".94" stroke="#d9dfd4"/>
            <text x="15" y="25" fontSize="11" fontWeight="700" fill="#53665a">LIVE CONDITIONS</text>
            <text x="15" y="47" fontSize="13" fontWeight="600" fill="#344d3c">{state.weather}  ·  {state.tariff}</text>
          </g>
        </svg>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#d8dfd3] bg-[#f8faf6] px-4 py-3 text-xs text-[#647366]">
        <span>Illustrative architecture and layout · no shared grid, heat network, or energy exchange is modeled</span>
        <span className="font-medium text-[#435b49]">Select a building to inspect its heating system</span>
      </div>
    </div>
  );
}
