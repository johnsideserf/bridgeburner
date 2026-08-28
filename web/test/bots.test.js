import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Game, legalActions, mulberry32, play, botTurn, CURRENT_RULES, RED, BLK } from '../engine.js';
import { makeBot, BOTS, STRATEGIES } from '../bots.js';

function fixed({ hand0 = [], bridge0 = [], hand1 = [], bridge1 = [], rules = CURRENT_RULES, turn = 0 }) {
  const g = new Game(rules, mulberry32(3));
  g.hands = [hand0.map(c => [...c]), hand1.map(c => [...c])];
  g.bridges = [bridge0.map(c => [...c]), bridge1.map(c => [...c])];
  g.turn = turn;
  return g;
}
const legal = (g, me, left, act) => legalActions(g, me, left).some(([a]) => JSON.stringify(a) === JSON.stringify(act));

test('bot roster has three tiers and strategies from the solver', () => {
  assert.deepEqual(Object.keys(BOTS), ['Builder', 'Equilibrium', 'Rollout']);
  assert.ok(STRATEGIES.Equilibrium.length === 10);
});

test('rollout bot returns a legal action', () => {
  const g = new Game(CURRENT_RULES, mulberry32(11));
  const decide = makeBot('Rollout', { rollouts: 4, rng: mulberry32(5) });
  const act = decide(g, 0, 2);
  assert.ok(legal(g, 0, 2, act), JSON.stringify(act));
});

test('rollout bot takes an immediate winning build', () => {
  const g = fixed({ hand0: [[9, RED], [2, BLK]], bridge0: [[2, RED], [3, RED], [4, RED], [5, RED]], hand1: [[6, BLK]] });
  const decide = makeBot('Rollout', { rollouts: 16, rng: mulberry32(5) });
  assert.deepEqual(decide(g, 0, 2), [1, [9, RED]]);
});

test('rollout bot burns the cap on a reply turn instead of finishing into a loss', () => {
  // Human (P0) finished 2..6 red. Bot (P1) is capped by a Q; 7r cannot be built but burns their 6r.
  const g = fixed({ hand0: [], bridge0: [[2, RED], [3, RED], [4, RED], [5, RED], [6, RED]],
                    hand1: [[7, RED], [2, BLK]], bridge1: [[2, BLK], [3, BLK], [4, BLK], [12, BLK]], turn: 1 });
  const decide = makeBot('Rollout', { rollouts: 32, rng: mulberry32(9) });
  const acts = [];
  const r = botTurn(decide, g, CURRENT_RULES, 1, (gg, me, act) => acts.push(act[0]));
  assert.ok(acts.includes(2), `expected a burn in the reply turn, got ${JSON.stringify(acts)}`);
  assert.equal(g.bridges[0].length, 4);          // the cap was burned
  assert.equal(r.over, false);                   // round continues
});

test('rollout bot beats the Builder bot clearly over a small sample', () => {
  let wins = 0; const n = 8;
  for (let i = 0; i < n; i++) {
    const g = new Game(CURRENT_RULES, mulberry32(100 + i));
    const roll = makeBot('Rollout', { rollouts: 32, rng: mulberry32(i) });
    const build = makeBot('Builder');
    const decideFor = i % 2 === 0 ? [roll, build] : [build, roll];
    let r;
    while (true) { const me = g.turn; r = botTurn((gg, m, l) => decideFor[m](gg, m, l), g, CURRENT_RULES, me); if (r.over || g.turn_count > 200) break; }
    const rollSeat = i % 2 === 0 ? 0 : 1;
    if (r.winner === rollSeat) wins++; else if (r.winner === null) wins += 0.5;
  }
  assert.ok(wins / n >= 0.6, `rollout won ${wins}/${n}`);
});
