// Dry run for baler.cjs: checks the locators on the live baler app without clicking anything.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.resolve(__dirname, "../../dashboard/node_modules/@playwright/test"));
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));
const FARMER = process.env.FARMER || "संस्कार";

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, isMobile: true, hasTouch: true, storageState: "D:/clearsky-video/screen/baler.state.json" });
  const page = await ctx.newPage();
  await page.goto(acc.base + "/baler/requests", { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  console.log("url:", page.url());
  console.log("Requests tab visible:", await page.locator("nav[aria-label=Baler] a:visible", { hasText: "Requests" }).count());
  const card = page.locator(`li[aria-label="Request from ${FARMER}"]`);
  console.log("request cards:", await card.count(), "accept buttons:", await card.getByRole("button", { name: /Accept/ }).count());
  if (await card.count()) console.log("card text:", (await card.first().innerText()).replace(/\s+/g, " ").slice(0, 240));
  await page.screenshot({ path: "D:/clearsky-video/stills/baler-probe.png" });
  await browser.close();
})();
