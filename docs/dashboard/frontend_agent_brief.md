# SuisseCL — brief for the frontend / visualization agent

From: the simulation and architecture workstream · Date: 2026-11-17 · Status: draft for the project owner to forward

This brief goes with the owner's "Dashboard Redesign — Implementation Specification". The specification sets the visual
and UX direction. This brief covers what the simulation actually provides, the rules every displayed value must follow,
who owns which files, and how the two workstreams stay out of each other's way.

If the specification, the mockup image and this brief disagree about **what is modeled or what a value is**, this brief
wins: it was written from the repository, not from the illustration. On **look and feel**, the specification wins.

---

## 1. How the system fits together (today)

```
data/canonical/*  ──►  swiss/citylearn_build  ──►  CityLearn 3.3.0 runs  ──►  swiss/experiments/results/*
                                                                                     │
docs/ registries, ui_map.yaml  ───────────────►  swiss/dashboard/build_bundle.py  ◄───┘
                                                          │  (Python, run locally)
                                                          ▼
                                             web/public/bundle/*.json   (committed)
                                                          │  fetch("/bundle/<name>.json")
                                                          ▼
                                             web/  Next.js 16 static export → Vercel
```

- **There is no backend or API.** The UI reads static JSON from `/bundle/`, through `useBundle()` /
  `useBundleFile()` in `web/src/lib/bundle.tsx`. This stays the delivery model (owner decision, 2026-11-17).
- **The UI holds no facts of its own.** Every number, label, citation and status comes from the bundle.
  `swiss/dashboard/lint.py` and `swiss/tests/test_dashboard.py` enforce this by scanning `web/src`.
- The site is publicly reachable at https://suisse-cl.vercel.app/ on purpose. Write every page as if anyone may read it.
- Stack: Next.js 16.4 (App Router, `output: "export"`), React 19, Tailwind 4, shadcn/base-ui, ECharts. **Read
  `web/AGENTS.md` first**: this Next.js version has breaking changes, and its docs are in `web/node_modules/next/dist/docs/`.

---

## 2. File ownership

| Owner | Paths |
|---|---|
| **Frontend agent (you)** | `web/src/app/**`, `web/src/components/**`, `web/src/app/globals.css`, new visual assets under `web/public/assets/**`, frontend dependencies in `web/package.json` (and the matching lockfile change) |
| **Simulation agent** | `swiss/**`, `data/**`, `docs/**` (except this brief and the design spec), `web/public/bundle/**` (generated, never hand-edited), the new `web/src/lib/contract/**` (types and loader for the new data contract) |
| **Shared — change by agreement only** | `swiss/dashboard/ui_map.yaml`, `web/src/lib/types.ts`, `web/src/lib/bundle.tsx`, `web/src/lib/names.ts`, `web/src/lib/deeplink.ts`, `swiss/dashboard/lint.py`, `swiss/tests/test_dashboard.py`, `README.md`, `web/README.md` |

Rules:
1. **Never commit `web/public/bundle/`** from a frontend branch. Only the simulation agent regenerates it, on `main`,
   in its own "Rebuild dashboard bundle" commit after merges.
2. **Do not edit `swiss/**` or `data/**`.** If you need a value the bundle does not have, request it (section 7).
   Do not compute it in the browser.
3. **`ui_map.yaml`:** you may add new UI keys, labels and plain-language prose for new elements. You may not change
   placeholder data paths, registry node lists or classifications. Every new clickable element needs a `ui_map.yaml`
   entry, or the lint fails.
4. Work on your own branch or worktree. Run the checks in section 8 before every PR.
5. Treat `types.ts` as frozen for the existing bundle files. New data types arrive in `web/src/lib/contract/`.

---

## 3. The six buildings: what is actually known

IDs are fixed (owner decision). Use `SFH-mid`, not "SFH-medium". Never show the bare ID as a visible label: the lint
rejects role codes in UI source. Use the display names from `story.json → buildings`, via `useNames().building(role)`.

| ID (CityLearn name) | Display name (from `ui_map.yaml`) | Known attributes (measured metadata) | Source |
|---|---|---|---|
| `SFH-low` (Building_1) | Single-family house (low use) | 220 m², 4 residents, floor heating, air-source heat pump | HEAPO household 7069411 |
| `SFH-mid` (Building_2) | Single-family house (medium use) | 166 m², 4 residents, floor heating, air-source heat pump | HEAPO 8011310 |
| `SFH-high` (Building_3) | Single-family house (high use) | 260 m², 2 residents, floor heating, air-source heat pump | HEAPO 1181060 |
| `MFH-small` (Building_4) | Apartment building (small) | 5 housing units | EKZ heat-pump meter 154832 |
| `MFH-medium` (Building_5) | Apartment building (medium) | 14 housing units | EKZ 145442 |
| `MFH-large` (Building_6) | Apartment building (large) | 24 housing units | EKZ 197873 |

- "Low / medium / high use" means the 2023 **measured heat-pump electricity**, not size. SFH-high is not the largest
  house in any sense the visuals should exaggerate. Scale houses by floor area, apartment blocks by housing units.
- **Not known for any building:** number of floors, apartment-building floor area, construction year, insulation,
  room layout, radiator types, roof type, PV. Visual details for these are illustrative only and must not be labelled
  or implied as data.
- **Apartment buildings:** only the heat-pump meter is measured. Their household electricity is a **synthetic**
  composite of other EKZ apartments (it does not come from these buildings). The heat-pump type (air or ground) is unknown.
- The six form a **constructed composite district**: different real buildings, from two datasets, placed together.
  The scene must not imply they are neighbours, share a grid connection or exchange energy. Call it "a representative
  Swiss residential development". There is no local grid, transformer, heat network or energy sharing in the model.
- Building metadata already in the bundle: `figures.json → district.buildings[]` (type `DistrictBuilding` in
  `types.ts`). It has area, residents, units, tank capacities, heat-pump sizes, supply temperature, source IDs, an
  `apartments_synthetic` flag and gap-filled hours.

---

## 4. What the simulation models in Phase A (and what it does not)

Per building, per hour, for the local year 2023 (8,760 hours):

```
Grid ──electricity──► Heat pump (space heating) ──heat──► Heating tank ──heat──► Space-heating demand
                                               └──heat (direct)──────────────────────────────► Space-heating demand
Grid ──electricity──► Heat pump ("DHW device") ──heat──► Hot-water tank* ──heat──► "Hot water and other heat-pump base load"
Grid ──electricity──► Household electricity (non-shiftable)
Inputs (not energy sources): outdoor temperature, electricity price, grid carbon intensity (relative only)
* SFH-low has no hot-water tank.
```

**Modeled and can be shown:** grid electricity, heat pumps (efficiency changes with outdoor temperature), a heating
tank in all six buildings, a hot-water tank in five, space-heating demand, the heat-pump base load, household
electricity, weather, tariff, relative carbon intensity, controller actions, and district totals.

**Not modeled — never show these as working, and never as zero:**
- Indoor temperature, comfort, or unmet heat. Demand is always met. The 21 °C in the data is a placeholder, not a result.
- PV, batteries, EVs, local energy communities, dynamic tariffs, cooling (Phase B/C). They may appear only as
  "future phase / not modeled".
- Pipes, radiators, rooms, which floor the equipment sits on, and any heat moving between buildings.
- Real weather forecasts. Absolute carbon emissions (see 5.4).

**Thermal storage is synthetic.** Tank sizes, efficiency (0.95) and loss rate (0.3 %/h) are assumptions (D-017a).
Every controller difference depends on them, so the cutaway and the Results page should say so.

---

## 5. Display rules (enforced or required)

### 5.1 Provenance classes (owner decision 2026-11-17)
Four data classes: **Measured**, **Derived**, **Modeled**, **Synthetic**. Assumed parameters (tank sizes, supply
temperatures, tank efficiency) get a separate **"assumed parameter"** badge. Classify by how a value was obtained:

| Value | Class |
|---|---|
| Outdoor temperature, irradiance | Measured (MeteoSwiss, Zurich-Kloten) |
| Electricity tariff | Registry class `measured`, but it is a published price schedule (EKZ standard 2023), not a metered quantity: label it as a tariff with its source |
| Heat-pump electricity, SFH household electricity | Measured |
| Apartment-building household electricity | **Synthetic** |
| Heating demand, hot-water/base-load demand | **Derived** (measured electricity × modeled efficiency; heat timing unvalidated) |
| Heat-pump efficiency (COP) | Modeled |
| Storage state of charge, controller decisions, district totals | Modeled (simulation output) |
| Tank sizes, efficiencies, supply temperatures | Assumed parameter |
| Grid carbon intensity | Modeled, **relative only** |
| One 24-hour gap on 2023-10-29 in the three houses | Synthetic (gap-filled); flagged in `series_inputs.buildings[*].gap_filled_flag` |
| Floor area, residents, housing units | Measured metadata |

The bundle's `provenance.json` currently uses six labels (it adds `assumption` and `mixed`), with colours in
`provenance.settings.classification_colours`. The new contract will map these to the four classes plus the badge.
Until then, map `assumption` → assumed-parameter badge, and treat `mixed` as "see details".

### 5.2 Hot water wording (owner decision)
The series named `dhw_demand` is **"hot water and other heat-pump base load"**, not pure hot water. It is the heat
pump's warm-weather baseline, which may include other uses (SFH-high has an unexplained ~10 kWh/day in summer).
- SFH-mid and SFH-high heat water with **electric water heaters**. That electricity sits inside household
  electricity, not in the heat pump.
- SFH-low has **no hot-water tank**. The old trace shows its tank state of charge as constant 0. Display it as
  **"not present"**, never as "0 %".

### 5.3 Energy vs power
- Every time-series value in the traces is **kWh per hourly step**. Over one hour, that equals the mean kW, which
  is why kW and kWh look numerically the same today. Phase B uses 15-minute steps, where they differ by a factor of
  4. **Always convert with the step length** (`series_inputs.step_s`, and `manifest.step_seconds` in the new contract).
  Never assume they are equal.
- Label electricity and heat separately: **kWh_el / kW_el** vs **kWh_th / kW_th**. Use different colours for
  electricity and heat flows everywhere (the district scene already uses `elec` amber and `heat` orange/`dhw` teal in
  `scene.tsx`, so keep or deliberately replace that convention across all pages).
- District peak (kW) and total energy (kWh) are different questions. Never put them on one axis.

### 5.4 Carbon (enforced by lint)
The modeled carbon series is about 61–63 % of the EPFL reference level, so **only relative statements are allowed**
outside the carbon audit card and the Inputs tab:
- No "g/kWh", "gCO2", "g CO₂" in UI source or prose (the lint rejects it).
- Do not read `series.carbon` / `series.carbon_domestic` directly. Use `carbonRelative(si, story, i)` from
  `components/charts/util.ts` (a "cleaner / dirtier than usual" rank).
- Carbon results are changes against "No control", never absolute tonnes, and never a headline claim.
- **The mockup's "95 gCO₂/kWh" tile is not allowed.**

### 5.5 Unavailable vs zero
`null` (or a component with `present: false`) means **not available / not modeled**: show "—" or "not present"
with a reason. `0` is a genuine zero (for example, the heat pump is off). Never fill missing values.

### 5.6 Numbers in prose
Do not write numbers into JSX text or prose. Numbers in UI copy come from bundle values. Prose in `ui_map.yaml` uses
`{placeholders}` only (the lint rejects stray digits). The "What is happening?" explanation must be built from data
for the selected hour (section 6.3).

---

## 6. Data available to you

### 6.1 Today (existing bundle, stable until the contract replaces it)

| File | What it holds |
|---|---|
| `meta.json` | Build time, git commit, dirty flag, manifest check, input hashes |
| `provenance.json` | The audit graph: every registry node with its classification, lineage, code excerpts and QC. Open cards with `useNodeParam().open(id)` |
| `story.json` | Display names (controllers, buildings), glossary, all story-page prose, the relative-carbon wording |
| `series_inputs.json` | 8,760 hourly values: `temp_c`, `ghi`, `diffuse`, `beam`, `price` (Rp/kWh), carbon (relative use only), `carbon_rank`, `tier_high`, `local_hour`, `weekday`, `utc_offset_h`; per-building input components and gap flags |
| `figures.json` | `district.buildings[]` (building metadata), `env_interface` (active observations and actions), model figures, sensitivity variants |
| `results.json` | One row per controller with district KPIs (`district_import_kwh`, `district_peak_kw`, `cost_chf_excl_vat`, `mean_daily_peak_kw`, `high_tariff_import_share`, `ramping_sum_kw`, `reward_return`, CityLearn `kpi_*`), sensitivity rows, the `traces` index (`same_as` = identical run) |
| `trace_<controller>.json` | **8,759** steps (CityLearn does not simulate the last hour). District: `district_net_kwh`, `reward`, `term_*`. Per building `b1…b6` (index = position in `district.buildings`): `_net_kwh`, `_hp_kwh_el` (both heat pumps combined), `_heating_storage_soc`, `_dhw_storage_soc` (0–1), `_action_heating_storage`, `_action_dhw_storage` |

Gotchas:
- Inputs have 8,760 steps and traces 8,759. Clamp the timeline to the trace length when showing run values.
- "Business as usual" (ALG-002) is identical to "No control" in this district. Its trace is `same_as` ALG-001. Say so;
  don't present it as a separate behaviour.
- Controllers available: No control, Business as usual, Night-charging rule, and Tariff-timed rule (gentle / medium /
  strong). There is **no learning (RL) controller yet**.
- Tariff: two tiers, 15.05 and 19.05 Rp/kWh excl. VAT (EKZ standard 2023), high on weekdays 07:00–20:00 local.
  **The mockup's "CHF 0.28/kWh" is not from the data.** Read the price from `series_inputs`.
- Building series are keyed by **position** (`b1`…`b6`), not ID. Map them through `figures.district.buildings[i].role`.
  The new contract fixes this.
- Not in the current bundle: heating demand, base-load demand, the split of heat-pump electricity into space
  heating and hot water, household electricity per step, heat output, tank charge and discharge flows, and
  per-building cost. **Do not reconstruct these in the browser.** They are provided by contract v1 (6.2).

### 6.2 Contract v1: available now as a sample (`web/public/bundle/sim/`)
The contract is specified in **`docs/dashboard/data_contract_v1.md`** (read it before building the District page). Machine-readable
schemas are in `swiss/contract/schema/`, TypeScript types and hooks in `web/src/lib/contract/` (`useManifest`, `useBuildings`,
`useComponents`, `useConditions`, `useRun`, `useComparisons`, plus `meanKw` for power). It supersedes the draft field names this
brief listed earlier (for example `hp_dhw_*` is now `hp_hw_*`, "hw" = hot water and other base load).

The current files are a **48-hour sample** (Monday 2023-12-04 and the following day, the coldest weekday of 2023) with all six
controllers, produced from real CityLearn rollouts. The full year will use the same files and schema (`--full`), so build against the
sample and read the length from `scope.n_steps`. Every variable's label, unit, provenance and source IDs are in `manifest.variables`;
show the label, never the field id.

Do not reconstruct anything physical in the browser: heat flows, tank losses, tank mode, situation tags and comparison
mechanisms are all in the files. If a field you need is missing, request it (section 7).

### 6.3 "What is happening?" text
Build it from `situations` tags and the values of the selected hour, using text templates whose numbers are inserted
from data. Only claim a mechanism the data shows. Example: "stored heat is covering part of the demand" only when
the tank discharge flow for that hour is above zero. Until `situations` exists, keep the explanation out or clearly
marked as a placeholder. Do not ship fixed sentences that ignore the hour.

---

## 7. How to request data or changes

- Need a field, unit or file that isn't in the bundle or contract? Ask the owner to pass a request to the simulation
  agent. Give: page/component, the question it answers, the field, unit, and per-step or summary.
- Never add a hardcoded stand-in "for now". Use a visible "data not yet available" state.
- Changes to shared files (section 2) go through the owner, so both agents know before either edits them.

---

## 8. Checks before every PR

From the repository root (Python environment in `cl/`):

```bash
PYTHONPATH=. cl/bin/python -I swiss/dashboard/lint.py --check-fresh
```

```bash
PYTHONPATH=. cl/bin/python -m pytest swiss/tests/test_dashboard.py -q
```

```bash
cd web && npm run lint && npm run build
```

Expected: lint 0 errors (17 known warnings are registry-parsing repairs), tests green, `next build` succeeds.

The lint fails the build when UI source:
- contains a bare building ID (`SFH-low` etc.) or feeds a role variable into a visible label;
- shows an absolute carbon unit or reads the carbon series outside the two allowed files;
- opens an audit card, KPI column or figure that has no `ui_map.yaml` entry;
- has prose with digits outside `{placeholders}`, or registry IDs in story prose.

---

## 9. Corrections to the mockup image

The mockup is a mood reference only. These elements must not be built as shown:

| Mockup | Use instead |
|---|---|
| "Building 3 — Apartment, 4 floors, 820 m²" | Building_3 is SFH-high: a house, 260 m², 2 residents. No floor counts exist |
| Solar panels on roofs | No PV in Phase A. Plain roofs, or PV clearly marked as a future phase |
| "95 gCO₂/kWh" | Relative wording only ("cleaner / dirtier than usual for this year") |
| "CHF 0.28/kWh" | The hour's actual tariff from the data (15.05 or 19.05 Rp/kWh excl. VAT) |
| "Measured: Weather, Tariff" / "Assumed: building characteristics" | Weather measured; tariff a published price schedule; floor area, residents and units measured metadata; tanks assumed |
| "DHW Storage 65 %" for any house | SFH-low has no hot-water tank; label the tank "hot water and base load" |
| "Heating Demand 28 kW", "Heat Pump Power 7 kW" | Live values from the run for the selected hour, labelled kW_th and kW_el |
| Cars, church, lake, mountains, roads | Fine as scenery, as long as nothing suggests shared infrastructure or a real location |
| Phase selector "Phase A ▾" | Only if Phase B/C are shown as "not yet available" |

---

## 10. Open items you should know about

- Thermal timing (when heat is needed within a day) is **unvalidated**: there is no measured heat or indoor temperature.
- The heating tank is small in houses (about 3.5 kWh_th) and the hot-water/base-load tanks vary widely
  (`figures.district.buildings[].dhw_tank_kwh_th`). Fill levels swing fast, so show them honestly, not smoothed.
- Results so far: the rule-based controllers shift 1.9–4.4 points of electricity out of the high tariff, but **raise
  cost by 0.15–1.1 % and carbon by 1.7–2.4 %** in every sensitivity variant (storage losses outweigh the tariff gap).
  The story should explain this trade-off, not hide it. Read the numbers from the bundle, not from this brief.
- RL controllers are planned (Phase A environment, after the contract and experiment tracking). Design controller
  selection to take more controllers and, later, several seeds per controller.
