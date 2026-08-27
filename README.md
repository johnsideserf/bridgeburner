# bridge-burner-proofs

Balance analysis for **Bridgeburner**, a two-player card game played with a
standard 52-card deck. Contains the game engine, a PSRO-style equilibrium
solver, earlier heuristic-bot tournaments, and the illustrated rules PDF.

## The game (current ruleset)

Race to build a 5-card ascending bridge (aces low, suits ignored). 2 actions
per turn:

| Action   | Cost | Effect |
|----------|------|--------|
| Draw     | 1    | Take top card of the draw pile |
| Build    | 2    | Play a hand card higher than your rightmost bridge card |
| Burn     | 1*   | Discard a same-color, higher hand card to destroy opponent's rightmost bridge card (it washes into the River). **Salvage:** the burned player draws 1 card. *Burning a J/Q costs 2 actions; Kings are unburnable (nothing beats them) |
| Ford     | 1    | Discard any hand card, take any of the 3 face-up River cards, refill River |
| Flush    | 1    | Replace all 3 River cards |
| Demolish | 1    | Remove your own rightmost bridge card |

Setup: deal 7 each, 3 face-up River cards. Empty draw pile → reshuffle
discards. First 5-card bridge wins; best of three.

## Files

- `engine.py` — fast game engine (~10k games/s) + parameterized policy space
  (10 genes, ~23k strategies). Rule variants via a `rules` dict: `slack`
  (keep-pace), `salvage`, `burn_cost2`, `hand_limit`, `clock` (no reshuffle,
  round ends when the pile runs out: longer bridge wins), `p2_extra` (extra
  cards for the second player), `first_turn_actions`. Policy never builds a
  King below slot 5 (dead end), demolishes when stuck, and has an `armor`
  gene (color-aware builds). `match_stats()` reports first-player win rate,
  burns/game, stalls, turns.
- `solve.py` — PSRO-lite: incremental round-robin payoff matrix → Nash
  mixture (regret matching) → coordinate-ascent best-response search →
  **held-out** re-evaluation of each best response (so reported
  exploitability isn't search noise) → exploitability trajectory,
  first-player advantage, comeback/stall rates, burns/game, mixture support.
  Rulesets live in `RULESETS`; pick with `--rules Name,Name`.
- `test_engine.py`, `test_solve.py` — pytest suite for the above.
- `sim.py`, `sim2.py` — earlier heuristic-bot tournaments (rounds 1 & 2).
- `make_rules.py` — regenerates `Bridgeburner_Rules.pdf` (reportlab).
- `RULES.md` — plain-text rulebook (same content as the PDF; keep in sync).

## Key findings so far

- Original unrestricted rules: equilibrium = hoard high cards + burn
  everything; 23% of games stall. Broken.
- Keep-pace rule (burn only if your bridge >= theirs): unexploitable but
  kills comebacks (4% after opponent reaches 4) and most interaction.
- Slack-1 keep-pace: re-enables the burn lock. Rejected.
- Salvage (burns always legal, burned player draws 1): 0% stalls, ~12-turn
  games, 10% comebacks — but equilibrium self-play is a near-pure race that
  the **first player wins 87%**. Not a fix.
- Most stalls under the original rules are King dead-ends (a King built at
  slot 1–4 can never be built past), not the burn war: 90% of stalled games
  had a King stuck on a bridge.
- Earlier "exploitability ~55%" numbers were the search's noise floor
  (winner's-curse bias), not real exploitability; the solver now re-evaluates
  best responses on held-out games.

## Run it

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                        # tests
.venv/bin/python solve.py                            # all rulesets (~2 min)
.venv/bin/python solve.py --rules NoLimit,BurnCost2   # subset (prefix match)
.venv/bin/python solve.py --games 500 --iters 8 --restarts 5 --heldout 8  # thorough
.venv/bin/python make_rules.py                       # rebuild the PDF
```

Solver output ends with a summary table: exploitability (held-out best
response win rate; 50% = unexploitable), first-player win rate (50% = fair),
comeback rates after the opponent reaches 3/4 cards, stall rate, average
turns, burns per game, and mixture support (number of strategies in the Nash
mix; 1 = one dominant way to play).

## Open questions

- Push exploitability from ~55% toward 50%: more eval games, richer gene
  space (e.g. color-aware burn timing, river denial).
- CFR/MCCFR solver for a miniature Bridgeburner (smaller deck, 3-card
  bridge) to get provably optimal play for the abstraction.
- Human playtesting of the salvage meta: do burns really cluster late?
