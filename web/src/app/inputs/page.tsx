import { PageHeader } from "@/components/page-shell";
import { InputsPage } from "@/components/inputs/inputs-page";

export default function Inputs() {
  return (
    <>
      <PageHeader title="Inputs" lead="The data that drives the simulation: weather, price, carbon and building electricity. Each tab shows the hourly series, how far to trust it, and where it comes from." />
      <InputsPage />
    </>
  );
}
