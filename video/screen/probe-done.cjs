// Dry run for baler-done.cjs: opens Schedule and the day, checks the stop and its Done button, clicks nothing real.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.resolve(__dirname, "../../dashboard/node_modules/@playwright/test"));
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));
const FARMER = process.env.FARMER || "संस्कार";
const DAY = process.env.DAY || "13";

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, isMobile: true, hasTouch: true, storageState: "D:/clearsky-video/screen/baler.state.json" });
  const page = await ctx.newPage();
  await page.goto(acc.base + "/baler/schedule", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const day = page.locator(`a[aria-label*="${DAY}"]`);
  console.log("day links:", await day.count(), (await day.first().getAttribute("aria-label")) ?? "");
  await day.first().click();
  await page.waitForTimeout(2500);
  console.log("url:", page.url());
  const stop = page.locator("li", { hasText: FARMER }).filter({ has: page.getByRole("button", { name: /Done/ }) });
  console.log("stops with Done:", await stop.count());
  if (await stop.count()) console.log("stop text:", (await stop.first().innerText()).replace(/\s+/g, " ").slice(0, 200));
  await browser.close();
})();
