# SuisseCL Phase A — audit dashboard

Static page: open `index.html` directly (works offline from `file://`) or serve the repo root with
`cl/bin/python -I swiss/dashboard/serve.py` and open <http://127.0.0.1:8000/dashboard/> (links to `docs/*.md` then work too).

Everything shown comes from `bundle/*.js`, generated from the repo's registries, QC reports, canonical data and results:

```bash
PYTHONPATH=. cl/bin/python -I swiss/experiments/run_baselines.py --traces   # only when results change
PYTHONPATH=. cl/bin/python -I swiss/dashboard/build_bundle.py
PYTHONPATH=. cl/bin/python -I swiss/dashboard/lint.py --check-fresh
```

- `swiss/dashboard/ui_map.yaml` is the only hand-written mapping (labels, plain-language summaries with placeholders, figure choices).
- `lint.py` fails on orphans, dangling IDs, unresolved placeholders, numbers typed into prose, missing KPI/map entries,
  lineage that reaches no source, and (with `--check-fresh`) a bundle older than its inputs. `swiss/tests/test_dashboard.py` runs it.
- `index.html` holds the hand-drawn system map; `app.js` the cards, search and deep links (`#node=ID`); `charts.js` all figures.
- `vendor/` holds plotly.js 2.11.1 (MIT), see `vendor/README.md`.
- The bundle is committed so every commit is an auditable snapshot; the header warns if it was built from a dirty tree
  or if `data/canonical/MANIFEST.sha256` does not verify.
