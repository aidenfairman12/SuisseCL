"use client";
import Link from "next/link";
import { FigureView } from "@/components/charts/registry";
import { TopicHeader } from "@/components/topic-header";
import { MoreViews } from "@/components/topic-more";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Section = {
  id: string; label: string; phase: string; node: string; main?: string; more?: string[];
  also?: string; alsoFig?: string[]; links?: { href: string; label: string }[];
};

// Phase A devices first (the hourly simulation), then what Phase B and C add on top.
const SECTIONS: Section[] = [
  { id: "hp", label: "Heat pumps", phase: "All phases", node: "card:cop_model", main: "cop_curves", more: ["spf_check", "hp_split_monthly"], also: "card:hp_nominal_power", alsoFig: ["hp_sizing"] },
  { id: "tanks", label: "Tanks", phase: "All phases", node: "card:tanks", main: "tank_sizes" },
  { id: "pv", label: "Solar", phase: "Phase B and C", node: "card:pv", links: [{ href: "/scenarios/", label: "Scenario ladder" }, { href: "/cooling/", label: "How much cooling solar covers" }] },
  { id: "battery", label: "Battery", phase: "Phase B and C", node: "card:battery", links: [{ href: "/scenarios/", label: "Scenario ladder" }, { href: "/controllers/", label: "Controllers against the ideal" }] },
  { id: "rc", label: "Building model", phase: "Phase B (third step) and C", node: "card:rc_building", links: [{ href: "/scenarios/", label: "Scenario ladder" }, { href: "/climate/", label: "Heat-wave week" }] },
  { id: "cooling", label: "Cooling", phase: "Phase C", node: "card:cooling", links: [{ href: "/cooling/", label: "Cooling across the district" }, { href: "/houses/", label: "Per building" }, { href: "/explorer/", label: "Explorer" }] },
  { id: "env", label: "Environment", phase: "Phase A simulation", node: "card:environment", main: "env_interface" },
  { id: "reward", label: "Reward", phase: "Phase A simulation", node: "card:reward", main: "reward_year" },
];

export function ModelPage() {
  return (
    <Tabs defaultValue="hp">
      <TabsList className="h-auto flex-wrap">{SECTIONS.map((s) => <TabsTrigger key={s.id} value={s.id}>{s.label}</TabsTrigger>)}</TabsList>
      {SECTIONS.map((s) => (
        <TabsContent key={s.id} value={s.id} className="space-y-4 pt-4">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">{s.phase}</p>
          <TopicHeader nodeId={s.node} maxNumbers={8} />
          {s.main && <FigureView name={s.main} />}
          <MoreViews figs={s.more ?? []} />
          {s.links && (
            <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              <span className="text-zinc-500">Results that use it:</span>
              {s.links.map((l) => <Link key={l.href} href={l.href} className="text-blue-700 hover:underline">{l.label} →</Link>)}
            </p>
          )}
          {s.also && (
            <div className="space-y-3 border-t pt-4">
              <TopicHeader nodeId={s.also} maxNumbers={3} />
              {s.alsoFig?.map((f) => <FigureView key={f} name={f} />)}
            </div>
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}
