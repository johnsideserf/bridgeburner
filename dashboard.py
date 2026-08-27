#!/usr/bin/env python3
"""Live dashboard for solve.py runs.

  # launch the solver and the dashboard together (opens your browser):
  .venv/bin/python dashboard.py -- --rules Current,NoLimit --games 300

  # or just serve an existing / in-progress progress file:
  .venv/bin/python dashboard.py --file runs/progress.jsonl
"""
import argparse, json, os, subprocess, sys, threading, uuid, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "dashboard.html")
PLAY_PAGE = os.path.join(HERE, "play.html")

SESSIONS = {}          # id -> game_session.Session (in-memory, single process)
SESSIONS_LOCK = threading.Lock()
MAX_BODY = 64 * 1024
LOOPBACK = {"127.0.0.1", "localhost", "[::1]", "::1"}

def _loopback(hostport):
    """True if a Host/Origin host (with optional port/scheme) is loopback."""
    if not hostport: return False
    h = hostport.split("://", 1)[-1]
    if h.startswith("["): h = h.split("]", 1)[0] + "]"
    else: h = h.split(":", 1)[0]
    return h.lower() in LOOPBACK

def make_handler(progress_path):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def _json(self, obj, status=200):
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def _local_only(self):
            """Reject DNS-rebound / cross-origin requests: Host and any Origin
            must be loopback (the server only ever binds 127.0.0.1)."""
            if not _loopback(self.headers.get("Host")) or \
               ("Origin" in self.headers and not _loopback(self.headers["Origin"])):
                self._json({"error": "forbidden"}, 403); return False
            return True
        def do_GET(self):
            if not self._local_only(): return
            u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path == "/progress.jsonl":
                # ?offset=N returns only bytes from N on, so the page can poll
                # incrementally instead of re-downloading a growing file.
                try: off = max(0, int(q.get("offset", 0)))
                except ValueError: off = 0
                try:
                    with open(progress_path, "rb") as f:
                        f.seek(off); body = f.read()
                except FileNotFoundError: body = b""
                return self._send(body, "application/x-ndjson")
            if u.path in ("/", "/index.html"):
                return self._send(open(PAGE, "rb").read(), "text/html; charset=utf-8")
            if u.path in ("/play", "/play.html"):
                return self._send(open(PLAY_PAGE, "rb").read(), "text/html; charset=utf-8")
            if u.path == "/api/options":
                from trace_game import STRATEGIES
                from solve import RULESETS
                return self._json({"bots": list(STRATEGIES), "rulesets": list(RULESETS)})
            if u.path == "/api/replay":
                from game_session import replay_frames
                from solve import RULESETS
                try:
                    return self._json(replay_frames(seed=int(q.get("seed", 0)),
                                                    a=q.get("a", "Equilibrium"), b=q.get("b", "Equilibrium"),
                                                    rules=RULESETS[q.get("rules", "Current")]))
                except (KeyError, ValueError) as e:
                    return self._json({"error": str(e)}, 400)
            self.send_response(404); self.end_headers()
        def do_POST(self):
            from game_session import Session
            from solve import RULESETS
            if not self._local_only(): return
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json({"error": "Content-Type must be application/json"}, 415)
            try: n = int(self.headers.get("Content-Length", 0))
            except ValueError: return self._json({"error": "bad Content-Length"}, 400)
            if n > MAX_BODY: return self._json({"error": "body too large"}, 413)
            try: body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError: return self._json({"error": "bad json"}, 400)
            if not isinstance(body, dict): return self._json({"error": "body must be an object"}, 400)
            if self.path == "/api/new":
                try:
                    s = Session(rules=RULESETS[body.get("rules", "Current")], bot=body.get("bot", "Equilibrium"),
                                seed=int(body.get("seed", 0)), human_first=bool(body.get("human_first", True)))
                except (KeyError, ValueError, TypeError) as e:
                    return self._json({"error": str(e)}, 400)
                sid = uuid.uuid4().hex[:12]
                with SESSIONS_LOCK:
                    if len(SESSIONS) > 200: SESSIONS.pop(next(iter(SESSIONS)))
                    SESSIONS[sid] = s
                return self._json({"id": sid, "state": s.state()})
            if self.path == "/api/act":
                with SESSIONS_LOCK: s = SESSIONS.get(body.get("id"))
                if s is None: return self._json({"error": "no such game"}, 404)
                try:
                    with SESSIONS_LOCK: st = s.act(body.get("action"))
                except (ValueError, TypeError) as e:
                    return self._json({"error": str(e)}, 400)
                return self._json({"id": body["id"], "state": st})
            self._json({"error": "not found"}, 404)
    return H

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=os.path.join(HERE, "runs", "progress.jsonl"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("solver_args", nargs="*",
                    help="after '--': arguments for solve.py (launches it)")
    args = ap.parse_args()
    d = os.path.dirname(args.file)
    if d: os.makedirs(d, exist_ok=True)
    proc = None
    if args.solver_args:
        open(args.file, "w").close()
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "solve.py"),
                                 "--progress", args.file] + args.solver_args)
    srv = HTTPServer(("127.0.0.1", args.port), make_handler(args.file))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"dashboard: {url}   progress file: {args.file}")
    if not args.no_browser: webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if proc and proc.poll() is None: proc.terminate()

if __name__ == "__main__":
    main()
