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

class BestResponseSelection(unittest.TestCase):
    def test_unaccepted_better_trial_does_not_break_selection(self):
        # Pool member scores 0.6; one neighbour scores 0.61 (above it, but below
        # the +0.02 acceptance threshold); everything else 0.4. The search must
        # return the pool member with its own score, not None / a worse genome.
        base = solve.SEEDS["Builder"]
        from engine import GENE_SPACE, GENE_KEYS
        ki = 0; alt = [v for v in GENE_SPACE[GENE_KEYS[ki]] if v != base[ki]][0]
        neighbour = tuple(alt if i == ki else v for i, v in enumerate(base))
        seen = []
        def stub(genes, pool, mix, rules, n, rng):
            seen.append(genes)
            return 0.6 if genes == base else 0.61 if genes == neighbour else 0.4
        orig = solve.wr_vs_mix; solve.wr_vs_mix = stub
        try:
            g, w = solve.best_response([base], [1.0], {}, random.Random(0), games=1,
                                       restarts=0, passes=1, on_trial=lambda n, w, b: None)
        finally:
            solve.wr_vs_mix = orig
        self.assertIn(neighbour, seen)
        self.assertEqual((g, w), (base, 0.6))

    def test_on_trial_reports_running_best(self):
        base = solve.SEEDS["Builder"]
        calls = []
        orig = solve.wr_vs_mix; solve.wr_vs_mix = lambda *a: 0.55
        try:
            solve.best_response([base], [1.0], {}, random.Random(0), games=1, restarts=0,
                                passes=1, on_trial=lambda n, w, b: calls.append((n, w, b)))
        finally:
            solve.wr_vs_mix = orig
        self.assertEqual(calls[0], (1, 0.55, 0.55))
        self.assertEqual([c[0] for c in calls], list(range(1, len(calls) + 1)))
