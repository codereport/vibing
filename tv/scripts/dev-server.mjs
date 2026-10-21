import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { applyProgress } from './import-progress.mjs';

const projectRoot = fileURLToPath(new URL('../', import.meta.url));
const maximumBodySize = 1_000_000;
const staticFiles = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/app.mjs', ['app.mjs', 'text/javascript; charset=utf-8']],
  ['/model.mjs', ['model.mjs', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/shows.json', ['shows.json', 'application/json; charset=utf-8']],
  ['/releases.json', ['releases.json', 'application/json; charset=utf-8']],
]);

function send(response, status, body, contentType = 'text/plain; charset=utf-8') {
  response.writeHead(status, {
    'Cache-Control': 'no-store',
    'Content-Type': contentType,
    'X-Content-Type-Options': 'nosniff',
  });
  response.end(body);
}

function sendJson(response, status, payload) {
  send(response, status, JSON.stringify(payload), 'application/json; charset=utf-8');
}

async function readJsonBody(request) {
  const chunks = [];
  let size = 0;
  let tooLarge = false;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > maximumBodySize) tooLarge = true;
    if (!tooLarge) chunks.push(chunk);
  }
  if (tooLarge) throw new Error('Watchlist data is too large.');
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

export function createDevServer({ root = projectRoot } = {}) {
  // Serialize saves so each import merges with the latest repository defaults.
  let pendingSave = Promise.resolve();
  const server = createServer(async (request, response) => {
    const port = server.address().port;
    const allowedHosts = new Set([`localhost:${port}`, `127.0.0.1:${port}`, `[::1]:${port}`]);
    if (!allowedHosts.has(request.headers.host)) {
      send(response, 403, 'This server only accepts local watchlist requests.');
      return;
    }
    const origin = `http://${request.headers.host}`;
    let pathname;
    try {
      pathname = new URL(request.url, origin).pathname;
    } catch {
      send(response, 400, 'Invalid request URL.');
      return;
    }
    if (pathname === '/tv') {
      response.writeHead(302, { Location: '/tv/' });
      response.end();
      return;
    }
    if (pathname.startsWith('/tv/')) pathname = pathname.slice(3);

    if (request.method === 'POST' && pathname === '/api/progress') {
      if ((request.headers.origin && request.headers.origin !== origin) || request.headers['sec-fetch-site'] === 'cross-site') {
        sendJson(response, 403, { error: 'Progress must be saved from this local site.' });
        return;
      }
      if (request.headers['content-type']?.split(';')[0].trim() !== 'application/json') {
        sendJson(response, 415, { error: 'Expected JSON watchlist data.' });
        return;
      }
      try {
        const payload = await readJsonBody(request);
        pendingSave = pendingSave.catch(() => {}).then(() => applyProgress(payload, { configPath: join(root, 'shows.json') }));
        const { count, changed } = await pendingSave;
        sendJson(response, 200, {
          message: changed ? `Saved progress for ${count} shows to shows.json. Ready to commit and push.` : 'shows.json already contains this progress. Ready to commit and push.',
        });
      } catch (error) {
        sendJson(response, 400, { error: error.message });
      }
      return;
    }

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      send(response, 405, 'Method not allowed.');
      return;
    }
    const staticFile = staticFiles.get(pathname);
    if (!staticFile) {
      send(response, 404, 'Not found.');
      return;
    }
    try {
      const [filename, contentType] = staticFile;
      const body = await readFile(join(root, filename));
      send(response, 200, request.method === 'HEAD' ? '' : body, contentType);
    } catch {
      send(response, 500, 'Could not read the site files.');
    }
  });
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const port = Number(process.argv[2] || process.env.TV_PORT || 8766);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    console.error('Choose a port between 1 and 65535.');
    process.exitCode = 1;
  } else {
    const server = createDevServer();
    server.on('error', error => {
      console.error(`Could not start the watchlist server: ${error.message}`);
      process.exitCode = 1;
    });
    server.listen(port, '127.0.0.1', () => {
      console.log(`The watchlist is running at http://localhost:${port}/`);
      console.log('Keep this process open while using Save to repository.');
    });
  }
}
