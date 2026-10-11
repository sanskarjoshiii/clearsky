// Look at the live buyer app (read-only) to plan the buyer video.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.resolve(__dirname, "../../dashboard/node_modules/@playwright/test"));
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, storageState: "D:/clearsky-video/screen/buyer.state.json" });
  const page = await ctx.newPage();
  await page.goto(acc.base + "/buyer", { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);
  const links = await page.locator("nav a, aside a").evaluateAll((as) => as.map((a) => `${a.getAttribute("aria-label") || a.textContent.trim()} -> ${a.getAttribute("href")}`));
  console.log("nav:", links.join(" | "));
  for (const [name, p] of [["overview", "/buyer"], ["deliveries", "/buyer/deliveries"], ["demand", "/buyer/demand"]]) {
    await page.goto(acc.base + p, { waitUntil: "networkidle" });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `D:/clearsky-video/stills/live-buyer-${name}.png` });
    console.log(name, ":", (await page.locator("main, body").first().innerText()).replace(/\s+/g, " ").slice(0, 260));
  }
  await browser.close();
})();
