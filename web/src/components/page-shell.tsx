"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useBundle } from "@/lib/bundle";
import { DEEP_DIVE } from "@/lib/nav";

const CLASSES = ["measured", "derived", "modeled", "synthetic", "assumption"];

/** Page title block shared by the deep-dive pages: eyebrow (its menu group), title, lede and the provenance legend. */
export function PageHeader({ title, page }: { title: string; page: string }) {
  const { story, colours } = useBundle();
  const pathname = usePathname();
  const group = DEEP_DIVE.find((g) => g.items.some((i) => i.href === pathname || i.href === `${pathname}/`))?.group;
  return (
    <header className="mb-8 max-w-3xl space-y-2">
      {group && <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Deep dive · {group}</p>}
      <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
      <p className="text-base leading-relaxed text-zinc-600">{story?.pages[page] ?? " "}</p>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-1 text-[11px] text-zinc-500">
        <span>Every value carries its provenance:</span>
        {CLASSES.map((c) => (
          <span key={c} className="inline-flex items-center gap-1"><span aria-hidden className="size-1.5 rounded-full" style={{ background: colours[c] ?? "#a1a1aa" }} />{c}</span>
        ))}
        <span>· missing values are never shown as zero</span>
      </p>
    </header>
  );
}

/** Says which project phase a page shows, and where the other phases live. */
export function PhaseNote({ children, links }: { children: React.ReactNode; links: { href: string; label: string }[] }) {
  return (
    <div className="-mt-4 mb-6 flex max-w-4xl flex-wrap items-baseline gap-x-3 gap-y-1 rounded-r-lg border-l-2 border-zinc-400 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
      <span>{children}</span>
      {links.map((l) => <Link key={l.href} href={l.href} className="text-blue-700 hover:underline">{l.label} →</Link>)}
    </div>
  );
}
