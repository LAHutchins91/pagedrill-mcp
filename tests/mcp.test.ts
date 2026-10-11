import fs from "node:fs";
import type { Server } from "node:http";
import { once } from "node:events";
import path from "node:path";
import { inflateRawSync } from "node:zlib";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { DEV_USER_ID, repoRoot } from "../src/config.js";
import { app } from "../src/server.js";
import { getStore, resetStoreForTests, sha256 } from "../src/store.js";

const SENTINEL = "More older adults now use the internet";
const logs: string[] = [];
const originalLog = console.log;
let server: Server;
let base = "";

type ToolData = { isError: boolean; data: Record<string, unknown>; status: number; text: string };

async function rpc(method: string, params?: unknown, id?: number, auth = false) {
  const body: Record<string, unknown> = { jsonrpc: "2.0", method };
  if (id !== undefined) body.id = id;
  if (params !== undefined) body.params = params;
  const response = await fetch(`${base}/mcp`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
      ...(auth ? { authorization: "Bearer dev-pagedrill" } : {})
    },
    body: JSON.stringify(body)
  });
  const text = await response.text();
  return { status: response.status, text, json: text ? JSON.parse(text) : null };
}

async function call(name: string, args: Record<string, unknown>): Promise<ToolData> {
  const payload = await rpc("tools/call", { name, arguments: args }, 10, true);
  const result = payload.json?.result;
  const data = (result?.structuredContent?.data ?? (result?.content?.[0]?.text ? JSON.parse(result.content[0].text) : {})) as Record<string, unknown>;
  return { isError: Boolean(result?.isError), data, status: payload.status, text: payload.text };
}

async function upload(filename: string, bytes: Buffer) {
  const started = await call("start_upload", { filename });
  expect(started.isError, started.text).toBe(false);
  const response = await fetch(String(started.data.upload_url), { method: "PUT", body: new Uint8Array(bytes) });
  const saved = (await response.json()) as { file_id?: string; sha256?: string; error?: { reason?: string } };
  expect(response.status, JSON.stringify(saved)).toBe(200);
  return saved;
}

beforeAll(async () => {
  console.log = (...args: unknown[]) => {
    logs.push(args.map(String).join(" "));
    originalLog(...args);
  };
  resetStoreForTests();
  await getStore().ensureDevProfile();
  server = app.listen(0);
  await once(server, "listening");
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  base = `http://127.0.0.1:${port}`;
  process.env.APP_BASE_URL = base;
});

afterAll(async () => {
  console.log = originalLog;
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

function extractDocumentXml(zip: Buffer): string {
  let offset = 0;
  while (offset + 30 < zip.length && zip.readUInt32LE(offset) === 0x04034b50) {
    const method = zip.readUInt16LE(offset + 8);
    const compressed = zip.readUInt32LE(offset + 18);
    const nameLength = zip.readUInt16LE(offset + 26);
    const extraLength = zip.readUInt16LE(offset + 28);
    const name = zip.subarray(offset + 30, offset + 30 + nameLength).toString();
    const start = offset + 30 + nameLength + extraLength;
    const data = zip.subarray(start, start + compressed);
    if (name === "word/document.xml") return (method === 0 ? data : inflateRawSync(data)).toString("utf8");
    offset = start + compressed;
  }
  throw new Error("word/document.xml was not in the package");
}

describe("MCP", () => {
  it("lists tools without a session", async () => {
    const listed = await rpc("tools/list", {}, 1, false);
    expect(listed.status).toBe(200);
    const names = listed.json.result.tools.map((tool: { name: string }) => tool.name);
    for (const name of ["check_document", "propose_format", "apply_format", "list_versions", "undo", "import_file", "start_upload", "list_styles", "import_references", "create_memorandum"]) {
      expect(names).toContain(name);
    }
    const imported = listed.json.result.tools.find((tool: { name: string }) => tool.name === "import_file");
    expect(imported._meta["openai/fileParams"]).toEqual(["file"]);
  });

  it("formats the student sample, checks every rule, and undoes to the import", async () => {
    const original = fs.readFileSync(path.join(repoRoot(), "samples/apa_before.docx"));
    const saved = await upload("apa_before.docx", original);
    const fileId = String(saved.file_id);
    expect(saved.sha256).toBe(sha256(original));

    const checked = await call("check_document", { file_id: fileId, style_id: "apa7-student" });
    expect(checked.isError, checked.text).toBe(false);
    const checkCounts = (checked.data.checklist as { counts: { FAIL: number } }).counts;
    expect(checkCounts.FAIL).toBeGreaterThan(0);

    const proposed = await call("propose_format", { file_id: fileId, style_id: "apa7-student" });
    expect(proposed.isError, proposed.text).toBe(false);
    const checklist = proposed.data.checklist as { counts: { PASS: number; FAIL: number; FLAG: number }; rules: { id: number; result: string }[] };
    expect(checklist.counts).toEqual({ PASS: 28, FAIL: 0, FLAG: 5 });
    expect(checklist.rules.filter((rule) => rule.result === "FLAG").map((rule) => rule.id)).toEqual([11, 12, 18, 27, 31]);
    const verification = proposed.data.verification as { untouched_identical: boolean; added_parts: string[] };
    expect(verification.untouched_identical).toBe(true);
    expect(verification.added_parts).toEqual([]);

    const applied = await call("apply_format", { proposal_id: proposed.data.proposal_id, base_version: proposed.data.base_version });
    expect(applied.isError, applied.text).toBe(false);
    expect(applied.data.version).toBe(2);

    const undone = await call("undo", { file_id: fileId, version: 1 });
    expect(undone.isError, undone.text).toBe(false);
    expect(undone.data.sha256).toBe(sha256(original));
    const downloaded = await fetch(String(undone.data.download_url));
    const bytes = Buffer.from(await downloaded.arrayBuffer());
    expect(sha256(bytes)).toBe(sha256(original));
    expect(logs.join("\n")).not.toContain(SENTINEL);
  });

  it("formats the memorandum and refuses an unverified style", async () => {
    const original = fs.readFileSync(path.join(repoRoot(), "samples/memo_before.docx"));
    const saved = await upload("memo_before.docx", original);
    const proposed = await call("propose_format", { file_id: saved.file_id, style_id: "army-ar25-50-memorandum" });
    expect(proposed.isError, proposed.text).toBe(false);
    expect((proposed.data.checklist as { counts: { FAIL: number; PASS: number; FLAG: number } }).counts).toEqual({ PASS: 20, FAIL: 0, FLAG: 4 });
    expect(String(proposed.data.notice)).toContain("Unclassified");
    expect(String(proposed.data.notice)).toContain("DoD");
    const refused = await call("propose_format", { file_id: saved.file_id, style_id: "mla9-research-paper" });
    expect(refused.isError).toBe(true);
    expect((refused.data.error as { code: string }).code).toBe("style_not_selectable");
    const styles = await call("list_styles", {});
    const ids = ((styles.data.styles as { id: string }[]) ?? []).map((item) => item.id);
    expect(ids).toContain("ieee-conference-letter");
    expect(ids).not.toContain("mla9-research-paper");
    expect(ids).not.toContain("vancouver-icmje-nlm");
  });

  it("writes tracked changes and a table-of-contents field when asked", async () => {
    const original = fs.readFileSync(path.join(repoRoot(), "samples/apa_before.docx"));
    const saved = await upload("tracked.docx", original);
    const proposed = await call("propose_format", {
      file_id: saved.file_id,
      style_id: "apa7-student",
      supplied: { track_changes: true, table_of_contents: true }
    });
    expect(proposed.isError, proposed.text).toBe(false);
    expect((proposed.data.checklist as { counts: { PASS: number; FAIL: number } }).counts.FAIL).toBe(0);
    const preview = await fetch(String(proposed.data.preview_url));
    const entry = extractDocumentXml(Buffer.from(await preview.arrayBuffer()));
    expect(entry).toContain('w:author="Pagedrill"');
    expect(entry).toContain("<w:ins");
    expect(entry).toContain("<w:del ");
    expect(entry).toContain("TOC");
  });

  it("imports references without inventing fields and creates a memorandum that undo can restore", async () => {
    const imported = await call("import_references", {
      style_id: "ieee-conference-letter",
      format: "bib",
      text: `@article{smith2020,\n  author = {Smith, Ada B.},\n  title = {A short title about displays},\n  journal = {Applied Physics Letters},\n  year = {2020},\n  volume = {10}\n}\n`
    });
    expect(imported.isError, imported.text).toBe(false);
    const rendered = String((imported.data.entries as { rendered: string }[])[0].rendered);
    expect(rendered.toLowerCase()).not.toContain("doi");
    expect(rendered).not.toContain("May");
    const created = await call("create_memorandum", {
      organization: "Example Battalion",
      office_symbol: "EXMP-OPS",
      memo_for: "Commander, Example Battalion",
      subject: "Range Schedule for the Drill",
      paragraphs: ["Report at 0630 on 30 October 2026. Bring water."],
      signature: { name: "Alex Quinn", rank: "Major", title: "Operations Officer", branch: "Infantry" },
      date: "October 5, 2026",
      poc: "The point of contact is Alex Quinn."
    });
    expect(created.isError, created.text).toBe(false);
    expect((created.data.checklist as { counts: { FAIL: number } }).counts.FAIL).toBe(0);
    expect(String((created.data.flags as { why: string }[]).map((item) => item.why).join(" ")).toLowerCase()).toContain("letterhead");
    const proposed = await call("propose_format", { file_id: created.data.file_id, style_id: "army-ar25-50-memorandum" });
    expect(proposed.isError, proposed.text).toBe(false);
    const applied = await call("apply_format", { proposal_id: proposed.data.proposal_id, base_version: proposed.data.base_version });
    expect(applied.isError, applied.text).toBe(false);
    const undone = await call("undo", { file_id: created.data.file_id, version: 1 });
    expect(undone.isError, undone.text).toBe(false);
    expect(undone.data.sha256).toBe(created.data.sha256);
  });

  it("keeps the check report and one formatted download without a subscription", async () => {
    const original = fs.readFileSync(path.join(repoRoot(), "samples/apa_before.docx"));
    const saved = await upload("again.docx", original);
    const secondFile = await upload("again-two.docx", original);
    await getStore().updateProfile(DEV_USER_ID, { subscription_status: "canceled", plan: "trial" });
    const checked = await call("check_document", { file_id: String(saved.file_id), style_id: "apa7-student" });
    expect(checked.status).toBe(200);
    expect(checked.isError, checked.text).toBe(false);
    const first = await call("propose_format", { file_id: saved.file_id, style_id: "apa7-student" });
    expect(first.isError, first.text).toBe(false);
    const applied = await call("apply_format", { proposal_id: first.data.proposal_id, base_version: first.data.base_version });
    expect(applied.isError, applied.text).toBe(false);
    const second = await call("propose_format", { file_id: secondFile.file_id, style_id: "apa7-student" });
    expect(second.isError, second.text).toBe(false);
    const blocked = await call("apply_format", { proposal_id: second.data.proposal_id, base_version: second.data.base_version });
    expect(blocked.isError).toBe(true);
    expect((blocked.data.error as { code: string }).code).toBe("usage_cap");
    await getStore().updateProfile(DEV_USER_ID, { subscription_status: "trialing", plan: "trial" });
  });

  it("refuses checkout when Stripe price ids are unset", async () => {
    const response = await fetch(`${base}/billing/checkout`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer dev-pagedrill" },
      body: JSON.stringify({ plan: "monthly" })
    });
    expect(response.status).toBe(503);
  });

  it("publishes OAuth protected-resource metadata", async () => {
    const response = await fetch(`${base}/.well-known/oauth-protected-resource/mcp`);
    const body = (await response.json()) as { resource: string; resource_name: string };
    expect(body.resource).toBe(`${base}/mcp`);
    expect(body.resource_name).toContain("Pagedrill");
  });
});
