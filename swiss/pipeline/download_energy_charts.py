"""Resumable, throttled download of Energy-Charts data (SRC-011) for the carbon reconstruction (D-013).

Raw JSON responses are stored unmodified in data/raw/energy_charts/ (one file per request; existing files are skipped).
Windows are UTC month chunks covering:
  2023 local year  : 2022-12-31T23:00Z .. 2023-12-31T23:00Z
  2016-2017 (EPFL reference GMT+1): 2015-12-31T23:00Z .. 2017-12-31T23:00Z
Endpoints: public_power for ch, de, fr, at, it ; cbpf for ch (cross-border physical flows).
Licence: CC BY 4.0, attribution "energy-charts.info". Rate limit: 2 requests/minute -> 31 s spacing, honours Retry-After.

Run: cl/bin/python -I swiss/pipeline/download_energy_charts.py [2023|2016-17|all]
"""
import json
import os
import sys
import time
import subprocess
import urllib.parse

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'data', 'raw', 'energy_charts')
BASE = 'https://api.energy-charts.info'
SPACING = 31
UA = 'swiss-citylearn-research-client'


def month_windows(start, end):
    edges = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq='MS', tz='UTC')
    # month boundaries expressed at 23:00Z of previous day (local midnight in CET)
    pts = [pd.Timestamp(start, tz='UTC')]
    cur = pd.Timestamp(start, tz='UTC')
    endt = pd.Timestamp(end, tz='UTC')
    while cur < endt:
        nxt = (cur + pd.offsets.MonthBegin(1)).normalize() - pd.Timedelta(hours=1)
        if nxt <= cur:
            nxt = (cur + pd.offsets.MonthBegin(2)).normalize() - pd.Timedelta(hours=1)
        nxt = min(nxt, endt)
        pts.append(nxt)
        cur = nxt
    return list(zip(pts[:-1], pts[1:]))


def jobs(which):
    spans = []
    if which in ('2023', 'all'):
        spans.append(('2022-12-31 23:00', '2023-12-31 23:00'))
    if which in ('2016-17', 'all'):
        spans.append(('2015-12-31 23:00', '2017-12-31 23:00'))
    for s, e in spans:
        for a, b in month_windows(s, e):
            for country in ['ch', 'de', 'fr', 'at', 'it']:
                yield 'public_power', country, a, b
            yield 'cbpf', 'ch', a, b


def fetch(endpoint, country, a, b):
    # end is exclusive-ish in the API; ask for the last quarter-hour of the window
    end = b - pd.Timedelta(minutes=15)
    q = urllib.parse.urlencode({'country': country, 'start': a.strftime('%Y-%m-%dT%H:%MZ'), 'end': end.strftime('%Y-%m-%dT%H:%MZ')})
    # curl is used because the python.org interpreter in cl/ has no CA bundle (TLS verification stays ON)
    r = subprocess.run(['curl', '-sS', '--max-time', '60', '-A', UA, '-D', '-', '-o', '-', f'{BASE}/{endpoint}?{q}'],
                       capture_output=True)
    head, _, body = r.stdout.partition(b'\r\n\r\n')
    code = int(head.split(b' ', 2)[1]) if head.startswith(b'HTTP') else 0
    if code != 200:
        retry = 60
        for line in head.split(b'\r\n'):
            if line.lower().startswith(b'retry-after:'):
                retry = int(line.split(b':')[1])
        raise RuntimeError(f'http {code} retry {retry} {r.stderr[:80]!r}')
    return body


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    os.makedirs(OUT, exist_ok=True)
    todo = list(jobs(which))
    print('requests planned', len(todo), flush=True)
    for i, (ep, c, a, b) in enumerate(todo, 1):
        fn = os.path.join(OUT, f"{ep}_{c}_{a.strftime('%Y%m%dT%H%MZ')}_{b.strftime('%Y%m%dT%H%MZ')}.json")
        if os.path.exists(fn):
            continue
        for attempt in range(6):
            try:
                body = fetch(ep, c, a, b)
                json.loads(body)  # validate
                open(fn, 'wb').write(body)
                print(i, 'ok', os.path.basename(fn), len(body), flush=True)
                break
            except Exception as e:  # HTTP/network/JSON error
                msg = str(e)
                wait = int(msg.split('retry ')[1].split()[0]) if 'retry ' in msg else 60
                print(i, 'err', msg[:120], 'wait', wait, flush=True)
                time.sleep(wait + 1)
        time.sleep(SPACING)
    print('finished', flush=True)
