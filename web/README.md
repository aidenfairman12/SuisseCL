# SuisseCL Phase A — audit dashboard (web UI)

Next.js static export that shows where every number of the Swiss Phase A simulation comes from. It holds no facts of
its own: it only reads `public/bundle/*.json`, which the Python side generates from the repository's registries, QC
reports, canonical data and results.

```bash
# from the repository root: regenerate the bundle (only when registries, data or results change)
PYTHONPATH=. cl/bin/python -I swiss/dashboard/build_bundle.py
PYTHONPATH=. cl/bin/python -I swiss/dashboard/lint.py --check-fresh   # 0 errors expected

# the UI
cd web
npm ci
npm run dev      # http://localhost:3000
npm run build    # static site in web/out (type-check included); npm run lint
```

- Pages: Story (home, with the illustrated district), Inputs, Model, Results, Audit, Glossary. The audit card opens as a side sheet; `?node=ID` deep-links to a card.
- Two data sources: the audit bundle (`public/bundle/*.json`, built by `swiss/dashboard/build_bundle.py`) and the **data contract v1** (`public/bundle/sim/`, built by `swiss/contract/export_v1.py`; types and hooks in `src/lib/contract/`, spec in `docs/dashboard/data_contract_v1.md`).
- Hand-written mapping of UI elements to registry nodes: `swiss/dashboard/ui_map.yaml`. `lint.py` fails if the UI opens a
  card that has no entry there, names an unknown figure or KPI column, or if the bundle is older than its inputs.
- Bundle committing rule: build the bundle on a **clean, committed** tree and commit it in a second commit, so the header
  shows "clean tree" for that snapshot.

## Hosting on Vercel (public, decision D-020)

The site is **public on purpose** (owner decision 2026-11-17): https://suisse-cl.vercel.app/ and every file under `/bundle/` can be opened and downloaded without a login.
Write every page as if anyone may read it. This replaces the earlier private-only plan (Vercel Authentication). The unlicensed source JASM (SRC-003, D-004) is not
used anywhere: no pipeline code, model or dashboard item depends on it, and none of its files are tracked in git.

What the public bundle contains:
- hourly data derived from HEAPO and ETH/EKZ (CC BY 4.0), MeteoSwiss data (cite "Source: MeteoSwiss") and Energy-Charts data (attribution "energy-charts.info"). The footer shows each source's licence text from the registry;
- aggregate statistics from the EPFL carbon series (dataset CC BY 4.0, article CC BY-NC-ND);
- work in progress that is not validated: a modeled carbon series (about 61-62 % of the EPFL reference level, shown only as relative values), assumed storage tanks, and the list of open issues.

Licence checks done 2026-11-17 (public documentation read; **not a legal review**): MeteoSwiss open data is CC BY 4.0 (commercial use, redistribution and derived data allowed;
cite the source and do not imply endorsement); Energy-Charts is CC BY 4.0 with attribution "energy-charts.info" for the endpoints and countries used (not the restricted day-ahead prices).

**Open compliance items now that the site is public** (none is solved by the hosting choice):
1. CC BY expects a link to the licence and a note that the data was changed; the footer gives publisher and licence text but not yet links or the change note.
2. The EPFL article is CC BY-NC-ND: show only aggregate statistics from the dataset (CC BY 4.0), never reproduce the article.
3. Vercel Hobby is for non-commercial use only.
4. Whether unvalidated work in progress should stay visible is the owner's call; the dashboard labels it as such.

Deployment settings: Root Directory `web`; Framework Preset Next.js; build command `npm run build`; default install; Production Branch `main`; no environment variables (static export, no server code).
Merging to `main` redeploys production; pull requests get preview deployments.

**Stale-bundle risk.** Vercel never runs Python, so a stale bundle deploys without warning. Before merging, regenerate the bundles on a clean committed tree and commit them
(`build_bundle.py`, `export_v1.py`), then run `lint.py --check-fresh` and `npm run build`.
