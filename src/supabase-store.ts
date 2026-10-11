import crypto from "node:crypto";
import { supabaseServiceKey, supabaseUrl } from "./config.js";
import { ToolError } from "./errors.js";
import { countKey, emptyUsage, expiryFrom, monthKey, normalizeUsage, planCaps, QuotaError, tierFor, usageView, type UsageCounts, type UsageMetric } from "./quota.js";
import type { FileRow, Profile, ProposalRow, SavedFile, VersionRow } from "./store.js";

type Row = Record<string, unknown>;

async function rest<T>(pathName: string, options: RequestInit = {}): Promise<T> {
  const base = supabaseUrl();
  const key = supabaseServiceKey();
  if (!base || !key) throw new ToolError("The database is not configured.", "unconfigured");
  const headers = new Headers(options.headers);
  headers.set("apikey", key);
  headers.set("Authorization", `Bearer ${key}`);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (!headers.has("Prefer")) headers.set("Prefer", "return=representation");
  const response = await fetch(`${base}/rest/v1/${pathName}`, { ...options, headers, signal: AbortSignal.timeout(20000) });
  const text = await response.text();
  if (!response.ok) throw new ToolError("The database could not complete that request.", "store_error");
  return (text ? JSON.parse(text) : null) as T;
}

function hash(bytes: Buffer): string {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

async function writeBlob(bytes: Buffer): Promise<string> {
  const sha = hash(bytes);
  const base = supabaseUrl();
  const key = supabaseServiceKey();
  const response = await fetch(`${base}/storage/v1/object/pagedrill-files/${sha}`, {
    method: "POST",
    headers: { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/octet-stream", "x-upsert": "true" },
    body: new Uint8Array(bytes),
    signal: AbortSignal.timeout(20000)
  });
  if (!response.ok && response.status !== 409) throw new ToolError("The file could not be stored.", "store_error");
  return sha;
}

async function readBlob(sha: string): Promise<Buffer> {
  const base = supabaseUrl();
  const key = supabaseServiceKey();
  const response = await fetch(`${base}/storage/v1/object/pagedrill-files/${sha}`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
    signal: AbortSignal.timeout(20000)
  });
  if (!response.ok) throw new ToolError("That version is not part of this file.", "not_found");
  return Buffer.from(await response.arrayBuffer());
}

function profileFrom(row: Row): Profile {
  return {
    id: String(row.id),
    email: typeof row.email === "string" ? row.email : undefined,
    plan: String(row.plan ?? "trial"),
    subscription_status: String(row.subscription_status ?? "trialing"),
    retention_hours: 24,
    stripe_customer_id: typeof row.stripe_customer_id === "string" ? row.stripe_customer_id : null,
    stripe_subscription_id: typeof row.stripe_subscription_id === "string" ? row.stripe_subscription_id : null,
    current_period_end: typeof row.current_period_end === "string" ? row.current_period_end : null,
    cancel_at_period_end: row.cancel_at_period_end === true
  };
}

export class SupabaseStore {
  async ensureDevProfile(): Promise<Profile> {
    return this.ensureProfile({ id: "00000000-0000-4000-8000-000000000001", email: "dev@pagedrill.local" });
  }

  async ensureProfile(input: { id: string; email?: string }): Promise<Profile> {
    const found = await rest<Row[]>(`profiles?id=eq.${input.id}&select=*`);
    if (found[0]) return profileFrom(found[0]);
    const created = await rest<Row[]>("profiles", {
      method: "POST",
      body: JSON.stringify({ id: input.id, email: input.email ?? null, plan: "trial", subscription_status: "trialing", retention_hours: 24 })
    });
    return profileFrom(created[0]);
  }

  async getProfile(id: string): Promise<Profile | null> {
    const found = await rest<Row[]>(`profiles?id=eq.${id}&select=*`);
    return found[0] ? profileFrom(found[0]) : null;
  }

  async updateProfile(id: string, patch: Partial<Profile>): Promise<Profile> {
    const body: Row = {};
    if (patch.email !== undefined) body.email = patch.email;
    if (patch.plan !== undefined) body.plan = patch.plan;
    if (patch.subscription_status !== undefined) body.subscription_status = patch.subscription_status;
    if (patch.stripe_customer_id !== undefined) body.stripe_customer_id = patch.stripe_customer_id;
    if (patch.stripe_subscription_id !== undefined) body.stripe_subscription_id = patch.stripe_subscription_id;
    if (patch.current_period_end !== undefined) body.current_period_end = patch.current_period_end;
    if (patch.cancel_at_period_end !== undefined) body.cancel_at_period_end = patch.cancel_at_period_end;
    body.updated_at = new Date().toISOString();
    const updated = await rest<Row[]>(`profiles?id=eq.${id}`, { method: "PATCH", body: JSON.stringify(body) });
    if (!updated[0]) throw new ToolError("Account not found.", "not_found");
    return profileFrom(updated[0]);
  }

  private async counts(ownerId: string, now: Date): Promise<UsageCounts> {
    const month = monthKey(now);
    const rows = await rest<Row[]>(`usage_monthly?owner_id=eq.${ownerId}&month=eq.${month}&select=*`);
    const row = rows[0];
    if (!row) return emptyUsage();
    return normalizeUsage({
      formats: Number(row.formats ?? 0),
      previews: Number(row.previews ?? 0),
      files: Number(row.files ?? 0),
      checks: Number(row.checks ?? 0),
      free_formats: Number(row.free_formats ?? 0),
      free_previews: Number(row.free_previews ?? 0),
      free_files: Number(row.free_files ?? 0)
    });
  }

  async usage(ownerId: string, now = new Date()) {
    const profile = await this.getProfile(ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    return usageView(tierFor(profile), await this.counts(ownerId, now), now);
  }

  private async consume(ownerId: string, metric: Exclude<UsageMetric, "checks">, now: Date) {
    const profile = await this.getProfile(ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    const tier = tierFor(profile);
    const counts = await this.counts(ownerId, now);
    const stored = countKey(tier, metric);
    const cap = planCaps(tier)[metric];
    if (counts[stored] >= cap) throw new QuotaError(metric, counts[stored], cap, tier, now);
    counts[stored] += 1;
    await rest(`usage_monthly?on_conflict=owner_id,month`, {
      method: "POST",
      headers: { Prefer: "resolution=merge-duplicates,return=representation" },
      body: JSON.stringify({ owner_id: ownerId, month: monthKey(now), ...counts })
    });
  }

  async charge(ownerId: string, metric: Exclude<UsageMetric, "checks">, now = new Date()): Promise<void> {
    await this.consume(ownerId, metric, now);
  }

  async noteCheck(ownerId: string, now = new Date()): Promise<void> {
    const counts = await this.counts(ownerId, now);
    counts.checks += 1;
    await rest(`usage_monthly?on_conflict=owner_id,month`, {
      method: "POST",
      headers: { Prefer: "resolution=merge-duplicates,return=representation" },
      body: JSON.stringify({ owner_id: ownerId, month: monthKey(now), ...counts })
    });
  }

  async reserveUpload(ownerId: string, filename: string, now = new Date()) {
    const profile = await this.getProfile(ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    await this.consume(ownerId, "files", now);
    const fileId = crypto.randomUUID();
    const nonce = crypto.randomUUID();
    const exp = Math.floor(now.getTime() / 1000) + 15 * 60;
    await rest("upload_nonces", { method: "POST", body: JSON.stringify({ nonce, owner_id: ownerId, file_id: fileId, filename, exp: new Date(exp * 1000).toISOString() }) });
    return { fileId, nonce, exp };
  }

  async commitNewFile(input: { ownerId: string; filename: string; kind: string; bytes: Buffer }, now = new Date()): Promise<SavedFile> {
    const profile = await this.getProfile(input.ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    await this.consume(input.ownerId, "files", now);
    return this.insertFile({ ...input, fileId: crypto.randomUUID() }, now);
  }

  async commitReservedFile(input: { ownerId: string; fileId: string; filename: string; kind: string; bytes: Buffer; nonce: string }, now = new Date()): Promise<SavedFile> {
    const profile = await this.getProfile(input.ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    const rows = await rest<Row[]>(`upload_nonces?nonce=eq.${input.nonce}&select=*`);
    const reserved = rows[0];
    if (!reserved || reserved.owner_id !== input.ownerId || reserved.file_id !== input.fileId) throw new ToolError("That upload link is not valid.", "bad_link");
    await rest(`upload_nonces?nonce=eq.${input.nonce}`, { method: "DELETE" });
    return this.insertFile(input, now);
  }

  private async insertFile(input: { ownerId: string; fileId: string; filename: string; kind: string; bytes: Buffer }, now: Date): Promise<SavedFile> {
    const sha = await writeBlob(input.bytes);
    const createdAt = now.toISOString();
    await rest("files", {
      method: "POST",
      body: JSON.stringify({
        id: input.fileId,
        owner_id: input.ownerId,
        filename: input.filename,
        kind: input.kind,
        head_sha: sha,
        size: input.bytes.length,
        created_at: createdAt,
        last_used_at: createdAt,
        expires_at: expiryFrom(createdAt, 24)
      })
    });
    await rest("file_versions", {
      method: "POST",
      body: JSON.stringify({ file_id: input.fileId, number: 1, sha256: sha, size: input.bytes.length, op: "import", created_at: createdAt })
    });
    return { file_id: input.fileId, filename: input.filename, sha256: sha, size: input.bytes.length, version: 1 };
  }

  private async fileRow(ownerId: string, fileId: string, now: Date): Promise<FileRow> {
    const rows = await rest<Row[]>(`files?id=eq.${fileId}&owner_id=eq.${ownerId}&select=*`);
    const row = rows[0];
    if (!row) throw new ToolError("File not found.", "not_found");
    if (Date.parse(String(row.expires_at)) <= now.getTime()) throw new ToolError("That file has expired and was deleted.", "expired_file");
    return {
      id: String(row.id),
      ownerId: String(row.owner_id),
      filename: String(row.filename),
      kind: String(row.kind),
      headSha: String(row.head_sha),
      size: Number(row.size),
      createdAt: String(row.created_at),
      lastUsedAt: String(row.last_used_at),
      expiresAt: String(row.expires_at)
    };
  }

  async readBytes(ownerId: string, fileId: string, sha?: string, now = new Date()) {
    const file = await this.fileRow(ownerId, fileId, now);
    const wanted = sha || file.headSha;
    const versions = await rest<Row[]>(`file_versions?file_id=eq.${fileId}&sha256=eq.${wanted}&select=sha256`);
    const proposals = await rest<Row[]>(`proposals?file_id=eq.${fileId}&owner_id=eq.${ownerId}&result_sha=eq.${wanted}&select=id`);
    if (!versions[0] && !proposals[0]) throw new ToolError("That version is not part of this file.", "not_found");
    const lastUsedAt = now.toISOString();
    await rest(`files?id=eq.${fileId}`, { method: "PATCH", body: JSON.stringify({ last_used_at: lastUsedAt, expires_at: expiryFrom(lastUsedAt, 24) }) });
    return { file, bytes: await readBlob(wanted) };
  }

  async listFiles(ownerId: string, now = new Date()) {
    const rows = await rest<Row[]>(`files?owner_id=eq.${ownerId}&expires_at=gt.${now.toISOString()}&select=*`);
    return rows.map((row) => ({ file_id: String(row.id), filename: String(row.filename), sha256: String(row.head_sha), size: Number(row.size), expires_at: String(row.expires_at) }));
  }

  async listVersions(ownerId: string, fileId: string, now = new Date()) {
    await this.fileRow(ownerId, fileId, now);
    const rows = await rest<Row[]>(`file_versions?file_id=eq.${fileId}&select=*&order=number.asc`);
    return rows.map((row) => ({ version: Number(row.number), sha256: String(row.sha256), size: Number(row.size), op: String(row.op), created_at: String(row.created_at) }));
  }

  async saveProposal(input: Omit<ProposalRow, "id" | "createdAt" | "expiresAt" | "appliedAt"> & { bytes: Buffer }, now = new Date()): Promise<ProposalRow> {
    const profile = await this.getProfile(input.ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    const file = await this.fileRow(input.ownerId, input.fileId, now);
    if (file.headSha !== input.baseSha) throw new ToolError("base_version does not match the current file. Propose the format again.", "stale_version");
    await this.consume(input.ownerId, "previews", now);
    const sha = await writeBlob(input.bytes);
    const row: ProposalRow = {
      id: crypto.randomUUID(),
      ownerId: input.ownerId,
      fileId: input.fileId,
      baseSha: input.baseSha,
      resultSha: sha,
      size: input.bytes.length,
      diff: input.diff,
      flags: input.flags,
      verification: input.verification,
      checklist: input.checklist,
      notice: input.notice,
      createdAt: now.toISOString(),
      expiresAt: new Date(now.getTime() + 30 * 60 * 1000).toISOString(),
      appliedAt: null
    };
    await rest("proposals", {
      method: "POST",
      body: JSON.stringify({
        id: row.id,
        owner_id: row.ownerId,
        file_id: row.fileId,
        base_sha: row.baseSha,
        result_sha: row.resultSha,
        size: row.size,
        diff: row.diff,
        flags: row.flags,
        verification: row.verification,
        checklist: row.checklist,
        notice: row.notice,
        created_at: row.createdAt,
        expires_at: row.expiresAt
      })
    });
    return row;
  }

  async getProposal(ownerId: string, proposalId: string, now = new Date()): Promise<ProposalRow> {
    const rows = await rest<Row[]>(`proposals?id=eq.${proposalId}&owner_id=eq.${ownerId}&select=*`);
    const row = rows[0];
    if (!row) throw new ToolError("Proposal not found.", "not_found");
    if (row.applied_at) throw new ToolError("That proposal was already applied.", "stale_version");
    if (Date.parse(String(row.expires_at)) <= now.getTime()) throw new ToolError("That proposal has expired. Propose the format again.", "expired_file");
    return this.proposalFrom(row);
  }

  private proposalFrom(row: Row): ProposalRow {
    return {
      id: String(row.id),
      ownerId: String(row.owner_id),
      fileId: String(row.file_id),
      baseSha: String(row.base_sha),
      resultSha: String(row.result_sha),
      size: Number(row.size),
      diff: row.diff,
      flags: row.flags,
      verification: row.verification,
      checklist: row.checklist,
      notice: typeof row.notice === "string" ? row.notice : null,
      createdAt: String(row.created_at),
      expiresAt: String(row.expires_at),
      appliedAt: typeof row.applied_at === "string" ? row.applied_at : null
    };
  }

  async publishEdit(ownerId: string, proposalId: string, baseVersion: string, now = new Date()): Promise<SavedFile> {
    const profile = await this.getProfile(ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    const proposal = await this.getProposal(ownerId, proposalId, now);
    const file = await this.fileRow(ownerId, proposal.fileId, now);
    if (proposal.baseSha !== baseVersion || file.headSha !== baseVersion) {
      throw new ToolError("base_version does not match the current file. Propose the format again.", "stale_version");
    }
    await this.consume(ownerId, "formats", now);
    const versions = await rest<Row[]>(`file_versions?file_id=eq.${file.id}&select=number&order=number.desc&limit=1`);
    const number = Number(versions[0]?.number ?? 0) + 1;
    const appliedAt = now.toISOString();
    await rest("file_versions", { method: "POST", body: JSON.stringify({ file_id: file.id, number, sha256: proposal.resultSha, size: proposal.size, op: "apply", created_at: appliedAt }) });
    await rest(`proposals?id=eq.${proposalId}`, { method: "PATCH", body: JSON.stringify({ applied_at: appliedAt }) });
    await rest(`files?id=eq.${file.id}`, { method: "PATCH", body: JSON.stringify({ head_sha: proposal.resultSha, size: proposal.size, last_used_at: appliedAt, expires_at: expiryFrom(appliedAt, 24) }) });
    return { file_id: file.id, filename: file.filename, sha256: proposal.resultSha, size: proposal.size, version: number };
  }

  async restore(ownerId: string, fileId: string, version: number, now = new Date()): Promise<SavedFile> {
    const file = await this.fileRow(ownerId, fileId, now);
    const rows = await rest<Row[]>(`file_versions?file_id=eq.${fileId}&number=eq.${version}&select=*`);
    const prior = rows[0] as VersionRow | undefined;
    if (!prior) throw new ToolError("That version is not part of this file.", "not_found");
    const versions = await rest<Row[]>(`file_versions?file_id=eq.${fileId}&select=number&order=number.desc&limit=1`);
    const number = Number(versions[0]?.number ?? 0) + 1;
    const createdAt = now.toISOString();
    const sha = String((prior as unknown as Row).sha256);
    const size = Number((prior as unknown as Row).size);
    await rest("file_versions", { method: "POST", body: JSON.stringify({ file_id: fileId, number, sha256: sha, size, op: "restore", created_at: createdAt }) });
    await rest(`files?id=eq.${fileId}`, { method: "PATCH", body: JSON.stringify({ head_sha: sha, size, last_used_at: createdAt, expires_at: expiryFrom(createdAt, 24) }) });
    return { file_id: fileId, filename: file.filename, sha256: sha, size, version: number };
  }

  async deleteFile(ownerId: string, fileId: string): Promise<void> {
    const rows = await rest<Row[]>(`files?id=eq.${fileId}&owner_id=eq.${ownerId}&select=id`);
    if (!rows[0]) throw new ToolError("File not found.", "not_found");
    await rest(`files?id=eq.${fileId}&owner_id=eq.${ownerId}`, { method: "DELETE" });
  }

  async deleteAll(ownerId: string): Promise<number> {
    const rows = await rest<Row[]>(`files?owner_id=eq.${ownerId}&select=id`);
    for (const row of rows) await rest(`files?id=eq.${String(row.id)}&owner_id=eq.${ownerId}`, { method: "DELETE" });
    return rows.length;
  }

  async purge(now = new Date()): Promise<{ files: number }> {
    const rows = await rest<Row[]>(`files?expires_at=lte.${now.toISOString()}&select=id`);
    for (const row of rows) await rest(`files?id=eq.${String(row.id)}`, { method: "DELETE" });
    return { files: rows.length };
  }

  async support(email: string, message: string): Promise<{ id: string }> {
    const id = crypto.randomUUID();
    await rest("support_requests", { method: "POST", body: JSON.stringify({ id, email, message }) });
    return { id };
  }

  async audit(): Promise<void> {
    return undefined;
  }
}

let singleton: SupabaseStore | undefined;

export function supabaseStore(): SupabaseStore {
  if (!singleton) singleton = new SupabaseStore();
  return singleton;
}
