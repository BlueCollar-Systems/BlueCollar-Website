import { createServer } from "node:http";
import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, extname, join, resolve, sep } from "node:path";
import { Readable } from "node:stream";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(join(root, "bundle.json"), "utf8"));
const port = Number(process.argv[2] || config.port);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("Invalid local port");
const instance = createHash("sha256").update(root.toLowerCase()).digest("hex");
const publicRoot = join(root, "public");
mkdirSync(join(root, "data"), { recursive: true });
// Never inherit a cloud database or authentication account into this local bundle.
delete process.env.DATABASE_URL;
delete process.env.NODE_OPTIONS;
process.env.TAGQC_LOCAL_DATA_DIR = join(root, "data", "shop-db");
const application = config.kind === "tag-qc"
  ? (await import(pathToFileURL(join(root, "server", "index.mjs")).href)).default
  : null;
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".xml": "application/xml", ".txt": "text/plain; charset=utf-8", ".wasm": "application/wasm", ".pdf": "application/pdf" };

function staticPath(pathname) {
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { return null; }
  if (decoded.includes("\\") || decoded.split("/").some((part) => part === ".." || part === ".")) return null;
  let relative = decoded.replace(/^\/+/, "");
  if (config.kind === "website") {
    if (!relative) relative = "index.html";
    else if (pathname.startsWith("/p/") || pathname === "/p") relative = "p/index.html";
    else if (relative === "security.txt") relative = ".well-known/security.txt";
    else if (!relative.includes("/") && !extname(relative)) relative += ".html";
  }
  const candidate = resolve(publicRoot, relative);
  if (!candidate.startsWith(resolve(publicRoot) + sep)) return null;
  return existsSync(candidate) && statSync(candidate).isFile() ? candidate : null;
}

function json(res, code, value) {
  res.writeHead(code, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(JSON.stringify(value));
}

let closing = false;
async function shutdown() {
  if (closing) return;
  closing = true;
  server.close();
  server.closeIdleConnections();
  try {
    const database = await globalThis.__pgliteInstance__;
    if (database) await database.close();
  } finally { process.exit(0); }
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://127.0.0.1:${port}`);
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "no-referrer");
    if (url.pathname === "/_local/health") {
      json(res, 200, { kind: config.kind, build: config.build, instance, pid: process.pid });
      return;
    }
    if (url.pathname === "/_local/stop") {
      if (req.method !== "POST" || req.headers["x-bluecollar-instance"] !== instance ||
          (req.headers.origin && req.headers.origin !== url.origin)) {
        json(res, 403, { error: "Stop only this package through its Stop launcher" });
        return;
      }
      json(res, 200, { stopping: true });
      setImmediate(() => { void shutdown(); });
      return;
    }
    if (["GET", "HEAD"].includes(req.method)) {
      const file = staticPath(url.pathname);
      if (file) {
        res.writeHead(200, { "Content-Type": MIME[extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
        if (req.method === "HEAD") res.end();
        else createReadStream(file).pipe(res);
        return;
      }
    }
    if (!application) { json(res, 404, { error: "Public page not found" }); return; }
    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(", ") : value);
    }
    const request = new Request(url, { method: req.method, headers,
      ...(!["GET", "HEAD"].includes(req.method) ? { body: Readable.toWeb(req), duplex: "half" } : {}) });
    const response = await application.fetch(request, { waitUntil(promise) { promise.catch(console.error); } });
    res.writeHead(response.status, Object.fromEntries(response.headers));
    if (!response.body || req.method === "HEAD") res.end();
    else Readable.fromWeb(response.body).pipe(res);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) json(res, 500, { error: "Local request failed; see data/server.log" });
    else res.end();
  }
});
server.on("error", (error) => { console.error(error); process.exitCode = 1; });
server.listen(port, "127.0.0.1", () => {
  writeFileSync(join(root, "data", "session.json"), JSON.stringify({ port, instance, pid: process.pid }));
  console.log(`${config.title}: http://127.0.0.1:${port}${config.startPath}`);
});
process.on("SIGTERM", () => { void shutdown(); });
process.on("SIGINT", () => { void shutdown(); });
