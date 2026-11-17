import { PageHeader } from "@/components/page-shell";
import { ModelPage } from "@/components/model/model-page";

export default function Model() {
  return (
    <>
      <PageHeader title="Model" lead="How inputs become heat demand, storage and electricity: heat pumps, tanks, the CityLearn environment and the reward." />
      <ModelPage />
    </>
  );
}
