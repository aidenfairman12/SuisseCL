// Shape of dashboard bundle files written by swiss/dashboard/build_bundle.py (web/public/bundle/*.json).
export type Json = string | number | boolean | null | Json[] | { [k: string]: Json };

export type Edge = { rel: string; to: string; note?: string };
export type Backlink = { rel: string; from: string };

export type CodeExcerpt = {
  file: string;
  symbol: string | null;
  commit: string | null;
  uncommitted_changes: boolean;
  kind: string;
  line: number;
  source: string;
  defines?: string[];
};

export type HistoryEntry = {
  date: string;
  text: string;
  affects: string;
  status: string;
  needs_user_approval: string;
  line: number;
};

export type NodeT = {
  id: string;
  kind: string;
  title: string;
  classification: string | null;
  classification_raw: string | null;
  summary: string | null;
  fields: Record<string, Json>;
  edges: Edge[];
  backlinks: Backlink[];
  qc: string[];
  figures: string[];
  code: CodeExcerpt[];
  docs: string[];
  source_ref: { file: string; line: number; raw: string } | null;
  parse_warnings: string[];
  lineage: string[];
  lineage_tree: Record<string, string[]>;
  produced_by: string[];
  // optional, depending on kind
  status?: string;
  open?: boolean;
  passed?: boolean;
  history?: HistoryEntry[];
  results?: Json;
  results_key?: string | null;
  numbers?: { label: string; value: string; unit: string; note?: string | null }[];
  caveats?: string[];
  ui?: boolean;
  primary?: string | null;
  lineage_end?: string | null;
  formula?: string | null;
  display_name?: string | null;
  short_name?: string | null;
  flags?: { column: string; label: string }[];
};

export type Provenance = {
  nodes: Record<string, NodeT>;
  ui_keys: string[];
  settings: { classification_colours?: Record<string, string> };
};

export type Meta = {
  built_utc: string;
  git: { commit: string; commit_full: string; dirty: boolean; dirty_paths: string[] };
  manifest: { verified: boolean; files_listed: number; failures: { file: string; problem: string }[] };
  inputs: Record<string, string>;
  node_counts: Record<string, number>;
  build_errors: string[];
  repo_url?: string | null;
};

export const KIND_LABEL: Record<string, string> = {
  source: "Data source",
  derived_dataset: "Derived dataset",
  transform: "Transformation",
  model: "Model",
  parameter: "Parameter",
  decision: "Decision",
  assumption: "Assumption",
  issue: "Issue",
  controller: "Controller",
  reward: "Reward",
  experiment: "Experiment",
  kpi: "KPI",
  validation_check: "Validation check",
  qc_report: "QC report",
  series: "Series",
  card: "Element",
  panel: "Panel",
  figure: "Figure",
  map_box: "System-map box",
};

export const REL_LABEL: Record<string, string> = {
  shows: "built from",
  mentions: "mentions",
  input: "input",
  output: "output",
  derived_from: "derived from",
  decided_in: "decided in",
  uses_model: "uses model",
  uses_dataset: "uses dataset",
  uses_controller: "uses controller",
  uses_reward: "uses reward",
  has_parameter: "parameter",
  parameter_of: "parameter of",
  qc: "QC",
};

// ---- other bundle files (series_inputs.json, figures.json, results.json, trace_<controller>.json)
export type Series = { label: string; unit: string; values: (number | null)[]; classification: string; ui: string; relative_only?: boolean };
export type SeriesInputs = {
  start_utc: string;
  step_s: number;
  n: number;
  utc_offset_h: number[];
  local_hour: number[];
  weekday: number[];
  tier_high: number[];
  series: Record<string, Series>;
  /** Percent of the year's hours with a lower modeled carbon intensity (null = no estimate); the only carbon figure shown outside the carbon audit card. */
  carbon_rank: { values: (number | null)[]; year: number; definition: string };
  flags: Record<string, { label: string; values: number[]; ui: string }>;
  buildings: Record<string, { gap_filled_flag: number[]; components: { key: string; label: string; classification: string; values: (number | null)[] }[] }>;
};

export type DistrictBuilding = {
  index: number;
  building: string;
  role: string;
  type: "SFH" | "MFH";
  source: string;
  source_id: number;
  units: number;
  area_m2: number | null;
  residents: number | null;
  heating_tank_kwh_th: number;
  dhw_tank_kwh_th: number;
  hp_sh_nominal_kw: number;
  hp_dhw_nominal_kw: number;
  T_sup_sh_c: number;
  eta_sh: number;
  apartments_synthetic: boolean;
  gap_filled_hours: number;
};
export type Figures = {
  district: { buildings: DistrictBuilding[]; files: string[] };
  env_interface: { observations_active: string[]; actions_active: string[] };
  [k: string]: unknown;
};

export type ResultRow = Record<string, number | string | null> & { controller: string };
export type Results = {
  columns: string[];
  rows: ResultRow[];
  meta: { git_head: string };
  experiment_of: Record<string, string[]>;
  traces: Record<string, { n: number; same_as: string | null; file: string }>;
  files: string[];
};
export type Trace = { arrays: Record<string, (number | null)[]>; n: number };

// ---- story.json (plain-language layer; built from swiss/dashboard/ui_map.yaml and the repository files)
export type Phase = { letter: string; focus: string; objective: string };
export type StoryDay = { index: number; date: string; label: string; mean_temp_c: number; hours: number };
export type StoryData = {
  controllers: Record<string, { key: string; display_name: string; short_name: string; node: string; note?: string }>;
  buildings: Record<string, string>;
  building_groups: Record<string, string>;
  carbon_relative: { cleaner: string; dirtier: string; typical: string; missing: string; sub: string; typical_band_pct: [number, number] };
  pages: Record<string, string>;
  glossary: { id: string; term: string; definition: string; node?: string }[];
  phases: Phase[];
  derived: { day: StoryDay };
  story: {
    hero: { question: string; context: string; status: string; tiles: { value: string; label: string }[] };
    district: { title: string; caption: string };
    how: { title: string; steps: { title: string; text: string; node: string }[] };
    findings: {
      title: string; verdict: string; rules_line: string; chart_title: string; chart_caption: string; tiles_caption: string; closing: string;
      tiles: { node: string; label: string; unit: string; value: number; reference: number; vs_none_pct: number }[];
      day: StoryDay; rule: { controller: string; name: string }; reference: { controller: string; name: string };
    };
    trust: {
      title: string; validation: string; classes_title: string; classes: Record<string, { label: string; meaning: string }>;
      limitations_title: string; limitations: { title: string; text: string; node: string }[];
    };
    next: { title: string; source_note: string; phases: Phase[] };
  };
};

// ---- scenarios.json and controllers.json (Phase B pages; built by swiss/dashboard/phase_b.py from committed result files)
export type PbLadder = { id: string; name: string; adds: string; classes: string[]; nodes: string[]; zero_bill_year_chf: number; saving_year_pct: number; saving_week_pct: number | null };
export type PbTariff = { id: string; label: string; spread_rp: number; mean_rp: number; S0: number; S1: number; S2: number; S3: number };
export type ScenariosData = {
  ladder: PbLadder[];
  ceilings: Record<string, { week: number | null; year: number }>;
  export_sweep: Record<string, { S1: number; S2: number; S3: number }>;
  bands: { s3_band_20_24: number; s3_band_21_24: number; s3_no_flex: number };
  tariffs: PbTariff[];
  resolution: { name: string; hourly_pct: number; q15_pct: number }[];
  ev: { name: string; zero_bill: number; saving_pct: number }[];
  leg: { discount: number; bill_with_leg: number; bill_before_leg_credit: number; zero_bill_with_leg: number; internal_kwh: number; sharing_share_of_import: number }[];
  metrics: { name: string; import_kwh: number; peak_kw: number; pv_self_consumption: number | null; self_sufficiency: number | null; battery_cycles: number | null; bill_chf: number; emissions_index: number | null }[];
  gate_pct: number;
  export_price_rp: number;
  sources: string[];
  prose: Record<string, string>;
};
export type PbRow = {
  id: string; group: string; label: string; saving_pct: number | null; corrected_pct?: number | null; share_of_ceiling_pct?: number | null; peak_kw?: number | null;
  peak_vs_zero_pct?: number | null; weekly_peak_kw?: number | null; comfort_kh?: number | null; n?: number | null; spread_pct?: number | null; steps_trained?: number; note?: string;
  mode?: string; horizon?: number; level?: number; peak_w?: number; rc_perturb?: number; rc_margin?: number; rc_correct?: boolean; scenarios?: number; share?: number; err_scale?: number;
};
export type PbTradeoffPoint = { peak_w: number; saving_pct: number; peak_kw: number; weekly_peak_kw: number; comfort_kh: number };
export type ControllersData = {
  scenarios: Record<string, { name: string; ceiling_pct: number; reference: { label: string; bill_chf: number; peak_kw: number; weekly_peak_kw: number }; rows: PbRow[] }>;
  rl_curves: { scenario: string; kind: string; seed: number; steps: number[]; bill_change_pct: number[] }[];
  forecast_quality: {
    scenario: string; ceiling_pct: number;
    synthetic: { x: number; saving_pct: number; kind: string; label: string }[];
    history_only: { x: number; saving_pct: number; label: string };
    weather_conditioned: { x: number; saving_pct: number; label: string; error_stored: boolean; pv_error: number; demand_error: number };
    measured_error: Record<string, unknown>;
  };
  peak_tradeoff: Record<string, { series: Record<string, PbTradeoffPoint[]>; zero_peak_kw: number; pv_rule: { saving_pct: number; peak_kw: number } }>;
  model_error_s3: { label: string; rc_perturb: number; rc_margin: number; rc_correct: boolean; peak_w: number; saving_pct: number; comfort_kh: number; peak_kw: number }[];
  stochastic: { label: string; scenarios: number; share: number; err_scale: number; horizon: number; saving_pct: number; peak_kw: number }[];
  deterministic_reference: { saving_pct: number; peak_kw: number; horizon: number };
  limitations: { id: string; kind: string; title: string; summary: string | null; status: string | null }[];
  sources: string[];
  prose: Record<string, string | string[]>;
};

// ---- climate.json, cooling.json, explorer.json, houses.json (Phase C pages; built by swiss/dashboard/phase_c.py from committed result files)
export type PcArchetype = { id: string; label: string };
export type PcSpell = { level: string; percentile: number; chain: string; model_year: number; start: string; severity_c: number; tasmax: number[]; tasmin: number[] };
export type ClimateScenario = {
  id: string; label: string; sensitivity: boolean; annual_mean_c: number; days_ge30: number; days_ge35: number; hottest_168h_c: number; week29_mean_c: number; week29_max_c: number;
  ghi_kwh_m2: number; pv_kwh_kwp: number; monthly_mean_c: number[]; week29_hourly_c?: number[];
};
export type ClimateData = {
  scenarios: Record<string, ClimateScenario>; order: string[]; sensitivity: string[]; spells: PcSpell[];
  validation: { recon_all_days: number; recon_all_rmse_k: number; recon_hot_days: number; recon_hot_rmse_k: number; ensemble: { level: string; days_ge30: number | null; days_ge35: number | null; hurs_max: number | null }[] };
  rule: string; inserted_rows: number[]; citation: string; sources: string[]; prose: Record<string, string | string[]>;
};
export type PcController = {
  saving_pct: number; share_of_ceiling_pct: number; highest_hour_kw: number; weekly_peak_kw: number; comfort_cold_kh: number; dh26: number; cooling_kwh: number; heating_kwh: number;
  import_kwh: number; export_kwh: number; cost_chf: number;
};
export type PcShare = { pv: number; battery: number; grid: number; cooling_kwh: number } | null;
export type PcPair = { baseline: number; optimum: number };
export type PcDiff = { cool_kwh: number; heat_kwh: number; import_kwh: number; export_kwh: number; summer_import_kwh: number; summer_peak_kw: number; peak_kw: number; degree_hours_above_26: number; emissions_kg: number };
export type CoolingCell = {
  id: string; archetype: string; scenario: string; adoption: string; cooled: string[]; ceiling_year_pct: number; pinned_year_pct: number; mass_value_pts: number; ceiling_weeks_pct: number;
  zero_bill_chf: number; opt_bill_chf: number; cooling_kwh: PcPair; heating_kwh: PcPair; dh26: PcPair; emissions_kg: PcPair; pv_self_consumption: PcPair;
  import_kwh: PcPair & { summer_baseline: number; summer_optimum: number }; export_kwh: PcPair & { summer_baseline: number; summer_optimum: number };
  peak_kw: PcPair & { summer_baseline: number; summer_optimum: number }; peak_kw_note?: string;
  pv_cooling_share: { thermostat: PcShare; optimum: PcShare; thermostat_hp_first: PcShare; optimum_hp_first: PcShare };
  controllers: Record<string, PcController>; difference_vs_none: Record<string, PcDiff> | null;
};
export type PcRobust = { cell: string; case: string; label: string; saving_pct: number; share_of_ceiling_pct: number; comfort_cold_kh: number; dh26: number; cooling_kwh: number; highest_hour_kw: number; synthetic: boolean };
export type PcLimitation = { id: string; kind: string; title: string; summary: string | null; status: string | null };
export type CoolingData = {
  archetypes: PcArchetype[]; scenarios: string[]; scenario_labels: Record<string, string>; adoption: string[]; adoption_labels: Record<string, string>; adoption_short: Record<string, string>;
  controllers: string[]; controller_labels: Record<string, string>; cells: CoolingCell[]; robustness: PcRobust[]; limitations: PcLimitation[]; pending_register: { title: string; text: string }[];
  meta: { test_weeks: number[] | null; export_price_rp: number }; sources: string[]; prose: Record<string, string | string[]>;
};
export type HoursSeries = { base: number[]; dhw: number[]; heat: number[]; cool: number[]; pv: number[]; batt: number[]; net: number[] };
export type ExplorerData = {
  archetypes: PcArchetype[]; scenarios: string[]; scenario_labels: Record<string, string>; adoption: string[]; adoption_labels: Record<string, string>; controllers: string[];
  controller_labels: Record<string, string>; week: { steps: number[]; number: number }; hourly: Record<string, { archetype: string } & Record<string, unknown>>; hours_note_cells: string[];
  house_groups: Record<string, string[]>; sources: string[]; prose: Record<string, string | string[]>;
};
export type HouseAnnual = {
  base: number; dhw: number; heat: number; cool: number; pv: number; import: number; export: number; pv_share_of_cooling: number | null; battery_share_of_cooling: number | null;
  grid_share_of_cooling: number | null; pv_used_onsite: number; pv_self_consumption: number | null; self_sufficiency: number | null;
};
export type HouseBlock = { annual: HouseAnnual; summer: HouseAnnual; peak_kw: number; dh26: number; pv_share_of_cooling_hp_first: number | null };
export type HousesData = {
  buildings: string[]; archetypes: PcArchetype[]; scenarios: string[]; scenario_labels: Record<string, string>; adoption: string[]; adoption_labels: Record<string, string>;
  cells: Record<string, { archetype: string } & Record<string, unknown>>; sources: string[]; prose: Record<string, string | string[]>;
};
