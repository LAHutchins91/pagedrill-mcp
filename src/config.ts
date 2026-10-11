import path from "node:path";
import { fileURLToPath } from "node:url";
import { ToolError } from "./errors.js";

const here = path.dirname(fileURLToPath(import.meta.url));

/** Repo root from src/ or dist/src/. */
export function repoRoot(): string {
  const parent = path.resolve(here, "..");
  return path.basename(parent) === "dist" ? path.resolve(parent, "..") : parent;
}

export function appBaseUrl(): string {
  return (process.env.APP_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
}

export function dataDir(): string {
  return process.env.PAGEDRILL_DATA_DIR || path.join(repoRoot(), ".data");
}

export function signingSecret(): string {
  const value = process.env.PAGEDRILL_SIGNING_SECRET;
  if (value) return value;
  if (process.env.NODE_ENV === "production") throw new ToolError("PAGEDRILL_SIGNING_SECRET is not set.", "bad_config");
  return "dev-signing-secret";
}

export function purgeSecret(): string {
  return process.env.PAGEDRILL_PURGE_SECRET || "";
}

export function devAuthEnabled(): boolean {
  if (process.env.NODE_ENV === "production") return false;
  return process.env.PAGEDRILL_DEV_AUTH === "1";
}

export function devToken(): string {
  return process.env.PAGEDRILL_DEV_TOKEN || "dev-pagedrill";
}

export const DEV_USER_ID = "00000000-0000-4000-8000-000000000001";

export function intEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw == null || raw.trim() === "") return fallback;
  if (!/^\d+$/.test(raw.trim())) throw new ToolError(`${name} must be a non-negative integer.`, "bad_config");
  return Number(raw.trim());
}

export function supabaseUrl(): string {
  return (process.env.SUPABASE_URL || "").replace(/\/+$/, "");
}

export function supabaseAnonKey(): string {
  return process.env.SUPABASE_ANON_KEY || "";
}

export function supabaseServiceKey(): string {
  return process.env.SUPABASE_SERVICE_ROLE_KEY || "";
}

export function useSupabaseStore(): boolean {
  if (process.env.PAGEDRILL_STORE === "local") return false;
  if (process.env.NODE_ENV === "test" && process.env.PAGEDRILL_STORE !== "supabase") return false;
  return Boolean(supabaseUrl() && supabaseServiceKey());
}

export function fileBaseUrl(): string {
  return (process.env.PAGEDRILL_FILE_BASE_URL || appBaseUrl()).replace(/\/$/, "");
}

export function acceptUploads(): boolean {
  return process.env.PAGEDRILL_ACCEPT_UPLOADS !== "0";
}

export function stripeSecret(): string {
  return process.env.STRIPE_SECRET_KEY || "";
}

export function stripeWebhookSecret(): string {
  return process.env.STRIPE_WEBHOOK_SECRET || "";
}

/** Existing Stripe product id. Empty until STRIPE_PRODUCT_ID is set. Nothing is created. */
export function stripeProductId(): string {
  return process.env.STRIPE_PRODUCT_ID || "";
}

export function stripePriceMonthly(): string {
  return process.env.STRIPE_PRICE_MONTHLY || "";
}

export function stripePriceYearly(): string {
  return process.env.STRIPE_PRICE_YEARLY || "";
}

export function priceIdForPlan(plan: string): string {
  if (plan === "annual" || plan === "yearly") return stripePriceYearly();
  return stripePriceMonthly();
}
