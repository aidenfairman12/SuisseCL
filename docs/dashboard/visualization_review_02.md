# Review 02 of the visualization branches — from the simulation workstream

Reviewed 2026-11-17 against contract v1 (`contract/v1-draft` at 40d0fef) and the repository's audit guards.

## Which branch
- `visualization/district-redesign` (22 commits, head c2f362c) still reads the OLD bundle and still fails the lint with the same 4 errors as in review 01. It is superseded.
- **`visualization/district-redesign-contract` (head 78014b9) is the one to merge.** It is built on contract commit 5475c60, changes only `district-view.tsx`, `scene.tsx` and
  `building-cutaway.tsx` (no overlap with the simulation side) and **merges cleanly** into `contract/v1-draft` (checked with a trial merge).

## Results on `visualization/district-redesign-contract`
`lint.py --check-fresh`: **0 errors** (review 01 blocker closed). `tsc`: clean. ESLint: 0 errors, 1 warning (`hpLabel` is assigned but never used in `building-cutaway.tsx`).

## Review 01 items
| # | Item | Status |
|---|---|---|
| 1 | Bare building codes | **Fixed**: default selection from `manifest.buildings`, names from `buildings.<id>.display_name`, branching on contract attributes |
| 2 | Hot-water tank of SFH-mid / SFH-high hidden | **Fixed**: tank drawn from `components.tank_hw.present`; the electric water heater is a separate note from the `water_heating` attribute |
| 3 | "Domestic hot water" wording | **Fixed**: "Hot-water / base-load", "hot water and other base load" |
| 4 | "Electricity from the grid" showed heat-pump electricity only | **Fixed**: grid electricity (`net_kwh_el`), heat-pump electricity (sh + hw) and household electricity are separate, household with its provenance |
| 5 | Static thermal arrows | **Open**: see below |
| 6 | Missing tank drawn as empty | **Fixed**: absent tank is drawn as "Not present"; `null` soc shows "—" |
| small | `district_note` on the scene | **Fixed** (shown under the timeline); carbon shown as a relative rank only |

## Still open
1. **The heat-flow arrows are drawn by presence, not by value.** The dashed paths appear whenever a component exists, whatever the step; the flow values are only in the side table.
   Spec §4.7 wants inactive flows shown as inactive, and the caption "flows are model outputs" overstates what the arrows show. Use `hp_sh_direct_kwh_th`, `hp_sh_to_tank_kwh_th`,
   `sh_tank_to_demand_kwh_th` (and the `hw` ones) and the tank mode: dim or stop the arrow at 0, scale width or speed with the value (`meanKw` for power).
2. **Two data sources in one view.** `district-view.tsx` still reads `figures.district.buildings` (old bundle) for the scene geometry (`area_m2`, `units`, `type`). The same values are in
   `buildings.<id>.attributes` (`floor_area_m2`, `housing_units`, `type`); using them would let the old `figures` dependency go.
3. **`water_heating` is matched as free text** (`includes("electric water heater")`). It works today; I can add a boolean contract attribute if you want a flag instead (tell me).
4. **Data length:** the full year is now available in `web/public/bundle/sim_full/` (D-028). Pass `"full"` as the last argument of the hooks to use it, one controller run at a time (about 10 MB each). With the full year the 500 ms playback step
   and the "Window start / Window end" buttons will need a rethink (a year is 8,759 steps), and the earlier jumps (coldest hour, highest grid draw) can come back from `situations` tags and `comparisons`.
5. Minor: show the tariff with its basis ("excl. VAT"); label tank values "assumed" wherever a capacity is shown (already done in the side panel).

## Merge order
1. `contract/v1-draft` → `main` (pull request not opened yet; owner decision).
2. `visualization/district-redesign-contract` rebased on `main` (or merged), after fixing the `hpLabel` warning.
3. `visualization/district-redesign` can be closed.
