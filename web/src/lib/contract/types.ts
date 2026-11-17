// Contract v1 types. Mirrors swiss/contract/schema/*.schema.json (generated from swiss/contract/variables.py).
// Owned by the simulation workstream: request changes instead of editing. test_contract.py fails if a variable is missing here.
export const CONTRACT_VERSION = "1.0.0-draft";

/** Four data classes plus the assumed-parameter badge. Classified by HOW a value was obtained, not by what it represents. */
export type Provenance = "measured" | "derived" | "modeled" | "synthetic" | "assumed_parameter";
export type ProvenanceOrByType = Provenance | { SFH: Provenance; MFH: Provenance };
export type BuildingId = string; // the six ids come from manifest.buildings; show buildings.<id>.display_name, never the id (lint rule)
export type TankMode = "charging" | "discharging" | "idle";
export type Scope = { kind: "window" | "year"; start_step: number; n_steps: number };

/** An attribute that may be unavailable. `available:false` means NOT KNOWN (never show it as 0); `value:null` then, `provenance:null`. */
export type Attribute = {
  value: number | string | boolean | null;
  unit: string | null;
  provenance: Provenance | null;
  source_ids: string[];
  available: boolean;
  unavailable_reason: string | null;
};

export type Variable = {
  label: string;            // always show the label, never the id (e.g. "hw" = "hot water and other base load")
  unit: string;             // kWh_el | kWh_th | CHF | fraction 0-1 | ...  (energy per STEP, see manifest.units and units.ts)
  quantity: "energy_per_step" | "state" | "ratio" | "money" | "control";
  carrier: "electricity" | "heat" | null;
  provenance: ProvenanceOrByType;
  description: string;
  source_ids: string[];
  absent_when: string | null; // non-null: the series is `null` (not zeros) for buildings without that component
};

export type Manifest = {
  contract_version: string;
  phase: "A";
  kind: "sample" | "full";
  description: string;
  district_note: string;    // show wherever the six buildings appear together
  year: number;
  timezone: string;
  index_convention: string;
  time_axis: { start_utc: string; step_seconds: number; n_steps_inputs: number; n_steps_simulated: number; scope: Scope };
  buildings: BuildingId[];
  controllers: {
    id: string; key: string; display_name: string; short_name: string; algorithm_id: string; reference: boolean;
    identical_to: string | null; note: string | null; parameters: Record<string, number>;
  }[];
  scenarios: { id: string; label: string; dataset: string; description: string }[];
  runs: { scenario: string; controller: string; file: string }[];
  variables: { building: Record<keyof BuildingSeries, Variable>; district: Record<keyof DistrictSeries, Variable>; conditions: Record<keyof ConditionSeries, ConditionVariable> };
  situation_tags: Record<string, string>;
  situation_thresholds: Record<string, number>;
  units: Record<string, string>;
  checks: Record<string, unknown>;
  generated: { git_commit: string; git_dirty: boolean; python: string; citylearn: string };
  files: Record<string, string>;
  inputs: Record<string, string>;
};

export type ConditionVariable = { label: string; unit: string; provenance: Provenance; source_ids: string[]; description: string; relative_only?: boolean };

export type BuildingComponent = { present: boolean; label: string; attributes: Record<string, Attribute> };
export type BuildingInfo = {
  id: BuildingId; citylearn_name: string; display_name: string; type: "SFH" | "MFH"; source_dataset: string;
  attributes: Record<string, Attribute>;        // type, floor_area_m2, residents, housing_units, floors, heat_pump_type, ...
  components: Record<"hp_sh" | "hp_hw" | "tank_sh" | "tank_hw", BuildingComponent>;
  related_ids: string[];                         // registry IDs (issues, decisions): open with useNodeParam().open(id)
};
export type BuildingsFile = { contract_version: string; buildings: Record<BuildingId, BuildingInfo> };

export type SystemComponent = {
  id: string; label: string; category: "grid" | "conversion" | "storage" | "demand" | "input" | "control" | "outcome" | "future";
  description: string; phase_available: "A" | "B" | "C"; status: "modeled" | "not_modeled";
  inputs: string[]; outputs: string[]; variables: string[]; provenance: ProvenanceOrByType; source_ids: string[]; present_in: string; docs: string[];
};
export type SystemFlow = {
  id: string; from: string; to: string; carrier: "electricity" | "heat" | "signal" | "control"; variable: string | null; unit: string | null;
  description: string; status: "modeled" | "not_modeled";
};
export type ComponentsFile = { contract_version: string; components: SystemComponent[]; flows: SystemFlow[] };

/** Shared hourly inputs. Index i of every array = step scope.start_step + i. `null` items are genuine gaps. */
export type ConditionSeries = {
  temp_c: (number | null)[]; ghi_wm2: (number | null)[]; diffuse_wm2: (number | null)[]; beam_horizontal_wm2: (number | null)[];
  price_chf_kwh: number[]; tariff_tier: ("low" | "high")[];
  /** Percent of the year's hours with LOWER modeled carbon intensity. The only carbon quantity exported; never convert it to an absolute intensity. */
  carbon_relative_rank: (number | null)[];
};
export type ConditionsFile = {
  contract_version: string; scope: Scope; timestamps_utc: string[]; local_time: string[]; local_hour: number[]; weekday: number[];
  series: ConditionSeries; building_flags: Record<BuildingId, { gap_filled: number[] }>;
};

type S = number[];
type SA = number[] | null; // null = component absent in this building (some buildings have no hot-water tank)
/** Per building, one value per step. Energies are per STEP (kWh_el / kWh_th), not power: use units.ts. */
export type BuildingSeries = {
  hp_sh_kwh_el: S; hp_hw_kwh_el: S; household_kwh_el: S; net_kwh_el: S; cost_chf: S;
  sh_demand_kwh_th: S; hw_demand_kwh_th: S;
  hp_sh_direct_kwh_th: S; hp_sh_to_tank_kwh_th: S; sh_tank_to_demand_kwh_th: S; sh_tank_loss_kwh_th: S; sh_tank_soc: S; sh_tank_action: S; sh_tank_mode: TankMode[];
  hp_hw_direct_kwh_th: S; hp_hw_to_tank_kwh_th: SA; hw_tank_to_demand_kwh_th: SA; hw_tank_loss_kwh_th: SA; hw_tank_soc: SA; hw_tank_action: SA; hw_tank_mode: TankMode[] | null;
  cop_sh: S; cop_hw: S;
};
export type DistrictSeries = {
  net_kwh_el: S; hp_kwh_el: S; household_kwh_el: S; sh_demand_kwh_th: S; hw_demand_kwh_th: S; cost_chf: S;
  reward: S; reward_cost: S; reward_peak: S; reward_ramp: S;
};
/** Sparse tags: tag -> steps (relative to scope.start_step) where it holds. A missing tag never holds. Definitions: manifest.situation_tags. */
export type Tags = Record<string, number[]>;
export type RunSummary = {
  import_kwh_el: number; peak_kw_el: number; peak_step: number; cost_chf: number; high_tariff_import_share: number;
  hp_kwh_el: number; tank_loss_kwh_th: number; heat_from_tanks_kwh_th: number; reward_sum: number;
};
export type RunFile = {
  contract_version: string; scenario: string; controller: string; algorithm_id: string; identical_to: string | null;
  experiment_ids: string[]; seed: number; reward: { id: string; weights: Record<string, number>; scales: Record<string, number> };
  scope: Scope; buildings: Record<BuildingId, BuildingSeries>; district: DistrictSeries;
  situations: { district: Tags; buildings: Record<BuildingId, Tags> }; summary: RunSummary;
};

export type Comparison = {
  metrics: Record<string, { unit: string; value: number; reference: number; delta: number; delta_pct: number | null }>;
  mechanisms: {
    import_moved_out_of_high_tariff_kwh_el: number; extra_tank_loss_kwh_th: number; extra_hp_electricity_kwh_el: number;
    /** Change of carbon-weighted import vs the reference, in percent. RELATIVE ONLY: never show absolute emissions. */
    relative_carbon_change_pct: number | null; peak_step_reference: number; peak_step: number;
  };
  relative_only: string[];
};
export type ComparisonsFile = { contract_version: string; scenario: string; reference_controller: string; scope: Scope; comparisons: Record<string, Comparison> };
