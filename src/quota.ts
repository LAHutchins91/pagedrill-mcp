import { intEnv } from "./config.js";
import { ToolError } from "./errors.js";

/** 25 MB as 25 × 1024 × 1024 bytes. */
export const DEFAULT_MAX_FILE_BYTES = 25 * 1024 * 1024;

export type PlanTier = "pro" | "trial";
export type UsageMetric = "formats" | "previews" | "files" | "checks";

export type PlanCaps = {
  formats: number;
  previews: number;
  files: number;
  maxFileBytes: number;
};

export type UsageCounts = Record<UsageMetric, number>;

/**
 * Trial and Pro share these caps unless an operator sets a different env value.
 * check_document is not one of these caps. Past a cap, the call is refused.
 */
export function planCaps(tier: PlanTier): PlanCaps {
  void tier;
  return {
    formats: intEnv("PAGEDRILL_CAP_FORMATS", 60),
    previews: intEnv("PAGEDRILL_CAP_PREVIEWS", 120),
    files: intEnv("PAGEDRILL_CAP_FILES", 120),
    maxFileBytes: intEnv("PAGEDRILL_CAP_MAX_BYTES", DEFAULT_MAX_FILE_BYTES)
  };
}

export function monthKey(now = new Date()): string {
  const month = String(now.getUTCMonth() + 1).padStart(2, "0");
  return `${now.getUTCFullYear()}-${month}`;
}

export function resetsAt(now = new Date()): string {
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1)).toISOString();
}

const METRIC_LABEL: Record<Exclude<UsageMetric, "checks">, string> = {
  formats: "formatted documents",
  previews: "previews",
  files: "files"
};

export class QuotaError extends ToolError {
  constructor(
    readonly metric: Exclude<UsageMetric, "checks">,
    readonly used: number,
    readonly cap: number,
    readonly tier: PlanTier,
    now = new Date()
  ) {
    super(
      `Monthly ${METRIC_LABEL[metric]} cap reached (${used} of ${cap} on the ${tier} plan). This request was blocked. Pagedrill does not bill overage. Usage resets ${resetsAt(now)}.`,
      "usage_cap"
    );
    this.name = "QuotaError";
  }
}

export class FileTooLargeError extends ToolError {
  constructor(size: number, maxBytes: number, tier: PlanTier) {
    super(`This file is ${size} bytes, above the ${maxBytes} byte limit. Pagedrill does not bill overage.`, "file_too_large");
    void tier;
    this.name = "FileTooLargeError";
  }
}

export function tierFor(profile: { subscription_status: string; plan: string }): PlanTier {
  if (profile.subscription_status === "active" && profile.plan === "pro") return "pro";
  if (profile.subscription_status === "active" || profile.subscription_status === "trialing") {
    return profile.subscription_status === "active" ? "pro" : "trial";
  }
  return "trial";
}

export function entitled(profile: { subscription_status: string }): boolean {
  return profile.subscription_status === "active" || profile.subscription_status === "trialing";
}

export function expiryFrom(lastUsedAt: string, hours = 24): string {
  return new Date(Date.parse(lastUsedAt) + hours * 60 * 60 * 1000).toISOString();
}

export function emptyUsage(): UsageCounts {
  return { formats: 0, previews: 0, files: 0, checks: 0 };
}

export function usageView(tier: PlanTier, counts: UsageCounts, now = new Date()) {
  const caps = planCaps(tier);
  const metric = (name: Exclude<UsageMetric, "checks">) => ({
    used: counts[name],
    cap: caps[name],
    remaining: Math.max(0, caps[name] - counts[name])
  });
  return {
    tier,
    month: monthKey(now),
    retention_hours: 24,
    max_file_bytes: caps.maxFileBytes,
    formats: metric("formats"),
    previews: metric("previews"),
    files: metric("files"),
    checks: { used: counts.checks }
  };
}

const checkHits = new Map<string, { count: number; end: number }>();

/** Free check_document calls: 30 per hour per account. This is not the format cap. */
export function allowCheck(key: string, now = Date.now()): boolean {
  for (const [name, value] of checkHits) if (value.end <= now) checkHits.delete(name);
  const value = checkHits.get(key);
  if (value) {
    value.count += 1;
    return value.count <= 30;
  }
  if (checkHits.size >= 10000) return false;
  checkHits.set(key, { count: 1, end: now + 3_600_000 });
  return true;
}
