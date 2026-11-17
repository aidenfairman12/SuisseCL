"""Lint the audit-dashboard bundle (plan §8.1, §8.3, §8.5). Non-zero exit on any failure.

Checks
  ui_map     every ui_map entry resolves to existing nodes; primary/qc/lineage_end exist
  dangling   every ID referenced by any node (edge or mention) exists as a node
  placeholders  every placeholder resolved at build time (meta.build_errors is empty)
  prose      hand-written prose holds no digits outside placeholders, registry IDs and allowed tokens
  coverage   every KPI column in baselines_2023.csv, and every audit-card key written in web/src (system-map boxes, district
             illustration, KPI tiles), has a ui_map entry; figures named in ui_map exist in web/src/components/charts/registry.tsx
  story      plain-language layer: no digits outside placeholders, no registry IDs, glossary terms exist, display names present,
             no registry ID in the story page sources (IDs belong in audit cards and Explore pages)
  roles      no bare building role code (SFH-low, MFH-large, ...) in any UI source except the colour table in charts/util.ts,
             and no visible-label sink (title/legend/axis/JSX text) fed a bare `role` variable (source-level check)
  carbon     no g/kWh (or gCO2) text, and no read of the modeled carbon series, outside the carbon audit card, its Inputs tab and
             its figures; carbon KPI columns are marked relative_only; the card shows the proxy range and the EPFL level
             caveat, taken from the QC files (placeholders), beside the absolute mean
  lineage    every series / KPI / card reaches a SRC-* node or ends in a decision / assumption / lineage_end
  registry   every registry row ID (SRC DER TR M D A ISS ALG EXP V R) is a node
  --check-fresh  every input recorded in meta.json still has the same sha256 (bundle is not stale)

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
from swiss.dashboard import story as story_mod  # noqa: E402
from swiss.dashboard.parse_registries import ID_RE, RANGE_RE, SLASH_LETTERS_RE, extract_ids  # noqa: E402

BUNDLE = os.path.join(ROOT, 'web', 'public', 'bundle')
WEB_SRC = os.path.join(ROOT, 'web', 'src')
REGISTRY = os.path.join(WEB_SRC, 'components', 'charts', 'registry.tsx')


def web_sources():
    """(relative path, text) of every .ts/.tsx file of the Next.js UI."""
    out = []
    for d, _, files in os.walk(WEB_SRC):
        for fn in files:
            if fn.endswith(('.ts', '.tsx')):
                p = os.path.join(d, fn)
                out.append((os.path.relpath(p, ROOT), open(p, encoding='utf-8').read()))
    return out


ROLE_CODE_RE = re.compile(r'\b(?:SFH|MFH)-(?:low|mid|high|small|medium|large)\b')
# visible-label sinks fed a bare role variable: `${role}`, JSX text {role}, `text: role`, `name: q.role`, `data: roles`
ROLE_SINK_RES = [re.compile(p) for p in (
    r'\$\{\s*[\w.?]*\brole\s*\}', r'>\s*\{\s*[\w.?]*\brole\s*\}', r'\b(?:text|name|label|title)\s*:\s*[\w.?]*\brole\b(?!\w)',
    r'\bdata\s*:\s*roles\s*[,}\]]', r'\bdata\s*:\s*\[?\s*[\w.]*\brole\b')]
LABEL_DIRS = ('/components/charts/', '/components/results/', '/components/inputs/', '/components/district/', '/components/story/')
CARBON_TEXT_RE = re.compile(r'g\s?/\s?kWh|gCO2|\bg\s?CO[₂2]')
CARBON_SERIES_RE = re.compile(r'\b(?:S|series|si\.series)\.carbon(?:_domestic)?\b|series\[\s*["\']carbon')
# the only UI sources that may show the absolute modeled carbon intensity (always under the carbon card's own caveats)
CARBON_ALLOWED_SRC = ('web/src/components/charts/figures-inputs.tsx', 'web/src/components/inputs/inputs-page.tsx')


def ui_source_violations(rel, text):
    """Source-level guards on one UI file (relative path, text). Returns error strings."""
    rel = rel.replace(os.sep, '/')
    errs = []
    if not rel.endswith('components/charts/util.ts'):
        for m in ROLE_CODE_RE.finditer(text):
            errs.append(f'roles: {rel} contains the bare role code "{m.group(0)}" (use useBuildingLabel / the _buildings names)')
    if any(d in '/' + rel for d in LABEL_DIRS):
        for rx in ROLE_SINK_RES:
            for m in rx.finditer(text):
                errs.append(f'roles: {rel} feeds a bare role variable into a visible label: "{m.group(0).strip()}"')
    if rel not in CARBON_ALLOWED_SRC:
        for m in CARBON_TEXT_RE.finditer(text):
            errs.append(f'carbon: {rel} shows an absolute carbon unit ("{m.group(0)}") outside the carbon card and its Inputs tab')
        for m in CARBON_SERIES_RE.finditer(text):
            errs.append(f'carbon: {rel} reads the modeled carbon series ("{m.group(0)}"); use the rank wording (carbonRelative)')
    return errs


def _strings(o, where=''):
    if isinstance(o, str):
        yield where, o
    elif isinstance(o, list):
        for i, x in enumerate(o):
            yield from _strings(x, f'{where}[{i}]')
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from _strings(v, f'{where}.{k}')


def carbon_text_violations(ui, prov, story, qc):
    """Carbon guards on the hand-written layer and the built bundle. `qc` is qc_carbon_2023.json."""
    errs = []
    card = 'series:carbon_intensity'
    for key, e in ui.items():
        if key == card or key.startswith('_'):
            continue
        for where, t in _strings({k: v for k, v in e.items() if k not in ('code', 'docs', 'nodes', 'qc', 'figures', 'flags')}, key):
            if CARBON_TEXT_RE.search(t):
                errs.append(f'carbon: {where} shows an absolute carbon unit outside the carbon card: "{t[:60]}"')
        if key.startswith('kpi:') and 'carbon' in key and not (e.get('fields') or {}).get('relative_only'):
            errs.append(f'carbon: {key} must set fields.relative_only (a carbon KPI is shown only as a change vs no control)')
    for where, t in _strings(story, 'story.json'):
        if CARBON_TEXT_RE.search(t):
            errs.append(f'carbon: {where} shows an absolute carbon unit: "{t[:60]}"')
    n = prov['nodes'].get(card)
    if not n:
        return errs + [f'carbon: {card} is missing from the bundle']
    lo, hi = (qc['proxy_sensitivity_mean_g_kwh'][k] for k in ('proxies_x0.5', 'proxies_x1.5'))
    text = ' '.join([n.get('summary') or '', *n.get('caveats', [])])
    for what, v in (('proxy range low', f'{lo:.0f}'), ('proxy range high', f'{hi:.0f}')):
        if v not in n.get('summary', '') or not any(v in c for c in n.get('caveats', [])):
            errs.append(f'carbon: the card summary and a caveat must both show the {what} ({v} g/kWh) from {os.path.basename("qc_carbon_2023.json")}')
    if not re.search(r'EPFL', text) or not re.search(r'\d+ ?%', text):
        errs.append('carbon: the card must state the level against the EPFL reference (percent)')
    return errs


def load():
    prov = read_bundle_file(os.path.join(BUNDLE, 'provenance.json'))
    meta = read_bundle_file(os.path.join(BUNDLE, 'meta.json'))
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

    # figures referenced in ui_map must be implemented in web/src/components/charts/registry.tsx
    known_figs = set(re.findall(r'^  (\w+): \{ title:', open(REGISTRY, encoding='utf-8').read(), re.M)) if os.path.exists(REGISTRY) else set()
    if not known_figs:
        errs.append('figures: no figures found in web/src/components/charts/registry.tsx')
    for key, e in ui.items():
        if key.startswith('_'):
            continue
        for f in e.get('figures', []) or []:
            if f not in known_figs:
                errs.append(f'figures: {key} uses figure "{f}", which the web UI registry does not implement')

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
    # audit-card keys written as string literals in the web UI (map boxes, district illustration, tiles, links)
    for rel, text in web_sources():
        for k in sorted(set(re.findall(r'["\']((?:series|card|kpi|panel|map):[a-z0-9_]+)["\']', text))):
            if k not in ui:
                errs.append(f'coverage: {rel} opens "{k}", which has no ui_map entry')
        # KPI column names listed in the UI become kpi:<column> keys
        for arr in re.findall(r'(?:HEADLINE|KPIS)\s*=\s*\[([^\]]*)\]', text):
            for col in re.findall(r'"([a-z0-9_]+)"', arr):
                if f'kpi:{col}' not in ui or col not in cols:
                    errs.append(f'coverage: {rel} lists KPI column "{col}" that is not a results column with a ui_map entry')

    # plain-language layer (story page): prose rules, display names, glossary terms used in the UI
    errs += story_mod.check_prose(ui, prose_digits)
    headline = set()
    for rel, text in web_sources():
        for arr in re.findall(r'(?:HEADLINE|KPIS)\s*=\s*\[([^\]]*)\]', text):
            headline |= set(re.findall(r'"([a-z0-9_]+)"', arr))
    for key, e in ui.items():
        if key.startswith('_'):
            continue
        kind = key.split(':')[0]
        needs = kind in ('series', 'card', 'panel') or key in {f'kpi:{c}' for c in set(story_mod.STORY_KPIS) | headline}
        if needs and not e.get('display_name'):
            errs.append(f'display names: {key} is shown on the story or Explore pages but has no display_name')
        if e.get('display_name') and story_mod.ID_PATTERN.search(e['display_name']):
            errs.append(f'display names: {key} display_name contains a registry ID')
    gl_ids = {g['id'] for g in ui.get('_glossary', [])}
    for rel, text in web_sources():
        for t in re.findall(r'<Term\s+id=["\']([a-z0-9_]+)["\']', text):
            if t not in gl_ids:
                errs.append(f'glossary: {rel} uses <Term id="{t}"> which is not in the glossary')
        story_page = '/components/story/' in rel or rel.endswith('web/src/app/page.tsx')
        if story_page:
            for lit in re.findall(r'"([^"\n]{3,})"', text) + re.findall(r'>([^<>{}\n]{3,})<', text):
                if story_mod.ID_PATTERN.search(lit):
                    errs.append(f'story prose: {rel} shows a registry ID in "{lit[:40]}" (IDs belong in audit cards only)')

    # building role codes and absolute carbon values in the UI sources and the bundle
    for rel, text in web_sources():
        errs += ui_source_violations(rel, text)
    import json
    qc = json.load(open(os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_carbon_2023.json'), encoding='utf-8'))
    errs += carbon_text_violations(ui, prov, read_bundle_file(os.path.join(BUNDLE, 'story.json')), qc)
    if not re.search(r'node:\s*"series:carbon_intensity"', open(os.path.join(WEB_SRC, 'components', 'inputs', 'inputs-page.tsx'), encoding='utf-8').read()):
        errs.append('carbon: the Inputs carbon tab must open with the carbon card header (its caveats sit above the chart)')

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
