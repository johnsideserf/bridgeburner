"""The rulebook (RULES.md, make_rules.py) must describe engine.CURRENT_RULES."""
import re, unittest
from engine import CURRENT_RULES
from solve import RULESETS

class RulesSync(unittest.TestCase):
    def test_solver_current_ruleset_is_the_engine_constant(self):
        self.assertEqual(RULESETS["Current"], CURRENT_RULES)

    def _texts(self):
        return {"RULES.md": open("RULES.md").read(), "make_rules.py": open("make_rules.py").read()}

    def test_torch_range_is_a_house_rule_not_a_standard_rule(self):
        self.assertNotIn("burn_span", CURRENT_RULES)
        for name, txt in self._texts().items():
            std = txt.split("house rule")[0].split("HOUSE RULE")[0]   # text before the house-rules section
            self.assertNotRegex(std, r"at most \d+ ranks above", f"{name}: standard Burn text still range-limited")
            m = re.search(r"at most (\d+) ranks above", txt)
            self.assertIsNotNone(m, f"{name}: house rule for torch range missing")
            self.assertEqual(int(m.group(1)), RULESETS["Current+CloseTorches"]["burn_span"], name)

    def test_clock_and_equal_turns_described(self):
        for name, txt in self._texts().items():
            if CURRENT_RULES.get("clock"):
                self.assertIn("never reshuffled", txt, name)
            if CURRENT_RULES.get("equal_turns"):
                self.assertRegex(txt, r"(?i)equal turns", name)
            self.assertNotIn("Salvage:", txt, name)   # removed mechanic must not linger

if __name__ == "__main__":
    unittest.main()
