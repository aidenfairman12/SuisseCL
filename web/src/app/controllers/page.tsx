import { ControllersPage } from "@/components/controllers/controllers-page";
import { PageHeader } from "@/components/page-shell";

export default function Controllers() {
  return (
    <>
      <PageHeader title="Controllers" page="controllers" />
      <ControllersPage />
    </>
  );
}
