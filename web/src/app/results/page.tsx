import { PageHeader } from "@/components/page-shell";
import { ResultsPage } from "@/components/results/results-page";

export default function Results() {
  return (
    <>
      <PageHeader title="Results" lead="What each controller does to cost, peak, import and carbon compared with no control, and when in the year it happens." />
      <ResultsPage />
    </>
  );
}
