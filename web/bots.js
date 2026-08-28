// Bot opponents for the browser game.
//   Builder      — easy: builds whatever it can, never burns (solver seed "Builder")
//   Equilibrium  — medium: the solver's equilibrium rule-bot for the standard rules
//   Rollout      — hard: determinised Monte-Carlo rollouts on top of the engine
import { legalActions, doAction, afterAction, endTurn, botTurn, play, policy, mulberry32 } from './engine.js';
import { STRATEGIES } from './strategies.js';
export { STRATEGIES };

export const BOTS = {
  Builder:     { label: 'Builder',     blurb: 'Builds fast, never burns. Learn the flow.' },
  Equilibrium: { label: 'Equilibrium', blurb: 'The solver’s best rule-bot. Fair fight.' },
  Rollout:     { label: 'Rollout',     blurb: 'Simulates every move to the end. Bring torches.' },
};

// Sample a world consistent with what `me` can see: the opponent's hand and the
// pile order are unknown, so redistribute them from the same pool of cards.
function determinize(g, me, rng) {
  const c = g.clone(); const opp = 1 - me;
  const pool = [...c.hands[opp], ...c.draw]; rng.shuffle(pool);
  const n = c.hands[opp].length;
  c.hands[opp] = pool.slice(0, n); c.draw = pool.slice(n); c.rng = rng;
  return c;
}

// Candidate pruning: every build/burn/draw/flush/demolish, but only the fords a
// sensible player considers (dump the lowest card for any River card, or any
// hand card for the best River card).
function candidates(g, me, left) {
  const all = legalActions(g, me, left).filter(([a]) => a[0] !== 9);
  const fords = all.filter(([a]) => a[0] === 3), rest = all.filter(([a]) => a[0] !== 3);
  if (!fords.length) return rest;
  const hand = g.hands[me];
  const low = hand.reduce((m, c) => c[0] < m[0] ? c : m, hand[0]);
  let bi = 0; for (let i = 1; i < g.river.length; i++) if (g.river[i][0] > g.river[bi][0]) bi = i;
  const keep = fords.filter(([a]) => (a[1][0] === low[0] && a[1][1] === low[1]) || a[2] === bi);
  return rest.concat(keep);
}

export function rolloutBot({ rollouts = 96, rng = mulberry32(1), genes = STRATEGIES.Equilibrium } = {}) {
  const pol = (gg, m, l) => policy(genes, gg, m, l);
  return (g, me, left) => {
    const rules = g.rules;
    const cands = candidates(g, me, left);
    if (!cands.length) return [9];
    // Common random numbers: every candidate is scored on the SAME sampled
    // worlds, so differences between candidates aren't drowned in sampling noise.
    const worlds = Array.from({ length: rollouts }, () => determinize(g, me, rng));
    const t0 = g.turn_count;
    let best = null, bestScore = -Infinity;
    for (const [act] of cands) {
      let total = 0;
      for (const w of worlds) {
        const c = w.clone(); c.rng = rng;
        const cst = doAction(c, me, act);
        if (cst === null) { total = -Infinity; break; }
        if (act[0] === 2) c.burns[me] += 1;
        let { over, winner, turnOver } = afterAction(c, rules, me);
        if (!over) {
          const l = left - cst;
          const e = (turnOver || l <= 0) ? endTurn(c, rules, me) : botTurn(pol, c, rules, me, null, l);
          over = e.over; winner = e.winner;
          if (!over) winner = play(genes, genes, rules, c).winner;
        }
        // Time discount: win sooner, lose later. Breaks the ties a plain
        // win-rate leaves between "win now" and "win in two turns".
        const result = winner === me ? 1 : winner === null ? 0.5 : 0;
        const dt = c.turn_count - t0;
        total += result + (result >= 0.5 ? -1 : 1) * Math.min(0.02, 0.001 * dt);
      }
      const s = total / rollouts;
      if (s > bestScore) { bestScore = s; best = act; }
    }
    return best;
  };
}

export function makeBot(name, opts = {}) {
  if (name === 'Rollout') return rolloutBot(opts);
  const genes = STRATEGIES[name];
  if (!genes) throw new Error(`unknown bot ${name}`);
  return (g, me, left) => policy(genes, g, me, left);
}
