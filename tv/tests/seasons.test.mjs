import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cycleSeason, seasonBoxes, showState, validProgress } from '../model.mjs';

const show = { id: 'example', watchedThrough: 0, watching: false };
const release = (count, status = 'Running') => ({ status, seasons: Array.from({ length: count }, (_, index) => ({ number: index + 1 })) });
const numbers = boxes => boxes.map(box => box.number);

test('Reacher and The Traitors: New Blood stop at S5 even when snapshots contain S6', () => {
  const config = JSON.parse(readFileSync(new URL('../shows.json', import.meta.url)));
  const snapshot = JSON.parse(readFileSync(new URL('../releases.json', import.meta.url)));
  for (const id of ['reacher', 'the-traitors']) {
    const entry = config.shows.find(show => show.id === id);
    const metadata = snapshot.shows[id];
    assert.deepEqual(numbers(seasonBoxes(entry, metadata)), [1, 2, 3, 4, 5]);
    assert.equal(showState(entry, metadata).latest, 5);
    assert.throws(() => cycleSeason(entry, metadata, 6), /visible season/);
    assert.deepEqual(numbers(seasonBoxes({ ...entry, watchedThrough: 5, watching: true }, metadata)), [1, 2, 3, 4, 5]);
    assert.equal(showState({ ...entry, watchedThrough: 5, watching: true }, metadata).status, 'waiting');
  }
});

test('unstarted shows show S1–S5, including while watching the first season', () => {
  assert.deepEqual(numbers(seasonBoxes(show, release(12))), [1, 2, 3, 4, 5]);
  const boxes = seasonBoxes({ ...show, watching: true }, release(12));
  assert.deepEqual(numbers(boxes), [1, 2, 3, 4, 5]);
  assert.equal(boxes[0].status, 'watching');
});

test('after a season is finished, the boxes show the latest five known seasons', () => {
  assert.deepEqual(numbers(seasonBoxes({ ...show, watchedThrough: 1 }, release(8))), [4, 5, 6, 7, 8]);
  const boxes = seasonBoxes({ ...show, watchedThrough: 10, watching: true }, release(11));
  assert.deepEqual(numbers(boxes), [7, 8, 9, 10, 11]);
  assert.deepEqual(boxes.map(box => box.status), ['done', 'done', 'done', 'done', 'watching']);
});

test('short shows display only their known season count and ignore specials', () => {
  const metadata = { ...release(2), seasons: [{ number: 0 }, ...release(2).seasons] };
  assert.deepEqual(numbers(seasonBoxes(show, metadata)), [1, 2]);
  assert.deepEqual(numbers(seasonBoxes({ ...show, watchedThrough: 1 }, metadata)), [1, 2]);
  assert.deepEqual(numbers(seasonBoxes(show, release(1))), [1]);
});

test('missing season metadata falls back to S1–S5 without inventing a premiere', () => {
  for (const metadata of [undefined, release(0)]) {
    assert.deepEqual(numbers(seasonBoxes(show, metadata)), [1, 2, 3, 4, 5]);
    assert.equal(showState(show, metadata).premiere, null);
  }
});

test('completed ended shows have only done boxes even if an old watching flag remains', () => {
  const boxes = seasonBoxes({ ...show, watchedThrough: 7, watching: true }, release(7, 'Ended'));
  assert.deepEqual(numbers(boxes), [3, 4, 5, 6, 7]);
  assert.ok(boxes.every(box => box.status === 'done'));
});

test('recorded progress remains visible when the release metadata is incomplete', () => {
  assert.deepEqual(numbers(seasonBoxes({ ...show, watchedThrough: 6 }, release(2))), [2, 3, 4, 5, 6]);
  const boxes = seasonBoxes({ ...show, watchedThrough: 6, watching: true }, release(2));
  assert.equal(boxes.at(-1).number, 7);
  assert.equal(boxes.at(-1).status, 'watching');
});

test('season clicks cycle unwatched → watching → done → unwatched and complete the prefix', () => {
  const metadata = release(5);
  const watching = cycleSeason(show, metadata, 3);
  assert.deepEqual(watching, { watchedThrough: 2, watching: true });
  assert.deepEqual(seasonBoxes({ ...show, ...watching }, metadata).map(box => box.status), ['done', 'done', 'watching', 'unwatched', 'unwatched']);
  const done = cycleSeason({ ...show, ...watching }, metadata, 3);
  assert.deepEqual(done, { watchedThrough: 3, watching: false });
  const unwatched = cycleSeason({ ...show, ...done }, metadata, 3);
  assert.deepEqual(unwatched, { watchedThrough: 2, watching: false });
  assert.ok([watching, done, unwatched].every(validProgress));
});

test('clicking a later empty season fills all earlier seasons, including hidden ones', () => {
  const initial = { ...show, watchedThrough: 6, watching: true };
  const metadata = release(10);
  const progress = cycleSeason(initial, metadata, 10);
  assert.deepEqual(progress, { watchedThrough: 9, watching: true });
  assert.deepEqual(seasonBoxes({ ...initial, ...progress }, metadata).map(box => box.status), ['done', 'done', 'done', 'done', 'watching']);
});

test('clearing an earlier completed season clears it and all later progress', () => {
  const metadata = release(5);
  const progress = cycleSeason({ ...show, watchedThrough: 4, watching: true }, metadata, 2);
  assert.deepEqual(progress, { watchedThrough: 1, watching: false });
  assert.deepEqual(seasonBoxes({ ...show, ...progress }, metadata).map(box => box.status), ['done', 'unwatched', 'unwatched', 'unwatched', 'unwatched']);
});

test('finishing the last season moves an ended show to Done; clearing it revives the show', () => {
  const metadata = release(5, 'Ended');
  const progress = cycleSeason({ ...show, watchedThrough: 4, watching: true }, metadata, 5);
  const finished = { ...show, ...progress };
  assert.equal(showState(finished, metadata).status, 'done');
  assert.equal(showState({ ...finished, ...cycleSeason(finished, metadata, 5) }, metadata).status, 'waiting');
});
