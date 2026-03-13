import { defineConfig, devices } from "@playwright/test";

/**
 * Q&Ace — Playwright E2E configuration.
 *
 * Tests the full user journey:
 *   Landing page → Session page → WebRTC connection → UI state transitions.
 *
 * Prerequisites:
 *   1. Backend running: cd server && ..\.venv311\Scripts\python.exe -m uvicorn app.main:app --port 8000
 *   2. Frontend running: cd client && npm run dev (port 3000)
 *
 * Run:
 *   cd client && npx playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    // Grant mic/camera permissions so WebRTC getUserMedia doesn't prompt
    permissions: ["microphone", "camera"],
    // Use fake media devices so tests work in headless CI
    launchOptions: {
      args: [
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
        "--allow-file-access",
      ],
    },
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Don't auto-start webServer — user controls backend + frontend separately
});
