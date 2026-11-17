"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useBundle } from "@/lib/bundle";
import { SearchButton } from "./search";
import { cn } from "@/lib/utils";

export const PAGES = [
  { href: "/", label: "Overview" },
  { href: "/inputs/", label: "Inputs" },
  { href: "/model/", label: "Model" },
  { href: "/results/", label: "Results" },
  { href: "/audit/", label: "Audit" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const { meta, error } = useBundle();
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5">
        <Link href="/" className="font-semibold tracking-tight">SuisseCL <span className="font-normal text-muted-foreground">Phase A</span></Link>
        <nav className="flex gap-1">
          {PAGES.map((p) => {
            const active = p.href === "/" ? pathname === "/" : pathname.startsWith(p.href);
            return (
              <Link key={p.href} href={p.href} className={cn("rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-muted", active && "bg-muted font-medium")}>
                {p.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <SearchButton />
          {error && <Badge2 bad>bundle error: {error}</Badge2>}
          {meta && (
            <>
              <Badge2 title={`bundle built ${meta.built_utc} from commit ${meta.git.commit_full}`}>build {meta.git.commit}</Badge2>
              {meta.git.dirty ? <Badge2 bad title={meta.git.dirty_paths.join("\n")}><AlertTriangle className="size-3" /> uncommitted changes</Badge2> : <Badge2 ok><CheckCircle2 className="size-3" /> clean tree</Badge2>}
              {meta.manifest.verified ? <Badge2 ok title="every file in data/canonical/MANIFEST.sha256 matched"><CheckCircle2 className="size-3" /> manifest {meta.manifest.files_listed}</Badge2> : <Badge2 bad title={JSON.stringify(meta.manifest.failures)}><AlertTriangle className="size-3" /> manifest fails</Badge2>}
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function Badge2({ children, ok, bad, title }: { children: React.ReactNode; ok?: boolean; bad?: boolean; title?: string }) {
  return (
    <span title={title} className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs", ok && "border-emerald-300 bg-emerald-50 text-emerald-800", bad && "border-red-300 bg-red-50 font-medium text-red-700")}>
      {children}
    </span>
  );
}
