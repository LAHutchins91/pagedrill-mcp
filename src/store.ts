import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { dataDir, DEV_USER_ID, useSupabaseStore } from "./config.js";
import { supabaseStore, type SupabaseStore } from "./supabase-store.js";
import { ToolError } from "./errors.js";
import { emptyUsage, entitled, expiryFrom, monthKey, planCaps, QuotaError, tierFor, usageView, type PlanTier, type UsageCounts, type UsageMetric } from "./quota.js";

export type Profile = {
  id: string;
  email?: string;
  plan: string;
  subscription_status: string;
  retention_hours: number;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

export type FileRow = {
  id: string;
  ownerId: string;
  filename: string;
  kind: string;
  headSha: string;
  size: number;
  createdAt: string;
  lastUsedAt: string;
  expiresAt: string;
};

export type VersionRow = { fileId: string; number: number; sha256: string; size: number; op: string; createdAt: string };

export type ProposalRow = {
  id: string;
  ownerId: string;
  fileId: string;
  baseSha: string;
  resultSha: string;
  size: number;
  diff: unknown;
  flags: unknown;
  verification: unknown;
  checklist: unknown;
  notice: string | null;
  createdAt: string;
  expiresAt: string;
  appliedAt: string | null;
};

export type SavedFile = { file_id: string; filename: string; sha256: string; size: number; version: number };

type State = {
  profiles: Record<string, Profile>;
  files: Record<string, FileRow>;
  versions: VersionRow[];
  proposals: Record<string, ProposalRow>;
  uploads: Record<string, { ownerId: string; fileId: string; filename: string; exp: string }>;
  usage: Record<string, UsageCounts>;
  support: { id: string; email: string; message: string; createdAt: string }[];
};

const EMPTY = (): State => ({ profiles: {}, files: {}, versions: [], proposals: {}, uploads: {}, usage: {}, support: [] });

function statePath() {
  return path.join(dataDir(), "state.json");
}

function blobPath(sha: string) {
  return path.join(dataDir(), "blobs", sha);
}

function load(): State {
  try {
    return JSON.parse(fs.readFileSync(statePath(), "utf8")) as State;
  } catch {
    return EMPTY();
  }
}

function save(state: State) {
  fs.mkdirSync(dataDir(), { recursive: true });
  fs.writeFileSync(statePath(), JSON.stringify(state));
}

export function sha256(bytes: Buffer): string {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function writeBlob(bytes: Buffer): string {
  const hash = sha256(bytes);
  const dest = blobPath(hash);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (!fs.existsSync(dest)) fs.writeFileSync(dest, bytes);
  return hash;
}

function readBlob(hash: string): Buffer {
  return fs.readFileSync(blobPath(hash));
}

function liveFile(state: State, ownerId: string, fileId: string, now: Date): FileRow {
  const file = state.files[fileId];
  if (!file || file.ownerId !== ownerId) throw new ToolError("File not found.", "not_found");
  if (Date.parse(file.expiresAt) <= now.getTime()) throw new ToolError("That file has expired and was deleted.", "expired_file");
  return file;
}

function headNumber(state: State, fileId: string): number {
  return state.versions.filter((version) => version.fileId === fileId).reduce((max, version) => Math.max(max, version.number), 0);
}

export class LocalStore {
  reset(): void {
    fs.rmSync(dataDir(), { recursive: true, force: true });
    save(EMPTY());
  }

  async ensureDevProfile(): Promise<Profile> {
    return this.ensureProfile({ id: DEV_USER_ID, email: "dev@pagedrill.local" });
  }

  async ensureProfile(input: { id: string; email?: string }): Promise<Profile> {
    const state = load();
    const existing = state.profiles[input.id];
    if (existing) {
      if (input.email && existing.email !== input.email) {
        existing.email = input.email;
        save(state);
      }
      return existing;
    }
    const profile: Profile = {
      id: input.id,
      email: input.email,
      plan: "trial",
      subscription_status: "trialing",
      retention_hours: 24,
      stripe_customer_id: null,
      stripe_subscription_id: null,
      current_period_end: null,
      cancel_at_period_end: false
    };
    state.profiles[input.id] = profile;
    save(state);
    return profile;
  }

  async getProfile(id: string): Promise<Profile | null> {
    return load().profiles[id] ?? null;
  }

  async updateProfile(id: string, patch: Partial<Profile>): Promise<Profile> {
    const state = load();
    const profile = state.profiles[id];
    if (!profile) throw new ToolError("Account not found.", "not_found");
    Object.assign(profile, patch, { id });
    save(state);
    return profile;
  }

  async usage(ownerId: string, now = new Date()) {
    const profile = await this.getProfile(ownerId);
    if (!profile) throw new ToolError("Account not found.", "not_found");
    const tier = tierFor(profile);
    const counts = load().usage[`${ownerId}:${monthKey(now)}`] ?? emptyUsage();
    return usageView(tier, counts, now);
  }

  private consume(state: State, ownerId: string, metric: Exclude<UsageMetric, "checks">, tier: PlanTier, now: Date) {
    const key = `${ownerId}:${monthKey(now)}`;
    const counts = state.usage[key] ?? emptyUsage();
    const cap = planCaps(tier)[metric];
    if (counts[metric] >= cap) throw new QuotaError(metric, counts[metric], cap, tier, now);
    counts[metric] += 1;
    state.usage[key] = counts;
  }

  async noteCheck(ownerId: string, now = new Date()): Promise<void> {
    const state = load();
    const key = `${ownerId}:${monthKey(now)}`;
    const counts = state.usage[key] ?? emptyUsage();
    counts.checks += 1;
    state.usage[key] = counts;
    save(state);
  }

  async reserveUpload(ownerId: string, filename: string, now = new Date()) {
    const profile = await this.getProfile(ownerId);
    if (!profile || !entitled(profile)) throw new ToolError("An active trial or Pro subscription is required.", "access");
    const state = load();
    this.consume(state, ownerId, "files", tierFor(profile), now);
    const fileId = crypto.randomUUID();
    const nonce = crypto.randomUUID();
    const exp = Math.floor(now.getTime() / 1000) + 15 * 60;
    state.uploads[nonce] = { ownerId, fileId, filename, exp: new Date(exp * 1000).toISOString() };
    save(state);
    return { fileId, nonce, exp };
  }

  async commitNewFile(input: { ownerId: string; filename: string; kind: string; bytes: Buffer }, now = new Date()): Promise<SavedFile> {
    const profile = await this.getProfile(input.ownerId);
    if (!profile || !entitled(profile)) throw new ToolError("An active trial or Pro subscription is required.", "access");
    const state = load();
    this.consume(state, input.ownerId, "files", tierFor(profile), now);
    const hash = writeBlob(input.bytes);
    const createdAt = now.toISOString();
    const row: FileRow = {
      id: crypto.randomUUID(),
      ownerId: input.ownerId,
      filename: input.filename,
      kind: input.kind,
      headSha: hash,
      size: input.bytes.length,
      createdAt,
      lastUsedAt: createdAt,
      expiresAt: expiryFrom(createdAt, 24)
    };
    state.files[row.id] = row;
    state.versions.push({ fileId: row.id, number: 1, sha256: hash, size: input.bytes.length, op: "import", createdAt });
    save(state);
    return { file_id: row.id, filename: row.filename, sha256: hash, size: row.size, version: 1 };
  }

  async commitReservedFile(input: { ownerId: string; fileId: string; filename: string; kind: string; bytes: Buffer; nonce: string }, now = new Date()): Promise<SavedFile> {
    const profile = await this.getProfile(input.ownerId);
    if (!profile || !entitled(profile)) throw new ToolError("An active trial or Pro subscription is required.", "access");
    const state = load();
    const reserved = state.uploads[input.nonce];
    if (!reserved || reserved.ownerId !== input.ownerId || reserved.fileId !== input.fileId) {
      throw new ToolError("That upload link is not valid.", "bad_link");
    }
    delete state.uploads[input.nonce];
    const hash = writeBlob(input.bytes);
    const createdAt = now.toISOString();
    const row: FileRow = {
      id: input.fileId,
      ownerId: input.ownerId,
      filename: input.filename,
      kind: input.kind,
      headSha: hash,
      size: input.bytes.length,
      createdAt,
      lastUsedAt: createdAt,
      expiresAt: expiryFrom(createdAt, 24)
    };
    state.files[row.id] = row;
    state.versions.push({ fileId: row.id, number: 1, sha256: hash, size: input.bytes.length, op: "import", createdAt });
    save(state);
    return { file_id: row.id, filename: row.filename, sha256: hash, size: row.size, version: 1 };
  }

  async readBytes(ownerId: string, fileId: string, sha?: string, now = new Date()) {
    const state = load();
    const file = liveFile(state, ownerId, fileId, now);
    const wanted = sha || file.headSha;
    const known =
      state.versions.some((version) => version.fileId === file.id && version.sha256 === wanted) ||
      Object.values(state.proposals).some((proposal) => proposal.fileId === file.id && proposal.resultSha === wanted && proposal.ownerId === ownerId);
    if (!known) throw new ToolError("That version is not part of this file.", "not_found");
    file.lastUsedAt = now.toISOString();
    file.expiresAt = expiryFrom(file.lastUsedAt, 24);
    save(state);
    return { file, bytes: readBlob(wanted) };
  }

  async listFiles(ownerId: string, now = new Date()) {
    return Object.values(load().files)
      .filter((file) => file.ownerId === ownerId && Date.parse(file.expiresAt) > now.getTime())
      .map((file) => ({ file_id: file.id, filename: file.filename, sha256: file.headSha, size: file.size, expires_at: file.expiresAt }));
  }

  async listVersions(ownerId: string, fileId: string, now = new Date()) {
    const state = load();
    const file = liveFile(state, ownerId, fileId, now);
    return state.versions
      .filter((version) => version.fileId === file.id)
      .sort((a, b) => a.number - b.number)
      .map((version) => ({ version: version.number, sha256: version.sha256, size: version.size, op: version.op, created_at: version.createdAt }));
  }

  async saveProposal(input: Omit<ProposalRow, "id" | "createdAt" | "expiresAt" | "appliedAt"> & { bytes: Buffer }, now = new Date()): Promise<ProposalRow> {
    const profile = await this.getProfile(input.ownerId);
    if (!profile || !entitled(profile)) throw new ToolError("An active trial or Pro subscription is required.", "access");
    const state = load();
    const file = liveFile(state, input.ownerId, input.fileId, now);
    if (file.headSha !== input.baseSha) throw new ToolError("base_version does not match the current file. Propose the format again.", "stale_version");
    this.consume(state, input.ownerId, "previews", tierFor(profile), now);
    const hash = writeBlob(input.bytes);
    const row: ProposalRow = {
      id: crypto.randomUUID(),
      ownerId: input.ownerId,
      fileId: input.fileId,
      baseSha: input.baseSha,
      resultSha: hash,
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
    state.proposals[row.id] = row;
    file.lastUsedAt = now.toISOString();
    file.expiresAt = expiryFrom(file.lastUsedAt, 24);
    save(state);
    return row;
  }

  async getProposal(ownerId: string, proposalId: string, now = new Date()): Promise<ProposalRow> {
    const row = load().proposals[proposalId];
    if (!row || row.ownerId !== ownerId) throw new ToolError("Proposal not found.", "not_found");
    if (row.appliedAt) throw new ToolError("That proposal was already applied.", "stale_version");
    if (Date.parse(row.expiresAt) <= now.getTime()) throw new ToolError("That proposal has expired. Propose the format again.", "expired_file");
    return row;
  }

  async publishEdit(ownerId: string, proposalId: string, baseVersion: string, now = new Date()): Promise<SavedFile> {
    const profile = await this.getProfile(ownerId);
    if (!profile || !entitled(profile)) throw new ToolError("An active trial or Pro subscription is required.", "access");
    const state = load();
    const proposal = state.proposals[proposalId];
    if (!proposal || proposal.ownerId !== ownerId) throw new ToolError("Proposal not found.", "not_found");
    if (proposal.appliedAt) throw new ToolError("That proposal was already applied.", "stale_version");
    if (Date.parse(proposal.expiresAt) <= now.getTime()) throw new ToolError("That proposal has expired. Propose the format again.", "expired_file");
    const file = liveFile(state, ownerId, proposal.fileId, now);
    if (proposal.baseSha !== baseVersion || file.headSha !== baseVersion) {
      throw new ToolError("base_version does not match the current file. Propose the format again.", "stale_version");
    }
    this.consume(state, ownerId, "formats", tierFor(profile), now);
    proposal.appliedAt = now.toISOString();
    const number = headNumber(state, file.id) + 1;
    state.versions.push({ fileId: file.id, number, sha256: proposal.resultSha, size: proposal.size, op: "apply", createdAt: proposal.appliedAt });
    file.headSha = proposal.resultSha;
    file.size = proposal.size;
    file.lastUsedAt = proposal.appliedAt;
    file.expiresAt = expiryFrom(file.lastUsedAt, 24);
    save(state);
    return { file_id: file.id, filename: file.filename, sha256: file.headSha, size: file.size, version: number };
  }

  async restore(ownerId: string, fileId: string, version: number, now = new Date()): Promise<SavedFile> {
    const state = load();
    const file = liveFile(state, ownerId, fileId, now);
    const prior = state.versions.find((item) => item.fileId === file.id && item.number === version);
    if (!prior) throw new ToolError("That version is not part of this file.", "not_found");
    const createdAt = now.toISOString();
    const number = headNumber(state, file.id) + 1;
    state.versions.push({ fileId: file.id, number, sha256: prior.sha256, size: prior.size, op: "restore", createdAt });
    file.headSha = prior.sha256;
    file.size = prior.size;
    file.lastUsedAt = createdAt;
    file.expiresAt = expiryFrom(createdAt, 24);
    save(state);
    return { file_id: file.id, filename: file.filename, sha256: file.headSha, size: file.size, version: number };
  }

  async deleteFile(ownerId: string, fileId: string): Promise<void> {
    const state = load();
    const file = state.files[fileId];
    if (!file || file.ownerId !== ownerId) throw new ToolError("File not found.", "not_found");
    delete state.files[fileId];
    state.versions = state.versions.filter((version) => version.fileId !== fileId);
    for (const [id, proposal] of Object.entries(state.proposals)) if (proposal.fileId === fileId) delete state.proposals[id];
    save(state);
  }

  async deleteAll(ownerId: string): Promise<number> {
    const ids = Object.values(load().files)
      .filter((file) => file.ownerId === ownerId)
      .map((file) => file.id);
    for (const id of ids) await this.deleteFile(ownerId, id);
    return ids.length;
  }

  async purge(now = new Date()): Promise<{ files: number }> {
    const state = load();
    let files = 0;
    for (const file of Object.values(state.files)) {
      if (Date.parse(file.expiresAt) <= now.getTime()) {
        delete state.files[file.id];
        state.versions = state.versions.filter((version) => version.fileId !== file.id);
        files += 1;
      }
    }
    const live = new Set<string>();
    for (const file of Object.values(state.files)) {
      for (const version of state.versions) if (version.fileId === file.id) live.add(version.sha256);
    }
    for (const proposal of Object.values(state.proposals)) {
      if (proposal.appliedAt || Date.parse(proposal.expiresAt) > now.getTime()) live.add(proposal.resultSha);
    }
    const dir = path.join(dataDir(), "blobs");
    if (fs.existsSync(dir)) {
      for (const name of fs.readdirSync(dir)) if (!live.has(name)) fs.rmSync(path.join(dir, name), { force: true });
    }
    save(state);
    return { files };
  }

  async support(email: string, message: string): Promise<{ id: string }> {
    const state = load();
    const id = crypto.randomUUID();
    state.support.push({ id, email, message, createdAt: new Date().toISOString() });
    save(state);
    return { id };
  }

  async audit(event: { ownerId?: string; op: string; code?: string; sha256?: string; size?: number }): Promise<void> {
    void event;
  }
}

let local: LocalStore | undefined;

export function getStore(): LocalStore | SupabaseStore {
  if (useSupabaseStore()) return supabaseStore();
  if (!local) local = new LocalStore();
  return local;
}

export function resetStoreForTests(): LocalStore {
  local = new LocalStore();
  local.reset();
  return local;
}
