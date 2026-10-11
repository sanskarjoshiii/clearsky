// Baler (15 s slot, phone): the farmer's request -> Accept (farmer gets a WhatsApp confirmation)
// -> Schedule -> that day's route -> Done (farmer is told the field is cleared, buyer receives the straw).
// These are REAL actions on the live site.
const fs = require("node:fs");
const path = require("node:path");
const { Recorder } = require("./rec.cjs");
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));
const STATE = "D:/clearsky-video/screen/baler.state.json";
const FARMER = process.env.FARMER || "संस्कार";

(async () => {
  const r = new Recorder("baler", { mobile: true });
  const page = await r.open(fs.existsSync(STATE) ? STATE : undefined);
  await page.goto(acc.base + "/baler", { waitUntil: "networkidle" });
  if (page.url().includes("/login")) {
    await page.getByLabel("Email").fill(acc.baler.email);
    await page.getByLabel("Password").fill(acc.baler.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL((u) => u.pathname === "/baler", { timeout: 30000 });
  }
  await page.waitForTimeout(2500);
  const tab = (name) => page.locator("nav[aria-label=Baler] a:visible", { hasText: name }).first();

  await r.start();
  r.mark("requests");
  await r.wait(500);
  await r.click(tab("Requests"), { zoom: 1.25, move: 650, after: 900 });
  const card = page.locator(`li[aria-label="Request from ${FARMER}"]`).first();
  await r.hover(card, { zoom: 1.3, move: 600, camOn: card });
  await r.wait(1100);

  r.mark("accept");
  await r.click(card.getByRole("button", { name: /Accept/ }), { zoom: 1.45, move: 600, after: 300 });
  await page.getByText(/Accepted\./).waitFor({ timeout: 15000 });
  await r.hover(page.getByText(/Accepted\./), { zoom: 1.4, move: 450 });
  await r.wait(1300);
  r.camOut(0.7);

  r.mark("route");
  await r.click(tab("Schedule"), { move: 600, after: 900 });
  const day = page.locator('a[aria-label*="13"]').first();
  await r.click(day, { zoom: 1.25, move: 600, after: 1200 });
  r.camOut(0.7);
  const stop = page.locator("li", { hasText: FARMER }).filter({ has: page.getByRole("button", { name: /Done/ }) }).first();
  await r.hover(stop, { zoom: 1.25, move: 550, camOn: stop });
  await r.wait(600);

  r.mark("done");
  await r.click(stop.getByRole("button", { name: /Done/ }), { zoom: 1.4, move: 500, after: 500 });
  await r.click(page.getByRole("button", { name: "Yes, field cleared" }), { zoom: 1.35, move: 500, after: 300 });
  await stop.getByText(/Field cleared/).waitFor({ timeout: 15000 }).catch(() => {});
  await r.hover(page.locator("li", { hasText: FARMER }).first(), { zoom: 1.3, move: 400 });
  await r.wait(1500);
  await r.stop();
})();
