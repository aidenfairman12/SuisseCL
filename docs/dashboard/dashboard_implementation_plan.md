# Audit dashboard: implementation plan (Swiss Phase A)

Status: implemented (milestones 1-6, PR #1), then **re-platformed on 2026-11-17** (see "Revision 2026-11-17" below).
Written 2026-11-17 from a design session with the owner.

## Revision 2026-11-17: guided pages on Next.js (supersedes parts of §1, §5, §7, §8.7)
The first version put everything on one long page and overwhelmed its reader. The owner chose **guided pages**, a **Next.js rebuild** and **private hosting on Vercel**. The Python side (parsers, provenance graph, `ui_map.yaml`, `lint.py`, traces, freshness check) is unchanged and remains the only source of facts.
- **Stack:** `web/` = Next.js (static export) + Tailwind + shadcn/ui + Apache ECharts. It only reads `web/public/bundle/*.json`; it holds no facts of its own. The old `dashboard/` (static HTML + Plotly) was removed; it is in git history (PR #1).
- **Bundle:** `build_bundle.py` writes plain JSON to `web/public/bundle/` (committed, so Vercel needs no Python). `lint.py` and `test_dashboard.py` read it there and scan `web/src` for card keys, KPI columns and figure names.
- **Pages:** Overview (the illustrated district, headline numbers, what is measured vs synthetic, flow diagram), Inputs (weather, price, carbon, buildings with trust overlay and click-for-hour), Model (heat pumps, tanks, environment, reward), Results (controller comparison, hour-by-hour with KPI drill-down, sensitivity, all KPIs), Audit (registry, validation, open issues, quality reports, snapshot integrity). The audit card is a side sheet opened from anywhere (`?node=ID`): summary, numbers, one figure and the lineage breadcrumb are always visible; method/code, parameters, QC, related items, full lineage and the registry row are in closed sections.
- **§8.7 replaced:** works offline only as a built site served by any static server (no `file://`); hosting on Vercel must be **private** (D-004 and the meter-data licences make a public link a publication).
- The original design below is kept for the requirements it still defines (§2-§4, §6, §8.1-8.6, §8.8).

Read `docs/HANDOFF.md` §3 (environment pins) and §8 (working agreements) first. In short: ask the owner before
committing, pushing or downloading anything, and never invent numbers.

## 1. Goal

Build a **simple dashboard of the Swiss Phase A simulation where almost everything on screen can be clicked to show
where it came from**: the data source, the transformation, the model or formula (with a figure of it), the parameters
and their citations, the QC results, and the decisions, assumptions and open issues that touch it. A reviewer should be
able to audit any number or curve without opening the repo.

Example: clicking the carbon-intensity curve opens a card that shows it is MODELED. The card gives the lineage
(Energy-Charts SRC-011 → TR-010 → DER-011 via model M-002), the tracing formula, the emission-factor table (IPCC AR5 and
proxies A-006..A-009), a stacked import-by-neighbour figure, the EPFL 2016-17 method check (shape r 0.98, level about
62 %), the flagged hours (4 interpolated, 120 fallback) and the source code of `build_carbon.py::intensity`.

### Decisions already made (owner, 2026-11-17)
| Topic | Decision |
|---|---|
| Stack | *(superseded, see Revision)* ~~Static HTML, vanilla JS, vendored Plotly.~~ A Python build script writes a JSON bundle; `web/` (Next.js static export) renders it. Python side uses only what is in `swiss/requirements-lock.txt` (pandas, numpy, PyYAML). |
| Bundle in git | **Committed.** `web/public/bundle/` is regenerated and committed with each results change, so every commit is a frozen, auditable snapshot that opens from a fresh clone. |
| System map | **Hand-drawn SVG.** |
| Scope | **Swiss Phase A only**: `swiss/`, `data/canonical/`, `swiss/datasets/swiss_district_2023` + 4 sensitivity variants, EXP-001..012. The `my_data/` cooling work is out of scope. |
| Run traces | **Yes.** Extend `run_baselines.py` to save per-step traces so every KPI can be drilled down to hours. |
| Audience | **Supervisor / reviewers.** Every card starts with a plain-language summary. IDs stay visible but secondary. |

### Design principles (these are requirements)
1. **The dashboard holds no facts of its own.** Every number, citation and status is read at build time from the
   existing registries, canonical data, QC JSONs and results. Hand-written prose (summaries) may reference values only
   through placeholders that are filled from data (for example `{qc_carbon.mean_consumption_g_kwh:.1f}`).
2. **No orphans.** Every clickable element maps to at least one registry ID. A test fails the build if an element has
   no provenance or references an ID that does not exist.
3. **Trust is visible.** Every series and number shows its classification (measured / derived / modeled / synthetic /
   assumption). Imputed, interpolated and fallback hours are visibly marked.
4. **Snapshot integrity.** The bundle records the git commit, a dirty-tree flag and whether `data/canonical/MANIFEST.sha256`
   verifies. The header shows a warning if either check fails.
5. **As simple as possible.** One page, a few views, one card template. No framework or build toolchain for the frontend.

## 2. Sources of truth (inputs to the build script)

| Content | File(s) | Format / parsing note |
|---|---|---|
| Data sources SRC-*, derived datasets DER-* | `docs/data/data_source_registry.csv` | CSV (quoted fields contain commas) |
| Transformations TR-* | `docs/data/transformation_log.md` | Markdown table |
| Models M-* | `docs/models/model_registry.md` | Markdown table |
| Parameters (values and citations) | `docs/models/parameter_registry.csv` | CSV; several rows per model |
| Decisions D-* (incl. D-013a, D-014a..e, D-017a) | `docs/decisions/decision_log.md` | Markdown table; IDs carry letter suffixes |
| Assumptions A-* | `docs/decisions/assumptions_log.md` | Markdown table |
| Issues ISS-* (45 rows today) | `docs/decisions/issues_and_risks.md` | Markdown table |
| Controllers ALG-* | `docs/algorithms/algorithm_registry.md`, `controller_documentation.md` | Markdown |
| Reward R-001 | `docs/algorithms/reward_function_documentation.md`, `swiss/experiments/rewards.py` docstring | Markdown / Python |
| Experiments EXP-* | `docs/experiments/experiment_registry.csv` | CSV |
| Column classifications | `data/canonical/hourly/columns.json` | JSON |
| QC reports | `docs/data/data_quality_reports/qc_*.json`, `backtest_gap_fill.json`, `carbon_epfl_comparison.json` | JSON (+ `.md` twins to link) |
| Validation V1..V8 | `docs/experiments/validation_reports/validation_phase_a.json` | JSON |
| Canonical series | `data/canonical/{weather_klo,tariff_ekz_standard,carbon_ch}_2023_hourly.csv`, `hourly/*.csv`, `thermal/*.csv`, `thermal/thermal_params.json` | CSV, UTC index `timestamp_utc` |
| CityLearn dataset | `swiss/datasets/swiss_district_2023/{schema.json,build_manifest.json,Building_*.csv,...}` | JSON/CSV |
| Results | `swiss/experiments/results/baselines_2023.csv` + `_meta.json`, `sensitivity_2023.csv`, `reward_scales.json`, **new** `traces/` (§6) | CSV/JSON |
| Integrity | `data/canonical/MANIFEST.sha256` | sha256sum format |

Parsing rules:
- Write one tolerant markdown-table parser. Unit-test it against known row counts (for example ISS = 45, TR = 11) so
  that a cell containing `|` cannot silently break a row.
- Extract IDs from free text with a regex (`\b(SRC|DER|TR|M|D|A|ISS|ALG|R|EXP|V)-?\d+[a-z]?\b`, adjusted for `V1`
  style). Use these to build cross-reference edges, for example a decision that mentions `ISS-029`.
- Use only the Python standard library plus pandas/numpy (already pinned). Run with `cl/bin/python -I`.

## 3. Provenance data model

Everything becomes a **node** in `provenance.json`:

```json
{
  "id": "DER-011",
  "kind": "derived_dataset",
  "title": "Modeled hourly Swiss electricity carbon intensity 2023",
  "classification": "modeled",
  "summary": "Hourly CO2 intensity of electricity used in Switzerland, rebuilt from generation and import data ...",
  "fields": { "...": "registry columns verbatim" },
  "edges": [ {"rel": "produced_by", "to": "TR-010"}, {"rel": "uses_model", "to": "M-002"},
             {"rel": "input", "to": "SRC-011"}, {"rel": "decided_in", "to": "D-013"} ],
  "qc": "qc_carbon_2023",
  "figures": ["carbon_import_stack", "carbon_epfl_check", "carbon_ef_table"],
  "code": [ {"file": "swiss/pipeline/build_carbon.py", "symbol": "intensity", "commit": "<git sha>"} ],
  "docs": ["docs/data/data_quality_reports/carbon_epfl_comparison.md"]
}
```

Node kinds: `source, transform, derived_dataset, model, parameter, decision, assumption, issue, controller, reward,
experiment, kpi, validation_check, qc_report, series, figure`.

Edges come from two places:
1. **Automatic.** The registry columns (`Inputs`, `Output`, `From ...` notes, `model_ids`, `algorithm_ids`, `dataset_ids`)
   and ID mentions in free text (stored as a weaker `mentions` edge).
2. **`swiss/dashboard/ui_map.yaml`** (hand-maintained, the only hand-written input). It maps UI elements to nodes and adds
   summaries and figure choices. YAML is used because the summaries are multi-line prose. PyYAML 6.0.3 is already in
   the venv and pinned in `swiss/requirements-lock.txt` (a CityLearn dependency), so no install is needed. Always load
   it with `yaml.safe_load`.

```yaml
series:carbon_intensity:
  label: Grid carbon intensity
  nodes: [DER-011, M-002, TR-010, SRC-011]
  primary: DER-011
  summary: >
    Modeled, not measured. Mean {qc_carbon.mean_consumption_g_kwh:.1f} g/kWh ...
  flags:
    - {column: neighbour_intensity_fallback_flag, label: neighbour fallback}
    - {column: gap_interpolated_flag, label: interpolated}
```

Code excerpts: at build time, use `ast` to cut the source of each referenced function out of the file. Embed it in the
bundle with the commit SHA, so the card shows the exact code without needing the repo.

## 4. Clickable element catalogue (what each card must show)

The minimum set. Every row is one card. "Figure" means a chart computed from data at build time or in the browser.

### 4.1 Inputs
| Element | Classification | Nodes | Card figure(s) and key content |
|---|---|---|---|
| Outdoor temperature, GHI, diffuse, beam | measured (beam = derived) | SRC-004, TR-005, DER-007, D-009, D-010, A-001 | Annual series; GHI vs diffuse scatter; QC table (1 missing diffuse hour, 1 negative beam hour clipped to 0 in TR-009); note on the end-of-interval → start-of-hour shift (D-009) and the KLO == HEAPO 8jB temperature check. |
| Electricity price | measured tariff (hourly mean = derived) | SRC-002, TR-007, DER-008, D-012 | Hour × weekday heatmap showing the two tiers (15.05 / 19.05 Rp/kWh); "excl. VAT and levies" caveat; QC (exactly 2 levels). |
| Carbon intensity | modeled | SRC-011, TR-010, DER-011, M-002, D-013/D-013a/D-013b, A-006..A-010 | Consumption vs domestic series; stacked imports by neighbour (columns `import_*_mwh`); EF table with proxy rows highlighted; proxy ±50 % band (46.8–69.4 mean); EPFL 2016-17 check (monthly overlay + scatter); flagged hours highlighted. |
| Building electricity (per building) | measured HP / other; **synthetic** MFH apartment composites; gap-filled hours synthetic | SRC-001/002, TR-001..004, TR-006, DER-001..005, D-006, D-008, D-011, D-015, `columns.json` | Stacked HP / other / common areas / synthetic apartments, with gap-filled hours (2023-10-29, SFH) hatched; selection-design summary (pool sizes 26 SFH / 59 MFH, median pick); gap-fill backtest figure (`backtest_gap_fill.json`). |
| Building selection | derived | DER-001..003, TR-003, `docs/data/building_selection_design.md` | Distribution of candidate annual kWh with the six picks marked. |

### 4.2 Models and environment
| Element | Classification | Nodes | Card figure(s) and key content |
|---|---|---|---|
| Heat-pump COP / thermal demand | derived (model M-001) | M-001, TR-008, DER-009, D-003, D-014..D-014e, D-016, A-002..A-005, parameter rows | **COP vs T_out curve** per building (COP = η·(T_sup+273.15)/(T_sup−T_out)) with calibrated η and T_sup; SPF targets vs achieved; warm-day baseline split figure (A-005); "linearity diagnostic NOT supportive" caveat from the QC report; Arpagaus et al. 2023 citation. |
| Thermal storage tanks | **synthetic** assumption | D-017, D-017a, `build_manifest.json` | Table of tank kWh_th per building and the sizing rule; link to the tank ×0.5 / ×2 sensitivity results. |
| HP nominal power | assumption | TR-009 (1.1 × peak electricity), `build_manifest.json`, `schema.json` | Peak measured electricity vs nominal power per building. |
| CityLearn environment | — | D-018, TR-009, DER-010, `schema.json` | Lists of active observations and actions, read from `schema.json`; stock classes only (CityLearn 3.3.0, commit 0eb78bc); placeholder indoor temperature caveat; V1 closure (simulated HP electricity within 1 % of measured). |

### 4.3 Control, reward, results
| Element | Nodes | Card content |
|---|---|---|
| Each controller ALG-001..004 (r = 0.05/0.10/0.20) | ALG-*, registry row, `run_baselines.py::tariff_map` | Plain description; for ALG-004 the 24-hour action map as a bar chart and the "weekends treated as weekdays" approximation; ALG-001 == ALG-002 note. |
| Reward R-001 | R-001, D-019, `rewards.py`, `reward_scales.json` | Formula with weights and scales; why there is no comfort term; per-term contributions over the year for the selected controller (from traces). |
| Each KPI number | EXP-*, the KPI definition | Formula. Mark clearly whether it is **our own computation** (`district_import_kwh`, `cost_chf_excl_vat`, ...) or a **CityLearn KPI normalised to the conventional counterfactual** (`kpi_*`, 1.0 = counterfactual, lower is better; see HANDOFF §4.1). The experiment row (git commit, versions, seed, status note). Comfort KPIs are NaN by design: say why. Drill-down: highlight the hours that drive it, e.g. the peak hour or the top 1 % of cost hours. |
| Sensitivity variants (eff0.99, flatcop, tank0.5, tank2) | `sensitivity_2023.csv`, dataset `build_manifest.json` per variant | Bars of % change vs zero-action per variant and controller. |
| Validation V1..V8 | `validation_phase_a.json` | Pass/fail table; each check expands to its numbers. |
| Open issues | ISS-* | Filterable list, also shown in context on every card that an issue affects. |

## 5. Layout and interaction

One page, top to bottom:

1. **Header.** Scenario selector (main + sensitivity variants; variants show aggregates only), controller selector,
   git SHA + dirty flag, MANIFEST check badge, "Trust overlay" toggle, global search box (type any ID such as `D-017a`
   to open its card).
2. **System map.** A hand-drawn SVG (owner decision; update it by hand when the model structure changes, e.g. Phase B), each box carrying a `data-ui` attribute that matches a `ui_map.yaml` key. Flow: Weather / Tariff / Carbon / Building loads → HP model (M-001) → Tanks →
   Grid ← Controller (ALG) → Reward (R-001) → KPIs. Each box is clickable and coloured by classification. This is the
   reviewer's entry point.
3. **Time series.** Stacked, x-synced panels (zoom one, all follow): carbon, price, outdoor temperature, district net
   load for the selected controller vs zero-action, tank SOC (per building, selectable), reward terms. Clicking a
   series opens its card. Clicking a point opens a small "this hour" popover with all inputs for that hour and their
   flags.
4. **KPI strip.** One tile per KPI, compared with ALG-001. Clicking a tile opens the KPI card (§4.3).
5. **Audit drawer (right side).** The single card template, in this order:
   - Title + classification badge + one-sentence summary (plain language)
   - Key numbers (templated from data)
   - Figure(s)
   - Lineage breadcrumb (clickable chain back to SRC-*)
   - Method: formula + embedded code excerpt (with commit)
   - Parameters table with citations
   - QC / validation results
   - Related decisions, assumptions, issues (each clickable; open issues shown in red)
   - Links to the full `.md` reports, and a CSV download of the series shown
   The drawer keeps a back/forward history so a reviewer can follow the lineage and return.
   It also supports deep links (`index.html#node=DER-011`) so a reviewer can send a link to one card.

**Trust overlay:** with the toggle on, series are drawn in their classification colour, and flagged hours (gap-filled,
interpolated, fallback, NaN set to 0) are shaded. The legend shows hour counts per flag.

Styling: neutral and print-friendly. Use one colour per classification, consistent across the map, series and badges.
Figures must be readable in a screenshot pasted into a report.

## 6. Run traces (change to `swiss/experiments/run_baselines.py`)

Add a `--traces` flag. When set, `rollout()` records one row per step and writes
`swiss/experiments/results/traces/<controller>.csv` (one file per controller, about 8,759 rows).

Columns (check the exact CityLearn 3.3.0 attribute names in the installed source before use; do not guess):
- `step`, `timestamp_utc` (from the canonical index), `price`, `carbon_intensity`
- per building `b{i}_`: `net_kwh`, `heating_device_kwh_el`, `dhw_device_kwh_el`, `heating_storage_soc`,
  `dhw_storage_soc`, `action_heating_storage`, `action_dhw_storage`, `heating_demand_kwh`, `dhw_demand_kwh`
- district: `district_net_kwh`, `reward`, `term_cost`, `term_peak`, `term_ramp`, `term_carbon`

Requirements:
- **No behaviour change.** With `--traces`, `baselines_2023.csv` must be byte-identical (or equal to 1e-9) to the
  committed version. Add a test for this. Sum the trace columns and assert they match the aggregate columns
  (`district_import_kwh`, `term_*_sum`, `reward_return`).
- Note that the script rewrites `reward_scales.json` and the results CSV each run. Diff them before proposing a commit.
- Traces for the sensitivity variants are optional (not needed for v1).
- Add the trace files to `docs/experiments/experiment_registry.csv` `output_location` (ask the owner first).

## 7. Build pipeline and files

```
swiss/dashboard/
  build_bundle.py      # reads §2 sources -> web/public/bundle/{provenance,meta,series_inputs,figures,results,trace_*}.json
  parse_registries.py  # markdown/CSV registry parsers + ID extraction
  figures.py           # precomputed figure data (COP curves, EPFL check, heatmaps, ...) as JSON for the chart lib
  ui_map.yaml          # the only hand-written mapping (§3)
  lint.py              # orphan / dangling-ID / placeholder checks; non-zero exit on failure
web/                           # Next.js UI (static export); see web/README.md
  src/app/                     # pages: Overview, Inputs, Model, Results, Audit
  src/components/              # audit card (sheet), district illustration, charts (ECharts), page components
  public/bundle/               # generated JSON; COMMITTED (owner decision) so Vercel builds without Python
swiss/tests/test_dashboard.py
```

Commands:
```bash
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py --traces
PYTHONPATH=. cl/bin/python -I swiss/dashboard/build_bundle.py
cd web && npm ci && npm run dev    # http://localhost:3000 (npm run build exports the static site to web/out)
```

Data size: keep the bundle at a few MB. Series are 8,760 points; send them as typed arrays in JSON, rounded to a
sensible number of digits. Do not inline the 15-min data.

Chart library: Plotly.js basic bundle, vendored (it covers line, bar, heatmap, scatter and synced zoom via relayout
events). uPlot is an acceptable lighter alternative if Plotly proves slow with many 8,760-point panels.

## 8. Acceptance criteria

1. `lint.py` passes. Every element in `ui_map.yaml` resolves to existing nodes, every ID mentioned in any card exists,
   every placeholder in a summary resolves, and every system-map box and KPI tile has a `ui_map` entry.
2. Every registry row (SRC, DER, TR, M, D, A, ISS, ALG, EXP, V) is reachable by search and opens a card.
3. From any series or KPI, the lineage breadcrumb reaches at least one SRC-* node, or explicitly ends in an
   assumption/decision (synthetic items such as the tanks).
4. Numbers shown in cards equal the source files. Test: pick 10 values (e.g. carbon mean 58.1, ALG-003 cost 35930.58,
   tank sizes, η values) and assert the bundle matches.
5. The header warns if the git tree is dirty or the MANIFEST does not verify.
   Because the bundle is committed, `meta.json` also stores a sha256 of every input file read. `lint.py --check-fresh`
   (also run in `test_dashboard.py`) fails if any input changed since the bundle was built, so a stale bundle cannot be
   committed unnoticed. The page shows the build commit and time.
6. Traces reproduce the aggregate results exactly (§6).
7. *(replaced, see Revision)* The built site works from any static server, offline.
8. Owner walkthrough: starting from the carbon curve, they reach the IPCC table, the EPFL check and the code in at
   most 3 clicks. The same holds for the COP model and the tank assumption.

## 9. Milestones (each ends with a short demo to the owner)

1. **Parsers + provenance graph + lint** (no UI). Output: `provenance.json`, with counts printed per node kind.
2. **Audit drawer + search** over the graph (the card template, lineage, code excerpts, deep links). This is useful on
   its own as a registry browser.
3. **Inputs time series + trust overlay + input cards** (weather, tariff, carbon, building loads).
4. **Model figures** (COP curves, carbon import stack + EPFL check, tank and HP sizing, gap-fill backtest).
5. **Run traces** (§6) + controller selector + KPI strip + KPI drill-down + reward-term view.
6. **System map** + sensitivity panel + validation table + polish for reviewers.

## 10. Out of scope / traps
- Do not modify CityLearn or the canonical data. The dashboard only reads.
- Do not change the venv pins (`numpy<2`, `pandas<3`, `torch 2.2.2`). Add no Python dependencies without asking.
- Do not re-run the data pipeline (`swiss/run_pipeline.sh`) or download anything as part of this work.
- `my_data/` (US cooling experiments) is out of scope.
- Comfort KPIs are NaN by design (no thermal dynamics, D-018). Show "not applicable" with the reason, not an error.
- ALG-001 and ALG-002 give identical results on this dataset. That is expected, not a bug.
- Carbon is modeled, and its level is about 62 % of the EPFL reference. The card must say so prominently. The
  dashboard must not present it as measured.
- Ask the owner before committing or pushing (HANDOFF §8).
