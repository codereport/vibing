import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { compareEntries, localDate, mergedShow, showState, validProgress } from '../model.mjs';

const today = '2026-10-19';
const show = { id: 'example', watching: false, watchedThrough: 1 };
const release = { status: 'Running', seasons: [{ number: 1, premiereDate: '2024-05-08' }, { number: 2, premiereDate: '2026-11-04' }] };

test('a future season waits and becomes ready on its premiere day', () => {
  assert.equal(showState(show, release, today).status, 'waiting');
  assert.equal(showState(show, release, '2026-11-04').status, 'ready');
  assert.equal(showState(show, release, '2026-11-05').status, 'ready');
});

test('actively watching overrides release-date classification', () => {
  assert.equal(showState({ ...show, watching: true }, release, today).status, 'watching');
});

test('an ended show with unwatched seasons stays active', () => {
  assert.equal(showState({ ...show, watchedThrough: 0 }, { ...release, status: 'Ended' }, today).status, 'ready');
});

test('an ended, fully watched show moves to Done even if watching was left on', () => {
  assert.equal(showState({ ...show, watchedThrough: 2, watching: true }, { ...release, status: 'Ended' }, today).status, 'done');
});

test('finishing a running show waits for the next season', () => {
  const state = showState({ ...show, watchedThrough: 2 }, release, today);
  assert.equal(state.status, 'waiting');
  assert.equal(state.season, 3);
  assert.equal(state.premiere, null);
});

test('a newly discovered season brings a finished show back into Active', () => {
  const watched = { ...show, watchedThrough: 2 };
  const old = { status: 'Ended', seasons: [{ number: 1 }, { number: 2 }] };
  assert.equal(showState(watched, old, today).status, 'done');
  const updated = { ...old, seasons: [...old.seasons, { number: 3, premiereDate: today }] };
  assert.equal(showState(watched, updated, today).status, 'ready');
});

test('missing metadata or unknown premiere dates never imply finished or available', () => {
  assert.equal(showState(show, undefined, today).status, 'waiting');
  assert.equal(showState(show, { status: 'Ended', seasons: [] }, today).status, 'waiting');
  assert.equal(showState(show, { ...release, seasons: [{ number: 2, premiereDate: null }] }, today).status, 'waiting');
});

test('season order is normalized without mutating metadata; specials are excluded', () => {
  const seasons = [{ number: 3, premiereDate: '2027-01-22' }, { number: 0 }, { number: 2, premiereDate: today }];
  const state = showState(show, { ...release, seasons }, today);
  assert.equal(state.season, 2);
  assert.equal(state.status, 'ready');
  assert.equal(seasons[0].number, 3);
});

test('local calendar dates do not shift at a UTC midnight boundary', () => {
  const now = new Date(2026, 9, 18, 23, 45);
  assert.equal(localDate(now), '2026-10-18');
});

test('only valid saved progress overrides the canonical show', () => {
  const original = { ...show, title: 'Original', tvmazeId: 42 };
  assert.deepEqual(mergedShow(original, { watching: true, watchedThrough: 3, title: 'Forged', tvmazeId: 99 }), { ...original, watching: true, watchedThrough: 3 });
  for (const invalid of [null, {}, { watching: true, watchedThrough: -1 }, { watching: 'yes', watchedThrough: 1 }, { watching: false, watchedThrough: 1.5 }, { watching: false, watchedThrough: 1001 }]) {
    assert.ok(!validProgress(invalid));
    assert.deepEqual(mergedShow(original, invalid), original);
  }
});

test('waiting shows sort by the nearest premiere, with unknown dates last', () => {
  const entry = (id, premiere, status = 'waiting') => ({ show: { id }, state: { status, premiere } });
  const unsorted = [entry('unknown-a', null), entry('far', '2027-01-22'), entry('watching', null, 'watching'), entry('near', '2026-11-04'), entry('ready', '2026-10-14', 'ready'), entry('same-date', '2026-11-04'), entry('unknown-b', null)];
  assert.deepEqual(unsorted.toSorted(compareEntries).map(e => e.show.id), ['watching', 'ready', 'near', 'same-date', 'far', 'unknown-a', 'unknown-b']);
});

test('the catalog includes all 28 unique shows with valid editable progress', () => {
  const config = JSON.parse(readFileSync(new URL('../shows.json', import.meta.url)));
  assert.equal(config.shows.length, 28);
  assert.equal(new Set(config.shows.map(show => show.id)).size, 28);
  assert.equal(new Set(config.shows.map(show => show.tvmazeId)).size, 28);
  assert.ok(config.shows.every(validProgress));
  const bear = { ...config.shows.find(show => show.id === 'the-bear'), watchedThrough: 2, watching: false };
  const releases = JSON.parse(readFileSync(new URL('../releases.json', import.meta.url)));
  assert.equal(showState(bear, releases.shows[bear.id], today).status, 'ready');
  assert.equal(showState(bear, releases.shows[bear.id], today).season, 3);
  assert.equal(showState({ ...bear, watchedThrough: 3 }, releases.shows[bear.id], today).season, 4);
});

test('Extrapolations starts Ready and follows progress into Watching and Done', () => {
  const config = JSON.parse(readFileSync(new URL('../shows.json', import.meta.url)));
  const releases = JSON.parse(readFileSync(new URL('../releases.json', import.meta.url)));
  const extrapolations = config.shows.find(show => show.id === 'extrapolations');
  const metadata = releases.shows[extrapolations.id];
  assert.equal(extrapolations.watchedThrough, 0);
  assert.equal(metadata.tvmazeId, extrapolations.tvmazeId);
  assert.equal(metadata.status, 'Ended');
  assert.equal(showState(extrapolations, metadata, today).status, 'ready');
  assert.equal(showState({ ...extrapolations, watching: true }, metadata, today).status, 'watching');
  assert.equal(showState({ ...extrapolations, watchedThrough: 1 }, metadata, today).status, 'done');
});
