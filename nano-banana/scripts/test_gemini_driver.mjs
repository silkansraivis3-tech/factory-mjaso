// The page driver finds Gemini's buttons by both their old and new labels, names the tiles to zoom, and stops at
// the daily picture limit with the time it ends.
//
//     node --test test_gemini_driver.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const SRC = readFileSync(process.env.GB_DRIVER || join(dirname(fileURLToPath(import.meta.url)), 'gemini_driver.js'), 'utf8');

// a page with these buttons and these replies - just enough of the DOM for the driver's own lookups
function page(labels = [], replies = []) {
  const button = l => ({ getAttribute: n => (n === 'aria-label' ? l : null), innerText: '', offsetParent: {}, disabled: false });
  const buttons = labels.map(button);
  const document = {
    querySelectorAll: s => (/model-response/.test(s) ? replies : /button/.test(s) ? buttons : []),
    querySelector: () => null,
    getElementById: () => null,
  };
  const ctx = { document, location: { pathname: '/app' }, setTimeout, Date, innerWidth: 1280, innerHeight: 800 };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return ctx.GB;
}
const plain = o => JSON.parse(JSON.stringify(o));   // objects from the vm have its own prototypes
const reply = text => ({ innerText: text, querySelectorAll: () => [] });

test('the Images chip and the aspect button are found by their new labels', () => {
  const s = page(['Deselect Images', 'Aspect ratio, 16:9']).state();
  assert.equal(s.images, true);
  assert.equal(s.aspect, '16:9');
});

test('and still by their old ones', () => {
  const s = page(['Close Images', 'Aspect ratio']).state();
  assert.equal(s.images, true);
  assert.equal(s.aspect, null);
  assert.equal(page(['Upload and tools']).state().images, false);
});

test('a 16:9 picture is two tiles side by side, a 4:3 one two by two', () => {
  const GB = page();
  assert.deepEqual(plain(GB.tiles(1024, 572)), { cols: 2, rows: 1, tiles: [[0, 0, 512, 572], [512, 0, 1024, 572]] });
  const t = GB.tiles(1024, 765);
  assert.equal(t.cols * t.rows, 4);
  assert.deepEqual(plain(t.tiles.map(r => r[3] - r[1])), [382, 382, 383, 383]);
  assert.ok(t.tiles.every(r => r[2] - r[0] === 512));
});

test('the limit reply gives its end time, and a clock time becomes the next moment it comes round', () => {
  const GB = page();
  const now = new Date(2026, 10, 5, 14, 0);
  const a = GB.limitOf("You've reached your image-generation limit until 7:42 PM. Try again then.", now);
  assert.equal(a.limit, true);
  assert.equal(a.until, '7:42 PM');
  assert.match(a.at, /^2026-11-05T19:42:00[+-]\d\d:\d\d$/);
  assert.match(GB.limitOf("You've reached your image generation limit until 9:05 AM", now).at, /^2026-11-06T09:05/);
  assert.match(GB.limitOf("You've reached your image-generation limit until tomorrow, 13:10.", now).at, /^2026-11-06T13:10/);
  const d = GB.limitOf("You've reached your image-generation limit until Nov 8, 3:15 AM.", now);
  assert.equal(d.until, 'Nov 8, 3:15 AM');
  assert.equal(d.at, null);
  assert.equal(GB.limitOf('Here is your picture of a gas carrier.', now), null);
});

test('GB.wait() stops at the limit instead of calling it a failure', async () => {
  const GB = page([], [reply("You've reached your image-generation limit until 7:42 PM.")]);
  const w = await GB.wait(2000);
  assert.equal(w.done, true);
  assert.equal(w.limit, true);
  assert.equal(w.until, '7:42 PM');
  assert.equal(w.failed, undefined);
});
