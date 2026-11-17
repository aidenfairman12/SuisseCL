"""Serve the repo root on 127.0.0.1 with caching disabled, so a rebuilt bundle shows up on reload.
Open http://127.0.0.1:8000/dashboard/ (repo root is served so the cards' links to docs/*.md work).
Run: cl/bin/python -I swiss/dashboard/serve.py [port]"""
import functools
import http.server
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(NoCache, directory=ROOT)).serve_forever()
