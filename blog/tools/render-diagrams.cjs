// Render the blog diagrams with Excalidraw itself (hand-drawn style) in headless Chrome:
// skeleton -> convertToExcalidrawElements -> .excalidraw file + PNG (2x).
// Usage: node blog/tools/render-diagrams.cjs [name-filter]
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.resolve(__dirname, "../../dashboard/node_modules/@playwright/test"));
const diagrams = require("./diagrams.cjs");

const OUT_IMG = path.resolve(__dirname, "../img");
const OUT_SRC = path.resolve(__dirname, "../diagrams");
const VERSION = "0.18.0";

(async () => {
  fs.mkdirSync(OUT_IMG, { recursive: true });
  fs.mkdirSync(OUT_SRC, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  page.on("pageerror", (e) => console.error("pageerror:", String(e).slice(0, 300)));
  await page.goto("https://esm.sh/", { waitUntil: "domcontentloaded" });
  await page.addScriptTag({ content: `window.EXCALIDRAW_ASSET_PATH = "https://esm.sh/@excalidraw/excalidraw@${VERSION}/dist/prod/";` });
  await page.addScriptTag({
    type: "module",
    content: `import * as X from "https://esm.sh/@excalidraw/excalidraw@${VERSION}?bundle"; window.X = X; window.xReady = true;`,
  });
  await page.waitForFunction(() => window.xReady === true, null, { timeout: 120000 });

  const only = process.argv[2];
  for (const d of diagrams.filter((d) => !only || d.name.includes(only))) {
    const { elements, files } = d.build();
    const res = await page.evaluate(async ({ skeleton, files }) => {
      const X = window.X;
      // Excalidraw drops parts of embedded SVGs: rasterise every SVG icon to a 2x PNG first.
      for (const f of Object.values(files)) {
        if (f.mimeType !== "image/svg+xml") continue;
        const img = new Image();
        await new Promise((ok, bad) => { img.onload = ok; img.onerror = bad; img.src = f.dataURL; });
        const c = document.createElement("canvas");
        c.width = c.height = 224;
        c.getContext("2d").drawImage(img, 0, 0, 224, 224);
        f.dataURL = c.toDataURL("image/png");
        f.mimeType = "image/png";
      }
      const els = X.convertToExcalidrawElements(skeleton, { regenerateIds: false });
      const appState = { exportBackground: true, viewBackgroundColor: "#ffffff", exportWithDarkMode: false, exportScale: 2 };
      const blob = await X.exportToBlob({ elements: els, appState, files, mimeType: "image/png", exportPadding: 48 });
      const png = await new Promise((r) => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(blob); });
      return { els, png };
    }, { skeleton: elements, files });
    const scene = { type: "excalidraw", version: 2, source: "https://excalidraw.com", elements: res.els, appState: { viewBackgroundColor: "#ffffff", gridSize: null }, files };
    fs.writeFileSync(path.join(OUT_SRC, `${d.name}.excalidraw`), JSON.stringify(scene));
    fs.writeFileSync(path.join(OUT_IMG, `${d.name}.png`), Buffer.from(res.png.split(",")[1], "base64"));
    console.log(`${d.name}: ${res.els.length} elements -> img/${d.name}.png`);
  }
  await browser.close();
})();
