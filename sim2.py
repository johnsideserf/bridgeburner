#!/usr/bin/env python3
"""Round 2: structural fixes + smarter counter-bots."""
import random
from itertools import combinations
from collections import defaultdict
from sim import State, apply as base_apply, end_of_turn, has_chain5, chain_len, \
                bot_builder, make_hoarder, bot_balanced

# --- engine wrappers with new rules -------------------------------
def burn_allowed(state, me):
    """Check structural burn rules."""
    opp = 1 - me
    if state.rules.get("keep_pace"):
        if len(state.bridges[me]) < len(state.bridges[opp]):
            return False
    if state.rules.get("burn_budget") is not None:
        if state.burns_used[me] >= state.rules["burn_budget"]:
            return False
    return True

def apply(state, me, act):
    if act[0] == "burn":
        if not burn_allowed(state, me):
            return None
        cost = base_apply(state, me, act)
        if cost is not None:
            state.burns_used[me] += 1
        return cost
    return base_apply(state, me, act)

def new_state(rules, rng):
    st = State(rules, rng)
    st.burns_used = [0, 0]
    return st

def play_game(state, bots, max_turns=300):
    while state.turn_count < max_turns:
        me = state.turn
        left = 2
        burns = 0
        while left > 0:
            act = bots[me](state, me, left, burns)
            cost = apply(state, me, act)
            if cost is None:
                cost = apply(state, me, ("pass",))
            if act[0] == "burn" and cost != 99:
                burns += 1
            left -= cost
            if len(state.bridges[me]) >= 5:
                return me
        end_of_turn(state, me)
        state.turn = 1 - me
        state.turn_count += 1
    return None

# --- extra bots ---------------------------------------------------
def can_burn_now(state, me, left, burns):
    if not burn_allowed(state, me): return None
    b = state.legal_burns(me)
    if not b: return None
    t = state.bridges[1 - me][-1]
    if state.burn_cost(t) > left: return None
    if state.rules.get("burn_once") and burns: return None
    return min(b, key=lambda c: c[0])

def bot_shadow(state, me, left, burns):
    """Keeps bridge level with opponent's, burns when able, hoards otherwise."""
    opp = 1 - me
    hand = state.hands[me]
    b = state.buildable(me)
    # win now
    if len(state.bridges[me]) == 4 and b and left >= 2:
        return ("build", min(b, key=lambda c: c[0]))
    # burn if the rules let us
    card = can_burn_now(state, me, left, burns)
    if card is not None:
        return ("burn", card)
    # stay level (or 1 ahead) so future burns stay legal
    if b and left >= 2 and len(state.bridges[me]) <= len(state.bridges[opp]):
        return ("build", min(b, key=lambda c: c[0]))
    # full chain? push for the win
    floor = state.bridges[me][-1][0] if state.bridges[me] else 0
    if b and left >= 2 and chain_len(hand, floor) >= 5 - len(state.bridges[me]):
        return ("build", min(b, key=lambda c: c[0]))
    # improve hand
    if state.river and hand:
        best = max(range(len(state.river)), key=lambda i: state.river[i][0])
        low = min(hand, key=lambda c: c[0])
        if state.river[best][0] > low[0] + 1:
            return ("ford", low, best)
    if state.draw or state.discard:
        return ("draw",)
    if state.river:
        return ("flush",)
    return ("pass",)

def bot_sniper(state, me, left, burns):
    """Hoards, saves scarce burns for when the opponent nears victory."""
    opp = 1 - me
    hand = state.hands[me]
    b = state.buildable(me)
    if len(state.bridges[me]) == 4 and b and left >= 2:
        return ("build", min(b, key=lambda c: c[0]))
    if len(state.bridges[opp]) >= 3:
        card = can_burn_now(state, me, left, burns)
        if card is not None:
            return ("burn", card)
    floor = state.bridges[me][-1][0] if state.bridges[me] else 0
    if b and left >= 2 and chain_len(hand, floor) >= 5 - len(state.bridges[me]):
        return ("build", min(b, key=lambda c: c[0]))
    if state.river and hand:
        best = max(range(len(state.river)), key=lambda i: state.river[i][0])
        low = min(hand, key=lambda c: c[0])
        if state.river[best][0] > low[0] + 1:
            return ("ford", low, best)
    if state.draw or state.discard:
        return ("draw",)
    if state.river:
        return ("flush",)
    return ("pass",)

BOTS = {
    "Builder":  lambda: bot_builder,
    "Balanced": lambda: bot_balanced,
    "Hoarder":  lambda: make_hoarder(True),
    "Shadow":   lambda: bot_shadow,
    "Sniper":   lambda: bot_sniper,
}

RULESETS = {
    "F: keep pace (burn only if your bridge >= theirs)": {"keep_pace": True},
    "G: burn budget (3 burns per round each)":           {"burn_budget": 3},
    "H: keep pace + hand limit 8":                       {"keep_pace": True, "hand_limit": 8},
}

def tournament(n=400, seed=11):
    rng = random.Random(seed)
    for rname, rules in RULESETS.items():
        print(f"\n=== {rname} ===")
        names = list(BOTS)
        overall = defaultdict(lambda: [0, 0])   # wins, games
        for a, b in combinations(names, 2):
            w = defaultdict(int); turns = []
            for g in range(n):
                order = [(a, b), (b, a)][g % 2]
                st = new_state(rules, random.Random(rng.random()))
                bots = [BOTS[order[0]](), BOTS[order[1]]()]
                res = play_game(st, bots)
                turns.append(st.turn_count)
                if res is None: w["stall"] += 1
                else: w[order[res]] += 1
            overall[a][0] += w[a]; overall[a][1] += n
            overall[b][0] += w[b]; overall[b][1] += n
            print(f"  {a:9s} vs {b:9s}:  {a} {100*w[a]/n:4.0f}%  "
                  f"{b} {100*w[b]/n:4.0f}%  stall {100*w['stall']/n:3.0f}%  "
                  f"(avg {sum(turns)/n:.0f} t)")
        print("  -- overall win rate --")
        for nm, (wins, games) in sorted(overall.items(), key=lambda kv: -kv[1][0]/kv[1][1]):
            print(f"     {nm:9s} {100*wins/games:4.0f}%")

if __name__ == "__main__":
    tournament()
