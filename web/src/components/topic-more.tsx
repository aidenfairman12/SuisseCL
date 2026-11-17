"use client";
import { FigureView, FIGURES } from "@/components/charts/registry";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

/** Secondary figures behind a closed accordion; each opens (and loads its chart) only when asked for. */
export function MoreViews({ figs }: { figs: string[] }) {
  const list = figs.filter((f) => FIGURES[f]);
  if (!list.length) return null;
  return (
    <Accordion multiple className="rounded-lg border px-3">
      {list.map((f) => (
        <AccordionItem key={f} value={f}>
          <AccordionTrigger>{FIGURES[f].title}</AccordionTrigger>
          <AccordionContent><FigureView name={f} bare /></AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
