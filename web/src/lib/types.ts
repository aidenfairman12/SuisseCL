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
export type Series = { label: string; unit: string; values: (number | null)[]; classification: string; ui: string };
export type SeriesInputs = {
  start_utc: string;
  step_s: number;
  n: number;
  utc_offset_h: number[];
  local_hour: number[];
  weekday: number[];
  tier_high: number[];
  series: Record<string, Series>;
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
