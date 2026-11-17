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

- Pages: Overview, Inputs, Model, Results, Audit. The audit card opens as a side sheet; `?node=ID` deep-links to a card.
- Hand-written mapping of UI elements to registry nodes: `swiss/dashboard/ui_map.yaml`. `lint.py` fails if the UI opens a
  card that has no entry there, names an unknown figure or KPI column, or if the bundle is older than its inputs.
- Bundle committing rule: build the bundle on a **clean, committed** tree and commit it in a second commit, so the header
  shows "clean tree" for that snapshot.

## Hosting on Vercel (private only)

Default to private until the checks below are done. This is **not** about JASM: that unlicensed source (SRC-003, the
subject of D-004) is not used anywhere. No pipeline code, transformation, model or dashboard item depends on it, and none
of its files are tracked in git. What the dashboard does contain:

- hourly data derived from HEAPO and EKZ (CC BY 4.0), MeteoSwiss data (citation "Source: MeteoSwiss" required) and
  Energy-Charts data (attribution "energy-charts.info" required). The footer shows each source's licence text from the registry;
- aggregate statistics from the EPFL carbon series (dataset CC BY 4.0, article CC BY-NC-ND);
- unvalidated work in progress: a modeled carbon series whose level is about 61–62 % of the EPFL reference, and the open issues.

Before a public URL, still to check (all recorded in the registry as unverified): the MeteoSwiss terms-of-use page was not
read, and the Energy-Charts per-response licence field has not been checked. This is not a legal review.

1. **Team default first (recommended).** In the Vercel team's settings, set the Deployment Protection default to
   **All Deployments** with **Vercel Authentication**, so a new project is never public, not even for its first deploy.
2. **Import** the private GitHub repository (grant the Vercel GitHub app access to this repository only).
3. **Project settings:** Root Directory `web`; Framework Preset Next.js; build command `npm run build`; install command
   default; Production Branch `main`; no environment variables (static export, no server code).
4. **Protect:** *Settings → Deployment Protection* → Vercel Authentication **on**, scope **All Deployments**.
   Do **not** use *Standard Protection*: it leaves the production domain (`<project>.vercel.app`) public.
   Password Protection is not available on Hobby (Pro: $20 per month per project); Passport and Trusted IPs are Enterprise.
5. **Prove it:** in a private window while logged out, open the production URL and
   `curl -I https://<project>.vercel.app/bundle/provenance.json` (the data files are static assets): expect a login
   redirect or 401, never 200. Repeat on one per-deployment URL.
6. **Access:** viewers need a Vercel login with access to the project (team member/viewer, or an access request you
   approve). On Hobby only one external user per account is allowed. A Shareable Link bypasses the login for anyone who has it.

Updating: merging to `main` redeploys production; pull requests get protected preview deployments. Vercel never runs
Python, so run `build_bundle.py` and `lint.py --check-fresh` locally and commit the bundle before merging, or the site
will show stale numbers.
