"""Use It Up pantry sync server (loopback only, standard library only).

Serves the shared pantry for a few phones. Put it behind Tailscale Serve:
    tailscale serve --bg --set-path /sync http://127.0.0.1:11437

    python sync-server.py [listen_port=11437] [data_dir=<next to this file>/sync-data]

API (the "code" is a long random string that acts as both the pantry id and its password):
    GET  /sync/<code>   -> {"items":[...], "hist":[...], "tomb":{id: ts}, "rules":[...]}
    POST /sync/<code>   body = same shape; merged into the stored pantry, merged result returned.

Merge rules (items never change after they are added, so this is simple and conflict-free):
    * an item exists if it was added on any phone and not deleted on any phone
    * a deletion is remembered as a tombstone {id: ms-timestamp} for 120 days
    * history entries are unioned by id
    * ingredient-match rules (alias / not) are unioned by id, minus tombstones, like items
"""
import json, os, re, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 11437
DATA = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync-data')
os.makedirs(DATA, exist_ok=True)
CODE_RE = re.compile(r'^[A-Za-z0-9_-]{16,64}$')
TOMB_KEEP_MS = 120 * 24 * 3600 * 1000
MAX_BODY = 2 * 1024 * 1024
LOCK = threading.Lock()


def path_for(code):
    return os.path.join(DATA, code + '.json')


def read_state(code):
    try:
        with open(path_for(code), 'r', encoding='utf-8') as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    return {'items': s.get('items', []), 'hist': s.get('hist', []), 'tomb': s.get('tomb', {}), 'rules': s.get('rules', [])}


def write_state(code, s):
    tmp = path_for(code) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(s, f)
    os.replace(tmp, path_for(code))  # atomic: a crash never leaves a half-written file


def merge(a, b):
    """Merge two states {items, hist, tomb}."""
    now = int(time.time() * 1000)
    tomb = dict(a['tomb'])
    for k, v in (b.get('tomb') or {}).items():
        if isinstance(v, (int, float)):
            tomb[k] = max(tomb.get(k, 0), v)
    tomb = {k: v for k, v in tomb.items() if now - v < TOMB_KEEP_MS}
    items = {}
    for it in list(a['items']) + list(b.get('items') or []):
        if isinstance(it, dict) and isinstance(it.get('id'), str) and it['id'] not in tomb and it['id'] not in items:
            items[it['id']] = it
    hist = {}
    for h in list(a['hist']) + list(b.get('hist') or []):
        if isinstance(h, dict) and isinstance(h.get('id'), str) and h['id'] not in hist:
            hist[h['id']] = h
    rules = {}   # the household's ingredient-match fixes: immutable, removed via tombstones like items
    for r in list(a.get('rules', [])) + list(b.get('rules') or []):
        if isinstance(r, dict) and isinstance(r.get('id'), str) and r['id'] not in tomb and r['id'] not in rules:
            rules[r['id']] = r
    return {'items': list(items.values()), 'hist': list(hist.values()), 'tomb': tomb, 'rules': list(rules.values())}


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, status, obj=None):
        body = json.dumps(obj).encode('utf-8') if obj is not None else b''
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Cache-Control', 'no-store')
        if obj is not None:
            self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _code(self):
        m = re.match(r'^(?:/sync)?/([^/?]+)/?(?:\?.*)?$', self.path)
        return m.group(1) if m and CODE_RE.match(m.group(1)) else None

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        if re.match(r'^(?:/sync)?/?(?:\?.*)?$', self.path):
            return self._send(200, {'ok': True, 'service': 'use-it-up-sync'})  # health check, no data
        code = self._code()
        if not code:
            return self._send(400, {'error': 'bad pantry code'})
        with LOCK:
            self._send(200, read_state(code))

    def do_POST(self):
        code = self._code()
        if not code:
            return self._send(400, {'error': 'bad pantry code'})
        n = int(self.headers.get('Content-Length') or 0)
        if n > MAX_BODY:
            return self._send(413, {'error': 'too big'})
        try:
            incoming = json.loads(self.rfile.read(n) or b'{}')
            if not isinstance(incoming, dict):
                raise ValueError
        except ValueError:
            return self._send(400, {'error': 'bad json'})
        try:
            with LOCK:
                merged = merge(read_state(code), incoming)
                write_state(code, merged)
        except Exception as e:  # report instead of dropping the connection
            return self._send(500, {'error': 'server could not save: %r' % (e,)})
        self._send(200, merged)


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    srv.daemon_threads = True
    srv.serve_forever()
