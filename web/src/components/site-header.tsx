"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { SearchButton } from "./search";
import { cn } from "@/lib/utils";
const EXPLORE=[{href:"/",label:"Overview",hint:"system scope and energy flows"},{href:"/district/",label:"District",hint:"inspect buildings and timestep flows"},{href:"/results/",label:"Results",hint:"annual controller comparison"}];
const INSPECT=[{href:"/inputs/",label:"Inputs",hint:"weather, price, carbon and demand"},{href:"/model/",label:"Model",hint:"devices, assumptions and control"},{href:"/audit/",label:"Audit",hint:"registry, validation and open issues"},{href:"/glossary/",label:"Glossary",hint:"terms and definitions"}];
function NavMenu({label,items}:{label:string;items:typeof EXPLORE}){
 const pathname=usePathname(),[open,setOpen]=useState(false),box=useRef<HTMLDivElement>(null);
 useEffect(()=>{const away=(e:MouseEvent)=>{if(box.current&&!box.current.contains(e.target as Node))setOpen(false)};const esc=(e:KeyboardEvent)=>{if(e.key==="Escape")setOpen(false)};document.addEventListener("mousedown",away);document.addEventListener("keydown",esc);return()=>{document.removeEventListener("mousedown",away);document.removeEventListener("keydown",esc)}},[]);
 const active=items.some(p=>p.href==="/"?pathname==="/":pathname.startsWith(p.href));
 return <div ref={box} className="relative"><button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)} className={cn("flex items-center gap-1 rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-muted",(active||open)&&"bg-muted font-medium")}>{label}<ChevronDown className={cn("size-3.5 transition-transform",open&&"rotate-180")}/></button>
 {open&&<div role="menu" className="absolute left-0 top-full z-50 mt-1 w-64 rounded-xl border bg-popover p-1 shadow-lg">{items.map(p=><Link key={p.href} href={p.href} role="menuitem" onClick={()=>setOpen(false)} className={cn("block rounded-lg px-3 py-2 hover:bg-muted",pathname===p.href&&"bg-muted")}><div className="text-sm font-medium">{p.label}</div><div className="text-xs text-muted-foreground">{p.hint}</div></Link>)}</div>}</div>;
}
export function SiteHeader(){return <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur"><div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5"><Link href="/" className="mr-2 font-semibold tracking-tight">SuisseCL</Link><nav className="flex items-center gap-1"><NavMenu label="Explore" items={EXPLORE}/><NavMenu label="Inspect" items={INSPECT}/></nav><div className="ml-auto"><SearchButton/></div></div></header>}
