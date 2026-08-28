# Bridgeburner roadmap

## Done (2026-08-27)

- Engine + PSRO-lite solver with held-out best-response evaluation, first-player
  and comeback metrics, cross-ruleset summary.
- Standard rules: **the pile is the clock, equal turns** (tiebreak: top card,
  then next card down). "Close torches" (2-rank torch rule) and "Quick
  foundations" are optional house rules. First human playtest 2026-08-27.
- Live solver dashboard (`dashboard.py`), bot-game viewer and human-vs-bot table
  (`/play`), turn-by-turn trace tool.
- **Browser game v1 (2026-08-28):** https://johnsideserf.github.io/bridgeburner/
  — static GitHub Pages, JS engine with Python parity fixtures, three bot
  tiers incl. a rollout bot, best-of-three matches, house-rule toggles,
  shareable seeds. Deployed by `.github/workflows/pages.yml` on push.

## Next

- **`cheap_spans 2`** (spans 1–2 cost 1 action) shipped as the optional
  "Quick Foundations" house rule: 17-turn rounds, first build on turn ~2, best
  comeback rates, ~30% fewer burns. Promote to the standard rules if
  playtesting prefers it.
- **Richer bot vocabulary** so "one dominant strategy" isn't an artifact of the
  gene space: bait builds, River denial (fording away the card the rival
  needs), torch conservation, colour-aware burn timing.
- **Interaction metrics** in the solver summary: turns to first build, share of
  turns where a burn was available, builds burned within one turn.
- **More human playtesting.** Track burns per round and how rounds end
  (finished bridge vs clock); if games drift into burn wars as players
  improve, promote Close torches to the standard rules. Feed observed human
  plans back into the bot vocabulary. Watch for the **clock drain**: a first player ahead
  on the tiebreak can empty the pile on their own turn and end the round
  before P2 replies (legal; no bot plays it; a hand-written drainer moved P1
  from 49% to 51%). The `clock_reply` rule flag (P2 always gets a reply turn
  when the pile runs out) is implemented as `Current+ClockReply`; in
  simulation it over-corrects for bots (P1 win 48–49% -> 45–46%, 2 seeds x
  400 games, nothing else changes), so it is **not** in the standard rules.
  Adopt it only if humans actually play the drain line.
- **Miniature CFR/MCCFR** (smaller deck, 3-card bridge) for a provably optimal
  baseline to sanity-check the PSRO results.

## Next: the web game

- **Mobile layout** (deferred from v1): stack the side panels, fan the hand,
  bigger touch targets.
- **PvP with a link:** the engine runs in the browser, so two humans need only
  a relay — a tiny WebSocket room server (or WebRTC via a signalling page)
  that forwards actions; each client validates with `engine.js`. Invite by
  URL, no accounts. Then matchmaking (a lobby list) on top of the same relay.
- **Bot strength:** the Rollout bot beats the Equilibrium rule-bot ~62%, so a
  stronger opponent *can* exploit the solver's equilibrium — worth feeding
  back into the solver as an exploiter, and adding a "watch the bots" mode.
- **Balance loop:** optional anonymised game logs from the web game, replayed
  through the solver's metrics, so the ruleset keeps being validated against
  real human play.
