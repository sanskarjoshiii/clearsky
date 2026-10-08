// Dev diagnostic: open a page in system Chrome, wait for the map, print its state, save a screenshot.
// Usage: node scripts/inspect-map.mjs "/officer?as=officer.Sangrur" out.png
import { chromium } from "@playwright/test";

const [path = "/officer?as=officer.Sangrur", out = "map.png"] = process.argv.slice(2);
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const logs = [];
page.on("console", (m) => logs.push(`${m.type()}: ${m.text()}`));
page.on("pageerror", (e) => logs.push(`pageerror: ${e.message}`));
await page.goto(`http://localhost:5173${path}`);
await page.waitForFunction(() => !!window.__clearskyMap, null, { timeout: 30000 }).catch(() => logs.push("no map instance"));
await page.waitForTimeout(4000);
const state = await page.evaluate(() => {
  const m = window.__clearskyMap;
  if (!m) return null;
  const src = (id) => m.getSource(id);
  return {
    loaded: m.loaded(),
    styleLoaded: m.isStyleLoaded(),
    layers: m.getStyle().layers.slice(-6).map((l) => `${l.id}:${l.layout?.visibility ?? "visible"}`),
    fieldsRendered: m.queryRenderedFeatures({ layers: ["fields"] }).length,
    villagesRendered: m.queryRenderedFeatures({ layers: ["villages"] }).length,
    fieldsSource: src("fields") ? "yes" : "no",
    zoom: m.getZoom(),
    center: m.getCenter(),
  };
});
console.log(JSON.stringify(state, null, 2));
console.log(logs.filter((l) => !l.includes("[vite]") && !l.includes("React DevTools")).join("\n"));
await page.screenshot({ path: out });
await browser.close();
