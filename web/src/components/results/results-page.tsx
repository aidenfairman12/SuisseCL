"use client";
import { useState } from "react";
import { FigureView } from "@/components/charts/registry";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { NodeLink } from "@/components/audit/bits";
import { DEFAULT_CONTROLLER } from "@/components/district/district-view";
import { TopicHeader } from "@/components/topic-header";
import { AllKpis } from "./all-kpis";
import { CompareTable } from "./compare-table";
import { HourlyView } from "./hourly-view";
import { useResults } from "./results-utils";

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return <section className="space-y-3"><h2 className="text-lg font-semibold">{title} {hint && <span className="text-sm font-normal text-muted-foreground">{hint}</span>}</h2>{children}</section>;
}

export function ResultsPage() {
  const res = useResults();
  const [controller, setController] = useState(DEFAULT_CONTROLLER);
  if (!res) return <p className="text-sm text-muted-foreground">Loading results…</p>;
  return (
    <div className="space-y-10">
      <Section title="Controllers compared" hint="full year 2023">
        <CompareTable res={res} controller={controller} onController={setController} />
      </Section>
      <Section title="Hour by hour" hint={`selected controller: ${controller}`}>
        <HourlyView res={res} controller={controller} />
      </Section>
      <Section title="How robust is this?" hint="the same controllers rerun under different synthetic assumptions">
        <TopicHeader nodeId="panel:sensitivity" maxNumbers={0} />
        <FigureView name="sensitivity_bars" bare />
      </Section>
      <Section title="All KPIs" hint={`for ${controller}, against no control`}>
        <Accordion className="rounded-lg border px-3">
          <AccordionItem value="all"><AccordionTrigger>Show all {res.columns.length - 2} results columns</AccordionTrigger><AccordionContent><AllKpis res={res} controller={controller} /></AccordionContent></AccordionItem>
        </Accordion>
        <p className="text-xs text-muted-foreground">How the controllers act: <NodeLink id="card:controllers" title /> · <NodeLink id="card:controller_tariff_map" title /> · <NodeLink id="panel:kpis" title /></p>
      </Section>
    </div>
  );
}
