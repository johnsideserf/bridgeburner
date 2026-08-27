#!/usr/bin/env python3
"""Live dashboard for solve.py runs.

  # launch the solver and the dashboard together (opens your browser):
  .venv/bin/python dashboard.py -- --rules Current,NoLimit --games 300

  # or just serve an existing / in-progress progress file:
  .venv/bin/python dashboard.py --file runs/progress.jsonl
"""
import argparse, os, subprocess, sys, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "dashboard.html")

def make_handler(progress_path):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path.startswith("/progress.jsonl"):
                try: body = open(progress_path, "rb").read()
                except FileNotFoundError: body = b""
                return self._send(body, "application/x-ndjson")
            if self.path == "/" or self.path.startswith("/index"):
                return self._send(open(PAGE, "rb").read(), "text/html; charset=utf-8")
            self.send_response(404); self.end_headers()
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
