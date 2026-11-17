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

The bundle contains hourly data derived from the HEAPO and EKZ meters, and the JASM data may be used only while the
project stays private (D-004). A public URL counts as publishing, so **do not deploy without access protection**.

1. In Vercel, import the (private) GitHub repository.
2. Settings: **Root Directory** `web`, Framework Preset **Next.js** (auto-detected), install command `npm ci`,
   build command `npm run build`. No environment variables are needed; no server code runs (`output: "export"`).
3. Before the first production deploy, turn on protection under *Settings → Deployment Protection* (Vercel
   Authentication, or Password Protection if your plan offers it) for **Production** as well as previews.
4. After deploying, open the production URL in a private window while logged out and confirm it is blocked.
