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
        def do_GET(self):
            u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path == "/progress.jsonl":
                try: body = open(progress_path, "rb").read()
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
            n = int(self.headers.get("Content-Length", 0))
            try: body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError: return self._json({"error": "bad json"}, 400)
            if self.path == "/api/new":
                try:
                    s = Session(rules=RULESETS[body.get("rules", "Current")], bot=body.get("bot", "Equilibrium"),
                                seed=int(body.get("seed", 0)), human_first=bool(body.get("human_first", True)))
                except (KeyError, ValueError) as e:
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
    os.makedirs(os.path.dirname(args.file), exist_ok=True)
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
