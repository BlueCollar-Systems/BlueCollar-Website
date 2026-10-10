import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, openSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(join(root, "bundle.json"), "utf8"));
const instance = createHash("sha256").update(root.toLowerCase()).digest("hex");
const action = process.argv[2] || "start";
const portArg = process.argv.indexOf("--port");
let port = Number(portArg >= 0 ? process.argv[portArg + 1] : config.port);
if (existsSync(join(root, "data", "session.json"))) {
  const saved = JSON.parse(readFileSync(join(root, "data", "session.json"), "utf8"));
  if (saved.instance === instance) {
    if (portArg < 0) port = Number(saved.port);
    else if (action === "start" && Number(saved.port) !== port) {
      let previous;
      try { previous = await (await fetch(`http://127.0.0.1:${saved.port}/_local/health`, { signal: AbortSignal.timeout(1000) })).json(); } catch { /* stopped */ }
      if (previous?.instance === instance) throw new Error(`This folder is already running at port ${saved.port}. Stop it before changing ports.`);
    }
  }
}
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("Invalid local port");
const origin = `http://127.0.0.1:${port}`;
async function health() {
  try {
    const res = await fetch(origin + "/_local/health", { signal: AbortSignal.timeout(1000) });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
let running = await health();
if (running && running.instance !== instance)
  throw new Error(`Port ${port} belongs to another package. Use --port with an available port.`);
if (action === "stop") {
  if (!running) {
    console.log("This package is already stopped.");
    process.exit(0);
  }
  const response = await fetch(origin + "/_local/stop", {
    method: "POST",
    headers: { "X-BlueCollar-Instance": instance },
  });
  if (!response.ok) throw new Error("This package refused the stop request");
  for (let i = 0; i < 60 && (await health()); i++)
    await new Promise((done) => setTimeout(done, 250));
  if (await health()) throw new Error("Server is still finishing; try Stop again shortly");
  console.log("Stopped this package. Saved test data remains in its data folder.");
  process.exit(0);
}
if (action !== "start") throw new Error("Use start or stop");
if (!running) {
  mkdirSync(join(root, "data"), { recursive: true });
  const log = openSync(join(root, "data", "server.log"), "a");
  const env = { NODE_ENV: "production" };
  for (const name of [
    "SystemRoot",
    "WINDIR",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "OS",
    "PROCESSOR_ARCHITECTURE",
    "NUMBER_OF_PROCESSORS",
  ]) {
    if (process.env[name]) env[name] = process.env[name];
  }
  const child = spawn(process.execPath, [join(root, "server.mjs"), String(port)], {
    cwd: root,
    env,
    detached: true,
    windowsHide: true,
    stdio: ["ignore", log, log],
  });
  child.unref();
  for (let i = 0; i < 120; i++) {
    running = await health();
    if (running?.instance === instance) break;
    await new Promise((done) => setTimeout(done, 250));
  }
  if (running?.instance !== instance)
    throw new Error("Server did not start; open data/server.log for details.");
}
const target = origin + config.startPath;
console.log(`${config.title} ready: ${target}`);
if (!process.argv.includes("--no-open")) {
  const shell = join(
    process.env.SystemRoot || "C:\\Windows",
    "System32",
    "WindowsPowerShell",
    "v1.0",
    "powershell.exe",
  );
  const browser = spawn(
    shell,
    [
      "-NoProfile",
      "-NonInteractive",
      "-WindowStyle",
      "Hidden",
      "-Command",
      `Start-Process -FilePath '${target.replaceAll("'", "''")}'`,
    ],
    { windowsHide: true, detached: true, stdio: "ignore" },
  );
  browser.unref();
}
