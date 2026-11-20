"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { SearchButton } from "./search";
import { DEEP_DIVE } from "@/lib/nav";
import { cn } from "@/lib/utils";

const LINKS = [{ href: "/", label: "Story" }, { href: "/explorer/", label: "Explorer" }, { href: "/methods/", label: "Data & methods" }];
const linkCls = (on: boolean) => cn("rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-muted", on && "bg-muted font-medium");

function DeepDiveMenu() {
  const pathname = usePathname(), [open, setOpen] = useState(false), box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const away = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", away); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, []);
  const active = DEEP_DIVE.some((g) => g.items.some((p) => pathname.startsWith(p.href) && !LINKS.some((l) => l.href !== "/" && l.href === p.href)));
  return (
    <div ref={box} className="relative">
      <button type="button" aria-expanded={open} onClick={() => setOpen((v) => !v)} className={cn("flex items-center gap-1", linkCls(active || open))}>Deep dive<ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} /></button>
      {open && (
        <div role="menu" className="absolute left-0 top-full z-50 mt-1 max-h-[80vh] w-72 overflow-y-auto rounded-xl border bg-popover p-1 shadow-lg">
          {DEEP_DIVE.map((g) => (
            <div key={g.group}>
              <div className="px-3 pb-0.5 pt-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{g.group}</div>
              {g.items.map((p) => (
                <Link key={p.href} href={p.href} role="menuitem" onClick={() => setOpen(false)} className={cn("block rounded-lg px-3 py-1.5 hover:bg-muted", pathname === p.href && "bg-muted")}>
                  <div className="text-sm font-medium">{p.label}</div><div className="text-xs text-muted-foreground">{p.hint}</div>
                </Link>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5">
        <Link href="/" className="mr-2 font-semibold tracking-tight">SuisseCL</Link>
        <nav className="flex flex-wrap items-center gap-1">
          {LINKS.map((l) => <Link key={l.href} href={l.href} className={linkCls(l.href === "/" ? pathname === "/" : pathname.startsWith(l.href))}>{l.label}</Link>)}
          <DeepDiveMenu />
        </nav>
        <div className="ml-auto"><SearchButton /></div>
      </div>
    </header>
  );
}
