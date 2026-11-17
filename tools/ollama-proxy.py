"""
Tiny loopback-only proxy in front of Ollama.

Why: Ollama (while bound to 127.0.0.1) rejects requests whose Host header isn't localhost / *.local, which is
exactly what `tailscale serve` sends (your .ts.net name) -> HTTP 403. This proxy forwards everything to Ollama
with the Host header rewritten to "localhost:<ollama port>". Nothing else is changed (CORS comes from Ollama itself).

Usage:  pythonw ollama-proxy.py [listen_port] [ollama_port]      (defaults: 11436 11434)
Listens on 127.0.0.1 only — never reachable from the network except through `tailscale serve`.
"""
import http.client
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN = int(sys.argv[1]) if len(sys.argv) > 1 else 11436
UPSTREAM = int(sys.argv[2]) if len(sys.argv) > 2 else 11434
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
       "transfer-encoding", "upgrade", "host", "content-length"}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"          # close the connection to end each response (also works for streaming)

    def log_message(self, *args):
        pass

    def _forward(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        headers["Host"] = f"localhost:{UPSTREAM}"
        if body is not None:
            headers["Content-Length"] = str(len(body))
        conn = http.client.HTTPConnection("127.0.0.1", UPSTREAM, timeout=900)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() not in HOP:
                    self.send_header(k, v)
            # Chrome's "Private Network Access" rule: a public https page may call a private address only if the
            # preflight says so. Harmless for other browsers.
            if self.command == "OPTIONS" and self.headers.get("Access-Control-Request-Private-Network"):
                self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception as e:             # Ollama down, client went away, etc.
            try:
                self.send_error(502, f"Ollama unreachable: {e}")
            except Exception:
                pass
        finally:
            conn.close()

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = _forward


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", LISTEN), Proxy).serve_forever()
