import { ExplorerPage } from "@/components/phase-c/explorer-page";
import { PageHeader } from "@/components/page-shell";

export default function Explorer() {
  return (
    <>
      <PageHeader title="Explorer" page="explorer" />
      <ExplorerPage />
    </>
  );
}
