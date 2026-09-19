import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const usage = "Usage: node scripts/import-reading-data.mjs [--check] <export.json|->";
const args = process.argv.slice(2);
const checkOnly = args.includes("--check");
const positional = args.filter((arg) => arg !== "--check");

if (positional.length !== 1) {
  console.error(usage);
  process.exit(1);
}

const appPath = fileURLToPath(new URL("../app.js", import.meta.url));
const importPath = positional[0] === "-" ? null : path.resolve(positional[0]);

async function readImport() {
  if (importPath) return readFile(importPath, "utf8");

  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

function fail(message) {
  console.error(`Import failed: ${message}`);
  process.exit(1);
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isValidDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function findRange(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  if (start === -1 || end === -1) fail(`Could not find ${startMarker.trim()} in app.js.`);
  return { start, end };
}

let payload;
let source;

try {
  [payload, source] = await Promise.all([
    readImport().then(JSON.parse),
    readFile(appPath, "utf8"),
  ]);
} catch (error) {
  fail(error.message);
}

if (!isPlainObject(payload)) fail("The export must contain a JSON object.");

const booksRange = findRange(source, "const BOOKS = [", "\n];\n\nconst SERIES");
const booksDeclaration = `${source.slice(booksRange.start, booksRange.end + 3)}\nreturn BOOKS;`;
let books;

try {
  books = new Function(booksDeclaration)();
} catch (error) {
  fail(`Could not read the book catalog: ${error.message}`);
}

const booksById = new Map(books.map((book) => [book.id, book]));
if (booksById.size !== books.length) fail("The book catalog contains duplicate IDs.");

const ratingsInput = payload.ratings ?? payload;
if (!isPlainObject(ratingsInput)) fail("The export does not contain a ratings object.");

const ratings = {};
for (const [id, value] of Object.entries(ratingsInput)) {
  if (!booksById.has(id)) fail(`Unknown book ID in ratings: ${id}`);
  if (typeof value !== "number" || !Number.isFinite(value) || value < 1 || value > 10) {
    fail(`Invalid rating for ${id}; expected a number from 1 to 10.`);
  }
  ratings[id] = Number(value.toFixed(1));
}

const hasReadDates = Object.hasOwn(payload, "readDates");
const readDates = {};
if (hasReadDates) {
  if (!isPlainObject(payload.readDates)) fail("readDates must be an object.");

  for (const [id, value] of Object.entries(payload.readDates)) {
    if (!booksById.has(id)) fail(`Unknown book ID in readDates: ${id}`);
    if (!isValidDate(value)) fail(`Invalid finish date for ${id}: ${value}`);
    readDates[id] = value;
  }
}

const effectiveReadDates = hasReadDates
  ? readDates
  : Object.fromEntries(books.filter((book) => book.readDate).map((book) => [book.id, book.readDate]));

for (const id of Object.keys(ratings)) {
  if (!effectiveReadDates[id]) fail(`Rated book has no finish date: ${id}`);
}

let updatedSource = source;

if (hasReadDates) {
  const currentBooksRange = findRange(updatedSource, "const BOOKS = [", "\n];\n\nconst SERIES");
  const booksSection = updatedSource.slice(currentBooksRange.start, currentBooksRange.end + 3);
  let updatedBookCount = 0;
  const updatedBooksSection = booksSection.replace(/  \{\n[\s\S]*?\n  \},/g, (bookBlock) => {
    const id = bookBlock.match(/\n    id: "([^"]+)",/)?.[1];
    if (!id || !booksById.has(id)) return bookBlock;
    updatedBookCount += 1;
    const dateLiteral = readDates[id] ? JSON.stringify(readDates[id]) : "null";
    return bookBlock.replace(/\n    readDate: (?:null|"[^"]+"),/, `\n    readDate: ${dateLiteral},`);
  });

  if (updatedBookCount !== books.length) {
    fail(`Updated ${updatedBookCount} of ${books.length} book records; app.js was not changed.`);
  }

  updatedSource =
    updatedSource.slice(0, currentBooksRange.start) +
    updatedBooksSection +
    updatedSource.slice(currentBooksRange.end + 3);
}

const sortedRatings = Object.entries(ratings).sort(([firstId, firstRating], [secondId, secondRating]) => {
  return secondRating - firstRating || booksById.get(firstId).title.localeCompare(booksById.get(secondId).title);
});
const ratingsBody = sortedRatings.map(([id, rating]) => `  ${JSON.stringify(id)}: ${rating},`).join("\n");
const ratingsDeclaration = `const DEFAULT_RATINGS = {\n${ratingsBody}${ratingsBody ? "\n" : ""}};`;
const ratingsRange = findRange(updatedSource, "const DEFAULT_RATINGS = {", "\n};\n\nconst VIEW_META");
updatedSource =
  updatedSource.slice(0, ratingsRange.start) +
  ratingsDeclaration +
  updatedSource.slice(ratingsRange.end + 3);

const summary = `${Object.keys(ratings).length} ratings${hasReadDates ? ` and ${Object.keys(readDates).length} finish dates` : ""}`;

if (checkOnly) {
  console.log(`Valid AI-FI export: ${summary}. app.js was not changed.`);
} else if (updatedSource === source) {
  console.log(`No changes needed; app.js already contains ${summary}.`);
} else {
  await writeFile(appPath, updatedSource);
  console.log(`Applied ${summary} to app.js. Review the result with: git diff -- app.js`);
}
