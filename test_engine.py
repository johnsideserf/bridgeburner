import random, unittest
import engine
from engine import G, RED, BLK, policy, play, do, match_stats, GENE_KEYS, GENE_SPACE

def genes(**over):
    """Default genes: build asap, burn always, with optional overrides."""
    base = dict(burn_min=0, spend_cap=13, build_trig=0, keep_chain=0,
                mortar=0, ford_gain=2, race_at=99, demolish=1, armor=0)
    base.update(over)
    return tuple(base[k] for k in GENE_KEYS)

def fixed_game(hand0, bridge0=(), hand1=(), bridge1=(), river=None, rules=None):
    g = G(rules or {}, random.Random(0))
    g.hands = [list(hand0), list(hand1)]
    g.bridges = [list(bridge0), list(bridge1)]
    if river is not None: g.river = list(river)
    return g

class PolicyKingGuard(unittest.TestCase):
    def test_never_builds_king_below_slot_5(self):
        g = fixed_game(hand0=[(13, RED), (2, BLK)], bridge0=[(10, RED)])
        act = policy(genes(), g, 0, 2, 0)
        self.assertFalse(act[0] == 1 and act[1][0] == 13, act)

    def test_builds_king_as_fifth_card(self):
        g = fixed_game(hand0=[(13, RED)], bridge0=[(2,RED),(4,RED),(6,RED),(8,RED)])
        act = policy(genes(), g, 0, 2, 0)
        self.assertEqual(act, (1, (13, RED)))

    def test_mortar_does_not_cap_slot_4_with_king(self):
        g = fixed_game(hand0=[(13, RED), (11, BLK)], bridge0=[(2,RED),(4,RED),(6,RED)])
        act = policy(genes(mortar=1), g, 0, 2, 0)
        self.assertEqual(act, (1, (11, BLK)))

class PolicyDemolish(unittest.TestCase):
    def test_demolishes_when_stuck_even_though_draw_available(self):
        # bridge ends in a K at slot 4 -> nothing can ever be built; demolish gene on
        g = fixed_game(hand0=[(5, RED), (7, RED), (9, BLK)],
                       bridge0=[(2,RED),(3,RED),(4,RED),(13,BLK)])
        self.assertTrue(g.draw)          # draw pile is available
        act = policy(genes(demolish=1), g, 0, 2, 0)
        self.assertEqual(act, (5,))

    def test_no_demolish_when_gene_off(self):
        g = fixed_game(hand0=[(5, RED)], bridge0=[(2,RED),(13,BLK)])
        act = policy(genes(demolish=0), g, 0, 2, 0)
        self.assertNotEqual(act, (5,))

class PolicyArmor(unittest.TestCase):
    def test_armor_prefers_color_with_fewer_unseen_higher_cards(self):
        # Two buildable 9s. All black cards above 9 are visible (in my hand /
        # river / bridges), so a black 9 cannot be burned; red 9 can.
        blk_high = [(10,BLK),(10,BLK),(11,BLK),(11,BLK),(12,BLK),(12,BLK),(13,BLK),(13,BLK)]
        g = fixed_game(hand0=[(9,RED),(9,BLK)] + blk_high[:5],
                       bridge0=[(3,RED)], river=blk_high[5:], bridge1=[])
        act = policy(genes(armor=1), g, 0, 2, 0)
        self.assertEqual(act, (1, (9, BLK)))

    def test_armor_off_builds_lowest(self):
        g = fixed_game(hand0=[(9,RED),(9,BLK),(4,RED)], bridge0=[(3,RED)])
        act = policy(genes(armor=0), g, 0, 2, 0)
        self.assertEqual(act, (1, (4, RED)))

class MatchStats(unittest.TestCase):
    def test_reports_first_player_rate_burns_turns_stalls(self):
        rng = random.Random(1)
        s = match_stats(genes(), genes(burn_min=99), {}, 40, rng)
        for k in ("winrate", "first_player", "stalls", "avg_turns", "burns_per_game"):
            self.assertIn(k, s)
        self.assertTrue(0 <= s["winrate"] <= 1)
        self.assertTrue(0 <= s["first_player"] <= 1)
        self.assertGreater(s["avg_turns"], 0)

    def test_pure_builders_first_player_always_wins_or_stalls(self):
        rng = random.Random(2)
        s = match_stats(genes(burn_min=99), genes(burn_min=99), {}, 40, rng)
        self.assertEqual(s["burns_per_game"], 0)
        self.assertGreater(s["first_player"], 0.9)

class GeneSpace(unittest.TestCase):
    def test_armor_gene_exists(self):
        self.assertIn("armor", GENE_SPACE)
        self.assertEqual(GENE_SPACE["armor"], [0, 1])

if __name__ == "__main__":
    unittest.main()
