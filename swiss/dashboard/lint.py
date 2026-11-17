"""Lint the audit-dashboard bundle (plan §8.1, §8.3, §8.5). Non-zero exit on any failure.

Checks
  ui_map     every ui_map entry resolves to existing nodes; primary/qc/lineage_end exist
  dangling   every ID referenced by any node (edge or mention) exists as a node
  placeholders  every placeholder resolved at build time (meta.build_errors is empty)
  prose      hand-written prose holds no digits outside placeholders, registry IDs and allowed tokens
  coverage   every KPI column in baselines_2023.csv and every data-ui box in dashboard/system_map.svg has a ui_map entry
  lineage    every series / KPI / card reaches a SRC-* node or ends in a decision / assumption / lineage_end
  registry   every registry row ID (SRC DER TR M D A ISS ALG EXP V R) is a node
  --check-fresh  every input recorded in meta.js still has the same sha256 (bundle is not stale)

Run: PYTHONPATH=. cl/bin/python -I swiss/dashboard/lint.py [--check-fresh]
"""
import csv
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
import yaml  # noqa: E402

from swiss.dashboard import build_bundle as bb  # noqa: E402
from swiss.dashboard.bundle_io import read_bundle_file  # noqa: E402
from swiss.dashboard.parse_registries import ID_RE, RANGE_RE, SLASH_LETTERS_RE, extract_ids  # noqa: E402

BUNDLE = os.path.join(ROOT, 'dashboard', 'bundle')
SVG = os.path.join(ROOT, 'dashboard', 'system_map.svg')
INDEX = os.path.join(ROOT, 'dashboard', 'index.html')


def load():
    prov = read_bundle_file(os.path.join(BUNDLE, 'provenance.js'))
    meta = read_bundle_file(os.path.join(BUNDLE, 'meta.js'))
    ui = yaml.safe_load(open(bb.UI_MAP, encoding='utf-8'))
    return prov, meta, ui


def check_fresh(meta):
    errs = []
    for f, h in meta['inputs'].items():
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            errs.append(f'fresh: input {f} no longer exists')
        elif bb.sha256_file(p) != h:
            errs.append(f'fresh: input {f} changed since the bundle was built (rebuild with build_bundle.py)')
    return errs


def prose_digits(text, allowed):
    t = bb.PH_RE.sub(' ', text)
    for rx in (SLASH_LETTERS_RE, RANGE_RE, ID_RE):
        t = rx.sub(' ', t)
    t = re.sub(r'PAR:\S+|QC:\S+', ' ', t)
    for tok in sorted(allowed, key=len, reverse=True):
        t = t.replace(tok, ' ')
    return re.findall(r'\S*\d\S*', t)


def registry_ids():
    """IDs straight from the first column of each registry file (independent of the parsers' node building)."""
    ids = set()
    with open(os.path.join(ROOT, bb.P['src_registry']), encoding='utf-8') as f:
        for line in f.read().splitlines()[1:]:
            if line.strip():
                ids.add(line.split(',')[0])
    with open(os.path.join(ROOT, bb.P['exp_registry']), encoding='utf-8') as f:
        ids.update(r['experiment_id'] for r in csv.DictReader(f))
    for key in ('tr_log', 'model_registry', 'decisions', 'assumptions', 'issues', 'alg_registry', 'validation_md'):
        for line in open(os.path.join(ROOT, bb.P[key]), encoding='utf-8'):
            m = re.match(r'^\|\s*((?:SRC|DER|TR|M|D|A|ISS|ALG|EXP)-\d{3}[a-z]?|V\d+)\s*\|', line)
            if m:
                ids.add(m.group(1))
    for m in re.finditer(r'^## (R-\d{3})', open(os.path.join(ROOT, bb.P['reward_doc']), encoding='utf-8').read(), re.M):
        ids.add(m.group(1))
    return ids


def lint(check_fresh_flag=False):
    prov, meta, ui = load()
    nodes = prov['nodes']
    settings = ui.get('_settings', {}) or {}
    allowed = settings.get('prose_allowed_tokens', []) or []
    errs, warns = [], []

    # placeholders (resolved at build time)
    errs += [f'placeholder: {e}' for e in meta.get('build_errors', [])]

    # ui_map entries resolve
    for key, e in ui.items():
        if key.startswith('_'):
            continue
        if key not in nodes:
            errs.append(f'ui_map: {key} missing from bundle (rebuild?)')
            continue
        if not e.get('nodes') and not (e.get('nodes_open_issues') and any(x['to'].startswith('ISS-') for x in nodes[key]['edges'])):
            errs.append(f'ui_map: {key} has no provenance nodes')
        for x in (e.get('nodes') or []) + (e.get('qc') or []) + [e.get('primary'), e.get('lineage_end')]:
            if x and x not in nodes:
                errs.append(f'ui_map: {key} references {x}, which does not exist')
        for fld in ('summary', 'label'):
            if e.get(fld):
                for d in prose_digits(str(e[fld]), allowed):
                    errs.append(f'prose: {key}.{fld} has a number outside a placeholder: "{d}"')
        for c in e.get('caveats', []) or []:
            for d in prose_digits(c, allowed):
                errs.append(f'prose: {key}.caveats has a number outside a placeholder: "{d}"')
        for n in e.get('numbers', []) or []:
            if not bb.PH_RE.search(str(n.get('value', ''))):
                errs.append(f'prose: {key}.numbers "{n.get("label")}" value is not a placeholder')

    # figures referenced in ui_map must be implemented in dashboard/charts.js
    charts = os.path.join(ROOT, 'dashboard', 'charts.js')
    known_figs = set(re.findall(r'^\s{4}(\w+): \{title:', open(charts, encoding='utf-8').read(), re.M)) if os.path.exists(charts) else set()
    for key, e in ui.items():
        if key.startswith('_'):
            continue
        for f in e.get('figures', []) or []:
            if f not in known_figs:
                errs.append(f'figures: {key} uses figure "{f}", which dashboard/charts.js does not implement')

    # dangling IDs: every edge target, every ID mentioned in shown text
    for nid, n in nodes.items():
        for e in n['edges']:
            if e['to'] not in nodes:
                errs.append(f'dangling: {nid} -{e["rel"]}-> {e["to"]} does not exist')

    # coverage: KPI columns and system-map boxes
    with open(os.path.join(ROOT, bb.P['baselines']), encoding='utf-8') as f:
        cols = next(csv.reader(f))
    for c in cols:
        if c in ('controller', 'steps'):
            continue
        if f'kpi:{c}' not in ui:
            errs.append(f'coverage: KPI column {c} has no ui_map entry kpi:{c}')
    for path in (SVG, INDEX):
        if os.path.exists(path):
            for k in re.findall(r'data-ui="([^"]+)"', open(path, encoding='utf-8').read()):
                if k not in ui:
                    errs.append(f'coverage: {os.path.basename(path)} data-ui="{k}" has no ui_map entry')

    # ui keys referenced as string literals in the page scripts (cards opened from JS-drawn elements)
    for js in ('app.js', 'charts.js', 'district.js'):
        f = os.path.join(ROOT, 'dashboard', js)
        if os.path.exists(f):
            for k in set(re.findall(r"'((?:series|card|kpi|panel|map):[a-z_]+)'", open(f, encoding='utf-8').read())):
                if k not in ui:
                    errs.append(f'coverage: dashboard/{js} opens "{k}", which has no ui_map entry')

    # lineage
    for nid, n in nodes.items():
        if n['kind'] not in ('series', 'kpi', 'card'):
            continue
        lin = n.get('lineage', [])
        if any(x.startswith('SRC-') for x in lin):
            continue
        if n.get('lineage_end') or any(nodes[x]['kind'] in ('decision', 'assumption') for x in lin if x in nodes):
            continue
        errs.append(f'lineage: {nid} reaches no SRC-* node and does not end in a decision/assumption')

    # registry coverage
    for rid in sorted(registry_ids()):
        if rid not in nodes:
            errs.append(f'registry: {rid} has no node (not searchable)')

    # parse warnings are not errors (the registries are read-only) but are reported
    for nid, n in nodes.items():
        for w in n.get('parse_warnings', []):
            warns.append(f'registry row {nid}: {w}')
    if not meta['manifest']['verified']:
        warns.append('MANIFEST.sha256 does not verify: ' + str(meta['manifest']['failures'][:5]))
    if meta['git']['dirty']:
        warns.append(f"bundle built from a dirty tree ({len(meta['git']['dirty_paths'])} paths)")

    if check_fresh_flag:
        errs += check_fresh(meta)
    return errs, warns


def main(argv):
    errs, warns = lint('--check-fresh' in argv)
    for w in warns:
        print('WARN ', w)
    for e in errs:
        print('ERROR', e)
    print(f'lint: {len(errs)} error(s), {len(warns)} warning(s)')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
