import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { repoRoot } from "../src/config.js";

const SKIP = new Set(["node_modules", "dist", ".data", "research", ".git"]);

function files(dir: string): string[] {
  const found: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) found.push(...files(full));
    else if (/\.(ts|js|py|md|json|sql|example|toml)$/.test(entry.name) || entry.name === "Dockerfile") found.push(full);
  }
  return found;
}

describe("product copy", () => {
  it("does not put dollar amounts in product code or docs", () => {
    const hits: string[] = [];
    for (const file of files(repoRoot())) {
      const text = fs.readFileSync(file, "utf8");
      if (/(?<![A-Za-z$])\$\d/.test(text)) hits.push(path.relative(repoRoot(), file));
    }
    expect(hits).toEqual([]);
  });
});
