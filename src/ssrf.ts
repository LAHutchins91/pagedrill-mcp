import dns from "node:dns/promises";
import net from "node:net";
import { ToolError } from "./errors.js";

const BLOCKED_NAMES = new Set(["localhost", "metadata.google.internal", "metadata.google.internal."]);

function octetBlocked(text: string): boolean {
  if (!/^\d{1,3}$/.test(text)) return true;
  if (text.length > 1 && text.startsWith("0")) return true;
  const value = Number(text);
  return value > 255;
}

export function isBlockedIpv4(ip: string): boolean {
  const parts = ip.split(".");
  if (parts.length !== 4 || parts.some(octetBlocked)) return true;
  const [a, b] = parts.map(Number);
  if (a === 0 || a === 10 || a === 127) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  if (a >= 224) return true;
  return false;
}

function ipv6Blocked(ip: string): boolean {
  const lower = ip.toLowerCase();
  if (lower === "::1" || lower === "::") return true;
  const mapped = lower.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
  if (mapped) return isBlockedIpv4(mapped[1]);
  const first = lower.split(":")[0] || "0";
  const value = Number.parseInt(first || "0", 16);
  if (Number.isNaN(value)) return true;
  if ((value & 0xfe00) === 0xfc00) return true;
  if ((value & 0xffc0) === 0xfe80) return true;
  return false;
}

export function isBlockedAddress(ip: string): boolean {
  const family = net.isIP(ip);
  if (family === 4) return isBlockedIpv4(ip);
  if (family === 6) return ipv6Blocked(ip);
  return true;
}

export function isBlockedHostname(hostname: string): boolean {
  const host = hostname.replace(/^\[|\]$/g, "").toLowerCase().replace(/\.$/, "");
  if (!host || BLOCKED_NAMES.has(host) || host.endsWith(".local")) return true;
  if (net.isIP(host)) return isBlockedAddress(host);
  if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) return true;
  return false;
}

export async function assertSafeDownloadUrl(raw: string): Promise<URL> {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new ToolError("The download URL is not valid.", "ssrf");
  }
  if (url.username || url.password) throw new ToolError("Download URLs cannot include credentials.", "ssrf");
  if (url.protocol !== "https:") throw new ToolError("Download URLs must use https. Private and local addresses are refused.", "ssrf");
  await assertPublicHost(url.hostname);
  return url;
}

async function assertPublicHost(hostname: string): Promise<void> {
  if (isBlockedHostname(hostname)) throw new ToolError("That download host is not allowed.", "ssrf");
  const host = hostname.replace(/^\[|\]$/g, "");
  if (net.isIP(host)) return;
  let records: { address: string }[];
  try {
    records = await dns.lookup(host, { all: true, verbatim: true });
  } catch {
    throw new ToolError("That download host is not allowed.", "ssrf");
  }
  if (records.length === 0 || records.some((record) => isBlockedAddress(record.address))) {
    throw new ToolError("That download host is not allowed.", "ssrf");
  }
}

export async function downloadLimited(raw: string, maxBytes: number): Promise<Buffer> {
  const url = await assertSafeDownloadUrl(raw);
  const response = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(20000) });
  if (response.status >= 300 && response.status < 400) throw new ToolError("Download redirects are refused.", "ssrf");
  if (!response.ok || !response.body) throw new ToolError("The file could not be downloaded.", "download_failed");
  const chunks: Buffer[] = [];
  let size = 0;
  const reader = response.body.getReader();
  for (;;) {
    const step = await reader.read();
    if (step.done) break;
    size += step.value.byteLength;
    if (size > maxBytes) throw new ToolError("The download is above the file size limit.", "file_too_large");
    chunks.push(Buffer.from(step.value));
  }
  if (size === 0) throw new ToolError("The download was empty.", "empty_upload");
  return Buffer.concat(chunks);
}
