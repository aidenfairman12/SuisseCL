"use client";
import { useState } from "react";
import { useComponents } from "@/lib/contract";
import type { SystemComponent } from "@/lib/contract";
const pos: Record<string,{x:number;y:number}> = {
 weather:{x:24,y:28},tariff:{x:24,y:132},carbon:{x:24,y:236},controller:{x:270,y:28},grid:{x:270,y:236},
 hp_sh:{x:520,y:88},hp_hw:{x:520,y:218},household:{x:520,y:360},tank_sh:{x:770,y:88},tank_hw:{x:770,y:218},
 demand_sh:{x:1010,y:88},demand_hw:{x:1010,y:218},district_outcomes:{x:1010,y:360}
};
const W=174,H=62;
const colors={electricity:"#2563eb",heat:"#ea580c",signal:"#a1a1aa",control:"#7c3aed"};
const prov=(v:SystemComponent["provenance"])=>typeof v==="string"?v.replaceAll("_"," "):"measured / synthetic by building type";
export function SystemFlowDiagram(){
 const file=useComponents("full"); const [selected,setSelected]=useState("grid");
 const components=file.data?.components??[]; const flows=file.data?.flows??[];
 const byId=new Map(components.map(c=>[c.id,c])); const active=byId.get(selected);
 if(!file.data)return <div className="rounded-xl border p-6 text-sm text-muted-foreground">Loading system contract…</div>;
 return <div className="space-y-4">
  <div className="overflow-x-auto rounded-2xl border bg-card p-3">
   <svg viewBox="0 0 1210 470" className="min-w-[900px] w-full" role="group" aria-label="Phase A energy and information flows from the simulation contract">
    <defs>{Object.entries(colors).map(([k,v])=><marker key={k} id={`arrow-${k}`} markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill={v}/></marker>)}</defs>
    <g fill="none" strokeWidth="2">{flows.filter(f=>pos[f.from]&&pos[f.to]).map(f=>{
      const a=pos[f.from],b=pos[f.to],sx=a.x+W,sy=a.y+H/2,ex=b.x,ey=b.y+H/2,bend=Math.max(32,(ex-sx)*.42);
      return <path key={f.id} d={`M ${sx} ${sy} C ${sx+bend} ${sy}, ${ex-bend} ${ey}, ${ex} ${ey}`} stroke={colors[f.carrier]} strokeDasharray={f.carrier==="signal"||f.carrier==="control"?"5 5":undefined} markerEnd={`url(#arrow-${f.carrier})`}><title>{f.description}</title></path>;
    })}</g>
    {components.filter(c=>pos[c.id]).map(c=>{const p=pos[c.id],on=selected===c.id;return <g key={c.id} transform={`translate(${p.x} ${p.y})`} onClick={()=>setSelected(c.id)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" ")setSelected(c.id)}} tabIndex={0} role="button" aria-pressed={on} className="cursor-pointer">
      <rect width={W} height={H} rx="10" fill={on?"#eff6ff":"#fff"} stroke={on?"#18181b":"#d4d4d8"} strokeWidth={on?3:1.5}/>
      <text x="12" y="24" fontSize="13" fontWeight="700" fill="#18181b">{c.label}</text>
      <text x="12" y="43" fontSize="10.5" fill="#71717a">{c.status==="modeled"?"Modeled":"Not modeled"} · Phase {c.phase_available}</text>
      <circle cx={W-14} cy="13" r="4" fill={c.status==="modeled"?"#0d9488":"#d4d4d8"}/>
    </g>})}
   </svg>
   <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 border-t pt-3 text-xs text-muted-foreground">
    <span><i className="mr-1 inline-block h-0.5 w-4 bg-[#2563eb]"/>Electricity</span><span><i className="mr-1 inline-block h-0.5 w-4 bg-[#ea580c]"/>Thermal energy</span><span><i className="mr-1 inline-block h-0.5 w-4 border-t border-dashed border-[#a1a1aa]"/>Input signal</span><span><i className="mr-1 inline-block h-0.5 w-4 border-t border-dashed border-[#7c3aed]"/>Control signal</span><span>Click a component to inspect its contract details.</span>
   </div>
  </div>
  {active&&<section className="rounded-xl border bg-card p-4" aria-live="polite">
   <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">{active.label}</h3><div className="flex items-center gap-2"><span className="rounded-full border px-2 py-0.5 text-[10px] capitalize text-muted-foreground">{prov(active.provenance)}</span><span className="text-xs text-muted-foreground">Phase {active.phase_available} · {active.status.replaceAll("_"," ")}</span></div></div>
   <p className="mt-2 max-w-4xl text-sm text-muted-foreground">{active.description}</p><p className="mt-2 text-xs text-muted-foreground">Present in: {active.present_in}{active.source_ids.length?` · Sources: ${active.source_ids.join(", ")}`:""}</p>
   {active.variables.length>0&&<p className="mt-1 text-xs text-muted-foreground">Contract variables: {active.variables.join(", ")}</p>}
  </section>}
  <section className="space-y-2"><div><h3 className="font-semibold">Planned beyond Phase A</h3><p className="text-sm text-muted-foreground">Not modeled in the Phase A simulation shown here. Phase B examines some of them as labelled scenarios (see the Scenarios and Controllers pages) and Phase C examines future climates and cooling (see the Climate, Cooling, Explorer and Houses pages).</p></div><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
   {components.filter(c=>c.status==="not_modeled").map(c=><button key={c.id} onClick={()=>setSelected(c.id)} className={`rounded-xl border p-3 text-left hover:bg-muted/50 ${selected===c.id?"border-foreground/50 bg-muted/40":"bg-card"}`}><div className="flex items-center justify-between gap-2"><span className="text-sm font-medium">{c.label}</span><span className="text-[10px] text-muted-foreground">Phase {c.phase_available}</span></div><p className="mt-1 text-xs text-muted-foreground">{c.description}</p></button>)}
  </div></section>
 </div>;
}