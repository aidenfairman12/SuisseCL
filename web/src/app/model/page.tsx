import { PageHeader } from "@/components/page-shell";
import { ModelPage } from "@/components/model/model-page";

export default function Model() {
  return (
    <>
      <PageHeader title="Model" page="model" />
      <ModelPage />
    </>
  );
}
