import random, unittest
import solve
from solve import solve_matrix, payoff_matrix, evaluate_heldout, RULESETS, select_rulesets

class SolveMatrix(unittest.TestCase):
    def test_rps_is_uniform(self):
        # rock/paper/scissors as winrates
        M = [[.5,0,1],[1,.5,0],[0,1,.5]]
        mix = solve_matrix(M)
        for p in mix: self.assertAlmostEqual(p, 1/3, places=1)

    def test_dominant_row_gets_all_mass(self):
        M = [[.5,.9],[.1,.5]]
        mix = solve_matrix(M)
        self.assertGreater(mix[0], 0.97)

class PayoffMatrix(unittest.TestCase):
    def test_incremental_update_keeps_old_entries(self):
        rng = random.Random(0)
        pool = [solve.SEEDS["Builder"], solve.SEEDS["Hoarder"]]
        M = payoff_matrix(pool, {}, 20, rng)
        old = M[0][1]
        pool.append(solve.SEEDS["Sniper"])
        M2 = payoff_matrix(pool, {}, 20, rng, prev=M)
        self.assertEqual(len(M2), 3)
        self.assertEqual(M2[0][1], old)
        self.assertAlmostEqual(M2[0][2] + M2[2][0], 1.0)
        self.assertEqual(M2[2][2], 0.5)

class HeldOut(unittest.TestCase):
    def test_heldout_uses_fresh_games_and_more_of_them(self):
        calls = []
        orig = solve.wr_vs_mix
        def spy(genes, pool, mix, rules, n, rng):
            calls.append(n); return 0.6
        solve.wr_vs_mix = spy
        try:
            w = evaluate_heldout(solve.SEEDS["Builder"], [solve.SEEDS["Builder"]], [1.0], {}, 100, random.Random(0), mult=4)
        finally:
            solve.wr_vs_mix = orig
        self.assertEqual(calls, [400])
        self.assertEqual(w, 0.6)

class Rulesets(unittest.TestCase):
    def test_new_rulesets_registered(self):
        keys = " ".join(RULESETS)
        for want in ("NoLimit", "BurnCost2", "HandLimit8", "Clock", "Clock+P2x1", "Clock+P1a1"):
            self.assertIn(want, keys)

    def test_select_by_prefix_and_all(self):
        self.assertEqual(select_rulesets("all"), list(RULESETS))
        sel = select_rulesets("NoLimit,BurnCost2")
        self.assertEqual(len(sel), 2)
        self.assertTrue(sel[0].startswith("NoLimit"))
        with self.assertRaises(SystemExit):
            select_rulesets("Nope")

if __name__ == "__main__":
    unittest.main()
