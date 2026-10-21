import { randomUUID } from 'node:crypto';
import { readFile, rename, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { importedProgress, mergedShow } from '../model.mjs';

const defaultConfigPath = fileURLToPath(new URL('../shows.json', import.meta.url));

export async function applyProgress(payload, { configPath = defaultConfigPath, checkOnly = false } = {}) {
  const source = await readFile(configPath, 'utf8');
  const config = JSON.parse(source);
  const updates = importedProgress(config, payload);
  const shows = config.shows.map(show => mergedShow(show, updates[show.id]));
  const count = Object.keys(updates).length;
  const changed = shows.some((show, index) => show.watching !== config.shows[index].watching || show.watchedThrough !== config.shows[index].watchedThrough);
  if (changed && !checkOnly) {
    const temporary = `${configPath}.${randomUUID()}.tmp`;
    try {
      await writeFile(temporary, JSON.stringify({ ...config, shows }, null, 2) + '\n', { flag: 'wx' });
      await rename(temporary, configPath);
    } finally {
      await rm(temporary, { force: true });
    }
  }
  return { count, changed };
}

async function main() {
  const args = process.argv.slice(2);
  const positional = args.filter(arg => arg !== '--check');
  if (positional.length !== 1 || (positional[0].startsWith('--'))) {
    throw new Error('Usage: node scripts/import-progress.mjs [--check] <shows.json|->');
  }
  let source;
  if (positional[0] === '-') {
    const chunks = [];
    for await (const chunk of process.stdin) chunks.push(chunk);
    source = Buffer.concat(chunks).toString('utf8');
  } else source = await readFile(resolve(positional[0]), 'utf8');
  const checkOnly = args.includes('--check');
  const { count, changed } = await applyProgress(JSON.parse(source), { checkOnly });
  if (checkOnly) console.log(`Valid progress for ${count} shows. shows.json was not changed.`);
  else if (!changed) console.log('No changes needed; shows.json already contains this progress.');
  else console.log(`Saved progress for ${count} shows to shows.json. Review with git diff, then commit and push.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => {
    console.error(`Import failed: ${error.message}`);
    process.exitCode = 1;
  });
}
