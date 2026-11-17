"""Bundle file format: plain JSON files in web/public/bundle/ (read by the Next.js UI and by lint/tests)."""
import json


def write_json_file(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        f.write('\n')


def read_bundle_file(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
