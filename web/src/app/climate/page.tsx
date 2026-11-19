import { ClimatePage } from "@/components/phase-c/climate-page";
import { PageHeader } from "@/components/page-shell";

export default function Climate() {
  return (
    <>
      <PageHeader title="Climate" page="climate" />
      <ClimatePage />
    </>
  );
}
