"use client";

import type { BuildingInfo } from "@/lib/contract";

type BuildingStep = {
  net: number | null; hpSh: number | null; hpHw: number | null; household: number | null;
  shDemand: number | null; hwDemand: number | null; hpShDirect: number | null; hpShToTank: number | null;
  shTankToDemand: number | null; shTankLoss: number | null; shSoc: number | null;
  hpHwDirect: number | null; hpHwToTank: number | null; hwTankToDemand: number | null; hwTankLoss: number | null; hwSoc: number | null;
};
const fmt = (v: number | null, d = 2) => v == null || !Number.isFinite(v) ? "—" : v.toFixed(d);
const attr = (b: BuildingInfo, key: string) => b.attributes[key]?.available ? b.attributes[key].value : null;

function Tank({ x, y, title, soc, present }: { x: number; y: number; title: string; soc: number | null; present: boolean }) {
  if (!present) return <g transform={`translate(${x} ${y})`}><rect width="84" height="108" rx="13" fill="#fafafa" stroke="#d4d4d8" strokeDasharray="5 4"/><text x="42" y="48" textAnchor="middle" fontSize="11" fill="#71717a">Not</text><text x="42" y="63" textAnchor="middle" fontSize="11" fill="#71717a">present</text><text x="42" y="88" textAnchor="middle" fontSize="9" fill="#71717a">{title}</text></g>;
  const fill = soc == null ? 0 : Math.max(0, Math.min(1, soc));
  return <g transform={`translate(${x} ${y})`}>
    <rect width="84" height="108" rx="13" fill="#f4f4f5" stroke="#a1a1aa" strokeWidth="2"/>
    {soc != null && <rect x="8" y={96 - 82 * fill} width="68" height={82 * fill} rx="7" fill="url(#tank-fill)"/>}
    <path d="M8 22H76" stroke="#ffffff" strokeWidth="2"/>
    <text x="42" y="126" textAnchor="middle" fontSize="11" fontWeight="700" fill="#27272a">{title}</text>
    <text x="42" y="143" textAnchor="middle" fontSize="10" fill="#52525b">{soc == null ? "—" : `${fmt(fill * 100, 0)}% full`}</text>
  </g>;
}

export function BuildingCutaway({ building, state, stepSeconds }: { building: BuildingInfo; state: BuildingStep; stepSeconds: number }) {
  const tankSh = building.components.tank_sh.present;
  const tankHw = building.components.tank_hw.present;
  const hpSh = building.components.hp_sh.present;
  const hpHw = building.components.hp_hw.present;
  const electricWaterHeater = attr(building, "electric_water_heater") === true;   // boolean contract attribute (unavailable counts as not shown)
  const capacity = building.components.tank_sh.attributes.capacity_kwh_th?.value;
  const householdProvenance = building.attributes.household_electricity_source?.provenance === "synthetic" ? "Synthetic composite" : "Measured";
  const hwCapacity = building.components.tank_hw.attributes.capacity_kwh_th?.value;
  const area = attr(building, "floor_area_m2");
  const units = attr(building, "housing_units");
  const shFill = state.shSoc == null ? null : Math.max(0, Math.min(1, state.shSoc));
  const hwFill = state.hwSoc == null ? null : Math.max(0, Math.min(1, state.hwSoc));
  const flowWidth = (value: number | null) => value == null || value <= 0.0001 ? 0 : 2 + Math.min(5, Math.sqrt(value) * 1.8);

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-[#fafafa]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#e4e4e7] px-3 py-2">
        <div><p className="text-sm font-semibold text-[#18181b]">Inside the building</p><p className="text-xs text-[#71717a]">Conceptual system cutaway · equipment placement is illustrative</p></div>
      </div>
      <div className="grid gap-3 p-3 lg:grid-cols-[minmax(0,1fr)_240px]">
        <svg viewBox="0 0 760 390" role="img" aria-label={`Conceptual heating system for ${building.display_name}`} className="block h-auto w-full rounded-lg bg-[#f4f4f5]">
          <defs>
            <linearGradient id="cut-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffffff"/><stop offset="1" stopColor="#f4f4f5"/></linearGradient>
            <linearGradient id="tank-fill" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor="#fb923c"/><stop offset="1" stopColor="#ea580c"/></linearGradient>
            <marker id="heat-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#ea580c"/></marker>
            <marker id="base-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#fb923c"/></marker>
          </defs>
          <path d="M28 300H730" stroke="#a1a1aa" strokeWidth="3"/>
          {building.type === "SFH" ? (
            <><path d="M48 128L222 42L396 128V300H48Z" fill="url(#cut-wall)" stroke="#a1a1aa" strokeWidth="3"/><path d="M36 130L222 34L408 130" fill="none" stroke="#71717a" strokeWidth="16" strokeLinejoin="round"/><path d="M74 160H370M74 230H370" stroke="#d4d4d8" strokeWidth="3"/><rect x="94" y="173" width="62" height="43" fill="#e4e4e7" stroke="#a1a1aa"/><rect x="286" y="173" width="62" height="43" fill="#e4e4e7" stroke="#a1a1aa"/><text x="222" y="260" textAnchor="middle" fontSize="12" fill="#52525b">Space-heating demand</text><text x="222" y="282" textAnchor="middle" fontSize="10" fill="#71717a">Building heat load</text></>
          ) : (
            <><path d="M48 98L222 48L396 98V300H48Z" fill="url(#cut-wall)" stroke="#a1a1aa" strokeWidth="3"/><path d="M48 166H396M48 232H396" stroke="#d4d4d8" strokeWidth="4"/>{[0,1,2].map((floor)=>[0,1,2,3].map((col)=><rect key={`${floor}-${col}`} x={72+col*78} y={113+floor*45} width="44" height="28" rx="2" fill="#e4e4e7" stroke="#a1a1aa"/>))}<text x="222" y="278" textAnchor="middle" fontSize="12" fill="#52525b">Space-heating demand</text></>
          )}
          <g transform="translate(430 80)">
            <rect width="100" height="78" rx="10" fill="#f4f4f5" stroke="#a1a1aa" strokeWidth="2"/>
            <circle cx="50" cy="29" r="18" fill="#ffffff" stroke="#a1a1aa" strokeWidth="2"/>
            <path d="M50 13L55 28L50 29L40 41" fill="none" stroke="#71717a" strokeWidth="2.5"/>
            <text x="50" y="60" textAnchor="middle" fontSize="10" fontWeight="700" fill="#27272a">HP · space heat</text>
            <text x="50" y="71" textAnchor="middle" fontSize="8.5" fill="#52525b">{hpSh ? "Modeled device" : "Not present"}</text>
          </g>
          <g transform="translate(430 205)">
            <rect width="100" height="78" rx="10" fill="#f4f4f5" stroke="#a1a1aa" strokeWidth="2"/>
            <circle cx="50" cy="29" r="18" fill="#ffffff" stroke="#a1a1aa" strokeWidth="2"/>
            <path d="M50 13L55 28L50 29L40 41" fill="none" stroke="#71717a" strokeWidth="2.5"/>
            <text x="50" y="60" textAnchor="middle" fontSize="10" fontWeight="700" fill="#27272a">HP · base load</text>
            <text x="50" y="71" textAnchor="middle" fontSize="8.5" fill="#52525b">{hpHw ? "Modeled device" : "Not present"}</text>
          </g>
          <Tank x={555} y={85} title="Heating tank" soc={shFill} present={tankSh}/>
          <Tank x={655} y={85} title="Hot-water / base-load" soc={hwFill} present={tankHw}/>
          <g fill="none" strokeLinecap="round" strokeLinejoin="round">
            {flowWidth(state.hpShToTank) > 0 && <path d="M530 119H555" stroke="#ea580c" strokeWidth={flowWidth(state.hpShToTank)} strokeDasharray="7 5" markerEnd="url(#heat-arrow)"/>}
            {flowWidth(state.hpShDirect) > 0 && <path d="M480 158V300H400" stroke="#ea580c" strokeWidth={flowWidth(state.hpShDirect)} strokeDasharray="6 5" markerEnd="url(#heat-arrow)"/>}
            {flowWidth(state.shTankToDemand) > 0 && <path d="M597 193V330H400" stroke="#ea580c" strokeWidth={flowWidth(state.shTankToDemand)} strokeDasharray="6 5" markerEnd="url(#heat-arrow)"/>}
            {tankHw && flowWidth(state.hpHwToTank) > 0 && <path d="M530 244H642V180H655" stroke="#fb923c" strokeWidth={flowWidth(state.hpHwToTank)} strokeDasharray="6 5" markerEnd="url(#base-arrow)"/>}
            {flowWidth(state.hpHwDirect) > 0 && <path d="M480 283V355H400" stroke="#fb923c" strokeWidth={flowWidth(state.hpHwDirect)} strokeDasharray="6 5" markerEnd="url(#base-arrow)"/>}
            {tankHw && flowWidth(state.hwTankToDemand) > 0 && <path d="M697 193V355H400" stroke="#fb923c" strokeWidth={flowWidth(state.hwTankToDemand)} strokeDasharray="6 5" markerEnd="url(#base-arrow)"/>}
          </g>
          <text x="480" y="70" textAnchor="middle" fontSize="9" fill="#52525b">Electricity in</text>
          <text x="480" y="196" textAnchor="middle" fontSize="9" fill="#c2410c">Heat</text>
          <text x="480" y="322" textAnchor="middle" fontSize="9" fill="#c2410c">Direct + stored heat</text>
          {electricWaterHeater && <g transform="translate(50 8)"><rect width="340" height="34" rx="8" fill="#fffbeb" stroke="#fcd34d"/><text x="12" y="14" fontSize="10" fontWeight="700" fill="#92400e">Separate electric water heater</text><text x="12" y="26" fontSize="9" fill="#92400e">Its electricity is included in household load, not HP electricity</text></g>}
          {!electricWaterHeater && <text x="50" y="25" fontSize="10" fill="#71717a">Base-load demand may include uses other than hot water</text>}
          <text x="445" y="375" fontSize="10" fill="#71717a">Line width scales with modeled thermal energy this timestep (kWh_th/step)</text>
        </svg>
        <div className="space-y-2">
          <div className="rounded-lg bg-white/80 p-3">
            <p className="text-xs font-semibold text-[#27272a]">Electricity this timestep</p>
            <p className="mt-1 text-xs text-[#71717a]">Space-heating heat pump</p><p className="font-semibold">{fmt(state.hpSh)} kWh_el</p>
            <p className="mt-1 text-xs text-[#71717a]">Hot-water / base-load heat pump</p><p className="font-semibold">{fmt(state.hpHw)} kWh_el</p>
            <p className="mt-1 text-xs text-[#71717a]">Household electricity · {householdProvenance.toLowerCase()}</p><p className="font-semibold">{fmt(state.household)} kWh_el</p>
          </div>
          <div className="rounded-lg bg-white/80 p-3">
            <p className="text-xs font-semibold text-[#27272a]">Thermal flows this timestep</p>
            <div className="mt-2 grid grid-cols-[1fr_auto] gap-x-2 gap-y-1 text-xs">
              <span className="text-[#71717a]">HP → space-heating demand</span><b>{fmt(state.hpShDirect)} kWh_th</b>
              <span className="text-[#71717a]">HP → heating tank</span><b>{fmt(state.hpShToTank)} kWh_th</b>
              <span className="text-[#71717a]">Heating tank → demand</span><b>{fmt(state.shTankToDemand)} kWh_th</b>
              <span className="text-[#71717a]">Heating tank losses</span><b>{fmt(state.shTankLoss)} kWh_th</b>
              <span className="text-[#71717a]">HP → base-load demand</span><b>{fmt(state.hpHwDirect)} kWh_th</b>
              {tankHw && <><span className="text-[#71717a]">HP → base-load tank</span><b>{fmt(state.hpHwToTank)} kWh_th</b><span className="text-[#71717a]">Tank → base-load demand</span><b>{fmt(state.hwTankToDemand)} kWh_th</b><span className="text-[#71717a]">Base-load tank losses</span><b>{fmt(state.hwTankLoss)} kWh_th</b></>}
            </div>
            <p className="mt-2 border-t pt-2 text-xs text-[#71717a]">Demand: {fmt(state.shDemand)} kWh_th space heating · {fmt(state.hwDemand)} kWh_th hot water and other base load</p>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-white p-3"><p className="text-xs font-semibold text-zinc-800">Assumed storage parameters</p><p className="mt-1 text-xs text-zinc-600">Heating tank: {capacity == null ? "not available" : `${fmt(Number(capacity),1)} kWh_th`}. Base-load tank: {hwCapacity == null ? "not present / unavailable" : `${fmt(Number(hwCapacity),1)} kWh_th`}. Efficiency and standby losses are assumed, not measured.</p></div>
          <div className="rounded-lg bg-white/80 p-3 text-xs text-[#71717a]">{area != null ? `${area} m²` : units != null ? `${units} housing units` : "Building metadata"} · timestep {stepSeconds/3600} h</div>
        </div>
      </div>
      <div className="border-t border-[#e4e4e7] bg-white/70 px-3 py-2 text-[10px] text-[#71717a]">Thermal storage is synthetic. Indoor temperature, comfort, room layouts, radiators, and physical equipment placement are not modeled. A missing tank is shown as “Not present”, never as 0%.</div>
    </div>
  );
}
