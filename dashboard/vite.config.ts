/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Local dev: the backend dev server (backend/scripts/dev_server.py) listens on 127.0.0.1:8787.
// Vite proxies /api and /health to it, so the browser talks to one origin and no CORS is needed.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8787",
      "/health": "http://127.0.0.1:8787",
    },
  },
  build: {
    chunkSizeWarningLimit: 1600,
    rolldownOptions: {
      output: {
        // Prioritised groups: React must win over "charts", otherwise it is pulled into the charts
        // chunk as a dependency of recharts and every role downloads the charts just to get React.
        codeSplitting: {
          groups: [
            { name: "react", test: /node_modules[\/](react|react-dom|scheduler|react-router|@tanstack)[\/]/, priority: 30 },
            { name: "maplibre", test: /maplibre-gl/, priority: 20 },
            { name: "amplify", test: /aws-amplify|@aws-amplify/, priority: 20 },
            { name: "charts", test: /node_modules[\/](recharts|d3-[^\/]+|victory-vendor)[\/]/, priority: 10 },
          ],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"], // e2e/*.spec.ts belong to Playwright

    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
