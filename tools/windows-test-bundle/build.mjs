import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const source = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const destination = resolve(process.argv[2] || "C:/BlueCollar-Test-Builds/2026-10-10/Website");
if (existsSync(destination) && readdirSync(destination).length) throw new Error("Choose an empty output folder; existing test data is never overwritten.");
mkdirSync(join(destination, "runtime"), { recursive: true });
mkdirSync(join(destination, "public", "p"), { recursive: true });
mkdirSync(join(destination, "public", "p-records"), { recursive: true });
mkdirSync(join(destination, "public", ".well-known"), { recursive: true });
for (const name of ["index.html", "404.html", "feedback.html", "privacy.html", "report-doctor.html", "shapes.html", "nav.js", "part-resolver.js", "report-doctor.js", "styles.css", "part-page.css", "favicon.ico", "favicon.svg", "og-image.png", "robots.txt", "sitemap.xml", "repo-metadata.json"])
  copyFileSync(join(source, name), join(destination, "public", name));
copyFileSync(join(source, "p", "index.html"), join(destination, "public", "p", "index.html"));
const partPage = join(destination, "public", "p", "index.html");
writeFileSync(partPage, readFileSync(partPage, "utf8").replace('<body ', '<body data-steel-logic-scheme="steellogictest" '));
const doctorPage = join(destination, "public", "report-doctor.html");
writeFileSync(doctorPage, readFileSync(doctorPage, "utf8").replace('<html ', '<html data-local-test-build="true" '));
copyFileSync(join(source, "p-records", "demo-part.json"), join(destination, "public", "p-records", "demo-part.json"));
copyFileSync(join(source, ".well-known", "security.txt"), join(destination, "public", ".well-known", "security.txt"));
copyFileSync(process.execPath, join(destination, "runtime", "node.exe"));
copyFileSync(join(dirname(process.execPath), "LICENSE"), join(destination, "runtime", "NODE-LICENSE.txt"));
copyFileSync(join(source, "LICENSE"), join(destination, "WEBSITE-LICENSE.txt"));
for (const name of ["launch.mjs", "server.mjs"]) copyFileSync(join(source, "tools", "windows-test-bundle", name), join(destination, name));
writeFileSync(join(destination, "bundle.json"), JSON.stringify({ kind: "website", title: "BlueCollar Website Test", build: "2026-10-10", port: 18341, startPath: "/" }, null, 2));
const launcher = (action) => `@echo off\r\ncd /d "%~dp0"\r\n"runtime\\node.exe" "launch.mjs" ${action}\r\nif errorlevel 1 pause\r\n`;
writeFileSync(join(destination, "OPEN_BlueCollar_Website.bat"), launcher("start"));
writeFileSync(join(destination, "STOP_BlueCollar_Website.bat"), launcher("stop"));
writeFileSync(join(destination, "README_START_HERE.txt"), `BLUECOLLAR WEBSITE WINDOWS TEST — 2026-10-10\r\n\r\nDouble-click OPEN_BlueCollar_Website.bat. It opens the current website locally at http://127.0.0.1:18341/ with working navigation and Report Doctor. No npm, Python, setup or internet is needed for local content. Keep runtime/public/server.mjs/launch.mjs with the launchers. Windows 10/11 x64 is the verified bundled runtime target.\r\n\r\nSTOP_BlueCollar_Website.bat stops only this package. No hosted website or app-store listing is changed. Download and support links still lead to their real external destinations and require internet.\r\n\r\nReport Doctor analyzes selected JSON on this computer, with Copy feedback and manual recovery. /p/demo-part is an explicitly fictional public mirror. Other part tags require a matching published record or import in Steel Logic; a link alone creates no inventory or time entry.\r\n\r\nThis package includes only public website assets, bundled Node, and localhost routing. It excludes source/development folders, credentials, shop databases, private PDFs/CAD and project records. No production content is preloaded.\r\n`);
mkdirSync(join(destination, "Samples"), { recursive: true });
writeFileSync(join(destination, "Samples", "Fictional-Import-Report.json"), JSON.stringify({ schema: "bcs.import_report/1.1", host: { app: "freecad" }, importer: { version: "TEST-2026-10-10" }, input: { pages: 1 }, mode: "vector", result: { primitives: 7, text_entities: 2, layers: 1 }, fallback: { used: false }, extra: { result_status: "success", text_mode: "labels", note: "Fictional training only" } }, null, 2));
const rows = [1, 2].map((piece) => ({ part_id: `D042-EX100-00${piece}`, piece_mark: "EX100", profile_hint: "W12X26", quantity: 1 }));
writeFileSync(join(destination, "Samples", "Fictional-Parts-Bootstrap.json"), JSON.stringify({ schema: "bcs.parts_bootstrap/1.0", rows }, null, 2));
for (const row of rows) writeFileSync(join(destination, "public", "p-records", `${row.part_id}.json`), JSON.stringify({ schema: "bcs.part/1.0", ...row, tag_url: `https://bluecollar-systems.com/p/${row.part_id}`, import_build_stamp: { host: "test", note: "Fictional local TEST mirror only; never published" } }, null, 2));
writeFileSync(join(destination, "Samples", "README_TEST_REPORT_DOCTOR.txt"), "Open Report Doctor and choose Fictional-Import-Report.json plus Fictional-Parts-Bootstrap.json. Analyze and copy the summary/tag links. Both D042 physical pieces have fictional records in this local TEST website only. Their app links use steellogictest:// and require that register in the isolated Steel Logic TEST app. No records were uploaded or published.\r\n");
function inventory(directory, prefix = "") {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => entry.isDirectory() ? inventory(join(directory, entry.name), prefix + entry.name + "/") : [{ path: prefix + entry.name, sha256: createHash("sha256").update(readFileSync(join(directory, entry.name))).digest("hex") }]);
}
writeFileSync(join(destination, "PACKAGE_SHA256.json"), JSON.stringify(inventory(destination), null, 2));
console.log(`Website package created: ${destination}`);
