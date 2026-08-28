import random, unittest
from engine import CURRENT_RULES
from game_session import Session, replay_frames

class SessionFlow(unittest.TestCase):
    def test_new_session_state_hides_bot_hand(self):
        s = Session(rules=CURRENT_RULES, bot="Equilibrium", seed=1, human_first=True)
        st = s.state()
        self.assertEqual(st["turn"], 0); self.assertEqual(st["left"], 2)
        self.assertEqual(len(st["hand"]), 7)
        self.assertEqual(st["bot_hand_size"], 7)
        self.assertNotIn("bot_hand", st)
        self.assertEqual(len(st["river"]), 3)
        self.assertTrue(st["legal"])          # list of {action, cost, label}
        self.assertIsNone(st["winner"])

    def test_bot_moves_first_when_human_second(self):
        s = Session(rules=CURRENT_RULES, bot="Equilibrium", seed=1, human_first=False)
        st = s.state()
        self.assertEqual(st["turn"], 0)      # human's seat is 1; state.turn is whose turn (0=human)
        self.assertTrue(st["log"])           # bot already acted
        self.assertEqual(st["log"][0]["who"], "bot")

    def test_illegal_action_rejected(self):
        s = Session(rules=CURRENT_RULES, bot="Equilibrium", seed=1, human_first=True)
        hand = {tuple(c) for c in s.state()["hand"]}
        missing = next(c for c in [(r, col) for r in range(1, 14) for col in (0, 1)] if c not in hand)
        with self.assertRaises(ValueError):
            s.act([1, list(missing)])        # card not in hand
        with self.assertRaises(ValueError):
            s.act([2, list(next(iter(hand)))])   # nothing to burn yet

    def test_draw_then_turn_passes_to_bot_after_two_actions(self):
        s = Session(rules=CURRENT_RULES, bot="Equilibrium", seed=1, human_first=True)
        st = s.act([0])
        self.assertEqual(st["left"], 1); self.assertEqual(len(st["hand"]), 8)
        st = s.act([0])
        # bot has now taken its turn, back to human with 2 actions (unless game over)
        self.assertEqual(st["left"], 2)
        self.assertTrue(any(e["who"] == "bot" for e in st["log"]))

    def test_pass_ends_turn(self):
        s = Session(rules=CURRENT_RULES, bot="Equilibrium", seed=1, human_first=True)
        st = s.act([9])
        self.assertEqual(st["left"], 2)
        self.assertEqual(st["turn_count"], 2)

    def test_game_runs_to_completion_with_random_legal_play(self):
        s = Session(rules=CURRENT_RULES, bot="Equilibrium", seed=2, human_first=True)
        rng = random.Random(0); st = s.state(); n = 0
        while st["winner"] is None and not st["over"] and n < 400:
            choice = rng.choice(st["legal"])
            st = s.act(choice["action"]); n += 1
        self.assertTrue(st["over"])

class Replay(unittest.TestCase):
    def test_replay_frames(self):
        fr = replay_frames(seed=3, a="Equilibrium", b="Builder", rules=CURRENT_RULES)
        self.assertGreater(len(fr["frames"]), 5)
        f = fr["frames"][0]
        for k in ("turn_count", "who", "action", "hands", "bridges", "river", "pile"): self.assertIn(k, f)
        self.assertIn("result", fr)
        self.assertIn("discard", f)
        self.assertEqual(fr["turns"], fr["frames"][-1]["turn_count"] + 1)

class HumanEqualTurns(unittest.TestCase):
    """Equal turns on the human path: finishing first must not end the round."""
    def four(self, col): return [(2,col),(3,col),(4,col),(5,col)]

    def test_human_first_finishing_gives_bot_a_reply_turn(self):
        s = Session(rules=CURRENT_RULES, bot="Builder", seed=1, human_first=True)
        s.g.hands = [[(6, 0)], [(7, 1)]]
        s.g.bridges = [self.four(0), self.four(1)]
        st = s.act([1, [6, 0]])                  # human completes 2..6 first
        self.assertTrue(st["over"])
        self.assertEqual(st["winner"], "bot")   # bot's reply turn: builds 7b, 7 beats 6 on the tiebreak
        self.assertTrue(any(e["who"] == "bot" and "Build" in e["text"] for e in st["log"]))

    def test_human_second_takes_reply_turn_and_wins_on_tiebreak(self):
        s = Session(rules=CURRENT_RULES, bot="Builder", seed=1, human_first=False)
        # Force the state: bot (seat 0) just completed its bridge; human to reply.
        s.g.bridges = [self.four(0) + [(6, 0)], self.four(1)]
        s.g.hands = [[], [(9, 1)]]
        s.g.turn = 1; s.left = 2; s.over = False
        st = s.act([1, [9, 1]])
        self.assertTrue(st["over"]); self.assertEqual(st["winner"], "human")

    def test_human_second_fails_to_reply_loses(self):
        s = Session(rules=CURRENT_RULES, bot="Builder", seed=1, human_first=False)
        s.g.bridges = [self.four(0) + [(6, 0)], self.four(1)]
        s.g.hands = [[], [(2, 1)]]
        s.g.turn = 1; s.left = 2; s.over = False
        st = s.act([9])
        self.assertTrue(st["over"]); self.assertEqual(st["winner"], "bot")

    def test_clock_ends_on_human_draw(self):
        s = Session(rules=CURRENT_RULES, bot="Builder", seed=1, human_first=True)
        s.g.bridges = [[(2, 0), (3, 0)], [(5, 1)]]
        s.g.hands = [[], []]; s.g.draw = [(1, 0)]; s.g.river = []
        st = s.act([0])                          # empties the pile mid-turn
        self.assertFalse(st["over"]); self.assertEqual(st["pile"], 0)
        st = s.act([9])                          # clock is scored when the turn ends
        self.assertTrue(st["over"]); self.assertEqual(st["winner"], "human")
