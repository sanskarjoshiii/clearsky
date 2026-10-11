// Baler part B (after Accept): Schedule -> that day's route -> Done -> confirm. REAL action on the live site:
// the farmer is told on WhatsApp that the field is cleared, and the buyer receives the straw.
const fs = require("node:fs");
const path = require("node:path");
const { Recorder, take } = require("./rec.cjs");
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));
const STATE = "D:/clearsky-video/screen/baler.state.json";
const FARMER = process.env.FARMER || "संस्कार";
const DAY = process.env.DAY || "13";

(async () => {
  const r = new Recorder("baler-b", { mobile: true });
  const page = await r.open(fs.existsSync(STATE) ? STATE : undefined);
  await page.goto(acc.base + "/baler/requests", { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const tab = (name) => page.locator("nav[aria-label=Baler] a:visible", { hasText: name }).first();

  await r.start();
  await take(r, async () => {
    r.mark("route");
    await r.wait(500);
    await r.click(tab("Schedule"), { zoom: 1.2, move: 650, after: 1000 });
    r.camOut(0.6);
    const day = page.locator(`a[aria-label*="${DAY}"]`).first();
    await r.click(day, { zoom: 1.3, move: 600, after: 1300, camOn: day });
    r.camOut(0.7);
    const stop = page.locator("li", { hasText: FARMER }).filter({ has: page.getByRole("button", { name: /Done/ }) }).first();
    await r.hover(stop, { zoom: 1.3, move: 550, camOn: stop });
    await r.wait(700);

    r.mark("done");
    await r.click(stop.getByRole("button", { name: /Done/ }), { zoom: 1.45, move: 500, after: 500 });
    await r.click(page.getByRole("button", { name: "Yes, field cleared" }), { zoom: 1.4, move: 500, after: 300 });
    await page.locator("li", { hasText: FARMER }).getByText(/Field cleared/).first().waitFor({ timeout: 25000 }).catch(() => console.log("note: 'Field cleared' not seen in 25 s"));
    await r.hover(page.locator("li", { hasText: FARMER }).first(), { zoom: 1.3, move: 400 });
    await r.wait(1800);
  });
})();
