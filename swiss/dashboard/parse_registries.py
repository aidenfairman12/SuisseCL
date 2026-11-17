"""Registry parsers for the audit dashboard (read-only; stdlib only).

Every parser returns plain dicts with the registry columns verbatim. Rows that do not parse cleanly are kept and
carry a `_parse_warnings` list and the raw source line, so the dashboard can show them instead of hiding them.
The registries in docs/ are never modified here.
"""
import csv
import io
import re

# Registry ID prefixes. `V` (validation checks V1..V8) has no hyphen; everything else needs one, so that plan
# task names such as "A5" or "A4/A5" are not mistaken for assumptions.
HYPHEN_PREFIXES = ('SRC', 'DER', 'TR', 'ISS', 'ALG', 'EXP', 'R', 'M', 'D', 'A')
_P = '|'.join(HYPHEN_PREFIXES)
ID_RE = re.compile(r'(?<![A-Za-z0-9_\-])(' + _P + r')-(\d{3})([a-z]?)(?![A-Za-z0-9])|(?<![A-Za-z0-9_\-])V([1-9]\d?)(?![A-Za-z0-9_.])')
# Ranges: "A-006..A-009", "D-014..D-014e", "ISS-010..012", "EXP-001..006", "D-014/a-e", "D-014a..e"
RANGE_RE = re.compile(r'(?<![A-Za-z0-9_\-])(' + _P + r')-(\d{3})([a-z]?)\s*(?:\.\.|–)\s*(?:(?:' + _P + r')-)?(\d{3})?([a-z]?)(?![A-Za-z0-9])')
SLASH_LETTERS_RE = re.compile(r'(?<![A-Za-z0-9_\-])(' + _P + r')-(\d{3})/([a-z])-([a-z])(?![A-Za-z0-9])')


def extract_ids(text):
    """Return registry IDs mentioned in free text, in order of first appearance, ranges expanded."""
    if not text:
        return []
    text = str(text)
    out = []

    def add(x):
        if x not in out:
            out.append(x)

    spans = []
    for m in SLASH_LETTERS_RE.finditer(text):
        p, n, a, b = m.groups()
        add(f'{p}-{n}')
        for c in range(ord(a), ord(b) + 1):
            add(f'{p}-{n}{chr(c)}')
        spans.append(m.span())
    for m in RANGE_RE.finditer(text):
        p, n1, l1, n2, l2 = m.groups()
        if n2 is None and not l2:
            continue
        if n2 is None or n2 == n1:  # letter range on the same number: D-014..D-014e, D-014a..e
            start = ord(l1) if l1 else ord('a') - 1
            if not l1:
                add(f'{p}-{n1}')
            for c in range(max(start, ord('a')), ord(l2 or 'a') + 1):
                add(f'{p}-{n1}{chr(c)}')
        else:
            i1, i2 = int(n1), int(n2)
            if not (0 < i2 - i1 <= 50):
                continue
            for i in range(i1, i2 + 1):
                add(f'{p}-{i:03d}')
        spans.append(m.span())
    for m in ID_RE.finditer(text):
        if m.group(4):
            add(f'V{m.group(4)}')
        else:
            add(f'{m.group(1)}-{m.group(2)}{m.group(3)}')
    return out


# ---------------------------------------------------------------- markdown tables

def _split_row(line):
    """Split a markdown table row on unescaped pipes outside backtick code spans."""
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|') and not s.endswith('\\|'):
        s = s[:-1]
    cells, cur, in_code, i = [], [], False, 0
    while i < len(s):
        ch = s[i]
        if ch == '\\' and i + 1 < len(s) and s[i + 1] == '|':
            cur.append('|'); i += 2; continue
        if ch == '`':
            in_code = not in_code
        if ch == '|' and not in_code:
            cells.append(''.join(cur).strip()); cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append(''.join(cur).strip())
    return cells


def parse_md_tables(text):
    """Return a list of tables: {'header': [...], 'rows': [{'cells': {...}, 'line': n, 'raw': str, '_parse_warnings': []}]}.
    A table is a header row followed by a |---| separator row; it ends at the first non-table line."""
    lines = text.splitlines()
    tables, i = [], 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith('|') and re.match(r'^\s*\|?\s*:?-{3,}', lines[i + 1]):
            header = _split_row(lines[i])
            t = {'header': header, 'header_line': i + 1, 'rows': []}
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith('|'):
                cells = _split_row(lines[j])
                warn = []
                if len(cells) != len(header):
                    warn.append(f'row has {len(cells)} cells, header has {len(header)}; '
                                f'{"missing cells padded at the end" if len(cells) < len(header) else "extra cells joined into the last column"}'
                                ' - column alignment uncertain, see raw line')
                    if len(cells) < len(header):
                        cells = cells + [''] * (len(header) - len(cells))
                    else:
                        cells = cells[:len(header) - 1] + [' | '.join(cells[len(header) - 1:])]
                t['rows'].append({'cells': dict(zip(header, cells)), 'line': j + 1, 'raw': lines[j],
                                  '_parse_warnings': warn})
                j += 1
            tables.append(t)
            i = j
        else:
            i += 1
    return tables


def parse_md_registry(path, id_col='ID'):
    """Rows of every table in `path` whose first column is `id_col`. Rows keep file order (update rows included)."""
    text = open(path, encoding='utf-8').read()
    rows = []
    for t in parse_md_tables(text):
        if t['header'] and t['header'][0] == id_col:
            rows.extend(t['rows'])
    return rows


# ---------------------------------------------------------------- CSV registries

_CLASS_RE = re.compile(r'^(measured|modeled|modelled|derived|synthetic)\b', re.I)


def _repair_csv_row(fields):
    """Re-join fields split by unquoted commas: thousands separators ("9,747,041") and ", " inside prose."""
    out = []
    for f in fields:
        if out and ((re.match(r'^\d{3}(\D|$)', f) and re.search(r'\d$', out[-1])) or f.startswith(' ')):
            out[-1] += ',' + f
        else:
            out.append(f)
    return out


def parse_csv_registry(path, anchor_col=None):
    """Tolerant CSV reader. Returns (header, rows) with rows = {'cells', 'line', 'raw', '_parse_warnings'}.
    Rows with unquoted commas are repaired (see _repair_csv_row); rows that are still short are aligned on
    `anchor_col` (a classification column recognised by its vocabulary) if possible, otherwise padded at the end."""
    raw_lines = open(path, encoding='utf-8', newline='').read().splitlines()
    reader = csv.reader(io.StringIO('\n'.join(raw_lines)))
    header = next(reader)
    rows = []
    for k, fields in enumerate(reader, start=2):
        if not fields or not any(fields):
            continue
        warn = []
        if len(fields) != len(header):
            fixed = _repair_csv_row(fields)
            warn.append(f'row has {len(fields)} comma-separated fields, header has {len(header)} (unquoted commas)')
            fields = fixed
            if len(fields) == len(header):
                warn.append('repaired by re-joining thousands separators and ", " inside text')
        if len(fields) < len(header):
            ai = header.index(anchor_col) if anchor_col in header else None
            hit = None
            if ai is not None:
                for j in range(max(0, ai - 3), min(len(fields), ai + 1)):
                    if _CLASS_RE.match(fields[j]):
                        hit = j
                        break
            if hit is not None and hit < ai:
                fields = fields[:hit] + [''] * (ai - hit) + fields[hit:]
                warn.append(f'aligned on the {anchor_col} column; {ai - hit} empty cell(s) inserted before it')
            if len(fields) < len(header):
                warn.append(f'{len(header) - len(fields)} missing cell(s) padded at the end')
                fields = fields + [''] * (len(header) - len(fields))
        if len(fields) > len(header):
            warn.append('extra fields joined into the last column - alignment uncertain')
            fields = fields[:len(header) - 1] + [','.join(fields[len(header) - 1:])]
        rows.append({'cells': dict(zip(header, fields)), 'line': k, 'raw': raw_lines[k - 1] if k - 1 < len(raw_lines) else '',
                     '_parse_warnings': warn})
    return header, rows


def normalise_classification(text):
    """Map a free-text classification to measured / derived / modeled / synthetic / mixed (raw text kept elsewhere)."""
    t = (text or '').strip().lower()
    if not t:
        return None
    outside = re.sub(r'\([^)]*\)', ' ', t)
    hits = {('modeled' if w == 'modelled' else w) for w in re.findall(r'measured|derived|modelled|modeled|synthetic', outside)}
    if len(hits) > 1:
        return 'mixed'
    m = _CLASS_RE.match(t)
    if m:
        w = m.group(1).lower()
        return 'modeled' if w == 'modelled' else w
    return next(iter(hits)) if hits else None


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
