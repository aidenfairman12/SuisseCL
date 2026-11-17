"use client";
import { useBundle } from "@/lib/bundle";
export function PageHeader({title,page}:{title:string;page:string}){
 const {story}=useBundle();
 return <div className="mb-6 max-w-3xl"><h1 className="text-2xl font-semibold tracking-tight">{title}</h1><p className="mt-1 text-muted-foreground">{story?.pages[page]??" "}</p><p className="mt-2 text-[11px] text-muted-foreground">Provenance labels distinguish measured, derived, modeled, synthetic and assumed-parameter values. Unavailable values are not treated as zero.</p></div>;
}