"""The rulebook (RULES.md, make_rules.py) must describe engine.CURRENT_RULES."""
import re, unittest
from engine import CURRENT_RULES
from solve import RULESETS

class RulesSync(unittest.TestCase):
    def test_solver_current_ruleset_is_the_engine_constant(self):
        self.assertEqual(RULESETS["Current"], CURRENT_RULES)

    def _texts(self):
        return {"RULES.md": open("RULES.md").read(), "make_rules.py": open("make_rules.py").read()}

    def test_burn_span_number_matches_rulebook(self):
        for name, txt in self._texts().items():
            m = re.search(r"at most (\d+) ranks above", txt)
            self.assertIsNotNone(m, f"{name}: burn-span sentence missing")
            self.assertEqual(int(m.group(1)), CURRENT_RULES["burn_span"], name)

    def test_clock_and_equal_turns_described(self):
        for name, txt in self._texts().items():
            if CURRENT_RULES.get("clock"):
                self.assertIn("never reshuffled", txt, name)
            if CURRENT_RULES.get("equal_turns"):
                self.assertRegex(txt, r"(?i)equal turns", name)
            self.assertNotIn("Salvage:", txt, name)   # removed mechanic must not linger

if __name__ == "__main__":
    unittest.main()
