import crypto from "node:crypto";
import path from "node:path";
import { pathToFileURL } from "node:url";
import express, { type Request, type Response } from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { billingPatch, checkoutForm, stripeEvent } from "./billing.js";
import {
  acceptUploads,
  appBaseUrl,
  DEV_USER_ID,
  devAuthEnabled,
  devToken,
  priceIdForPlan,
  purgeSecret,
  stripeProductId,
  stripeSecret,
  supabaseAnonKey,
  supabaseUrl
} from "./config.js";
import { engineCall } from "./engine-client.js";
import { ToolError } from "./errors.js";
import { logEvent } from "./log.js";
import { MCP_CORS_HEADERS, mcpBrowserOriginAllowed } from "./mcp-clients.js";
import { createPagedrillServer } from "./pagedrill-tools.js";
import { installPluginAuth } from "./plugin-auth.js";
import { homePage, privacyPage, supportPage, termsPage } from "./public-pages.js";
import { entitled, FileTooLargeError, planCaps, tierFor, type PlanTier } from "./quota.js";
import { getStore } from "./store.js";
import { assertFresh, readToken } from "./tokens.js";

export const app = express();
export default app;
app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use((_req, res, next) => {
  res.set({ "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY", "Cache-Control": "no-store" });
  next();
});

const publicLimits = new Map<string, { count: number; end: number }>();
function allowPublic(key: string, limit: number, ms: number) {
  const now = Date.now();
  for (const [name, value] of publicLimits) if (value.end <= now) publicLimits.delete(name);
  const value = publicLimits.get(key);
  if (value) {
    value.count += 1;
    return value.count <= limit;
  }
  if (publicLimits.size >= 10000) return false;
  publicLimits.set(key, { count: 1, end: now + ms });
  return true;
}

function bearer(req: Request) {
  const header = req.header("authorization") ?? "";
  return header.startsWith("Bearer ") ? header.slice(7).trim() : "";
}

async function supabaseRequest<T>(pathName: string, options: RequestInit = {}, accessToken?: string): Promise<T> {
  const base = supabaseUrl();
  const key = supabaseAnonKey();
  if (!base || !key) throw new ToolError("Sign-in is not configured.", "unconfigured");
  const headers = new Headers(options.headers);
  headers.set("apikey", key);
  headers.set("Authorization", `Bearer ${accessToken ?? key}`);
  const response = await fetch(`${base}${pathName}`, { ...options, headers, signal: AbortSignal.timeout(20000) });
  const text = await response.text();
  if (!response.ok) throw new ToolError("Sign-in could not be verified.", "unauthorized");
  return (text ? JSON.parse(text) : null) as T;
}

async function stripeRequest<T>(stripePath: string, params: URLSearchParams): Promise<T> {
  const secret = stripeSecret();
  if (!secret) throw new ToolError("Billing is not configured.", "billing_unconfigured");
  const response = await fetch(`https://api.stripe.com/v1/${stripePath}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${secret}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString()
  });
  if (!response.ok) throw new ToolError("Billing could not be reached.", "billing");
  return (await response.json()) as T;
}

type AuthUser = { id: string; email?: string };

async function authenticatedUser(req: Request): Promise<AuthUser> {
  const token = bearer(req);
  if (!token) throw new ToolError("Sign in to Pagedrill.", "unauthorized");
  if (devAuthEnabled() && token === devToken()) {
    await getStore().ensureDevProfile();
    return { id: DEV_USER_ID, email: "dev@pagedrill.local" };
  }
  const user = await supabaseRequest<AuthUser>("/auth/v1/user", { method: "GET" }, token);
  if (!user?.id) throw new ToolError("Sign in to Pagedrill.", "unauthorized");
  await getStore().ensureProfile({ id: user.id, email: user.email });
  return user;
}

app.post("/billing/webhook", express.raw({ type: "application/json" }), async (req, res) => {
  try {
    const signature = req.header("stripe-signature");
    if (!signature || !Buffer.isBuffer(req.body)) return res.status(400).send("Missing Stripe signature");
    const event = stripeEvent(req.body, signature);
    const update = billingPatch(event.type, event.data.object);
    if (update?.userId) {
      await getStore().ensureProfile({ id: update.userId });
      await getStore().updateProfile(update.userId, update.patch);
    }
    logEvent({ op: "stripe_webhook", code: "ok" });
    res.json({ received: true });
  } catch {
    logEvent({ op: "stripe_webhook", code: "rejected" });
    res.status(400).send("Webhook could not be processed");
  }
});

app.use(express.json({ limit: "128kb" }));
app.get("/", (_req, res) => {
  const ready = Boolean(stripeSecret() && stripeProductId() && priceIdForPlan("monthly") && priceIdForPlan("annual"));
  res.type("html").send(homePage(ready));
});
app.get("/privacy", (_req, res) => res.type("html").send(privacyPage()));
app.get("/terms", (_req, res) => res.type("html").send(termsPage()));
app.get("/support", (_req, res) => res.type("html").send(supportPage()));
installPluginAuth(app, appBaseUrl(), supabaseUrl() ? `${supabaseUrl()}/auth/v1` : "");

app.post("/billing/checkout", async (req, res) => {
  try {
    const user = await authenticatedUser(req);
    const plan = z.enum(["monthly", "annual", "yearly"]).parse(req.body?.plan ?? "monthly");
    const priceId = priceIdForPlan(plan);
    if (!stripeSecret() || !stripeProductId() || !priceId) {
      return res.status(503).json({ error: { code: "billing_unconfigured", reason: "Billing is not configured." } });
    }
    const profile = await getStore().getProfile(user.id);
    const params = checkoutForm({
      userId: user.id,
      email: user.email,
      priceId,
      customerId: profile?.stripe_customer_id,
      baseUrl: appBaseUrl()
    });
    if ([...params.keys()].some((key) => key.includes("price_data") || key.includes("unit_amount"))) {
      return res.status(500).json({ error: { code: "billing", reason: "Checkout is misconfigured." } });
    }
    const session = await stripeRequest<{ url: string }>("checkout/sessions", params);
    logEvent({ op: "checkout", code: "ok" });
    res.json({ url: session.url });
  } catch (error) {
    const reason = error instanceof ToolError ? error.message : "Checkout could not be started.";
    res.status(error instanceof ToolError && error.code === "unauthorized" ? 401 : 400).json({ error: { code: "billing", reason } });
  }
});

app.post("/api/support", async (req, res) => {
  if (!allowPublic(`support:${req.ip}`, 5, 3_600_000)) return res.status(429).json({ error: "Too many requests. Please try again in an hour." });
  const input = z.object({ email: z.string().email().max(254), message: z.string().trim().min(10).max(4000) }).safeParse(req.body);
  if (!input.success) return res.status(400).json({ error: "Enter a valid reply email and a message of 10–4000 characters." });
  const saved = await getStore().support(input.data.email, input.data.message);
  logEvent({ op: "support", code: "ok" });
  res.json({ id: saved.id });
});

function readLimited(req: Request, max: number, tier: PlanTier): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    let settled = false;
    const fail = (error: Error) => {
      if (settled) return;
      settled = true;
      reject(error);
    };
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > max) {
        fail(new FileTooLargeError(size, max, tier));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => {
      if (settled) return;
      settled = true;
      if (size === 0) reject(new ToolError("The upload was empty.", "empty_upload"));
      else resolve(Buffer.concat(chunks));
    });
    req.on("error", () => fail(new ToolError("Upload failed. The file was not stored.", "upload_failed")));
  });
}

function httpError(error: unknown, res: Response) {
  const code = error instanceof ToolError ? error.code : "request_failed";
  const reason = error instanceof ToolError ? error.message : "The request failed. The file was not changed.";
  const status = code === "file_too_large" ? 413 : code === "usage_cap" ? 429 : code === "unauthorized" || code === "bad_link" || code === "expired_link" ? 401 : code === "not_found" || code === "expired_file" ? 404 : code === "access" ? 403 : 400;
  logEvent({ op: "http", code });
  res.status(status).json({ error: { code, reason } });
}

app.put("/v1/upload/:token", async (req, res) => {
  if (!acceptUploads()) {
    res.status(421).json({ error: { code: "use_file_host", reason: "This host does not accept file bodies. Use the upload link exactly as the tool returned it." } });
    req.destroy();
    return;
  }
  try {
    const parsed = readToken(String(req.params.token));
    if (parsed.typ !== "put") throw new ToolError("This link is not an upload link.", "bad_link");
    assertFresh(parsed.exp);
    const profile = await getStore().getProfile(parsed.ownerId);
    if (!profile || !entitled(profile)) throw new ToolError("An active trial or Pro subscription is required.", "access");
    const tier = tierFor(profile);
    const bytes = await readLimited(req, planCaps(tier).maxFileBytes, tier);
    await engineCall<{ kind: string }>({ action: "inspect", filename: parsed.filename, data_b64: bytes.toString("base64") });
    const saved = await getStore().commitReservedFile({
      ownerId: parsed.ownerId,
      fileId: parsed.fileId,
      filename: parsed.filename,
      kind: "docx",
      bytes,
      nonce: parsed.nonce
    });
    logEvent({ op: "upload", code: "ok", sha256: saved.sha256, size: saved.size });
    res.json(saved);
  } catch (error) {
    httpError(error, res);
  }
});

app.get("/v1/download/:token", async (req, res) => {
  if (!acceptUploads()) {
    return res.status(421).json({ error: { code: "use_file_host", reason: "This host does not accept file bodies. Use the download link exactly as the tool returned it." } });
  }
  try {
    const parsed = readToken(String(req.params.token));
    if (parsed.typ !== "get") throw new ToolError("This link is not a download link.", "bad_link");
    assertFresh(parsed.exp);
    const loaded = await getStore().readBytes(parsed.ownerId, parsed.fileId, parsed.sha);
    const filename = loaded.file.filename.replace(/["\r\n]/g, "");
    logEvent({ op: "download", code: "ok", sha256: parsed.sha, size: loaded.bytes.length });
    res.set({
      "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "Content-Length": String(loaded.bytes.length),
      "Content-Disposition": `attachment; filename="${filename}"`
    });
    res.end(loaded.bytes);
  } catch (error) {
    httpError(error, res);
  }
});

app.post("/internal/purge", async (req, res) => {
  const secret = purgeSecret();
  const given = req.header("x-pagedrill-purge") || "";
  if (!secret || given.length !== secret.length || !timingSafe(given, secret)) {
    return res.status(401).json({ error: { code: "unauthorized", reason: "Purge is not authorized." } });
  }
  const result = await getStore().purge();
  logEvent({ op: "purge", code: "ok" });
  res.json(result);
});

function timingSafe(given: string, expected: string) {
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function guardMcpOrigin(req: Request, res: Response) {
  const origin = req.header("origin");
  if (!mcpBrowserOriginAllowed(origin, appBaseUrl())) {
    res.status(403).json({ error: "Origin is not allowed." });
    return false;
  }
  if (origin) res.set({ ...MCP_CORS_HEADERS, "Access-Control-Allow-Origin": origin, Vary: "Origin" });
  return true;
}

app.options("/mcp", (req, res) => {
  if (!guardMcpOrigin(req, res)) return;
  res.status(204).end();
});

app.post("/mcp", async (req, res) => {
  if (!guardMcpOrigin(req, res)) return;
  if (!allowPublic(`mcp:${req.ip}`, 300, 60_000)) return res.status(429).set("Retry-After", "60").json({ error: "Too many requests. Retry in one minute." });
  const publicMethods = new Set(["initialize", "notifications/initialized", "tools/list", "ping"]);
  const toolName = req.body?.params?.name;
  const freeCheck = req.body?.method === "tools/call" && toolName === "check_document";
  let ownerId = "";
  if (!publicMethods.has(req.body?.method)) {
    try {
      const user = await authenticatedUser(req);
      ownerId = user.id;
    } catch {
      res.set("WWW-Authenticate", `Bearer resource_metadata="${appBaseUrl()}/.well-known/oauth-protected-resource/mcp"`);
      return res.status(401).json({ error: "Sign in to Pagedrill to use these tools." });
    }
    if (!freeCheck) {
      const profile = await getStore().getProfile(ownerId);
      if (!profile || !entitled(profile)) {
        return res.status(403).json({ error: "A Pagedrill trial or Pro subscription is required. check_document stays available without one." });
      }
    }
  }
  let server: McpServer | undefined;
  try {
    server = createPagedrillServer(ownerId);
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    res.on("close", () => {
      void transport.close();
      void server?.close();
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch {
    if (!res.headersSent) res.status(500).json({ error: "Unable to process the plugin request." });
  }
});

app.get("/mcp", (req, res) => {
  if (!guardMcpOrigin(req, res)) return;
  res.set("WWW-Authenticate", `Bearer resource_metadata="${appBaseUrl()}/.well-known/oauth-protected-resource/mcp"`);
  res.status(401).json({ error: "Use Streamable HTTP POST with your Pagedrill connection." });
});

app.use((error: { type?: string }, _req: Request, res: Response, _next: express.NextFunction) => {
  res.status(error?.type === "entity.too.large" ? 413 : 400).json({ error: "Invalid or oversized request." });
});

function runningAsEntry() {
  const entry = process.argv[1];
  if (!entry) return false;
  return import.meta.url === pathToFileURL(path.resolve(entry)).href;
}

if (process.env.NODE_ENV !== "test" && !process.env.VITEST && runningAsEntry()) {
  const port = Number(process.env.PORT ?? 3000);
  const stdio = process.stdin.isTTY !== true && process.env.PAGEDRILL_HTTP_ONLY !== "1";
  app.listen(port, () => {
    const line = `Pagedrill by Ouroboros listening on ${port}`;
    if (stdio) console.error(line);
    else console.log(line);
  });
  if (stdio) {
    const stdioServer = createPagedrillServer("");
    await stdioServer.connect(new StdioServerTransport());
  }
}
