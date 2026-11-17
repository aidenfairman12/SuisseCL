"use client";
import { useState } from "react";
import { useComparisonsYear,useManifest } from "@/lib/contract";
import type { Comparison } from "@/lib/contract";
const DEFAULT="ALG-003_basic_rbc";
const specs=[{id:"import_kwh_el",label:"Grid electricity",unit:"kWh_el"},{id:"peak_kw_el",label:"Peak grid demand",unit:"kW_el"},{id:"mean_daily_peak_kw_el",label:"Mean daily peak",unit:"kW_el"},{id:"cost_chf",label:"Electricity cost",unit:"CHF"},{id:"high_tariff_import_share",label:"High-tariff import share",unit:"%"},{id:"hp_kwh_el",label:"Heat-pump electricity",unit:"kWh_el"}] as const;
const fmt=(v:number|null|undefined,d=1)=>v==null||!Number.isFinite(v)?"—":v.toLocaleString("en-CH",{maximumFractionDigits:d,minimumFractionDigits:d});
const val=(c:Comparison|undefined,k:string)=>c?.metrics[k]?.value??null;
const delta=(c:Comparison|undefined,k:string)=>c?.metrics[k]?.delta_pct??null;
function Mechanism({label,value,unit,detail}:{label:string;value:number|null|undefined;unit:string;detail?:string}){return <div className="rounded-xl border bg-card p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-lg font-semibold tabular-nums">{fmt(value,2)} <span className="text-xs font-normal text-muted-foreground">{unit}</span></p>{detail&&<p className="mt-1 text-xs text-muted-foreground">{detail}</p>}</div>}
export function ResultsPage(){
 const mf=useManifest("full"),cf=useComparisonsYear("full"),m=mf.data,c=cf.data;const [controller,setController]=useState(DEFAULT);
 if(!m||!c)return <p className="text-sm text-muted-foreground">Loading annual comparison contract…</p>;
 const refId=c.reference_controller,refComparison=Object.values(c.comparisons)[0],selected=c.comparisons[controller],mechanisms=selected?.mechanisms;
 const name=(id:string)=>m.controllers.find(x=>x.id===id)?.display_name??id;
 const refValue=(key:string)=>refComparison?.metrics[key]?.reference??null;
 return <div className="space-y-8">
  <header className="max-w-4xl space-y-2"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Annual evaluation · {m.year}</p><h1 className="text-3xl font-semibold tracking-tight">What changes when the controller acts?</h1><p className="text-sm leading-relaxed text-muted-foreground">Compare each controller against the zero-action reference, then inspect the mechanism behind the selected result. Annual energy is reported in kWh; peak demand is mean power in kW. Carbon results are relative comparisons only.</p></header>
  <section className="space-y-3"><div><h2 className="text-xl font-semibold">Controller comparison</h2><p className="text-sm text-muted-foreground">Annual values from the comparison contract. Select a row to inspect its mechanism below.</p></div>
   <div className="overflow-x-auto rounded-xl border"><table className="w-full min-w-[820px] text-sm"><thead className="bg-muted/40 text-left text-xs"><tr><th className="p-3">Controller</th>{specs.map(s=><th key={s.id} className="p-3 text-right">{s.label}<span className="block font-normal text-muted-foreground">{s.unit}</span></th>)}</tr></thead><tbody>
    <tr className="border-t bg-muted/30"><td className="p-3 font-medium">{name(refId)} <span className="text-xs text-muted-foreground">· reference</span></td>{specs.map(s=>{const v=refValue(s.id);return <td key={s.id} className="p-3 text-right tabular-nums">{s.id==="high_tariff_import_share"?(v==null?"—":fmt(v*100)+"%"):fmt(v)}</td>})}</tr>
    {m.controllers.filter(x=>x.id!==refId).map(x=>{const comp=c.comparisons[x.id],active=controller===x.id;return <tr key={x.id} onClick={()=>setController(x.id)} className={`cursor-pointer border-t transition-colors hover:bg-muted/30 ${active?"bg-sky-50":""}`}><td className="p-3 font-medium">{x.display_name}{active&&<span className="ml-2 text-xs text-sky-700">selected</span>}</td>{specs.map(s=>{const v=val(comp,s.id),d=delta(comp,s.id);return <td key={s.id} className="p-3 text-right tabular-nums"><div>{s.id==="high_tariff_import_share"?(v==null?"—":fmt(v*100)+"%"):fmt(v)}</div><div className="text-xs text-muted-foreground">{d==null?"—":`${d>0?"+":""}${fmt(d,2)}%`}</div></td>})}</tr>})}
   </tbody></table></div><p className="text-xs text-muted-foreground">Percent changes are relative to {name(refId)}. High-tariff share is the fraction of annual grid electricity imported during high-tariff hours.</p>
  </section>
  <section className="space-y-3"><div><h2 className="text-xl font-semibold">Why did {name(controller)} change the outcome?</h2><p className="text-sm text-muted-foreground">The decomposition separates shifted imports, additional electricity use, storage losses and cost timing. Values are differences against the reference.</p></div>
   {!mechanisms?<p className="rounded-xl border p-4 text-sm text-muted-foreground">No mechanism decomposition is available for this controller.</p>:<>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
     <Mechanism label="Imports moved out of high-tariff hours" value={mechanisms.import_moved_out_of_high_tariff_kwh_el} unit="kWh_el" detail="A timing shift, not a reduction in annual electricity."/>
     <Mechanism label="Additional heat-pump electricity" value={mechanisms.extra_hp_electricity_kwh_el} unit="kWh_el"/>
     <Mechanism label="Extra thermal storage losses" value={mechanisms.extra_tank_loss_kwh_th} unit="kWh_th" detail="Losses from synthetic tanks with assumed parameters."/>
     <Mechanism label="Heat charged into tanks" value={mechanisms.tank_heat_in_kwh_th} unit="kWh_th"/>
     <Mechanism label="Heat delivered from tanks" value={mechanisms.tank_heat_out_kwh_th} unit="kWh_th"/>
     <Mechanism label="Stored-energy change" value={mechanisms.stored_heat_change_kwh_th} unit="kWh_th" detail="Difference in stored heat at the end of the run."/>
     <Mechanism label="Cost effect from tariff timing" value={mechanisms.cost_from_tariff_timing_chf} unit="CHF" detail="Can be negative when imports shift to cheaper hours."/>
     <Mechanism label="Cost effect from extra electricity" value={mechanisms.cost_from_extra_electricity_chf} unit="CHF"/>
     <Mechanism label="Relative carbon-index change" value={mechanisms.relative_carbon_change_pct} unit="%" detail="Relative model comparison only; no absolute emissions or tonnes are available."/>
    </div>
    <div className="rounded-xl border bg-muted/20 p-4 text-sm"><p className="font-semibold">Reading the result</p><p className="mt-1 text-muted-foreground">A controller can move electricity use away from high-tariff periods and reduce peak power while still increasing total annual electricity. Thermal storage introduces losses, and the heat pump may use more electricity to replace that lost heat. The cost result is the balance between tariff timing and the cost of extra electricity.</p><p className="mt-2 text-xs text-muted-foreground">Peak step: reference {mechanisms.peak_step_reference.toLocaleString()} · selected {mechanisms.peak_step.toLocaleString()}. Carbon-index decomposition is relative only and must not be interpreted as absolute CO₂ emissions.</p></div>
   </>}
  </section>
  <p className="text-xs text-muted-foreground">Annual simulation outputs and mechanism decompositions are modeled results. Storage size, efficiency and standby losses are assumed parameters. This is not a measured field trial.</p>
 </div>;
}