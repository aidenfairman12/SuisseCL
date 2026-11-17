"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { SearchButton } from "./search";
import { cn } from "@/lib/utils";

export const EXPLORE = [
  { href: "/inputs/", label: "Inputs", hint: "weather, price, CO₂, building use" },
  { href: "/model/", label: "Model", hint: "heat pumps, tanks, scoring" },
  { href: "/results/", label: "Results", hint: "every rule, hour by hour" },
  { href: "/audit/", label: "Sources & audit", hint: "registry, checks, open issues" },
  { href: "/glossary/", label: "Glossary", hint: "what the terms mean" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const away = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, []);
  const onExplore = EXPLORE.some((p) => pathname.startsWith(p.href));
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
        <Link href="/" className="mr-2 font-semibold tracking-tight">SuisseCL</Link>
        <nav className="flex items-center gap-1">
          <Link href="/" className={cn("rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-muted", pathname === "/" && "bg-muted font-medium")}>Story</Link>
          <div ref={box} className="relative">
            <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className={cn("flex items-center gap-1 rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-muted", (onExplore || open) && "bg-muted font-medium")}>
              Explore <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
            </button>
            {open && (
              <div role="menu" className="absolute left-0 top-full z-50 mt-1 w-64 rounded-xl border bg-popover p-1 shadow-lg">
                {EXPLORE.map((p) => (
                  <Link key={p.href} href={p.href} role="menuitem" onClick={() => setOpen(false)} className={cn("block rounded-lg px-3 py-2 hover:bg-muted", pathname.startsWith(p.href) && "bg-muted")}>
                    <div className="text-sm font-medium">{p.label}</div>
                    <div className="text-xs text-muted-foreground">{p.hint}</div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </nav>
        <div className="ml-auto"><SearchButton /></div>
      </div>
    </header>
  );
}
