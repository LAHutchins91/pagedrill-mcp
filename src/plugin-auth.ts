import type { Express } from "express";
import { appBaseUrl } from "./config.js";

export function protectedResourceMetadata(baseUrl: string, supabaseAuthUrl: string) {
  return {
    resource: `${baseUrl}/mcp`,
    resource_name: "Pagedrill by Ouroboros",
    authorization_servers: supabaseAuthUrl ? [supabaseAuthUrl] : [],
    scopes_supported: ["email", "offline_access"],
    bearer_methods_supported: ["header"],
    resource_documentation: `${baseUrl}/connect`
  };
}

export function installPluginAuth(app: Express, baseUrl: string, supabaseAuthUrl: string) {
  app.get(["/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"], (_req, res) => {
    res.set("Access-Control-Allow-Origin", "*").json(protectedResourceMetadata(appBaseUrl(), supabaseAuthUrl));
  });
  void baseUrl;
  app.get("/connect", (_req, res) => {
    res.type("html").send(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Connect Pagedrill</title></head><body>
<main><h1>Connect Pagedrill</h1>
<p>Sign in with the host's Supabase project, then approve the assistant. Pagedrill can format the .docx files you send, keep versions for undo, and read whether your trial or Pro subscription is active.</p>
<p>check_document stays available without a subscription and is rate-limited. propose_format and apply_format need an active trial or Pro subscription.</p>
<p><a href="/">Back</a></p></main></body></html>`);
  });
}
