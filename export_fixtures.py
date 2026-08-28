#!/usr/bin/env python3
"""Export replay fixtures so the browser (JS) engine can be checked against the
Python engine move for move.

  .venv/bin/python export_fixtures.py            # writes web/test/fixtures/

Each fixture holds the full initial deal (both hands, river, pile order), then
every action with the actions-left count before it and the full state after
it. A JS test replays the actions (engine parity) and re-decides each bot
action with the JS policy (policy parity). No RNG parity is needed.
"""
import json, os, random
from engine import (G, play, turn_actions, GENE_KEYS, GENE_SPACE, CURRENT_RULES)
from solve import SEEDS, RULESETS

def snapshot(g):
    return {"hands": [[list(c) for c in g.hands[0]], [list(c) for c in g.hands[1]]],
            "river": [list(c) for c in g.river], "draw": [list(c) for c in g.draw],
            "discard": [list(c) for c in g.discard],
            "bridges": [[list(c) for c in g.bridges[0]], [list(c) for c in g.bridges[1]]],
            "turn": g.turn, "turn_count": g.turn_count, "burns": list(g.burns)}

def make_fixture(seed, rules, a, b):
    g = G(rules, random.Random(seed))
    initial = snapshot(g)
    steps = []
    left = {"v": turn_actions(g), "key": (g.turn_count, g.turn)}
    def hook(gg, me, act, cost):
        key = (gg.turn_count, me)
        if key != left["key"]:
            left["key"] = key; left["v"] = turn_actions(gg)
        steps.append({"who": me, "left": left["v"],
                      "action": [act[0]] + [list(x) if isinstance(x, tuple) else x for x in act[1:]],
                      "cost": cost, "after": snapshot(gg)})
        left["v"] -= cost
    r, g2 = play(SEEDS[a], SEEDS[b], rules, random.Random(seed), g=g, on_action=hook)
    return {"seed": seed, "rules": rules, "a": a, "b": b,
            "genes": {"a": list(SEEDS[a]), "b": list(SEEDS[b])},
            "initial": initial, "steps": steps,
            "result": r, "turns": g2.turn_count}

CASES = [
    ("Current", "Equilibrium", "Builder"), ("Current", "Equilibrium", "Equilibrium"),
    ("Current", "Hoarder", "Sniper"), ("Current", "Armored", "Clockwatcher"),
    ("Current+CloseTorches", "CloseTorchEq", "Builder"), ("Current+Cheap2", "Equilibrium", "Balanced"),
    ("Current+BothHouse", "CloseTorchEq", "Sniper"),   # (no NoLimit: reshuffles use Python's RNG)
    ("Clock+BurnCost2+Equal", "Sniper", "Balanced"), ("Current+ClockReply", "Equilibrium", "Hoarder"),
]

def write_all(out_dir, seeds=(1, 2, 3)):
    os.makedirs(out_dir, exist_ok=True)
    json.dump({"gene_keys": GENE_KEYS, "gene_space": GENE_SPACE,
               "strategies": {k: list(v) for k, v in SEEDS.items()},
               "rulesets": RULESETS, "current_rules": CURRENT_RULES},
              open(os.path.join(out_dir, "strategies.json"), "w"), indent=1)
    paths = []
    for rname, a, b in CASES:
        for seed in seeds:
            fx = make_fixture(seed, RULESETS[rname], a, b)
            p = os.path.join(out_dir, f"{rname.replace('+', '_')}-{a}-{b}-{seed}.json")
            json.dump(fx, open(p, "w")); paths.append(p)
    return paths

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    paths = write_all(os.path.join(here, "web", "test", "fixtures"))
    print(f"wrote {len(paths)} fixtures")
