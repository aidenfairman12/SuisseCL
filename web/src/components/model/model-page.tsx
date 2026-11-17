"use client";
import { FigureView } from "@/components/charts/registry";
import { TopicHeader } from "@/components/topic-header";
import { MoreViews } from "@/components/topic-more";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const SECTIONS = [
  { id: "hp", label: "Heat pumps", node: "card:cop_model", main: "cop_curves", more: ["spf_check", "hp_split_monthly"], also: "card:hp_nominal_power", alsoFig: ["hp_sizing"] },
  { id: "tanks", label: "Tanks", node: "card:tanks", main: "tank_sizes", more: [] as string[] },
  { id: "env", label: "Environment", node: "card:environment", main: "env_interface", more: [] as string[] },
  { id: "reward", label: "Reward", node: "card:reward", main: "reward_year", more: [] as string[] },
];

export function ModelPage() {
  return (
    <Tabs defaultValue="hp">
      <TabsList>{SECTIONS.map((s) => <TabsTrigger key={s.id} value={s.id}>{s.label}</TabsTrigger>)}</TabsList>
      {SECTIONS.map((s) => (
        <TabsContent key={s.id} value={s.id} className="space-y-4 pt-4">
          <TopicHeader nodeId={s.node} maxNumbers={8} />
          <FigureView name={s.main} />
          <MoreViews figs={s.more} />
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
