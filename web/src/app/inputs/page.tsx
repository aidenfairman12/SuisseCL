import { PageHeader, PhaseNote } from "@/components/page-shell";
import { InputsPage } from "@/components/inputs/inputs-page";

export default function Inputs() {
  return (
    <>
      <PageHeader title="Inputs" page="inputs" />
      <PhaseNote links={[{ href: "/model/", label: "Solar, battery and cooling models" }, { href: "/scenarios/", label: "Export price and tariff scenarios" }, { href: "/climate/", label: "Warmer weather years" }]}>
        <b className="font-semibold">Measured inputs for 2023</b> used by every phase. Later phases add assumed solar, other tariffs and warmer weather on top.
      </PhaseNote>
      <InputsPage />
    </>
  );
}
