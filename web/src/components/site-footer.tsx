"use client";
import { useMemo } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { NodeLink } from "@/components/audit/bits";
import { useBundle } from "@/lib/bundle";
import { cn } from "@/lib/utils";

function Chip({ children, ok, bad, title }: { children: React.ReactNode; ok?: boolean; bad?: boolean; title?: string }) {
  return <span title={title} className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5", ok && "border-emerald-300 bg-emerald-50 text-emerald-800", bad && "border-red-300 bg-red-50 font-medium text-red-700")}>{children}</span>;
}

/** Data sources the dashboard actually shows (licence text exactly as recorded in the registry) and the build status. */
export function SiteFooter() {
  const { nodes, meta } = useBundle();
  const sources = useMemo(() => {
    const used = new Set<string>();
    for (const n of Object.values(nodes)) {
      if (!n.ui) continue;
      for (const id of [...n.lineage, ...n.edges.filter((e) => e.rel === "shows").map((e) => e.to)]) if (id.startsWith("SRC-") && nodes[id]) used.add(id);
    }
    return [...used].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).map((id) => nodes[id]);
  }, [nodes]);
  return (
    <footer className="border-t bg-muted/20">
      <div className="mx-auto max-w-[1400px] space-y-4 px-4 py-6 text-xs text-muted-foreground">
        {sources.length > 0 && (
          <>
            <h2 className="text-sm font-semibold text-foreground">Data sources and licences</h2>
            <ul className="grid gap-x-8 gap-y-2 md:grid-cols-2">
              {sources.map((s) => (
                <li key={s.id}>
                  <NodeLink id={s.id} label={String(s.fields.name)} className="font-sans text-xs font-medium" /> — {String(s.fields.publisher)}.{" "}
                  <span>Licence: {String(s.fields.licence)}.</span>
                </li>
              ))}
            </ul>
            <p>Shown as recorded in this project’s data-source registry; open a source for its full entry. Series marked estimated, calculated or constructed were produced by this project from these sources.</p>
          </>
        )}
        {meta && (
          <div className="flex flex-wrap items-center gap-2 border-t pt-3">
            <Chip title={`bundle built ${meta.built_utc} from commit ${meta.git.commit_full}`}>build {meta.git.commit}</Chip>
            {meta.git.dirty ? <Chip bad title={meta.git.dirty_paths.join("\n")}><AlertTriangle className="size-3" /> built from uncommitted changes</Chip> : <Chip ok><CheckCircle2 className="size-3" /> clean tree</Chip>}
            {meta.manifest.verified ? <Chip ok title="every file in data/canonical/MANIFEST.sha256 matched"><CheckCircle2 className="size-3" /> data checksums verified ({meta.manifest.files_listed} files)</Chip> : <Chip bad><AlertTriangle className="size-3" /> data checksums do not verify</Chip>}
            <Link href="/audit/" className="underline">Sources &amp; audit</Link>
            {meta.repo_url && <a href={meta.repo_url} target="_blank" rel="noreferrer" className="underline">Repository</a>}
          </div>
        )}
      </div>
    </footer>
  );
}
