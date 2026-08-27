import json, os, subprocess, sys, threading, unittest, urllib.request
from http.server import HTTPServer
import dashboard

SCRATCH = os.environ.get("BB_SCRATCH", "/tmp")
HERE = os.path.dirname(os.path.abspath(__file__))

class ProgressEvents(unittest.TestCase):
    def test_solver_writes_progress_events(self):
        path = os.path.join(SCRATCH, "progress_test.jsonl")
        if os.path.exists(path): os.remove(path)
        subprocess.run([sys.executable, os.path.join(HERE, "solve.py"), "--games", "4", "--iters", "1",
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

class GameApi(unittest.TestCase):
    def setUp(self):
        path = os.path.join(SCRATCH, "progress_api.jsonl"); open(path, "w").close()
        self.srv = HTTPServer(("127.0.0.1", 0), dashboard.make_handler(path))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"
    def tearDown(self): self.srv.shutdown()
    def post(self, path, obj):
        req = urllib.request.Request(self.base + path, data=json.dumps(obj).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            r = urllib.request.urlopen(req); return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_play_page_and_options(self):
        page = urllib.request.urlopen(self.base + "/play").read().decode()
        self.assertIn("<title>", page); self.assertIn("/api/", page)
        opts = json.loads(urllib.request.urlopen(self.base + "/api/options").read())
        self.assertIn("Equilibrium", opts["bots"]); self.assertIn("Current", opts["rulesets"])

    def test_replay_endpoint(self):
        r = json.loads(urllib.request.urlopen(self.base + "/api/replay?seed=2&a=Builder&b=Equilibrium&rules=Current").read())
        self.assertGreater(len(r["frames"]), 5)

    def test_new_and_act(self):
        code, r = self.post("/api/new", {"rules": "Current", "bot": "Equilibrium", "seed": 1, "human_first": True})
        self.assertEqual(code, 200); self.assertIn("id", r); self.assertEqual(r["state"]["left"], 2)
        code, r2 = self.post("/api/act", {"id": r["id"], "action": [0]})
        self.assertEqual(code, 200); self.assertEqual(r2["state"]["left"], 1)
        code, r3 = self.post("/api/act", {"id": r["id"], "action": [2, [1, 0]]})
        self.assertEqual(code, 400); self.assertIn("error", r3)
        code, r4 = self.post("/api/act", {"id": "nope", "action": [0]})
        self.assertEqual(code, 404)


class RequestHardening(GameApi):
    def get(self, path, headers=None):
        req = urllib.request.Request(self.base + path, headers=headers or {})
        try:
            r = urllib.request.urlopen(req); return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_foreign_host_or_origin_rejected(self):
        self.assertEqual(self.get("/api/options", {"Host": "evil.example:8765"})[0], 403)
        self.assertEqual(self.get("/api/options", {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.get("/api/options", {"Origin": "http://127.0.0.1:8765"})[0], 200)

    def test_post_requires_json_object(self):
        req = urllib.request.Request(self.base + "/api/new", data=b'{"rules":"Current"}',
                                     headers={"Content-Type": "text/plain"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm: urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 415)
        self.assertEqual(self.post("/api/new", [1, 2])[0], 400)
        self.assertEqual(self.post("/api/new", {"rules": ["Current"]})[0], 400)   # unhashable -> TypeError -> 400
        self.assertEqual(self.post("/api/new", {"bot": {"x": 1}})[0], 400)

    def test_progress_offset(self):
        path = os.path.join(SCRATCH, "progress_api.jsonl")
        open(path, "w").write('{"event":"start"}\n{"event":"done"}\n')
        full = self.get("/progress.jsonl")[1]
        tail = self.get("/progress.jsonl?offset=%d" % len('{"event":"start"}\n'))[1]
        self.assertEqual(tail, b'{"event":"done"}\n')
        self.assertEqual(self.get("/progress.jsonl?offset=%d" % len(full))[1], b"")
        self.assertEqual(self.get("/progress.jsonl?offset=junk")[1], full)

if __name__ == "__main__":
    unittest.main()
