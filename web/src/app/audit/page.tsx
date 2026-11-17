import { PageHeader } from "@/components/page-shell";
import { AuditPage } from "@/components/audit-page/audit-page";

export default function Audit() {
  return (
    <>
      <PageHeader title="Audit" lead="Everything behind the numbers: every registry row, the validation checks, the open issues, the quality reports, and which version of the repository this page was built from." />
      <AuditPage />
    </>
  );
}
