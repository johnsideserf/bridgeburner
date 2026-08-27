#!/usr/bin/env python3
"""Print one Bridgeburner game turn by turn, to eyeball what play looks like.

  .venv/bin/python trace_game.py --seed 7
  .venv/bin/python trace_game.py --a Builder --b Equilibrium --rules NoLimit
"""
import argparse, random
from engine import play, CURRENT_RULES, gname

RANK = {1:"A",11:"J",12:"Q",13:"K"}
def cs(card):
    r, col = card
    return f"{RANK.get(r, str(r))}{'r' if col == 0 else 'b'}"
def hand_s(cards): return " ".join(cs(c) for c in sorted(cards))
def bridge_s(cards): return "-".join(cs(c) for c in cards) if cards else "(empty)"

# Equilibrium strategy found for the locked ruleset (confirmation sweep, 3 seeds).
STRATEGIES = {
    "Equilibrium": (0, 2, 1, 1, 0, 3, 99, 0, 0, 6),
    "Builder":     (99, 13, 0, 1, 0, 2, 99, 1, 0, 0),
    "Hoarder":     (0, 13, 1, 1, 0, 1, 99, 0, 0, 0),
    "Sniper":      (3, 13, 1, 1, 0, 1, 4, 0, 0, 0),
}
ACT = {0:"DRAW", 1:"BUILD", 2:"BURN", 3:"FORD", 4:"FLUSH", 5:"DEMOLISH", 9:"PASS"}

def describe(g, me, act, cost):
    k = act[0]
    if k == 1: return f"BUILD {cs(act[1])}"
    if k == 2: return f"BURN with {cs(act[1])} (cost {cost})"
    if k == 3: return f"FORD: discard {cs(act[1])}, take {cs(g.hands[me][-1])} from River"
    if k == 0: return f"DRAW ({cs(g.hands[me][-1])})" if g.hands[me] else "DRAW (pile empty)"
    return ACT[k]

def trace(seed=0, a="Equilibrium", b="Equilibrium", rules=None):
    rules = CURRENT_RULES if rules is None else rules
    lines = []
    state = {"turn": -1}
    def hook(g, me, act, cost):
        if g.turn_count != state["turn"]:
            state["turn"] = g.turn_count
            lines.append(f"\nTurn {g.turn_count+1}  P{me+1}   pile {len(g.draw):2d}   "
                         f"River [{hand_s(g.river)}]")
            lines.append(f"   P1 bridge {bridge_s(g.bridges[0])}   P2 bridge {bridge_s(g.bridges[1])}")
            lines.append(f"   hand: {hand_s(g.hands[me] + ([act[1]] if act[0] in (1,2) else []))}")
        lines.append(f"   > {describe(g, me, act, cost)}")
    r, g = play(STRATEGIES[a], STRATEGIES[b], rules, random.Random(seed), on_action=hook)
    lines.append("")
    lines.append(f"Final:  P1 bridge {bridge_s(g.bridges[0])}   P2 bridge {bridge_s(g.bridges[1])}   "
                 f"pile {len(g.draw)}   burns {g.burns}")
    lines.append("Result: " + ("draw" if r is None else f"P{r+1} ({a if r==0 else b}) wins")
                 + f" after {g.turn_count} turns")
    return "\n".join(lines)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--a", default="Equilibrium", choices=STRATEGIES)
    ap.add_argument("--b", default="Equilibrium", choices=STRATEGIES)
    ap.add_argument("--rules", default="Current")
    args = ap.parse_args()
    from solve import RULESETS
    print(trace(args.seed, args.a, args.b, RULESETS[args.rules]))
