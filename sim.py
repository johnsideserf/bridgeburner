#!/usr/bin/env python3
"""Bridgeburner simulator: bot tournament across candidate rulesets."""
import random
from itertools import combinations
from collections import defaultdict

RED, BLK = "R", "B"

def fresh_deck():
    # 13 ranks (A=1 .. K=13), 2 red + 2 black of each
    return [(r, col) for r in range(1, 14) for col in (RED, RED, BLK, BLK)]

class State:
    def __init__(self, rules, rng):
        self.rules = rules
        self.rng = rng
        deck = fresh_deck(); rng.shuffle(deck)
        self.hands = [deck[:7], deck[7:14]]
        self.river = deck[14:17]
        self.draw = deck[17:]
        self.discard = []
        self.bridges = [[], []]
        self.turn = 0          # whose turn (0/1)
        self.turn_count = 0

    # ---- helpers -------------------------------------------------
    def refill(self):
        if not self.draw and self.discard:
            self.draw = self.discard[:]
            self.discard = []
            self.rng.shuffle(self.draw)

    def draw_card(self):
        self.refill()
        return self.draw.pop() if self.draw else None

    def burn_cost(self, target):
        if self.rules.get("burn_cost2"):
            return 2
        return 2 if target[0] in (11, 12, 13) else 1

    def legal_burns(self, me):
        opp = 1 - me
        if not self.bridges[opp]:
            return []
        t = self.bridges[opp][-1]
        return [c for c in self.hands[me] if c[1] == t[1] and c[0] > t[0]]

    def buildable(self, me):
        b = self.bridges[me]
        floor = b[-1][0] if b else 0
        return [c for c in self.hands[me] if c[0] > floor]

# ---- engine ------------------------------------------------------
def apply(state, me, act):
    """Apply action; return action cost, or None if illegal."""
    hand = state.hands[me]
    kind = act[0]
    if kind == "draw":
        card = state.draw_card()
        if card is None: return None
        hand.append(card); return 1
    if kind == "build":
        card = act[1]
        b = state.bridges[me]
        floor = b[-1][0] if b else 0
        if card not in hand or card[0] <= floor: return None
        hand.remove(card); b.append(card); return 2
    if kind == "burn":
        card = act[1]
        opp = 1 - me
        if not state.bridges[opp]: return None
        t = state.bridges[opp][-1]
        cost = state.burn_cost(t)
        if card not in hand or card[1] != t[1] or card[0] <= t[0]: return None
        hand.remove(card); state.discard.append(card)
        state.bridges[opp].pop()
        if state.river: state.discard.append(state.river.pop(0))
        state.river.append(t)
        return cost
    if kind == "ford":
        _, hcard, ridx = act
        if hcard not in hand or ridx >= len(state.river): return None
        hand.remove(hcard); state.discard.append(hcard)
        hand.append(state.river.pop(ridx))
        c2 = state.draw_card()
        if c2 is not None: state.river.append(c2)
        return 1
    if kind == "flush":
        if not state.river: return None
        state.discard.extend(state.river); state.river = []
        for _ in range(3):
            c2 = state.draw_card()
            if c2 is None: break
            state.river.append(c2)
        return 1
    if kind == "demolish":
        if not state.bridges[me]: return None
        state.discard.append(state.bridges[me].pop()); return 1
    if kind == "pass":
        return 99   # ends turn
    return None

def end_of_turn(state, me):
    limit = state.rules.get("hand_limit")
    if limit:
        hand = state.hands[me]
        while len(hand) > limit:
            # discard lowest card (hoarders keep the top)
            low = min(hand, key=lambda c: c[0])
            hand.remove(low); state.discard.append(low)

def play_game(state, bots, max_turns=300):
    while state.turn_count < max_turns:
        me = state.turn
        actions_left = 2
        burns_this_turn = 0
        while actions_left > 0:
            act = bots[me](state, me, actions_left, burns_this_turn)
            cost = apply(state, me, act)
            if cost is None:            # illegal fallback
                cost = apply(state, me, ("pass",))
            if act[0] == "burn": burns_this_turn += 1
            actions_left -= cost
            if len(state.bridges[me]) >= 5:
                return me
        end_of_turn(state, me)
        state.turn = 1 - me
        state.turn_count += 1
    return None   # stalemate

# ---- bots --------------------------------------------------------
def has_chain5(cards, floor=0):
    """Any strictly ascending 5-chain above floor?"""
    ranks = sorted({c[0] for c in cards if c[0] > floor})
    return len(ranks) >= 5

def chain_len(cards, floor=0):
    return len({c[0] for c in cards if c[0] > floor})

def bot_builder(state, me, left, burns):
    """Greedy: build whenever possible, race to 5."""
    hand = state.hands[me]
    b = state.buildable(me)
    if b and left >= 2:
        return ("build", min(b, key=lambda c: c[0]))
    # try ford toward something buildable / useful
    floor = state.bridges[me][-1][0] if state.bridges[me] else 0
    for i, rc in enumerate(state.river):
        if rc[0] > floor and hand:
            junk = [c for c in hand if c[0] <= floor]
            dump = min(junk, key=lambda c: c[0]) if junk else min(hand, key=lambda c: c[0])
            return ("ford", dump, i)
    if state.draw or state.discard:
        return ("draw",)
    if state.bridges[me] and chain_len(hand, 0) > chain_len(hand, state.bridges[me][-1][0]):
        return ("demolish",)
    if state.river and hand:
        return ("ford", min(hand, key=lambda c: c[0]), 0)
    return ("pass",)

def make_hoarder(build_when_chain=True):
    """User's strategy: hoard high cards, burn everything, build late."""
    def bot(state, me, left, burns):
        hand = state.hands[me]
        opp = 1 - me
        # 1. finish the bridge if possible
        b = state.buildable(me)
        if len(state.bridges[me]) == 4 and b and left >= 2:
            return ("build", min(b, key=lambda c: c[0]))
        # 2. burn whatever the opponent builds (cheapest qualifying card)
        burnable = state.legal_burns(me)
        if burnable:
            t = state.bridges[opp][-1]
            if state.burn_cost(t) <= left and (not state.rules.get("burn_once") or burns == 0):
                return ("burn", min(burnable, key=lambda c: c[0]))
        # 3. start/continue building only with a full ascending 5-chain in hand
        if build_when_chain and b and left >= 2:
            floor = state.bridges[me][-1][0] if state.bridges[me] else 0
            need = 5 - len(state.bridges[me])
            if chain_len(hand, floor) >= need:
                return ("build", min(b, key=lambda c: c[0]))
        # 4. upgrade hand: ford lowest hand card for highest river card
        if state.river and hand:
            best = max(range(len(state.river)), key=lambda i: state.river[i][0])
            low = min(hand, key=lambda c: c[0])
            if state.river[best][0] > low[0] + 1:
                return ("ford", low, best)
        # 5. otherwise draw / flush
        if state.draw or state.discard:
            return ("draw",)
        if state.river:
            return ("flush",)
        return ("pass",)
    return bot

def bot_balanced(state, me, left, burns):
    """Builds steadily; burns only when opponent is close to winning."""
    opp = 1 - me
    hand = state.hands[me]
    burnable = state.legal_burns(me)
    if burnable and len(state.bridges[opp]) >= 3:
        t = state.bridges[opp][-1]
        if state.burn_cost(t) <= left and (not state.rules.get("burn_once") or burns == 0):
            return ("burn", min(burnable, key=lambda c: c[0]))
    return bot_builder(state, me, left, burns)

BOTS = {
    "Builder": lambda: bot_builder,
    "Balanced": lambda: bot_balanced,
    "Hoarder": lambda: make_hoarder(True),
}

RULESETS = {
    "A: current rules":            {},
    "B: hand limit 8":             {"hand_limit": 8},
    "C: burn always costs 2":      {"burn_cost2": True},
    "D: max 1 burn per turn":      {"burn_once": True},
    "E: burn=2  +  hand limit 8":  {"burn_cost2": True, "hand_limit": 8},
}

def tournament(n=400, seed=7):
    rng = random.Random(seed)
    for rname, rules in RULESETS.items():
        print(f"\n=== {rname} ===")
        names = list(BOTS)
        for a, b in combinations(names, 2):
            w = defaultdict(int); turns = []
            for g in range(n):
                order = [(a, b), (b, a)][g % 2]   # alternate who goes first
                st = State(rules, random.Random(rng.random()))
                bots = [BOTS[order[0]](), BOTS[order[1]]()]
                res = play_game(st, bots)
                turns.append(st.turn_count)
                if res is None: w["stall"] += 1
                else: w[order[res]] += 1
            print(f"  {a:9s} vs {b:9s}:  {a} {100*w[a]/n:4.0f}%  "
                  f"{b} {100*w[b]/n:4.0f}%  stalemate {100*w['stall']/n:4.0f}%  "
                  f"(avg {sum(turns)/n:.0f} turns)")
        # mirror hoarder
        w = defaultdict(int); turns = []
        for g in range(n):
            st = State(rules, random.Random(rng.random()))
            res = play_game(st, [make_hoarder(True), make_hoarder(True)])
            turns.append(st.turn_count)
            w["p1" if res == 0 else "p2" if res == 1 else "stall"] += 1
        print(f"  Hoarder mirror:  decisive {100*(w['p1']+w['p2'])/n:.0f}%  "
              f"stalemate {100*w['stall']/n:.0f}%  (avg {sum(turns)/n:.0f} turns)")

if __name__ == "__main__":
    tournament()
