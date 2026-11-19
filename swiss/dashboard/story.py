"""Story-page content for the dashboard: display names, glossary, filled prose and the numbers behind it.

Everything shown comes from repository files: results CSVs, QC reports, the validation table, docs/master_plan.md and the
plain-language sections (`_controllers`, `_buildings`, `_pages`, `_glossary`, `_story`) of ui_map.yaml. The UI computes nothing:
percent changes, counts and the winter day are computed here, so lint and tests can check them.
"""
import datetime as dt
import re

REF = 'ALG-001_zero_action'
BAU = 'ALG-002_business_as_usual'
NIGHT = 'ALG-003_basic_rbc'
TERM_RE = re.compile(r'\[\[([^\]|]+)\|([a-z_0-9]+)\]\]')
ID_PATTERN = re.compile(r'\b(SRC|DER|TR|M|D|A|ISS|ALG|R|EXP)-\d')
STORY_KPIS = ('cost_chf_excl_vat', 'district_peak_kw', 'district_import_kwh')


def parse_master_plan(text):
    """Phases from docs/master_plan.md section 2: letter, focus (table) and objective (first sentence of each phase)."""
    sec = text[text.index('## 2. Phase roadmap'):text.index('## 3.')]
    focus = {m.group(1): m.group(2).strip() for m in re.finditer(r'^\|\s*([A-Z])\s*\|\s*([^|]+?)\s*\|', sec, re.M)}
    obj = {m.group(1): m.group(3).strip() for m in re.finditer(r'^### Phase ([A-Z]) — (.+?)\n\n\*\*Objective:\*\* (.+?)\n', sec, re.M)}
    phases = [{'letter': k, 'focus': focus[k], 'objective': obj[k]} for k in sorted(focus) if k in obj]
    if not phases:
        raise ValueError('no phases found in docs/master_plan.md section 2')
    return phases


def pct(row, ref, col):
    return (row[col] - ref[col]) / abs(ref[col]) * 100.0


def winter_day(si):
    """Coldest weekday that starts at local midnight and lies fully inside the 8,759-step simulation."""
    temp, lh, wd, off = si['series']['temp_c']['values'], si['local_hour'], si['weekday'], si['utc_offset_h']
    best = None
    for i in range(0, si['n'] - 24):
        if lh[i] != 0 or wd[i] >= 5 or i + 24 > 8759 or any(v is None for v in temp[i:i + 24]):
            continue
        m = sum(temp[i:i + 24]) / 24
        if best is None or m < best[1]:
            best = (i, m)
    i, m = best
    t0 = dt.datetime.strptime(si['start_utc'], '%Y-%m-%dT%H:%M:%SZ')
    local = t0 + dt.timedelta(seconds=i * si['step_s'] + off[i] * 3600)
    return {'index': i, 'date': local.strftime('%Y-%m-%d'), 'mean_temp_c': round(m, 2),
            'label': local.strftime('%A %Y-%m-%d'), 'hours': 24}


def compute_derived(data, graph_nodes, si, phases):
    res, sens = data['results'], data['sensitivity']
    ref = res[REF]
    rule_row = res[NIGHT]
    derived = {
        'n_buildings': len(data['build_manifest']),
        'n_houses': sum(1 for b in data['build_manifest'].values() if b['role'].startswith('SFH')),
        'n_apartments': sum(1 for b in data['build_manifest'].values() if b['role'].startswith('MFH')),
        'hours': si['n'],
        'phases': {'count': len(phases), 'a': phases[0], **{p['letter'].lower(): p for p in phases}},
        'rule': {'cost_pct': pct(rule_row, ref, 'cost_chf_excl_vat'), 'peak_cut_pct': -pct(rule_row, ref, 'district_peak_kw'),
                 'import_pct': pct(rule_row, ref, 'district_import_kwh'),
                 # percentage points of annual import moved out of the high-tariff hours (from sensitivity_2023.csv)
                 'shift_pts': -sens['reference|basic_rbc']['high_tariff_share_pts_vs_zero']},
    }
    tr = [c for c in res if c.startswith('ALG-004')]
    cost = [pct(res[c], ref, 'cost_chf_excl_vat') for c in tr]
    peak = [pct(res[c], ref, 'district_peak_kw') for c in tr]
    derived['tariff_rules'] = {'cost_min': min(cost), 'cost_max': max(cost), 'peak_min': min(peak), 'peak_max': max(peak)}
    checks = [n for n in graph_nodes.values() if n['kind'] == 'validation_check']
    derived['validation'] = {'total': len(checks), 'passed': sum(1 for n in checks if n.get('passed'))}
    derived['day'] = winter_day(si)
    return derived


def names_namespace(controllers):
    n = {c['key']: c['display_name'] for c in controllers.values()}
    n['night_lower'] = n['night'][0].lower() + n['night'][1:]
    return n


def fill_tree(obj, fill, errors, where):
    """Fill {placeholders} in every string of a nested structure (lists/dicts); [[term|id]] markup is left in place."""
    if isinstance(obj, str):
        return fill(re.sub(r'\s+', ' ', obj.strip()), errors, where)
    if isinstance(obj, list):
        return [fill_tree(x, fill, errors, f'{where}[{i}]') for i, x in enumerate(obj)]
    if isinstance(obj, dict):
        return {k: fill_tree(v, fill, errors, f'{where}.{k}') for k, v in obj.items()}
    return obj


def build_story(ui, data, derived, graph_nodes, phases, fill, errors):
    controllers = ui['_controllers']
    for c in data['results']:
        if c not in controllers:
            errors.append(f'story: controller {c} has no display name in ui_map _controllers')
    story = fill_tree(ui['_story'], fill, errors, '_story')
    res, ref = data['results'], data['results'][REF]
    night = res[NIGHT]
    tiles = []
    for col in STORY_KPIS:
        node = graph_nodes[f'kpi:{col}']
        tiles.append({'node': f'kpi:{col}', 'label': node.get('display_name') or node['title'], 'unit': node['fields'].get('unit', ''),
                      'value': night[col], 'reference': ref[col], 'vs_none_pct': pct(night, ref, col)})
    story['findings']['tiles'] = tiles
    story['findings']['day'] = derived['day']
    story['findings']['rule'] = {'controller': NIGHT, 'name': controllers[NIGHT]['display_name']}
    story['findings']['reference'] = {'controller': REF, 'name': controllers[REF]['display_name']}
    shown = story['next'].pop('phases_shown')
    story['next']['phases'] = [p for p in phases if p['letter'] in shown]
    glossary = fill_tree(ui['_glossary'], fill, errors, '_glossary')
    for g in glossary:
        if g.get('node') and g['node'] not in graph_nodes:
            errors.append(f"glossary: term {g['id']} points at unknown node {g['node']}")
    return {
        'controllers': controllers, 'buildings': ui['_buildings'], 'building_groups': ui['_building_groups'],
        'carbon_relative': ui['_carbon_relative'], 'pages': ui['_pages'],
        'glossary': glossary, 'story': story, 'phases': phases, 'derived': {'day': derived['day']},
    }


def check_prose(ui, prose_digits):
    """Lint-style checks on the plain-language layer. Returns a list of error strings."""
    errs = []
    gl_ids = {g['id'] for g in ui.get('_glossary', [])}

    def walk(o, where):
        if isinstance(o, str):
            yield where, o
        elif isinstance(o, list):
            for i, x in enumerate(o):
                yield from walk(x, f'{where}[{i}]')
        elif isinstance(o, dict):
            for k, v in o.items():
                yield from walk(v, f'{where}.{k}')

    for sec in ('_story', '_glossary', '_pages', '_buildings', '_building_groups', '_carbon_relative', '_phase_b', '_phase_c'):
        for where, text in walk(ui.get(sec, {}), sec):
            if where.endswith(('.node', '.id', '.key')) or '.nodes[' in where or '.limitations[' in where or '.pending_register[' in where and where.endswith('.title') or '.classes[' in where:
                continue          # identifiers (registry IDs, classification names) are links, not shown prose
            for d in prose_digits(text, ui['_settings'].get('prose_allowed_tokens', [])):
                errs.append(f'story prose: {where} has a number outside a placeholder: "{d}"')
            if ID_PATTERN.search(re.sub(r'\{[^{}]*\}', ' ', text)):   # placeholders are data lookups, not shown text
                errs.append(f'story prose: {where} contains a registry ID (IDs belong in audit cards only)')
            for m in TERM_RE.finditer(text):
                if m.group(2) not in gl_ids:
                    errs.append(f'story prose: {where} uses unknown glossary term "{m.group(2)}"')
    for c, e in (ui.get('_controllers') or {}).items():
        if not e.get('display_name'):
            errs.append(f'display names: controller {c} has no display_name')
    return errs
