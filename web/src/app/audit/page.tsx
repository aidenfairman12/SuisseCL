import { PageHeader } from "@/components/page-shell";
import { AuditPage } from "@/components/audit-page/audit-page";
import { FlowDiagram } from "@/components/overview/flow-diagram";

export default function Audit() {
  return (
    <>
      <PageHeader title="Sources & audit" page="audit" />
      <section className="mb-8 space-y-2">
        <h2 className="text-lg font-semibold">How the pieces connect <span className="text-sm font-normal text-muted-foreground">click any box; colours show the classification</span></h2>
        <FlowDiagram />
      </section>
      <AuditPage />
    </>
  );
}
