"""Minimal JSON-Schema validator for the contract schemas (no third-party dependency; the repo pins its environment).

Supported keywords (all schema_gen.py uses): type (string or list), enum, const, properties, required, additionalProperties
(bool or schema), items, minItems, minimum, pattern, oneOf, $ref ("#/$defs/x" and "common.schema.json#/$defs/x"), $defs.
Anything else in a schema raises, so a schema cannot silently use a keyword this validator ignores.
Standard validators (e.g. Python `jsonschema`, Ajv) accept the same files if given common.schema.json as a resolvable resource.
"""
import json
import os
import re

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema')
KNOWN = {'$schema', 'title', '$defs', 'type', 'enum', 'const', 'properties', 'required', 'additionalProperties', 'items', 'minItems', 'minimum', 'pattern', 'oneOf', '$ref'}
TYPES = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}
_cache = {}


def load(name):
    if name not in _cache:
        with open(os.path.join(DIR, f'{name}.schema.json'), encoding='utf-8') as f:
            _cache[name] = json.load(f)
    return _cache[name]


def _is(value, t):
    if t == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if t == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[t])


def _resolve(r, current):
    file, _, frag = r.partition('#')
    root = load(file.replace('.schema.json', '')) if file else current
    node = root
    for part in [p for p in frag.split('/') if p]:
        node = node[part]
    return node, root


def errors(value, schema, root=None, path='$'):
    root = root or schema
    out = []
    bad = set(schema) - KNOWN
    if bad:
        raise ValueError(f'validator does not support keywords {sorted(bad)} at {path}')
    if '$ref' in schema:
        sub, subroot = _resolve(schema['$ref'], root)
        return errors(value, sub, subroot, path)
    if 'oneOf' in schema:
        ok = [s for s in schema['oneOf'] if not errors(value, s, root, path)]
        if len(ok) != 1:
            out.append(f'{path}: matches {len(ok)} of the oneOf alternatives')
    if 'const' in schema and value != schema['const']:
        out.append(f'{path}: expected {schema["const"]!r}, got {value!r}')
    if 'enum' in schema and value not in schema['enum']:
        out.append(f'{path}: {value!r} not in {schema["enum"]}')
    if 'type' in schema:
        ts = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        if not any(_is(value, t) for t in ts):
            return out + [f'{path}: expected {ts}, got {type(value).__name__}']
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 'minimum' in schema and value < schema['minimum']:
        out.append(f'{path}: {value} < minimum {schema["minimum"]}')
    if isinstance(value, str) and 'pattern' in schema and not re.search(schema['pattern'], value):
        out.append(f'{path}: {value!r} does not match {schema["pattern"]}')
    if isinstance(value, dict):
        for k in schema.get('required', []):
            if k not in value:
                out.append(f'{path}: missing required "{k}"')
        props = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        for k, x in value.items():
            if k in props:
                out += errors(x, props[k], root, f'{path}.{k}')
            elif extra is False:
                out.append(f'{path}: unexpected property "{k}"')
            elif isinstance(extra, dict):
                out += errors(x, extra, root, f'{path}.{k}')
    if isinstance(value, list):
        if 'minItems' in schema and len(value) < schema['minItems']:
            out.append(f'{path}: fewer than {schema["minItems"]} items')
        if 'items' in schema:
            for i, x in enumerate(value):
                out += errors(x, schema['items'], root, f'{path}[{i}]')
                if len(out) > 20:
                    return out + ['… (more errors suppressed)']
    return out


def validate_file(path, name):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return errors(data, load(name))
