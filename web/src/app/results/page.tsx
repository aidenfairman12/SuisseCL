import { PageHeader } from "@/components/page-shell";
import { ResultsPage } from "@/components/results/results-page";

export default function Results() {
  return (
    <>
      <PageHeader title="Results" page="results" />
      <ResultsPage />
    </>
  );
}
