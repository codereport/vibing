import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const importerPath = fileURLToPath(new URL("./import-reading-data.mjs", import.meta.url));
const requestedPort = Number(process.argv[2] || process.env.AI_FI_PORT || 8765);
const port = Number.isInteger(requestedPort) && requestedPort > 0 && requestedPort < 65536 ? requestedPort : 8765;
const maximumBodySize = 1024 * 1024;
const staticFiles = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/index.html", ["index.html", "text/html; charset=utf-8"]],
  ["/app.js", ["app.js", "text/javascript; charset=utf-8"]],
  ["/styles.css", ["styles.css", "text/css; charset=utf-8"]],
]);

function send(response, status, body, contentType = "text/plain; charset=utf-8") {
  response.writeHead(status, {
    "Cache-Control": "no-store",
    "Content-Type": contentType,
    "X-Content-Type-Options": "nosniff",
  });
  response.end(body);
}

function sendJson(response, status, payload) {
  send(response, status, JSON.stringify(payload), "application/json; charset=utf-8");
}

async function readJsonBody(request) {
  const chunks = [];
  let size = 0;

  for await (const chunk of request) {
    size += chunk.length;
    if (size > maximumBodySize) throw new Error("Reading data is too large.");
    chunks.push(chunk);
  }

  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function applyReadingData(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [importerPath, "-"], {
      cwd: projectRoot,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let output = "";
    let errors = "";

    child.stdout.on("data", (chunk) => {
      output += chunk;
    });
    child.stderr.on("data", (chunk) => {
      errors += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve(output.trim());
      else reject(new Error(errors.trim() || output.trim() || `Importer exited with status ${code}.`));
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

const server = createServer(async (request, response) => {
  const allowedHosts = new Set([`localhost:${port}`, `127.0.0.1:${port}`, `[::1]:${port}`]);
  if (!allowedHosts.has(request.headers.host)) {
    send(response, 403, "This server only accepts local AI-FI requests.");
    return;
  }

  const requestUrl = new URL(request.url, `http://${request.headers.host}`);

  if (request.method === "POST" && requestUrl.pathname === "/api/reading-data") {
    if (!request.headers["content-type"]?.startsWith("application/json")) {
      sendJson(response, 415, { error: "Expected JSON reading data." });
      return;
    }

    try {
      const payload = await readJsonBody(request);
      const details = await applyReadingData(payload);
      const ratingCount = Object.keys(payload.ratings || {}).length;
      const finishDateCount = Object.keys(payload.readDates || {}).length;
      sendJson(response, 200, {
        message: `Saved ${ratingCount} ratings and ${finishDateCount} finish dates to app.js. Ready to commit.`,
        details,
      });
    } catch (error) {
      sendJson(response, 400, { error: error.message });
    }
    return;
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    send(response, 405, "Method not allowed.");
    return;
  }

  const staticFile = staticFiles.get(requestUrl.pathname);
  if (!staticFile) {
    send(response, 404, "Not found.");
    return;
  }

  try {
    const [filename, contentType] = staticFile;
    const body = await readFile(new URL(`../${filename}`, import.meta.url));
    send(response, 200, request.method === "HEAD" ? "" : body, contentType);
  } catch {
    send(response, 500, "Could not read the site files.");
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`AI-FI is running at http://localhost:${port}`);
  console.log("Keep this process open while using Save to repository.");
});
