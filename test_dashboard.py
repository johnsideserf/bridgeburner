import json, os, subprocess, sys, threading, unittest, urllib.request
from http.server import HTTPServer
import dashboard

SCRATCH = os.environ.get("BB_SCRATCH", "/tmp")

class ProgressEvents(unittest.TestCase):
    def test_solver_writes_progress_events(self):
        path = os.path.join(SCRATCH, "progress_test.jsonl")
        if os.path.exists(path): os.remove(path)
        subprocess.run([sys.executable, "solve.py", "--games", "4", "--iters", "1",
                        "--restarts", "0", "--heldout", "1", "--rules", "Current",
                        "--progress", path], check=True, capture_output=True)
        events = [json.loads(l) for l in open(path)]
        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "start")
        self.assertIn("ruleset", kinds); self.assertIn("search", kinds)
        self.assertIn("iter", kinds); self.assertIn("final", kinds)
        self.assertEqual(kinds[-1], "done")
        it = next(e for e in events if e["event"] == "iter")
        for k in ("ruleset", "iter", "brw", "search_w", "mix", "exploiter"): self.assertIn(k, it)
        fin = next(e for e in events if e["event"] == "final")
        for k in ("ruleset", "exploit", "support", "first_player", "comeback4",
                  "stalls", "avg_turns", "burns_per_game", "mix"): self.assertIn(k, fin)
        s = next(e for e in events if e["event"] == "search")
        for k in ("ruleset", "iter", "n", "w", "best"): self.assertIn(k, s)

class Server(unittest.TestCase):
    def test_serves_page_and_progress(self):
        path = os.path.join(SCRATCH, "progress_serve.jsonl")
        open(path, "w").write('{"event":"start"}\n')
        srv = HTTPServer(("127.0.0.1", 0), dashboard.make_handler(path))
        t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
        try:
            base = f"http://127.0.0.1:{srv.server_port}"
            page = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn("<title>", page); self.assertIn("progress.jsonl", page)
            prog = urllib.request.urlopen(base + "/progress.jsonl").read().decode()
            self.assertEqual(prog, '{"event":"start"}\n')
            self.assertEqual(urllib.request.urlopen(base + "/progress.jsonl").headers["Cache-Control"], "no-store")
        finally:
            srv.shutdown()

if __name__ == "__main__":
    unittest.main()
