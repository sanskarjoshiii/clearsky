// Buyer (15 s slot): overview KPIs and incoming straw -> the delivery from the farmer's field -> demand and price.
// Read-only: nothing is saved (saving demand would re-match live bookings).
const fs = require("node:fs");
const path = require("node:path");
const { Recorder, take } = require("./rec.cjs");
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));
const STATE = "D:/clearsky-video/screen/buyer.state.json";

(async () => {
  const r = new Recorder("buyer");
  const page = await r.open(fs.existsSync(STATE) ? STATE : undefined);
  await page.goto(acc.base + "/buyer", { waitUntil: "networkidle" });
  if (page.url().includes("/login")) {
    await page.getByLabel("Email").fill(acc.buyer.email);
    await page.getByLabel("Password").fill(acc.buyer.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL((u) => u.pathname === "/buyer", { timeout: 30000 });
  }
  await page.getByText("Incoming straw by day").waitFor({ timeout: 30000 });
  await page.waitForTimeout(2000);
  const rail = (name) => page.getByRole("link", { name, exact: true }).first();

  r.mouse = { x: 1500, y: 860 }; // start below the chart, so no tooltip shows before the first move
  await r.start();
  await take(r, async () => {
    r.mark("overview");
    await r.hover(page.getByText("Booked to you", { exact: true }), { zoom: 1.45, move: 650 });
    await r.wait(500);
    await r.hover(page.getByText("Delivered", { exact: true }).first(), { zoom: 1.45, move: 500 });
    await r.wait(700);
    const bar = page.locator(".recharts-bar-rectangle").first();
    await r.hover(bar, { zoom: 1.3, move: 650, camOn: page.getByText("Incoming straw by day") });
    await r.wait(900);
    r.camOut(0.7);

    r.mark("deliveries");
    await r.click(rail("Deliveries"), { move: 650, after: 1000 });
    const row = page.locator("tr", { hasText: "Sangrur" }).first();
    await r.hover(row, { zoom: 1.5, move: 650, camOn: row });
    await r.wait(1200);
    await r.hover(page.getByRole("button", { name: /Export CSV/ }), { zoom: 1.5, move: 550 });
    await r.wait(500);
    r.camOut(0.7);

    r.mark("demand");
    await r.click(rail("Demand and price"), { move: 650, after: 1000 });
    const price = page.getByLabel(/Price per tonne/);
    await r.hover(price, { zoom: 1.4, move: 650, camOn: page.getByText("Current values") });
    await r.wait(700);
    await r.hover(page.getByText("Change history"), { zoom: 1.35, move: 650 });
    await r.wait(1300);
  });
})();
