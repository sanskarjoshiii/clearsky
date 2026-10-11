// Render the blog cover (1600x840, 2x) from cover.html with headless Chrome.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.resolve(__dirname, "../../dashboard/node_modules/@playwright/test"));

const dataUrl = (p, mime) => `data:${mime};base64,${fs.readFileSync(p).toString("base64")}`;

(async () => {
  const html = fs.readFileSync(path.join(__dirname, "cover.html"), "utf8")
    .replace("COVER_SRC", dataUrl(process.env.COVER_SRC || "D:/clearsky-blog/cover-src.jpg", "image/jpeg"))
    .replace("LOGO_SRC", dataUrl(path.resolve(__dirname, "../../dashboard/public/logo.png"), "image/png"));
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 1600, height: 840 }, deviceScaleFactor: 2 });
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.locator("#cover").screenshot({ path: path.resolve(__dirname, "../img/cover.png") });
  await browser.close();
  console.log("img/cover.png");
})();
