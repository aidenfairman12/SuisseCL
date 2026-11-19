import { PageHeader } from "@/components/page-shell";
import { ScenariosPage } from "@/components/scenarios/scenarios-page";

export default function Scenarios() {
  return (
    <>
      <PageHeader title="Scenarios" page="scenarios" />
      <ScenariosPage />
    </>
  );
}
