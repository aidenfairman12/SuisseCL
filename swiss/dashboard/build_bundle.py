"""Build the audit-dashboard bundle (docs/dashboard/dashboard_implementation_plan.md).

Reads the registries, QC reports, results and ui_map.yaml (all read-only) and writes web/public/bundle/*.json.
The Next.js UI in web/ reads these files; lint.py and the tests read them with `bundle_io.read_bundle_file`.

Run: PYTHONPATH=. cl/bin/python -I swiss/dashboard/build_bundle.py
"""
import ast
import csv
import datetime as _dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
import yaml  # noqa: E402  (PyYAML 6.0.3, pinned; CityLearn dependency)

from swiss.dashboard import bundle_io  # noqa: E402
from swiss.dashboard.parse_registries import (extract_ids, normalise_classification, parse_csv_registry,  # noqa: E402
                                              parse_md_registry, slug)

BUNDLE = os.path.join(ROOT, 'web', 'public', 'bundle')
UI_MAP = os.path.join(ROOT, 'swiss', 'dashboard', 'ui_map.yaml')

P = {  # every input file the build reads (paths relative to ROOT)
    'src_registry': 'docs/data/data_source_registry.csv',
    'tr_log': 'docs/data/transformation_log.md',
    'model_registry': 'docs/models/model_registry.md',
    'param_registry': 'docs/models/parameter_registry.csv',
    'decisions': 'docs/decisions/decision_log.md',
    'assumptions': 'docs/decisions/assumptions_log.md',
    'issues': 'docs/decisions/issues_and_risks.md',
    'alg_registry': 'docs/algorithms/algorithm_registry.md',
    'controller_doc': 'docs/algorithms/controller_documentation.md',
    'reward_doc': 'docs/algorithms/reward_function_documentation.md',
    'rewards_py': 'swiss/experiments/rewards.py',
    'exp_registry': 'docs/experiments/experiment_registry.csv',
    'columns': 'data/canonical/hourly/columns.json',
    'validation_json': 'docs/experiments/validation_reports/validation_phase_a.json',
    'validation_md': 'docs/experiments/validation_reports/validation_phase_a.md',
    'thermal_params': 'data/canonical/thermal/thermal_params.json',
    'build_manifest': 'swiss/datasets/swiss_district_2023/build_manifest.json',
    'schema': 'swiss/datasets/swiss_district_2023/schema.json',
    'baselines': 'swiss/experiments/results/baselines_2023.csv',
    'baselines_meta': 'swiss/experiments/results/baselines_2023_meta.json',
    'sensitivity': 'swiss/experiments/results/sensitivity_2023.csv',
    'reward_scales': 'swiss/experiments/results/reward_scales.json',
    'manifest': 'data/canonical/MANIFEST.sha256',
    'ui_map': 'swiss/dashboard/ui_map.yaml',
    'master_plan': 'docs/master_plan.md',
}
QC_DIR = 'docs/data/data_quality_reports'
QC_REPORTS = {  # placeholder namespace -> (json file, markdown twin or None, title)
    'qc_carbon': ('qc_carbon_2023.json', None, 'QC: modeled carbon intensity 2023'),
    'qc_weather': ('qc_weather_klo_2023.json', None, 'QC: Zurich/Kloten weather 2023'),
    'qc_tariff': ('qc_tariff_2023.json', None, 'QC: EKZ standard tariff 2023'),
    'qc_thermal': ('qc_thermal_2023.json', 'qc_thermal_2023.md', 'QC: derived thermal demand 2023'),
    'qc_buildings': ('qc_2023_buildings.json', 'qc_2023_buildings.md', 'QC: building electricity 2023'),
    'backtest': ('backtest_gap_fill.json', None, 'Gap-fill backtest'),
    'epfl': ('carbon_epfl_comparison.json', 'carbon_epfl_comparison.md', 'Carbon method check vs EPFL 2016-17'),
}
# Builder code is an input too: a changed builder means a stale bundle.
BUILDER_FILES = ['swiss/dashboard/build_bundle.py', 'swiss/dashboard/parse_registries.py', 'swiss/dashboard/bundle_io.py',
                 'swiss/dashboard/figures.py', 'swiss/dashboard/story.py', 'swiss/pipeline/select_buildings.py', 'swiss/experiments/run_baselines.py',
                 'swiss/experiments/run_sensitivity.py', 'swiss/datasets/swiss_district_2023/pricing.csv', 'swiss/dashboard/phase_b.py', 'swiss/dashboard/phase_c.py', 'swiss/dashboard/climate_series.py']

_read_files = set()


def rel(path):
    return os.path.relpath(path, ROOT)


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def read_text(p):
    _read_files.add(rel(_abs(p)))
    return open(_abs(p), encoding='utf-8').read()


def read_json(p):
    return json.loads(read_text(p))


def read_csv_dicts(p):
    _read_files.add(rel(_abs(p)))
    with open(_abs(p), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def read_df(p):
    import pandas as pd
    _read_files.add(rel(_abs(p)))
    return pd.read_csv(_abs(p))


def sha256_file(p):
    h = hashlib.sha256()
    with open(_abs(p), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    r = subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True)
    return r.stdout.strip()


def num(x):
    """CSV cell -> float/None (NaN and empty become None so the JSON stays valid)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return x
    return None if math.isnan(v) else v


def clean(o):
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def first_sentence(text, limit=220):
    t = re.sub(r'\s+', ' ', (text or '').strip())
    m = re.match(r'(.+?[.;])(\s|$)', t)
    s = m.group(1) if m else t
    return s if len(s) <= limit else s[:limit - 1].rstrip() + '…'


# ---------------------------------------------------------------- code excerpts

_file_commit_cache = {}


def file_commit(path):
    if path not in _file_commit_cache:
        sha = git('log', '-1', '--format=%h', '--', path) or None
        dirty = bool(git('status', '--porcelain', '--', path))
        _file_commit_cache[path] = (sha, dirty)
    return _file_commit_cache[path]


def code_excerpt(path, symbol=None):
    """Cut a function/class (or the module docstring if symbol is None) out of a Python file with ast."""
    src = read_text(path)
    tree = ast.parse(src)
    sha, dirty = file_commit(path)
    out = {'file': path, 'symbol': symbol, 'commit': sha, 'uncommitted_changes': dirty}
    if symbol is None:
        doc = ast.get_docstring(tree)
        out.update({'kind': 'module docstring', 'line': 1, 'source': doc or '',
                    'defines': [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]})
        return out
    parts = symbol.split('.')
    nodes = tree.body
    found = None
    for part in parts:
        found = next((n for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.name == part), None)
        if found is None:
            break
        nodes = found.body
    if found is None:
        raise KeyError(f'{path}::{symbol} not found')
    start = min([found.lineno] + [d.lineno for d in found.decorator_list])
    lines = src.splitlines()[start - 1:found.end_lineno]
    out.update({'kind': type(found).__name__, 'line': start, 'source': '\n'.join(lines)})
    return out


def parse_code_ref(ref):
    path, _, symbol = ref.partition('::')
    return code_excerpt(path, symbol or None)


# ---------------------------------------------------------------- placeholder data namespace

def load_data():
    d = {}
    for ns, (fn, _, _) in QC_REPORTS.items():
        d[ns] = read_json(f'{QC_DIR}/{fn}')
    d['validation'] = read_json(P['validation_json'])
    d['thermal_params'] = read_json(P['thermal_params'])
    d['build_manifest'] = read_json(P['build_manifest'])
    d['reward_scales'] = read_json(P['reward_scales'])
    d['baselines_meta'] = read_json(P['baselines_meta'])
    d['columns'] = read_json(P['columns'])
    d['results'] = {r['controller']: {k: num(v) for k, v in r.items()} for r in read_csv_dicts(P['baselines'])}
    d['sensitivity'] = {f"{r['variant']}|{r['controller']}": {k: num(v) for k, v in r.items()}
                        for r in read_csv_dicts(P['sensitivity'])}
    return d


PH_RE = re.compile(r'\{([a-z_][a-z0-9_]*(?:\.[^{}:.\[\]\s]+|\[[^\]]+\])*)(?::([^{}]*))?\}')


def resolve_path(data, path):
    m = re.match(r'([a-z_][a-z0-9_]*)', path)
    cur = data[m.group(1)]
    for part in re.findall(r'\.([^.\[\]]+)|\[([^\]]+)\]', path[m.end():]):
        key = part[0] or part[1]
        if isinstance(cur, list):
            cur = cur[int(key)]
        else:
            cur = cur[key]
    return cur


def fill(template, data, errors, where):
    def sub(m):
        try:
            v = resolve_path(data, m.group(1))
        except (KeyError, IndexError, ValueError, TypeError):
            errors.append(f'{where}: placeholder {{{m.group(1)}}} does not resolve')
            return m.group(0)
        spec = m.group(2) or ''
        try:
            return format(v, spec) if spec else (f'{v:g}' if isinstance(v, float) else str(v))
        except (ValueError, TypeError):
            errors.append(f'{where}: format spec "{spec}" invalid for {m.group(1)}={v!r}')
            return str(v)
    return PH_RE.sub(sub, template)


# ---------------------------------------------------------------- graph

class Graph:
    def __init__(self):
        self.nodes = {}

    def add(self, nid, kind, title, **kw):
        if nid in self.nodes:
            raise ValueError(f'duplicate node {nid}')
        n = {'id': nid, 'kind': kind, 'title': title, 'classification': None, 'classification_raw': None,
             'summary': None, 'fields': {}, 'edges': [], 'qc': [], 'figures': [], 'code': [], 'docs': [],
             'source_ref': None, 'parse_warnings': []}
        n.update(kw)
        self.nodes[nid] = n
        return n

    def edge(self, a, rel_, b, note=None):
        if a == b:
            return
        n = self.nodes[a]
        for e in n['edges']:
            if e['to'] == b and (e['rel'] == rel_ or rel_ == 'mentions'):
                return
        if rel_ != 'mentions':  # a typed edge replaces a weaker mention edge
            n['edges'] = [e for e in n['edges'] if not (e['to'] == b and e['rel'] == 'mentions')]
        e = {'rel': rel_, 'to': b}
        if note:
            e['note'] = note
        n['edges'].append(e)

    def mentions_from(self, nid, texts):
        for t in texts:
            for x in extract_ids(t):
                self.edge(nid, 'mentions', x)


def registry_ref(path, row):
    return {'file': path, 'line': row['line'], 'raw': row['raw']}


def build_registry_nodes(g):
    # --- SRC / DER
    hdr, rows = parse_csv_registry(_abs(P['src_registry']), anchor_col='classification')
    _read_files.add(P['src_registry'])
    for r in rows:
        c = r['cells']
        nid = c['dataset_id']
        kind = 'source' if nid.startswith('SRC') else 'derived_dataset'
        n = g.add(nid, kind, c['name'], fields=c, classification=normalise_classification(c['classification']),
                  classification_raw=c['classification'], source_ref=registry_ref(P['src_registry'], r),
                  parse_warnings=r['_parse_warnings'],
                  summary=f"{c['name']}. {('Intended use: ' + c['intended_use'] + '.') if c.get('intended_use') else ''}".strip())
        notes = c.get('notes', '')
        mfrom = re.match(r'\s*From\s+(.*)', notes)
        if mfrom:
            for x in extract_ids(mfrom.group(1).split(';')[0]):
                g.edge(nid, 'derived_from', x)
        g.mentions_from(nid, c.values())
    # --- TR
    _read_files.add(P['tr_log'])
    for r in parse_md_registry(_abs(P['tr_log'])):
        c = r['cells']
        nid = c['ID']
        scripts = re.findall(r'swiss/[\w/]+\.py', c.get('Script', ''))
        n = g.add(nid, 'transform', f"{c['Inputs']} → {c['Output']}", fields=c,
                  source_ref=registry_ref(P['tr_log'], r), parse_warnings=r['_parse_warnings'],
                  summary=f"Transformation producing {c['Output']} from {c['Inputs']} ({', '.join(scripts) or c.get('Script', '')}).")
        for x in extract_ids(c['Inputs']):
            g.edge(nid, 'input', x)
        for x in extract_ids(c['Output']):
            g.edge(nid, 'output', x)
        for s in scripts:
            if os.path.exists(_abs(s)):
                n['code'].append(code_excerpt(s))
        g.mentions_from(nid, c.values())
    # --- M
    for r in parse_md_registry(_abs(P['model_registry'])):
        c = r['cells']
        nid = c['ID']
        g.add(nid, 'model', c['Name'], fields=c, classification=normalise_classification(c.get('Type')) or
              ('derived' if 'derived' in c.get('Type', '') else None), classification_raw=c.get('Type'),
              source_ref=registry_ref(P['model_registry'], r), parse_warnings=r['_parse_warnings'],
              summary=f"{c['Purpose'][:1].upper() + c['Purpose'][1:]}. Method: {c['Method']}.")
        for x in extract_ids(c.get('Status', '')):
            if x.startswith('D-'):
                g.edge(nid, 'decided_in', x)
        for s in re.findall(r'swiss/[\w/]+\.py', c.get('Status', '')):
            if os.path.exists(_abs(s)):
                g.nodes[nid]['code'].append(code_excerpt(s))
        g.mentions_from(nid, c.values())
    _read_files.add(P['model_registry'])
    # --- parameters
    hdr, rows = parse_csv_registry(_abs(P['param_registry']))
    _read_files.add(P['param_registry'])
    last_source = {}
    for r in rows:
        c = r['cells']
        src = c.get('source', '')
        if re.match(r'\s*same\b', src, re.I) and c['model_id'] in last_source:
            # "same" in the registry refers to the row above; show what it resolves to (registry text kept verbatim)
            c = dict(c, source_resolved=last_source[c['model_id']] + src.strip()[4:])
        elif src:
            last_source[c['model_id']] = src
        nid = f"PAR:{c['model_id']}:{slug(c['name'])}"
        g.add(nid, 'parameter', c['name'], fields=c, source_ref=registry_ref(P['param_registry'], r),
              parse_warnings=r['_parse_warnings'], classification_raw=c.get('classification'),
              summary=f"{c['parameter']} = {c['value']} {c['unit'] if c['unit'] not in ('-', '') else ''}".strip()
              + f" ({c['classification']}).")
        if c['model_id'] in g.nodes:
            g.edge(c['model_id'], 'has_parameter', nid)
        g.edge(nid, 'parameter_of', c['model_id'])
        g.mentions_from(nid, [c['source']])
    # --- D, A
    for key, kind, col in (('decisions', 'decision', 'Decision'), ('assumptions', 'assumption', 'Assumption')):
        for r in parse_md_registry(_abs(P[key])):
            c = r['cells']
            g.add(c['ID'], kind, first_sentence(c[col], 140), fields=c, source_ref=registry_ref(P[key], r),
                  parse_warnings=r['_parse_warnings'], summary=first_sentence(c[col], 400),
                  classification='assumption' if kind == 'assumption' else None,
                  status=c.get('Status'))
            g.mentions_from(c['ID'], c.values())
        _read_files.add(P[key])
    # --- ISS (update rows are merged into the first row's node as history)
    for r in parse_md_registry(_abs(P['issues'])):
        c = r['cells']
        nid = c['ID']
        entry = {'date': c['Date'], 'text': c['Issue'], 'affects': c['Affects'], 'status': c['Status'],
                 'needs_user_approval': c['Needs user approval'], 'line': r['line']}
        if nid not in g.nodes:
            g.add(nid, 'issue', first_sentence(c['Issue'], 140), fields=c, source_ref=registry_ref(P['issues'], r),
                  parse_warnings=r['_parse_warnings'], summary=first_sentence(c['Issue'], 400), history=[entry])
        else:
            g.nodes[nid]['history'].append(entry)
            g.nodes[nid]['parse_warnings'] += r['_parse_warnings']
        g.mentions_from(nid, c.values())
    _read_files.add(P['issues'])
    for n in g.nodes.values():
        if n['kind'] == 'issue':
            n['status'], n['open'] = issue_status(n['history'])
    # --- ALG
    for r in parse_md_registry(_abs(P['alg_registry'])):
        c = r['cells']
        g.add(c['ID'], 'controller', c['Name'], fields=c, source_ref=registry_ref(P['alg_registry'], r),
              parse_warnings=r['_parse_warnings'], summary=f"{c['Objective'][:1].upper() + c['Objective'][1:]}.")
        g.mentions_from(c['ID'], c.values())
    _read_files.add(P['alg_registry'])
    read_text(P['controller_doc'])
    # --- R-001, R-002 (one node per "## R-nnn" heading of the reward documentation)
    rdoc = read_text(P['reward_doc'])
    heads = list(re.finditer(r'^## (R-\d{3})\s+(.*)$', rdoc, re.M))
    terms_first = [r_['cells'] for r_ in parse_md_registry(_abs(P['reward_doc']), id_col='Term')]
    for k, m in enumerate(heads):
        rid = m.group(1)
        end = heads[k + 1].start() if k + 1 < len(heads) else len(rdoc)
        section = rdoc[m.start():end]
        formula = re.search(r'^reward_t = .*$', section, re.M)
        cls = re.search(r'`swiss\.experiments\.rewards\.(\w+)`', m.group(2))
        cname = cls.group(1) if cls else 'SwissDistrictReward'
        g.add(rid, 'reward', m.group(2).strip(), fields={'formula': formula.group(0) if formula else None, 'terms': terms_first[:4] if k == 0 else terms_first[4:]},
              source_ref={'file': P['reward_doc'], 'line': rdoc[:m.start()].count('\n') + 1, 'raw': m.group(0)},
              summary=first_sentence(formula.group(0) if formula else section.split('\n', 1)[1].strip().split('\n')[0]),
              code=[code_excerpt(P['rewards_py']), code_excerpt(P['rewards_py'], f'{cname}.terms'), code_excerpt(P['rewards_py'], f'{cname}.calculate')])
        for x in extract_ids(m.group(2)):
            g.edge(rid, 'decided_in', x)
        g.mentions_from(rid, [section])
    # --- EXP
    hdr, rows = parse_csv_registry(_abs(P['exp_registry']))
    _read_files.add(P['exp_registry'])
    for r in rows:
        c = r['cells']
        nid = c['experiment_id']
        g.add(nid, 'experiment', f"{nid}: {c['algorithm_ids']} — {c['scenario'][:80]}", fields=c,
              source_ref=registry_ref(P['exp_registry'], r), parse_warnings=r['_parse_warnings'],
              summary=f"{c['scenario']}. Status: {c['status']}.", status=c['status'])
        for col, rel_ in (('dataset_ids', 'uses_dataset'), ('model_ids', 'uses_model'), ('algorithm_ids', 'uses_controller'),
                          ('reward_version', 'uses_reward')):
            ids = extract_ids(c[col])
            for x in ids[:1] if col in ('dataset_ids', 'reward_version') else ids:
                g.edge(nid, rel_, x)
        g.mentions_from(nid, c.values())
    # --- V (validation checks): status table in the .md, numbers in the .json
    vjson = read_json(P['validation_json'])
    for r in parse_md_registry(_abs(P['validation_md'])):
        c = r['cells']
        vid = c['ID']
        jkey = next((k for k in vjson if k.split('_')[0] == vid), None)
        st = c['Status']
        g.add(vid, 'validation_check', c['Check'], fields=c, source_ref=registry_ref(P['validation_md'], r),
              parse_warnings=r['_parse_warnings'], summary=f"{c['Check']}. Result: {c['Result']}.",
              status=st, passed=st.lower().startswith('pass'),
              results_key=jkey, results=clean(vjson[jkey]) if jkey else None,
              docs=[P['validation_md']] + ([P['validation_json']] if jkey else []))
        g.mentions_from(vid, c.values())
    _read_files.add(P['validation_md'])
    # --- QC reports
    for ns, (fn, md, title) in QC_REPORTS.items():
        nid = f'QC:{fn[:-5]}'
        docs = [f'{QC_DIR}/{fn}'] + ([f'{QC_DIR}/{md}'] if md else [])
        g.add(nid, 'qc_report', title, docs=docs, results=clean(read_json(f'{QC_DIR}/{fn}')), namespace=ns,
              summary=f'Machine-readable QC results from {QC_DIR}/{fn}.')
        if md:
            g.mentions_from(nid, [read_text(f'{QC_DIR}/{md}')])


def issue_status(history):
    """Current status = last non-empty Status cell; an update row starting with RESOLVED / Closed / Superseded
    closes the issue. Both the original status and every update are shown verbatim on the card."""
    status = next((h['status'] for h in reversed(history) if h['status']), '')
    closed = False
    for h in history:
        if re.match(r'\s*(\*\*)?(resolved|closed|superseded)', h['text'], re.I):
            closed = True
            status = h['text'].split(':')[0].split('.')[0][:60] + f" (update {h['date'].strip('() ').replace('update ', '')})"
    if re.match(r'\s*(resolved|closed|superseded|accepted|done)', status, re.I):
        closed = True
    return status, (not closed) and bool(re.match(r'\s*open', status, re.I))


def build_ui_nodes(g, ui, data, errors):
    """ui_map entries become nodes too (series, kpi, map boxes, figures, panels)."""
    for key, e in ui.items():
        if key.startswith('_'):
            continue
        kind = key.split(':')[0]
        kind = {'series': 'series', 'kpi': 'kpi', 'map': 'map_box', 'figure': 'figure', 'panel': 'panel',
                'card': 'card'}.get(kind, kind)
        summary = fill(e.get('summary', '').strip(), data, errors, key) if e.get('summary') else None
        numbers = []
        for item in e.get('numbers', []) or []:
            numbers.append({'label': item['label'], 'value': fill(str(item['value']), data, errors, key),
                            'unit': item.get('unit', ''), 'note': item.get('note')})
        code = []
        for ref in e.get('code', []) or []:
            try:
                code.append(parse_code_ref(ref))
            except (KeyError, FileNotFoundError, SyntaxError) as ex:
                errors.append(f'{key}: code ref {ref}: {ex}')
        n = g.add(key, kind, e.get('label', key), summary=summary, classification=e.get('classification'),
                  display_name=e.get('display_name'), short_name=e.get('short_name'),
                  numbers=numbers, code=code, docs=e.get('docs', []) or [], figures=e.get('figures', []) or [],
                  qc=e.get('qc', []) or [], primary=e.get('primary'), flags=e.get('flags', []) or [],
                  formula=e.get('formula'), caveats=[fill(c, data, errors, key) for c in e.get('caveats', []) or []],
                  lineage_end=e.get('lineage_end'), fields=e.get('fields', {}) or {}, ui=True)
        for x in e.get('nodes', []) or []:
            g.edge(key, 'shows', x)
        if e.get('nodes_open_issues'):
            for x, nn in g.nodes.items():
                if nn['kind'] == 'issue' and nn.get('open'):
                    g.edge(key, 'shows', x)
        for q in n['qc']:
            g.edge(key, 'qc', q)
        for t in (summary or '', *(n['caveats'])):
            for x in extract_ids(t):
                g.edge(key, 'mentions', x)


DATA_EDGES = ('decided_in', 'derived_from', 'input', 'uses_dataset', 'uses_model', 'uses_controller', 'uses_reward', 'parameter_of')


def lineage(g, nid, produced_by, max_depth=10):
    """Walk data edges (and TR outputs in reverse) upstream from `nid`. UI nodes start at their primary node (or
    their first listed node). Returns (ordered node list, tree {node: [upstream nodes]})."""
    n = g.nodes[nid]
    start = nid
    order, tree = [], {}
    if n.get('ui'):
        first = n.get('primary') or next((e['to'] for e in n['edges'] if e['rel'] == 'shows'), None)
        if first is None or first not in g.nodes:
            return [], {}
        tree[nid] = [first]
        order.append(first)
        start = first
    seen, frontier = {nid, start}, [start]
    for _ in range(max_depth):
        nxt = []
        for x in frontier:
            targets = [e['to'] for e in g.nodes[x]['edges'] if e['rel'] in DATA_EDGES] + produced_by.get(x, [])
            ups = []
            for t in targets:
                if t in g.nodes and t not in ups:
                    ups.append(t)
                    if t not in seen:
                        seen.add(t); order.append(t); nxt.append(t)
            if ups:
                tree[x] = ups
        frontier = nxt
    end = n.get('lineage_end')
    if end and end in g.nodes and end not in order:
        tree.setdefault(start, []).append(end)
        order.append(end)
    return order, tree


def finalise(g):
    # backlinks
    back = {k: [] for k in g.nodes}
    for n in g.nodes.values():
        for e in n['edges']:
            if e['to'] in back:
                back[e['to']].append({'rel': e['rel'], 'from': n['id']})
    for k, n in g.nodes.items():
        n['backlinks'] = back[k]
    produced_by = {}
    for n in g.nodes.values():
        for e in n['edges']:
            if e['rel'] == 'output':
                produced_by.setdefault(e['to'], []).append(n['id'])
    for n in g.nodes.values():
        n['produced_by'] = produced_by.get(n['id'], [])
        n['lineage'], n['lineage_tree'] = lineage(g, n['id'], produced_by)


# ---------------------------------------------------------------- snapshot integrity

def manifest_check():
    base = os.path.dirname(_abs(P['manifest']))
    _read_files.add(P['manifest'])
    bad, n = [], 0
    for line in open(_abs(P['manifest']), encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        h, _, f = line.partition('  ')
        n += 1
        fp = os.path.normpath(os.path.join(base, f))
        if not os.path.exists(fp):
            bad.append({'file': rel(fp), 'problem': 'missing'})
        elif sha256_file(fp) != h:
            bad.append({'file': rel(fp), 'problem': 'sha256 mismatch'})
    return {'verified': not bad, 'files_listed': n, 'failures': bad}


def dirty_lines(porcelain):
    """`git status --porcelain` lines that make the tree dirty, ignoring the generated bundle itself.
    The raw output must not be stripped: the first line may start with a space (' M path')."""
    return [l for l in porcelain.splitlines() if l and not l[3:].startswith('web/public/bundle')]


def repo_url():
    """https URL of the origin repository (for links to docs on the hosted dashboard), or None."""
    import re as _re
    u = git('remote', 'get-url', 'origin')
    m = _re.match(r'(?:git@github\.com:|https://github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?$', u)
    return f'https://github.com/{m.group(1)}' if m else None


def git_state():
    head = git('rev-parse', '--short', 'HEAD')
    raw = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain'], capture_output=True, text=True).stdout
    porcelain = dirty_lines(raw)
    return {'commit': head, 'commit_full': git('rev-parse', 'HEAD'), 'dirty': bool(porcelain),
            'dirty_paths': [l[3:] for l in porcelain][:50]}


def main():
    os.makedirs(BUNDLE, exist_ok=True)
    errors = []
    ui = yaml.safe_load(read_text(P['ui_map'])) or {}
    data = load_data()
    from swiss.dashboard import figures
    series = figures.build_inputs(read_df)
    figs = figures.build_figures(read_df)
    figs.update(figures.build_model_figures(read_df, read_json))
    figs['action_maps'] = figures.action_maps()
    figs['district'] = figures.district(read_df, read_json)
    from swiss.experiments import run_sensitivity
    figs['sensitivity_variants'] = {'datasets': dict(run_sensitivity.VARIANTS), 'controllers': list(run_sensitivity.CTRL),
                                    'source': 'swiss/experiments/run_sensitivity.py (VARIANTS, CTRL)'}
    _, exp_rows = parse_csv_registry(_abs(P['exp_registry']))
    results, traces = figures.build_results(read_df, read_json, [r['cells'] for r in exp_rows])
    results['traces'] = {k: {kk: vv for kk, vv in v.items() if kk != 'arrays'} for k, v in traces.items()}
    data['res'] = results
    data['fig'] = figs
    g = Graph()
    build_registry_nodes(g)
    from swiss.dashboard import story as story_mod
    phases = story_mod.parse_master_plan(read_text(P['master_plan']))
    derived = story_mod.compute_derived(data, g.nodes, series, phases)
    data['derived'] = derived
    data['names'] = story_mod.names_namespace(ui['_controllers'])
    data['tariff'] = {'low': data['qc_tariff']['distinct_total_rp'][0], 'high': data['qc_tariff']['distinct_total_rp'][1]}
    build_ui_nodes(g, ui, data, errors)
    story_obj = story_mod.build_story(ui, data, derived, g.nodes, phases, lambda t, errs, where: fill(t, data, errs, where), errors)
    # KPI nodes for every results column without a ui_map entry are NOT created: lint requires an entry.
    finalise(g)
    from swiss.dashboard import phase_b
    scenarios_obj, controllers_obj, data['pb'] = phase_b.build(sys.modules[__name__], ui, errors, g.nodes)
    from swiss.dashboard import phase_c
    climate_obj, cooling_obj, explorer_obj, houses_obj, data['pc'] = phase_c.build(sys.modules[__name__], ui, errors, g.nodes, data['pb'])
    for f in BUILDER_FILES:
        _read_files.add(f)
    counts = {}
    for n in g.nodes.values():
        counts[n['kind']] = counts.get(n['kind'], 0) + 1
    meta = {
        'built_utc': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'git': git_state(),
        'repo_url': repo_url(),
        'manifest': manifest_check(),
        'inputs': {f: sha256_file(f) for f in sorted(_read_files)},
        'node_counts': dict(sorted(counts.items())),
        'build_errors': errors,
        'python': sys.version.split()[0],
    }
    prov = {'nodes': g.nodes, 'ui_keys': [k for k in ui if not k.startswith('_')],
            'settings': clean(ui.get('_settings', {}))}

    def emit(name, obj):
        bundle_io.write_json_file(os.path.join(BUNDLE, f'{name}.json'), obj)

    emit('provenance', clean(prov))
    emit('story', clean(story_obj))
    emit('series_inputs', clean(series))
    emit('figures', clean(figs))
    emit('results', clean(results))
    emit('scenarios', clean(scenarios_obj))
    emit('controllers', clean(controllers_obj))
    emit('climate', clean(climate_obj))
    emit('cooling', clean(cooling_obj))
    emit('explorer', clean(explorer_obj))
    emit('houses', clean(houses_obj))
    for f in os.listdir(BUNDLE):
        if f.startswith('trace_'):
            os.remove(os.path.join(BUNDLE, f))
    for name, t in traces.items():
        if t['arrays'] is not None:
            emit(f'trace_{name}', clean(t))
    emit('meta', clean(meta))
    print('nodes per kind:')
    for k, v in sorted(counts.items()):
        print(f'  {k:18s} {v}')
    print(f'  {"total":18s} {len(g.nodes)}')
    print(f"git {meta['git']['commit']} dirty={meta['git']['dirty']}  MANIFEST verified={meta['manifest']['verified']}"
          f" ({meta['manifest']['files_listed']} files)  inputs hashed={len(meta['inputs'])}")
    if errors:
        print('BUILD ERRORS:')
        for e in errors:
            print('  ' + e)
        sys.exit(1)


if __name__ == '__main__':
    main()
