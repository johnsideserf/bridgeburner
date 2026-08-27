import random, unittest
import engine
from engine import G, RED, BLK, policy, play, do, match_stats, GENE_KEYS, GENE_SPACE

def genes(**over):
    """Default genes: build asap, burn always, with optional overrides."""
    base = dict(burn_min=0, spend_cap=13, build_trig=0, keep_chain=0,
                mortar=0, ford_gain=2, race_at=99, demolish=1, armor=0, endgame=0)
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

# ---------------------------------------------------------------- new rules
from engine import clock_winner, turn_actions

genes2 = genes

class Clock(unittest.TestCase):
    def test_no_reshuffle_under_clock(self):
        g = fixed_game(hand0=[], rules={"clock": True})
        g.draw = []; g.discard = [(5, RED)]
        self.assertIsNone(g.draw_card())
        self.assertEqual(g.discard, [(5, RED)])

    def test_reshuffle_without_clock(self):
        g = fixed_game(hand0=[])
        g.draw = []; g.discard = [(5, RED)]
        self.assertEqual(g.draw_card(), (5, RED))

    def test_clock_winner_longer_bridge_then_top_card_then_tie(self):
        g = fixed_game(hand0=[], bridge0=[(2,RED),(3,RED)], bridge1=[(9,BLK)])
        self.assertEqual(clock_winner(g), 0)
        g = fixed_game(hand0=[], bridge0=[(2,RED)], bridge1=[(9,BLK)])
        self.assertEqual(clock_winner(g), 1)
        g = fixed_game(hand0=[], bridge0=[(9,RED)], bridge1=[(9,BLK)])
        self.assertIsNone(clock_winner(g))

    def test_play_ends_when_pile_runs_out(self):
        g = fixed_game(hand0=[], bridge0=[(2,RED),(3,RED)], hand1=[], bridge1=[(5,BLK)],
                       rules={"clock": True})
        g.draw = [(1, RED)]; g.discard = []
        r, g2 = play(genes2(burn_min=99), genes2(burn_min=99), {"clock": True},
                     random.Random(0), g=g)
        self.assertEqual(r, 0)              # P0 drew the last card, longer bridge wins
        self.assertEqual(g2.turn_count, 1)

    def test_policy_does_not_try_to_draw_from_empty_pile_under_clock(self):
        g = fixed_game(hand0=[(2,RED)], river=[(3,RED),(4,RED),(5,RED)], rules={"clock": True})
        g.draw = []; g.discard = [(9, BLK)]; g.bridges = [[(12, RED)], []]
        act = policy(genes2(burn_min=99, ford_gain=99), g, 0, 2, 0)
        self.assertNotEqual(act[0], 0)

class EndgameGene(unittest.TestCase):
    def test_builds_asap_when_pile_low(self):
        g = fixed_game(hand0=[(4,RED),(6,BLK)], bridge0=[(2,RED)])
        g.draw = g.draw[:3]
        self.assertEqual(policy(genes2(build_trig=1, endgame=6), g, 0, 2, 0), (1, (4, RED)))
        self.assertNotEqual(policy(genes2(build_trig=1, endgame=0), g, 0, 2, 0)[0], 1)

class SecondPlayerCompensation(unittest.TestCase):
    def test_p2_extra_cards(self):
        g = G({"p2_extra": 2}, random.Random(0))
        self.assertEqual(len(g.hands[0]), 7)
        self.assertEqual(len(g.hands[1]), 9)
        self.assertEqual(len(g.draw), 52 - 16 - 3)

    def test_first_turn_actions(self):
        g = G({"first_turn_actions": 1}, random.Random(0))
        self.assertEqual(turn_actions(g), 1)
        g.turn_count = 1; g.turn = 1
        self.assertEqual(turn_actions(g), 2)
        self.assertEqual(turn_actions(G({}, random.Random(0))), 2)

    def test_first_turn_actions_prevents_p1_opening_build(self):
        g = fixed_game(hand0=[(2,RED)], hand1=[], rules={"first_turn_actions": 1})
        g.draw = g.draw[:1]        # P0's 1-action turn draws the last card -> clock ends... no clock here
        # Without clock the game continues; check P0 could not build on turn 1:
        seen = {}
        import engine as E
        orig = E.do
        def spy(gg, me, act):
            seen.setdefault(gg.turn_count, []).append(act[0]); return orig(gg, me, act)
        E.do = spy
        try:
            play(genes2(burn_min=99), genes2(burn_min=99), {"first_turn_actions": 1},
                 random.Random(0), g=g, max_turns=1)
        finally:
            E.do = orig
        self.assertNotIn(1, seen[0])

# ---------------------------------------------------------------- equal turns / burn span
from engine import legal_burn_cards

class BurnSpan(unittest.TestCase):
    def test_legal_burns_limited_to_span(self):
        g = fixed_game(hand0=[(8,RED),(9,RED),(12,RED),(9,BLK)], bridge1=[(5,RED)],
                       rules={"burn_span": 3})
        self.assertEqual(sorted(legal_burn_cards(g, 0)), [(8,RED)])
        self.assertIsNone(do(g, 0, (2, (9,RED))))
        self.assertEqual(do(g, 0, (2, (8,RED))), 1)

    def test_no_span_rule_allows_any_higher(self):
        g = fixed_game(hand0=[(12,RED)], bridge1=[(5,RED)])
        self.assertEqual(legal_burn_cards(g, 0), [(12,RED)])

class EqualTurns(unittest.TestCase):
    def four(self, col): return [(2,col),(3,col),(4,col),(5,col)]

    def go(self, hand1, rules):
        g = fixed_game(hand0=[(6,RED)], bridge0=self.four(RED),
                       hand1=hand1, bridge1=self.four(BLK), rules=rules)
        return play(genes(burn_min=99), genes(burn_min=99), rules, random.Random(0), g=g)

    def test_without_rule_p1_wins_immediately(self):
        r, g = self.go([(7,BLK)], {})
        self.assertEqual((r, g.turn_count), (0, 0))

    def test_p2_gets_final_turn_and_wins_on_higher_top_card(self):
        r, g = self.go([(7,BLK)], {"equal_turns": True})
        self.assertEqual(r, 1)
        self.assertEqual(g.turn_count, 1)

    def test_both_finish_equal_top_card_is_draw(self):
        r, g = self.go([(6,BLK)], {"equal_turns": True})
        self.assertIsNone(r)
        self.assertEqual(g.turn_count, 1)

    def test_p2_fails_to_finish_p1_wins(self):
        r, g = self.go([], {"equal_turns": True})
        self.assertEqual((r, g.turn_count), (0, 2))   # P2's full turn elapsed

    def test_p2_burns_cap_game_continues(self):
        # P2 holds a red 7: burns P1's red 6 cap, nobody has 5, game goes on
        g = fixed_game(hand0=[(6,RED)], bridge0=self.four(RED),
                       hand1=[(7,RED)], bridge1=[], rules={"equal_turns": True})
        r, g2 = play(genes(burn_min=99), genes(burn_min=0), {"equal_turns": True},
                     random.Random(0), g=g, max_turns=2)
        self.assertEqual(len(g2.bridges[0]), 4)
        self.assertEqual(g2.turn_count, 2)     # ran to max_turns, no winner yet
        self.assertIsNone(r)

    def test_p2_finishing_first_ends_immediately(self):
        g = fixed_game(hand0=[], bridge0=[], hand1=[(6,BLK)], bridge1=self.four(BLK),
                       rules={"equal_turns": True})
        g.turn = 1
        r, g2 = play(genes(burn_min=99), genes(burn_min=99), {"equal_turns": True},
                     random.Random(0), g=g)
        self.assertEqual(r, 1)
