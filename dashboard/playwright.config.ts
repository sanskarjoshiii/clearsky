import { defineConfig } from "@playwright/test";

/**
 * Smoke tests (PLAN.md Phase 7) against the local stack: backend dev server (mock DynamoDB + seed,
 * dev auth, WhatsApp simulator) + Vite. Uses the installed Google Chrome (no browser download).
 * `CLEARSKY_API_CMD` overrides how the backend is started (Windows without uv on PATH:
 *   $env:CLEARSKY_API_CMD = "python -m uv run python scripts/dev_server.py").
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    channel: "chrome",
    headless: true,
    viewport: { width: 1440, height: 950 },
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: process.env.CLEARSKY_API_CMD ?? "uv run python scripts/dev_server.py",
      cwd: "../backend",
      url: "http://127.0.0.1:8787/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true, timeout: 60_000 },
  ],
});
