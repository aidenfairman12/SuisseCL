import { PageHeader, PhaseNote } from "@/components/page-shell";
import { ResultsPage } from "@/components/results/results-page";

export default function Results() {
  return (
    <>
      <PageHeader title="Results" page="results" />
      <PhaseNote links={[{ href: "/scenarios/", label: "Solar and battery scenarios" }, { href: "/controllers/", label: "Controllers against the ideal" }, { href: "/explorer/", label: "Warmer climate" }]}>
        <b className="font-semibold">Phase A setup:</b> heat pumps, tanks and grid electricity only; no solar, battery or cooling.
      </PhaseNote>
      <ResultsPage />
    </>
  );
}
