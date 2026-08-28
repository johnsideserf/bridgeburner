import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Game, legalActions, doAction, clockWinner, compareBridges, mulberry32, RED, BLK } from '../engine.js';

function fixed({ hand0 = [], bridge0 = [], hand1 = [], bridge1 = [], river = null, rules = {} }) {
  const g = new Game(rules, mulberry32(1));
  g.hands = [hand0.map(c => [...c]), hand1.map(c => [...c])];
  g.bridges = [bridge0.map(c => [...c]), bridge1.map(c => [...c])];
  if (river) g.river = river.map(c => [...c]);
  return g;
}

test('deal is 7/7/3 and the pile holds the rest', () => {
  const g = new Game({}, mulberry32(42));
  assert.equal(g.hands[0].length, 7); assert.equal(g.hands[1].length, 7);
  assert.equal(g.river.length, 3); assert.equal(g.draw.length, 52 - 17);
  const all = [...g.hands[0], ...g.hands[1], ...g.river, ...g.draw].map(c => c.join(':')).sort();
  assert.equal(new Set(all).size, 26);   // 26 distinct (rank,color) pairs, each twice
  assert.equal(all.length, 52);
});

test('seeded RNG is deterministic', () => {
  const a = new Game({}, mulberry32(7)), b = new Game({}, mulberry32(7));
  assert.deepEqual(a.hands, b.hands); assert.deepEqual(a.draw, b.draw);
});

test('legal actions respect burn span, cost and actions left', () => {
  const g = fixed({ hand0: [[4, RED], [9, BLK], [6, RED]], bridge0: [[3, RED]], bridge1: [[5, RED]],
                    river: [[2, BLK], [7, RED], [11, BLK]], rules: { burn_span: 2 } });
  const acts = legalActions(g, 0, 2).map(([a, c]) => JSON.stringify([a, c]));
  assert.ok(acts.includes(JSON.stringify([[1, [4, RED]], 2])));
  assert.ok(acts.includes(JSON.stringify([[2, [6, RED]], 1])));
  assert.ok(!acts.includes(JSON.stringify([[2, [9, BLK]], 1])));
  assert.equal(legalActions(g, 0, 2).filter(([a]) => a[0] === 3).length, 9);
  assert.ok(!legalActions(g, 0, 1).some(([a]) => a[0] === 1));
});

test('burn washes the card into the river and clock winner compares top-down', () => {
  const g = fixed({ hand0: [[8, RED]], bridge1: [[6, RED]], river: [[2, BLK], [3, BLK], [4, BLK]] });
  assert.equal(doAction(g, 0, [2, [8, RED]]), 1);
  assert.deepEqual(g.river, [[3, BLK], [4, BLK], [6, RED]]);
  assert.deepEqual(g.bridges[1], []);
  const h = fixed({ bridge0: [[2, RED], [9, RED]], bridge1: [[4, BLK], [9, BLK]] });
  assert.equal(clockWinner(h), 1);
  assert.equal(compareBridges([[2, RED]], [[2, BLK]]), null);
});
