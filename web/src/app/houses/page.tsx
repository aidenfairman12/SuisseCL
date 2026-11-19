import { HousesPage } from "@/components/phase-c/houses-page";
import { PageHeader } from "@/components/page-shell";

export default function Houses() {
  return (
    <>
      <PageHeader title="Houses" page="houses" />
      <HousesPage />
    </>
  );
}
