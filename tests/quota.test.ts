import { beforeEach, describe, expect, it } from "vitest";
import { DEV_USER_ID } from "../src/config.js";
import { QuotaError } from "../src/quota.js";
import { LocalStore, resetStoreForTests } from "../src/store.js";

describe("per-user usage counters", () => {
  beforeEach(() => {
    resetStoreForTests();
  });

  it("blocks the 61st formatted document and the 121st preview", async () => {
    const store = resetStoreForTests();
    await store.ensureProfile({ id: DEV_USER_ID });
    for (let index = 0; index < 60; index += 1) await store.charge(DEV_USER_ID, "formats");
    await expect(store.charge(DEV_USER_ID, "formats")).rejects.toBeInstanceOf(QuotaError);
    for (let index = 0; index < 120; index += 1) await store.charge(DEV_USER_ID, "previews");
    await expect(store.charge(DEV_USER_ID, "previews")).rejects.toMatchObject({ code: "usage_cap" });
  });

  it("gives a free account the check report only", async () => {
    const store = resetStoreForTests();
    await store.ensureProfile({ id: DEV_USER_ID });
    await store.updateProfile(DEV_USER_ID, { subscription_status: "canceled", plan: "free" });
    await expect(store.charge(DEV_USER_ID, "formats")).rejects.toMatchObject({ code: "usage_cap" });
    await expect(store.charge(DEV_USER_ID, "previews")).rejects.toMatchObject({ code: "usage_cap" });
    const view = await store.usage(DEV_USER_ID);
    expect(view.formats).toEqual({ used: 0, cap: 0, remaining: 0 });
    expect(view.previews).toEqual({ used: 0, cap: 0, remaining: 0 });
    expect(view.files.cap).toBe(5);
  });

  it("keeps the hourly check window after a new store reads the same file", async () => {
    const store = resetStoreForTests();
    await store.ensureProfile({ id: DEV_USER_ID });
    const start = new Date("2026-10-13T12:00:00.000Z");
    for (let index = 0; index < 30; index += 1) expect(await store.allowCheck(DEV_USER_ID, start)).toBe(true);
    expect(await store.allowCheck(DEV_USER_ID, start)).toBe(false);
    const restarted = new LocalStore();
    expect(await restarted.allowCheck(DEV_USER_ID, start)).toBe(false);
    expect(await restarted.allowCheck("", start)).toBe(false);
    const later = new Date(start.getTime() + 3_600_000);
    expect(await restarted.allowCheck(DEV_USER_ID, later)).toBe(true);
  });
});
