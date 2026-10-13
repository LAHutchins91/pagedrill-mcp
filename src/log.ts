/** Logs the operation, a status code, a hash, and a size. Never file contents. */

export function logEvent(event: { op: string; code?: string; sha256?: string; size?: number }): void {
  console.log(
    JSON.stringify({
      service: "pagedrill",
      op: event.op,
      code: event.code ?? "ok",
      sha256: event.sha256,
      size: event.size
    })
  );
}
