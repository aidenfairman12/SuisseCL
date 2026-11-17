# Review 01 of `visualization/district-redesign` (head 329c982) — from the simulation workstream

Reviewed 2026-11-17 against contract v1 and the repository's audit guards. The branch builds on `contract/v1-draft` (0ddca2e).
Scope reviewed: `district-view.tsx`, `scene.tsx`, `building-cutaway.tsx` (the only files it changes). Nothing outside them was touched.

## Verdict
Good direction, not mergeable yet: **1 blocking gate failure** and **5 model-accuracy problems**, all in the cutaway/panel.
`tsc` and ESLint pass. `swiss/dashboard/lint.py --check-fresh` reports **4 errors** (0 on `contract/v1-draft`).

## What is right (keep)
- Building size is driven by `area_m2` (houses) and `units` (apartment buildings), never by energy use. Matches spec §4.3.
- Names come from the bundle (`names.building`); buildings are keyboard-selectable buttons with accessible labels.
- No PV, no absolute carbon, no invented building attributes. Apartment cutaway is labelled "schematic floors", the panel carries a
  "Representative building model" badge, and tank parameters are marked "assumed".

## Blocking (CI gate: `swiss/dashboard/lint.py`)
1. **Bare building codes in source.** `district-view.tsx` has `useState("SFH-low")`; `building-cutaway.tsx` branches on
   `role === "SFH-mid" || role === "SFH-high"` and puts `${building.role}` into an `aria-label`.
   Fix: default to the first entry of `manifest.buildings` (or the first of `figures.district.buildings`); never branch on a role code
   (use contract attributes, item 2); use the display name in labels.

## Model accuracy (these would mislead a reader)
2. **The hot-water tank of SFH-mid and SFH-high is hidden and replaced by an "Electric water heater" note.** In the model both buildings
   DO have a modeled second heat-pump device and a tank for the hot-water/base-load demand (about 3.7 and 24.3 kWh_th). Their electric
   water heater is a separate thing: its electricity sits inside household electricity and is not drawn as a component (D-014a, D-022).
   Fix: draw the tank when `buildings.<id>.components.tank_hw.present` is true (false only for the first low-use house); show the water-heater
   note from the building attribute `water_heating` (when `available`), not from a role check.
3. **"Domestic hot water" and "Hot water" labels.** The series is **hot water and other heat-pump base load** (D-014e, D-022). Use the
   label from `manifest.variables` (`hw_*`), not the word "domestic".
4. **"Electricity from the grid" shows heat-pump electricity only.** Grid electricity also includes household electricity. Show
   `hp_sh_kwh_el + hp_hw_kwh_el` under "Heat-pump electricity", and `net_kwh_el` as grid electricity, with household electricity separate
   (`household_kwh_el`; measured for houses, synthetic for apartment buildings).
5. **The thermal arrows are static.** The cutaway draws fixed arrows, whereas spec §4.7 wants flows driven by the simulation and inactive
   components shown as inactive. The contract has the flows: `hp_sh_direct_kwh_th`, `hp_sh_to_tank_kwh_th`, `sh_tank_to_demand_kwh_th`
   (and `hw` equivalents), plus `sh_tank_mode` (charging / discharging / idle). Animate or dim by the value at the selected step (0 = inactive).
6. **Missing tank vs empty tank.** `dhwFill = socDhw ?? 0` draws an empty tank when data is missing. In the contract an absent tank is a `null`
   series; draw no tank (and say "not present"), never an empty one.

## Smaller
- Panel text such as "Combined devices in current trace" exposes internal jargon; use the variable labels.
- The scene caption should carry `manifest.district_note` (the six buildings are a constructed composite, not neighbours; spec §4.2).
- Add provenance badges to the panel values (`manifest.variables.building.<id>.provenance`; `household_kwh_el` differs for SFH and MFH).

## Data source: the branch still reads the OLD bundle
It uses `figures`, `series_inputs`, `results` and `trace_*`; it does not use `web/src/lib/contract/`. Items 2, 3, 4, 5 and 6 need contract
fields (separate heat-pump electricity, heat flows, tank presence, tank mode) that the old bundle does not have. The contract is
available now as a 48-hour sample (`/bundle/sim/`, Monday 2023-12-04 and the following day).

**Decision (project owner, 2026-11-17): build against the 48-hour sample first.** Consequences for the visualization work:
- Read the timeline length from `scope.n_steps` and the clock from `conditions.timestamps_utc`; do not hardcode 48 or a year, because the
  full-year export (same files, same schema, `export_v1.py --full`) replaces the sample later without a code change.
- Until then the District timeline covers these 48 hours only. The old "coldest hour / highest grid draw / a winter night" jumps still need
  the old bundle; either drop them for now or keep them reading the old bundle behind a clearly separate code path.
- The full year is about 10 MB raw (2.6 MB gzipped) per controller run and 56 MB raw for all six; it will be committed together with the
  removal of the old `trace_*` files once the frontend has migrated.

## Merge order proposed
`contract/v1-draft` merges to `main` first (it adds new files, appends seven rows to `decision_log.md`, changes one row-count in `test_dashboard.py`, and carries the rebuilt dashboard bundle);
`visualization/district-redesign` then rebases onto `main` and the lint must pass before its pull request.
