// Engine + policy parity: every Python-exported fixture must replay identically.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { Game, play, snapshot } from '../engine.js';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures');
const files = readdirSync(dir).filter(f => f.endsWith('.json') && f !== 'strategies.json');
assert.ok(files.length >= 10, 'fixtures present');

for (const f of files) {
  test(`parity ${f}`, () => {
    const fx = JSON.parse(readFileSync(path.join(dir, f), 'utf8'));
    const g = Game.fromSnapshot(fx.rules, fx.initial);
    const steps = [];
    const hook = (gg, me, act, cost, left) => steps.push({ who: me, left, action: act, cost, after: snapshot(gg) });
    const { winner, game } = play(fx.genes.a, fx.genes.b, fx.rules, g, hook);
    for (let i = 0; i < Math.min(steps.length, fx.steps.length); i++) {
      const got = steps[i], want = fx.steps[i];
      assert.deepEqual({ who: got.who, left: got.left, action: got.action, cost: got.cost },
                       { who: want.who, left: want.left, action: want.action, cost: want.cost },
                       `${f}: step ${i} decision differs (turn ${want.after.turn_count + 1})`);
      assert.deepEqual(got.after, want.after, `${f}: step ${i} state differs`);
    }
    assert.equal(steps.length, fx.steps.length, `${f}: step count`);
    assert.equal(winner, fx.result, `${f}: winner`);
    assert.equal(game.turn_count, fx.turns, `${f}: turns`);
  });
}
