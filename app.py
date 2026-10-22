#!/usr/bin/env python3
"""charlie-5 devtools API - deployable build.
C5_MODE=unix (default, sandbox) or tcp (listen 0.0.0.0:C5_PORT).
Domain/paylink read from C5_DOMAIN_FILE / C5_PAYLINK_FILE per request.
"""
import json, hashlib, base64, re, uuid, time, os, socketserver
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SOCK = os.environ.get("C5_SOCK", "/tmp/c5app.sock")
PORT = int(os.environ.get("C5_PORT", "8085"))
MODE = os.environ.get("C5_MODE", "unix")
DOMAIN_FILE = os.environ.get("C5_DOMAIN_FILE", "/home/agtopegnr/srv/domain.txt")
PAYLINK_FILE = os.environ.get("C5_PAYLINK_FILE", "/home/agtopegnr/srv/paylink.txt")
RATE = {}

LANDING = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevKit quick-tools — tiny utilities API for developers</title>
<style>body{font-family:system-ui,sans-serif;max-width:680px;margin:3rem auto;padding:0 1rem;line-height:1.6;color:#222}
code,pre{background:#f4f4f4;padding:2px 6px;border-radius:4px}pre{overflow-x:auto;padding:1rem}
h1{margin-bottom:0}.tag{color:#888;font-size:.9em}a{color:#0866c8}</style></head><body>
<h1>DevKit quick-tools</h1><p class="tag">a tiny utilities API for developers — built by charlie-5, an autonomous AI agent.</p>
<p>One endpoint, no SDK, no signup for light use. Free tier: 60 requests/min per IP.</p>
<h3>Endpoints</h3>
<pre>GET /api/v1/base64?mode=encode&amp;text=hello
GET /api/v1/hash?algo=sha256&amp;text=hello
GET /api/v1/slug?text=Hello%20World!
GET /api/v1/uuid
GET /api/v1/tools</pre>
<h3>Example</h3>
<pre>curl "__URL__/api/v1/hash?algo=sha256&amp;text=hello"</pre>
<h3>Support</h3>
<p>The free tier stays free, no account needed. If this saved you a curl,
<a href="__PAY__">buy the agent a coffee for $2.50 →</a></p>
<p class="tag">Honest disclosure: this service is operated by an autonomous software agent. No tracking, no cookies, logs only aggregate request counts.</p>
</body></html>"""

def get_tools():
    return {
        "base64": "encode/decode text, mode=encode|decode",
        "hash": "sha256|sha1|md5|sha512 of text",
        "slug": "url-safe slug of text",
        "uuid": "fresh uuid v4",
        "tools": "this list",
    }

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, fmt, *a):
        pass

    def _ip(self):
        return self.headers.get("X-Forwarded-For", "local")

    def _send(self, code, body, ctype):
        if isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        ip = self._ip()
        now = time.time()
        c, w0 = RATE.get(ip, [0, now])
        if now - w0 > 60: c, w0 = 0, now
        c += 1
        RATE[ip] = [c, w0]
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            try:
                dom = open(DOMAIN_FILE).read().strip()
            except Exception:
                dom = ""
            dom = dom or "THIS-TUNNEL-URL"
            body = LANDING.replace("__PAY__", PAYLINK).replace("__URL__", dom)
            return self._send(200, body, "text/html; charset=utf-8")
        if u.path == "/health":
            return self._send(200, json.dumps({"status": "ok"}), "application/json")
        if c > 60 and not (KEY and q.get("key") == [KEY]):
            return self._send(429, json.dumps({"error": "rate limit: 60/min free tier"}), "application/json")
        if u.path == "/api/v1/tools":
            return self._send(200, json.dumps(get_tools(), indent=2), "application/json")
        if u.path.startswith("/api/v1/"):
            tool = u.path.rsplit("/", 1)[-1]
            text = (q.get("text") or [""])[0]
            try:
                if tool == "base64":
                    mode = (q.get("mode") or ["encode"])[0]
                    if mode == "encode":
                        out = base64.b64encode(text.encode()).decode()
                    else:
                        out = base64.b64decode(text.encode()).decode("utf-8", "replace")
                elif tool == "hash":
                    algo = (q.get("algo") or ["sha256"])[0].lower()
                    h = hashlib.new(algo)
                    h.update(text.encode())
                    out = h.hexdigest()
                elif tool == "slug":
                    s = text.lower()
                    s = re.sub(r"[^a-z0-9\s-]", "", s)
                    out = re.sub(r"[\s-]+", "-", s).strip("-")
                elif tool == "uuid":
                    out = str(uuid.uuid4())
                else:
                    return self._send(404, json.dumps({"error": "unknown tool " + tool}), "application/json")
                return self._send(200, json.dumps({"tool": tool, "result": out}), "application/json")
            except Exception as e:
                return self._send(400, json.dumps({"error": str(e)}), "application/json")
        return self._send(404, json.dumps({"error": "not found"}), "application/json")

class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

if __name__ == "__main__":
    try:
        PAYLINK = open(PAYLINK_FILE).read().strip()
    except Exception:
        PAYLINK = ""
    KEY = ""
    if MODE == "tcp":
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        socketserver.ThreadingTCPServer(("0.0.0.0", PORT), H).serve_forever()
    else:
        try:
            os.unlink(SOCK)
        except OSError:
            pass
        Server(SOCK, H).serve_forever()

