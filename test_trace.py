import random, unittest
from trace_game import trace

class Trace(unittest.TestCase):
    def test_trace_prints_turns_and_result(self):
        out = trace(seed=1)
        self.assertIn("Turn 1", out)
        self.assertRegex(out, r"(wins|draw)")
        self.assertIn("bridge", out.lower())
