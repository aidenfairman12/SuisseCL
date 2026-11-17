"use client";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useNodeParam } from "@/lib/deeplink";
import { NodeCard } from "./node-card";

/** Right-hand audit card, opened by ?node=ID on any page. */
export function AuditSheet() {
  const { id, close } = useNodeParam();
  return (
    <Sheet open={!!id} onOpenChange={(o) => { if (!o) close(); }}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-2xl">
        <SheetHeader className="sr-only">
          <SheetTitle>Audit card {id}</SheetTitle>
          <SheetDescription>Where this value comes from: source, method, parameters, quality checks and related decisions.</SheetDescription>
        </SheetHeader>
        <ScrollArea className="h-full">
          <div className="p-5 pr-12">{id && <NodeCard key={id} id={id} />}</div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
