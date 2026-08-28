# bridge-burner-proofs

Balance analysis for **Bridgeburner**, a two-player card game played with a
standard 52-card deck. Contains the game engine, a PSRO-style equilibrium
solver, earlier heuristic-bot tournaments, and the illustrated rules PDF.

## The game (locked ruleset, 2026-08-27)

Race to build a 5-card ascending bridge (aces low, suits ignored). 2 actions
per turn. Full rules in [RULES.md](RULES.md) / `Bridgeburner_Rules.pdf`.

| Action   | Cost | Effect |
|----------|------|--------|
| Draw     | 1    | Take top card of the draw pile |
| Build    | 2    | Play a hand card higher than your rightmost bridge card |
| Burn     | 1*   | Discard a same-color card that beats the opponent's rightmost bridge card **by at most 2 ranks**; it washes into the River. *J/Q cost 2 actions; Kings are unburnable |
| Ford     | 1    | Discard any hand card, take any of the 3 face-up River cards, refill River |
| Flush    | 1    | Replace all 3 River cards |
| Demolish | 1    | Remove your own rightmost bridge card |

Setup: deal 7 each, 3 face-up River cards. **The pile is the clock** — never
reshuffled; when it runs out the round ends and the longer bridge wins.
**Equal turns** — if the first player finishes, the second gets a reply turn.
Ties compare the top card, then the next card down. Best of three.

## Files

- `engine.py` — fast game engine (~10k games/s) + parameterized policy space
  (10 genes, ~23k strategies). Rule variants via a `rules` dict: `slack`
  (keep-pace), `salvage`, `burn_cost2`, `hand_limit`, `clock` (no reshuffle,
  round ends when the pile runs out: longer bridge wins), `p2_extra` (extra
  cards for the second player), `first_turn_actions`, `equal_turns` (second
  player always gets a reply turn; both finished → compare top card, then
  next card down),
  `burn_span` (torch must be within N ranks of the target), `cheap_spans`
  (build costs 1 while your bridge has fewer than N cards). Policy never builds a
  King below slot 5 (dead end), demolishes when stuck, and has an `armor`
  gene (color-aware builds). `match_stats()` reports first-player win rate,
  burns/game, stalls, turns.
- `solve.py` — PSRO-lite: incremental round-robin payoff matrix → Nash
  mixture (regret matching) → coordinate-ascent best-response search →
  **held-out** re-evaluation of each best response (so reported
  exploitability isn't search noise) → exploitability trajectory,
  first-player advantage, comeback/stall rates, burns/game, mixture support.
  Rulesets live in `RULESETS`; pick with `--rules Name,Name`.
- `dashboard.py` + `dashboard.html` — live browser dashboard for solver runs
  (`solve.py --progress` streams JSON-lines events; the page polls them).
- `play.html` + `game_session.py` — the Table page at `/play`: watch two bots
  play a game frame by frame, or play against a bot yourself.
- `ROADMAP.md` — what's next, including the online playable version.
- `trace_game.py` — prints one game turn by turn (`--seed N --a Builder --b Equilibrium --rules NoLimit`).
- `test_*.py` — pytest suite.
- `sim.py`, `sim2.py` — earlier heuristic-bot tournaments (rounds 1 & 2).
- `make_rules.py` — regenerates `Bridgeburner_Rules.pdf` (reportlab).
- `RULES.md` — plain-text rulebook (same content as the PDF; keep in sync).

## Key findings (simulation, 2026-08-27)

- Original rules: equilibrium = hoard high cards + burn everything; 23%
  stalls, 115-turn games. Broken.
- Every "price of burning" knob alone (keep-pace, salvage, burn costs 2, hand
  limit) lands in one of two bad buckets: a burn war (fair, unplayable) or a
  race the first player wins 84–95%.
- `clock` (no reshuffle) removes stalls outright but alone just puts a
  deadline on the burn war (82% of games decided on the tiebreak).
- `equal_turns` fixes first-player advantage robustly (48–55%) regardless of
  the burn economy, unlike dealing the second player extra cards.
- `burn_span 2` (torch within 2 ranks) kills "hoard highs" as a dual-purpose
  plan: high cards become finishers, not weapons. Under a flat 2-action burn
  cost the solver *voluntarily* limits itself to 2-rank torches anyway.
- **Locked: Clock + Span2 + Equal turns.** Confirmed over 3 seeds at 500
  games/eval: exploitability 49–50%, first player 48–49%, comeback after the
  opponent reaches 4 cards 29–31%, 0% stalls, 25-turn rounds, 6 burns/game.
  Equilibrium: build once you hold a full chain, burn with cheap torches,
  race when the pile is low. One dominant strategy within the bot policy
  space (support 1) — needs table testing for human-only play (bluffs, bait).
- Earlier "exploitability ~55%" numbers were search noise; the solver now
  re-evaluates best responses on held-out games.

## Run it

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                        # tests
.venv/bin/python solve.py                            # all rulesets (~2 min)
.venv/bin/python solve.py --rules NoLimit,BurnCost2   # subset (prefix match)
.venv/bin/python solve.py --games 500 --iters 8 --restarts 5 --heldout 8  # thorough
.venv/bin/python dashboard.py -- --rules Current,NoLimit --games 300   # live dashboard (opens browser)
.venv/bin/python dashboard.py                                        # just the dashboard + /play table
.venv/bin/python trace_game.py --seed 3                              # watch one game
.venv/bin/python make_rules.py                       # rebuild the PDF
```

Solver output ends with a summary table: exploitability (held-out best
response win rate; 50% = unexploitable), first-player win rate (50% = fair),
comeback rates after the opponent reaches 3/4 cards, stall rate, average
turns, burns per game, and mixture support (number of strategies in the Nash
mix; 1 = one dominant way to play).

**Reading the exploitability number honestly.** It is a *floor* estimate: the
best response is searched only within the bot policy space (10 genes), and it
is measured against the Nash mixture *before* the final exploiter joined the
pool. 50% means "nothing in this vocabulary beats the mix", not "the game is
solved". Early stopping (`--stop`, default 53%) is confirmed on a second
held-out batch before it fires; for any number you intend to quote, run with
`--stop 0.0` so every iteration executes, and use `--games 500 --heldout 8`
over several `--seed`s.

## Open questions

- Richer policy space (bait builds, River denial, torch conservation) to see
  whether the locked ruleset supports a genuinely mixed equilibrium.
- CFR/MCCFR solver for a miniature Bridgeburner (smaller deck, 3-card
  bridge) to get provably optimal play for the abstraction.
- Human playtesting of the locked ruleset.
