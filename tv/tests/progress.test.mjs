import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { request } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { applyProgress } from '../scripts/import-progress.mjs';
import { createDevServer } from '../scripts/dev-server.mjs';

const config = {
  version: 1,
  shows: [
    { id: 'first', title: 'First', tvmazeId: 42, watching: true, watchedThrough: 1, note: 'Keep this note.' },
    { id: 'second', title: 'Second', tvmazeId: 43, watching: false, watchedThrough: 2 },
  ],
};
const payload = (id = 'first', watchedThrough = 3) => ({ version: 1, shows: [{ id, watching: false, watchedThrough }] });

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'tv-progress-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const configPath = join(root, 'shows.json');
  const source = JSON.stringify(config, null, 2) + '\n';
  await writeFile(configPath, source);
  return { root, configPath, source };
}

async function localServer(t) {
  const files = await fixture(t);
  const server = createDevServer({ root: files.root });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const port = server.address().port;
  function call(path, { method = 'GET', body, headers = {} } = {}) {
    return new Promise((resolve, reject) => {
      const req = request({ host: '127.0.0.1', port, path, method, headers }, response => {
        const chunks = [];
        response.on('data', chunk => chunks.push(chunk));
        response.on('end', () => resolve({ status: response.statusCode, headers: response.headers, body: Buffer.concat(chunks).toString() }));
      });
      req.on('error', reject);
      req.end(body);
    });
  }
  const post = (data, options = {}) => call('/api/progress', {
    method: 'POST', body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' }, ...options,
  });
  return { ...files, port, call, post };
}

test('repository imports change only progress for matching shows and preserve catalog metadata', async t => {
  const { configPath } = await fixture(t);
  const imported = payload();
  Object.assign(imported.shows[0], { title: 'Replaced', tvmazeId: 999, note: 'Replaced' });
  imported.shows.push({ id: 'unknown', watching: true, watchedThrough: 10 });
  const result = await applyProgress(imported, { configPath });
  assert.deepEqual(result, { count: 1, changed: true });
  assert.deepEqual(JSON.parse(await readFile(configPath, 'utf8')), {
    ...config, shows: [{ ...config.shows[0], watching: false, watchedThrough: 3 }, config.shows[1]],
  });
});

test('validation rejects invalid exports atomically and leaves no temporary files', async t => {
  const { root, configPath, source } = await fixture(t);
  for (const imported of [
    null, {}, { version: 2, shows: payload().shows }, { version: 1, shows: [] },
    payload('unknown'), payload('first', -1), payload('first', 1.5), payload('first', 1001),
    { version: 1, shows: [...payload().shows, ...payload().shows] },
    { version: 1, shows: [{ id: 'first', watching: 'yes', watchedThrough: 2 }] },
    { version: 1, shows: [...payload().shows, null] },
  ]) {
    await assert.rejects(applyProgress(imported, { configPath }));
    assert.equal(await readFile(configPath, 'utf8'), source);
  }
  assert.deepEqual(await readdir(root), ['shows.json']);
});

test('dry runs and unchanged imports preserve the original file bytes', async t => {
  const { root, configPath, source } = await fixture(t);
  assert.deepEqual(await applyProgress(payload(), { configPath, checkOnly: true }), { count: 1, changed: true });
  assert.deepEqual(await applyProgress(config, { configPath }), { count: 2, changed: false });
  assert.equal(await readFile(configPath, 'utf8'), source);
  assert.deepEqual(await readdir(root), ['shows.json']);
});

test('the CLI accepts stdin in check mode from another working directory and reports invalid JSON', () => {
  const script = fileURLToPath(new URL('../scripts/import-progress.mjs', import.meta.url));
  const valid = spawnSync(process.execPath, [script, '--check', '-'], {
    input: JSON.stringify(payload('the-wire')), cwd: tmpdir(), encoding: 'utf8',
  });
  assert.equal(valid.status, 0, valid.stderr);
  assert.match(valid.stdout, /Valid progress for 1 shows/);
  const invalid = spawnSync(process.execPath, [script, '--check', '-'], { input: '{', encoding: 'utf8' });
  assert.equal(invalid.status, 1);
  assert.match(invalid.stderr, /Import failed/);
});

test('the local server serves static JSON and modules at / and /tv/ without exposing scripts', async t => {
  const { root, call } = await localServer(t);
  await writeFile(join(root, 'model.mjs'), 'export const test = true;');
  for (const path of ['/shows.json', '/tv/shows.json']) {
    const result = await call(path);
    assert.equal(result.status, 200);
    assert.equal(result.headers['cache-control'], 'no-store');
    assert.deepEqual(JSON.parse(result.body), config);
  }
  assert.match((await call('/tv/model.mjs')).headers['content-type'], /javascript/);
  const head = await call('/shows.json', { method: 'HEAD' });
  assert.equal(head.status, 200);
  assert.equal(head.body, '');
  assert.equal((await call('/scripts/import-progress.mjs')).status, 404);
  assert.equal((await call('/tv/../README.md')).status, 404);
  const redirect = await call('/tv');
  assert.equal(redirect.status, 302);
  assert.equal(redirect.headers.location, '/tv/');
});

test('the local save API persists progress, accepts /tv/, and recovers after invalid imports', async t => {
  const { configPath, post, call } = await localServer(t);
  assert.equal((await post(null)).status, 400);
  const saved = await post(payload());
  assert.equal(saved.status, 200);
  assert.match(JSON.parse(saved.body).message, /Saved progress/);
  const second = await call('/tv/api/progress', {
    method: 'POST', body: JSON.stringify(payload('second', 4)), headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
  assert.equal(second.status, 200);
  const updated = JSON.parse(await readFile(configPath, 'utf8'));
  assert.equal(updated.shows[0].watchedThrough, 3);
  assert.equal(updated.shows[1].watchedThrough, 4);
  assert.equal(updated.shows[0].title, config.shows[0].title);
});

test('concurrent partial saves merge without losing changes', async t => {
  const { configPath, post } = await localServer(t);
  const results = await Promise.all([post(payload('first', 5)), post(payload('second', 6))]);
  assert.ok(results.every(result => result.status === 200));
  assert.deepEqual(JSON.parse(await readFile(configPath, 'utf8')).shows.map(show => show.watchedThrough), [5, 6]);
});

test('the save server rejects foreign hosts and origins, non-JSON bodies, and oversized data', async t => {
  const { configPath, source, port, call, post } = await localServer(t);
  assert.equal((await call('/shows.json', { headers: { Host: 'published.example' } })).status, 403);
  assert.equal((await post(payload(), { headers: { 'Content-Type': 'application/json', Origin: 'https://published.example' } })).status, 403);
  assert.equal((await post(payload(), { headers: { 'Content-Type': 'application/json', Origin: `http://127.0.0.1:${port}`, 'Sec-Fetch-Site': 'cross-site' } })).status, 403);
  assert.equal((await post(payload(), { headers: { 'Content-Type': 'text/plain' } })).status, 415);
  assert.equal((await post(payload(), { body: '{' })).status, 400);
  assert.equal((await post(payload(), { body: ' '.repeat(1_000_001) })).status, 400);
  assert.equal((await call('/api/progress', { method: 'PUT' })).status, 405);
  assert.equal(await readFile(configPath, 'utf8'), source);
});
