const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const PORT = 3001;
const STATIC_DIR = __dirname;

const LANGUAGES = [
  'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C', 'C#', 'Go',
  'Rust', 'Kotlin', 'Swift', 'Ruby', 'PHP', 'Scala', 'Haskell', 'R',
  'MATLAB', 'APL', 'BQN', 'Other',
];

const tallies = Object.fromEntries(LANGUAGES.map(l => [l, 0]));

const MIME = {
  '.html': 'text/html',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg':  'image/svg+xml',
  '.json': 'application/json',
};

const server = http.createServer((req, res) => {
  let filePath = path.join(STATIC_DIR, req.url === '/' ? 'vote.html' : req.url);
  filePath = decodeURIComponent(filePath.split('?')[0]);

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

const wss = new WebSocketServer({ server });

function broadcast() {
  const msg = JSON.stringify({ type: 'tallies', data: tallies });
  for (const client of wss.clients) {
    if (client.readyState === 1) client.send(msg);
  }
}

wss.on('connection', (ws) => {
  ws.send(JSON.stringify({ type: 'tallies', data: tallies }));

  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw);
      if (msg.type === 'vote' && msg.lang in tallies) {
        tallies[msg.lang] += msg.delta;
        if (tallies[msg.lang] < 0) tallies[msg.lang] = 0;
        broadcast();
      } else if (msg.type === 'reset') {
        for (const k of LANGUAGES) tallies[k] = 0;
        broadcast();
      }
    } catch {}
  });
});

server.listen(PORT, '0.0.0.0', async () => {
  const nets = require('os').networkInterfaces();
  let ip = 'localhost';
  for (const addrs of Object.values(nets)) {
    for (const a of addrs) {
      if (a.family === 'IPv4' && !a.internal) { ip = a.address; break; }
    }
  }
  console.log(`Poll server running:`);
  console.log(`  Local:     http://localhost:${PORT}/vote.html`);
  console.log(`  Network:   http://${ip}:${PORT}/vote.html`);
  console.log(`  Presenter: open poll.html in the deck`);
  console.log(`\nOpening tunnel...`);

  const { spawn } = require('child_process');
  const cfPath = path.join(__dirname, 'cloudflared');
  const cf = spawn(cfPath, ['tunnel', '--url', `http://localhost:${PORT}`], { stdio: ['ignore', 'pipe', 'pipe'] });

  let tunnelUrl = null;
  const handleOutput = (data) => {
    const line = data.toString();
    const match = line.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
    if (match && !tunnelUrl) {
      tunnelUrl = match[0];
      console.log(`\n  ★ Public URL: ${tunnelUrl}/vote.html`);
      console.log(`    (share this with the audience — works on any network)\n`);
    }
  };
  cf.stdout.on('data', handleOutput);
  cf.stderr.on('data', handleOutput);
  cf.on('error', (err) => {
    console.log(`  Tunnel failed: ${err.message}`);
    console.log(`  Falling back to local-only mode.\n`);
  });
  cf.on('close', () => { if (!tunnelUrl) console.log('  Tunnel closed without connecting.\n'); });
});
