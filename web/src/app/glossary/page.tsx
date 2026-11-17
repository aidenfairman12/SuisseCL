import { PageHeader } from "@/components/page-shell";
import { GlossaryPage } from "@/components/glossary-page";

export default function Glossary() {
  return (
    <>
      <PageHeader title="Glossary" page="glossary" />
      <GlossaryPage />
    </>
  );
}
