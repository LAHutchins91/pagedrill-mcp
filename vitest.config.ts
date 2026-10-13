import os from "node:os";
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    fileParallelism: false,
    hookTimeout: 120000,
    testTimeout: 120000,
    env: {
      NODE_ENV: "test",
      PAGEDRILL_DEV_AUTH: "1",
      PAGEDRILL_DEV_TOKEN: "dev-pagedrill",
      PAGEDRILL_SIGNING_SECRET: "test-signing-secret",
      PAGEDRILL_PURGE_SECRET: "test-purge-secret",
      PAGEDRILL_STORE: "local",
      PAGEDRILL_DATA_DIR: path.join(os.tmpdir(), "pagedrill-vitest"),
      APP_BASE_URL: "http://127.0.0.1:9"
    }
  }
});
