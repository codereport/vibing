import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../app.js", import.meta.url), "utf8");
const catalog = source.slice(0, source.indexOf("const VIEW_META ="));
const storageKeys = source.slice(source.indexOf("const storageKey ="), source.indexOf("const editableHosts ="));
const persistence = source.slice(source.indexOf("function loadRatings()"), source.indexOf("function escapeHtml("));
const savedScores = {
  "dark-matter": 8.5,
  "flowers-for-algernon": 9.1,
  "speaker-for-the-dead": 9.6,
  "a-scanner-darkly": 7.6,
};

function browser({ stored, legacy, readDateOverrides = {}, editable = true, unavailable = false } = {}) {
  const storage = new Map();
  const context = vm.createContext({
    localStorage: {
      getItem(key) {
        if (unavailable) throw new Error("Storage unavailable");
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        if (unavailable) throw new Error("Storage unavailable");
        storage.set(key, value);
      },
    },
    readDateOverrides,
  });
  const run = (code) => vm.runInContext(code, context);
  run(`${catalog}\n${storageKeys}\nconst canEditRatings = ${editable};\nlet ratings;\n${persistence}`);
  if (stored !== undefined) storage.set(run("storageKey"), JSON.stringify(stored));
  if (legacy !== undefined) storage.set(run("legacyStorageKey"), JSON.stringify(legacy));
  return {
    run,
    defaults: () => JSON.parse(run("JSON.stringify(DEFAULT_RATINGS)")),
    load: () => JSON.parse(run("ratings = loadRatings(); JSON.stringify(ratings)")),
    save(ratings) {
      context.nextRatings = ratings;
      run("ratings = nextRatings; saveRatings();");
    },
  };
}

test("an older browser snapshot recovers newer repository scores and keeps local edits", () => {
  const previousScores = browser().defaults();
  for (const id of Object.keys(savedScores)) delete previousScores[id];
  previousScores["dark-forest"] = 9.7;
  const loaded = browser({ stored: previousScores }).load();
  for (const [id, score] of Object.entries(savedScores)) assert.equal(loaded[id], score);
  assert.equal(loaded["dark-forest"], 9.7);
});

test("an explicit removal stays removed when migrating an old browser snapshot", () => {
  const stored = browser().defaults();
  delete stored["dark-matter"];
  const session = browser({ stored, readDateOverrides: { "dark-matter": null } });
  assert.equal(session.load()["dark-matter"], undefined);
  session.save(session.load());
  assert.equal(session.load()["dark-matter"], undefined);
});

test("an imported snapshot can intentionally leave a finished book unscored across reloads", () => {
  const session = browser();
  const imported = session.defaults();
  delete imported["flowers-for-algernon"];
  session.save(imported);
  assert.deepEqual(session.load(), imported);
  session.save({});
  assert.deepEqual(session.load(), {});
});

test("a later repository score appears without replacing another locally edited score", () => {
  const session = browser();
  session.run('delete DEFAULT_RATINGS["dark-matter"];');
  session.save({ ...session.defaults(), "dark-forest": 9.7 });
  session.run('DEFAULT_RATINGS["dark-matter"] = 8.5;');
  const loaded = session.load();
  assert.equal(loaded["dark-matter"], 8.5);
  assert.equal(loaded["dark-forest"], 9.7);
});

test("legacy storage migrates with new defaults while retaining explicit unread overrides", () => {
  const session = browser({
    legacy: { "dark-forest": 9.7 },
    readDateOverrides: { "dark-matter": null },
  });
  const loaded = session.load();
  assert.equal(loaded["dark-forest"], 9.7);
  assert.equal(loaded["flowers-for-algernon"], savedScores["flowers-for-algernon"]);
  assert.equal(loaded["dark-matter"], undefined);
  assert.deepEqual(session.load(), loaded);
});

test("published pages ignore browser ratings", () => {
  const session = browser({ stored: { "dark-forest": 1 }, editable: false });
  assert.deepEqual(session.load(), session.defaults());
});

test("unavailable storage falls back to repository ratings", () => {
  const session = browser({ unavailable: true });
  assert.deepEqual(session.load(), session.defaults());
});
