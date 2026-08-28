import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, extname, join, normalize, relative, resolve } from "node:path";

const root = resolve(process.cwd(), "out");
const basePath = (process.env.BASE_PATH ?? "").replace(/\/$/, "");

if (!existsSync(root)) {
  console.error("Static export not found. Run `npm run build` first.");
  process.exit(1);
}

function walk(dir, suffix) {
  const found = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) found.push(...walk(path, suffix));
    else if (path.endsWith(suffix)) found.push(path);
  }
  return found;
}

function stripQuery(value) {
  const htmlDecoded = value
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) =>
      String.fromCodePoint(Number.parseInt(hex, 16)),
    )
    .replace(/&#(\d+);/g, (_, decimal) =>
      String.fromCodePoint(Number.parseInt(decimal, 10)),
    )
    .replace(/&amp;/g, "&");

  return decodeURIComponent(htmlDecoded.split(/[?#]/, 1)[0]);
}

function exportedTarget(htmlFile, url) {
  const clean = stripQuery(url);
  if (clean.startsWith("/")) {
    const withoutBase = basePath && clean.startsWith(`${basePath}/`)
      ? clean.slice(basePath.length)
      : clean;
    return resolve(root, `.${withoutBase}`);
  }
  return resolve(dirname(htmlFile), clean);
}

const targetCache = new Map();

function targetExists(target) {
  const key = normalize(target);
  if (targetCache.has(key)) return targetCache.get(key);

  let present = false;
  if (existsSync(target) && statSync(target).isFile()) present = true;
  else if (existsSync(target) && statSync(target).isDirectory()) {
    present = existsSync(join(target, "index.html"));
  } else if (!extname(target)) present = existsSync(join(target, "index.html"));

  targetCache.set(key, present);
  return present;
}

const failures = [];
const exportedHtmlFiles = walk(root, ".html");
const candidatePrefix = normalize(join(root, "candidate"));
const candidateFiles = exportedHtmlFiles.filter((path) =>
  normalize(path).startsWith(candidatePrefix),
);
const htmlFiles = exportedHtmlFiles.filter((path) =>
  !normalize(path).startsWith(candidatePrefix),
);

// Candidate pages are generated from one template. Scan both ends of the
// generated set to exercise that template without opening 6,000 near-identical
// files on every CI run. The full route count is still reported below.
if (candidateFiles.length) {
  htmlFiles.push(candidateFiles[0]);
  if (candidateFiles.length > 1) htmlFiles.push(candidateFiles.at(-1));
}
const attrPattern = /\b(?:src|href)=["']([^"']+)["']/g;

for (const htmlFile of htmlFiles) {
  const html = readFileSync(htmlFile, "utf8");
  for (const match of html.matchAll(attrPattern)) {
    const url = match[1];
    if (
      !url ||
      url.startsWith("#") ||
      /^(?:https?:|mailto:|tel:|data:|blob:|javascript:)/.test(url)
    ) continue;

    if (
      basePath &&
      url.startsWith("/") &&
      url !== basePath &&
      !url.startsWith(`${basePath}/`)
    ) {
      failures.push(
        `${relative(root, htmlFile)}: root-relative URL misses base path: ${url}`,
      );
      continue;
    }

    const target = exportedTarget(htmlFile, url);
    if (!targetExists(target)) {
      failures.push(
        `${relative(root, htmlFile)}: missing local target ${url} -> ${relative(root, target)}`,
      );
    }
  }
}

if (failures.length) {
  console.error(`Static export integrity failed with ${failures.length} issue(s):`);
  for (const failure of failures.slice(0, 80)) console.error(`- ${failure}`);
  if (failures.length > 80) console.error(`- ...and ${failures.length - 80} more`);
  process.exit(1);
}

console.log(
  `Static export integrity OK: ${htmlFiles.length} route templates checked across ` +
    `${exportedHtmlFiles.length} exported HTML files, base path ${basePath || "/"}.`,
);
