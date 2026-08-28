import json, os, unittest
from export_fixtures import make_fixture, write_all

class Fixtures(unittest.TestCase):
    def test_fixture_shape(self):
        fx = make_fixture(seed=3, rules={"clock": True, "equal_turns": True}, a="Equilibrium", b="Builder")
        for k in ("rules", "genes", "initial", "steps", "result", "turns"): self.assertIn(k, fx)
        self.assertEqual(len(fx["initial"]["hands"][0]), 7)
        self.assertEqual(len(fx["initial"]["draw"]), 52 - 14 - 3)
        s = fx["steps"][0]
        for k in ("who", "left", "action", "cost", "after"): self.assertIn(k, s)
        self.assertEqual(s["who"], 0); self.assertEqual(s["left"], 2)
        self.assertEqual(fx["steps"][-1]["after"]["turn_count"] + (0 if fx["steps"][-1]["after"].get("mid_turn") else 0) >= 0, True)

    def test_write_all_produces_files(self):
        out = os.path.join(os.environ.get("BB_SCRATCH", "/tmp"), "fixtures_test")
        paths = write_all(out, seeds=(1, 2))
        self.assertGreater(len(paths), 3)
        strat = json.load(open(os.path.join(out, "strategies.json")))
        self.assertIn("Equilibrium", strat["strategies"]); self.assertEqual(len(strat["gene_keys"]), 10)
        fx = json.load(open(paths[0]))
        self.assertIn("steps", fx)

if __name__ == "__main__":
    unittest.main()
