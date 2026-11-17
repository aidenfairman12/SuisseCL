"use client";
import { ExternalLink } from "lucide-react";
import { ClassBadge, Linkified } from "@/components/audit/bits";
import { Button } from "@/components/ui/button";
import { useBundle } from "@/lib/bundle";
import { useNodeParam } from "@/lib/deeplink";

/** Title, classification, plain summary, caveats and key numbers of one audit node, with a button to open its card. */
export function TopicHeader({ nodeId, maxNumbers = 4 }: { nodeId: string; maxNumbers?: number }) {
  const { nodes } = useBundle();
  const { open } = useNodeParam();
  const n = nodes[nodeId];
  if (!n) return null;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">{n.display_name || n.title}</h2>
        <ClassBadge cls={n.classification} />
        <Button size="sm" variant="outline" className="ml-auto gap-1.5" onClick={() => open(nodeId)}>Audit card <ExternalLink className="size-3.5" /></Button>
      </div>
      {n.summary && <p className="max-w-4xl text-[15px] leading-relaxed"><Linkified text={n.summary} /></p>}
      {(n.caveats ?? []).map((c, i) => <p key={i} className="max-w-4xl rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-sm text-amber-950"><Linkified text={c} /></p>)}
      {n.numbers && n.numbers.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {n.numbers.slice(0, maxNumbers).map((x, i) => (
            <div key={i} className="rounded-lg border px-3 py-2">
              <div className="text-lg font-semibold tabular-nums">{x.value} {x.unit && x.unit !== "-" && <span className="text-xs font-normal text-muted-foreground">{x.unit}</span>}</div>
              <div className="text-xs text-muted-foreground">{x.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
