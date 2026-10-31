// Package the web demo into a self-contained site/ folder for static hosting.
//
// During development the page lives in web/ and reaches up into the
// repository (../argumentation/, ../results/, ../report/). Hosts serve one
// folder as the site root, so this copies everything the page needs into
// site/ and rewrites those "../" paths to be relative to the page.
//
// Usage: node web/build.mjs   (run from anywhere; writes <repo>/site)

import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "site");

const copies = [
  ["web/style.css", "style.css"],
  ["web/bridge.py", "bridge.py"],
  ["argumentation", "argumentation"],
  ["experiments/__init__.py", "experiments/__init__.py"],
  ["experiments/run_experiments.py", "experiments/run_experiments.py"],
  ["results/summary.csv", "results/summary.csv"],
  ["results/q3_examples.json", "results/q3_examples.json"],
  ["results/exhaustive/summary.csv", "results/exhaustive/summary.csv"],
  ["results/exhaustive-self-attacks/summary.csv", "results/exhaustive-self-attacks/summary.csv"],
  ["report/report.pdf", "report/report.pdf"],
];

// Files whose "../" references point at the repository root.
const rewrites = ["web/index.html", "web/app.js"];

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

for (const [from, to] of copies) {
  cpSync(join(root, from), join(out, to), {
    recursive: true,
    filter: (src) => !src.includes("__pycache__") && !src.endsWith("visualize.py"),
  });
}

for (const file of rewrites) {
  const text = readFileSync(join(root, file), "utf8").replaceAll("../", "");
  writeFileSync(join(out, file.replace(/^web\//, "")), text);
}

console.log(`built ${out}`);
