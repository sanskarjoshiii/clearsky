// Super admin (15 s slot): Burn Risk Radar -> village alert (opened, then cancelled: nothing is sent)
// -> Bookings: the farmer's WhatsApp booking -> Approvals.
const fs = require("node:fs");
const path = require("node:path");
const { Recorder } = require("./rec.cjs");
const acc = JSON.parse(fs.readFileSync(path.join(__dirname, "accounts.local.json"), "utf8"));
const STATE = "D:/clearsky-video/screen/officer.state.json";
const FARMER = process.env.FARMER || "संस्कार";

(async () => {
  const r = new Recorder("admin");
  const page = await r.open(fs.existsSync(STATE) ? STATE : undefined);
  await page.goto(acc.base + "/admin", { waitUntil: "networkidle" });
  if (page.url().includes("/login")) {
    await page.getByLabel("Email").fill(acc.officer.email);
    await page.getByLabel("Password").fill(acc.officer.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL((u) => u.pathname === "/admin", { timeout: 30000 });
  }
  await page.locator(".maplibregl-canvas").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(2500);
  const rail = (name) => page.getByRole("link", { name, exact: true }).first();

  await r.start();
  r.mark("radar");
  await r.hover(page.getByText("Acres booked", { exact: true }), { zoom: 1.4, move: 650 });
  await r.wait(350);
  await r.hover(page.getByText("Straw routed", { exact: true }), { zoom: 1.4, move: 700 });
  await r.wait(500);
  await r.hover(page.locator(".maplibregl-canvas").first(), { zoom: 1.2, move: 600 });
  await r.wait(400);

  r.mark("alert");
  const village = page.getByRole("button", { name: /^Alert / }).first();
  await r.click(village, { zoom: 1.35, move: 700, after: 500 });
  const dialog = page.getByRole("dialog");
  await r.hover(dialog.getByRole("button", { name: "Send WhatsApp offer" }), { zoom: 1.5, move: 500, camOn: dialog });
  await r.wait(900);
  await r.click(dialog.getByRole("button", { name: "Cancel" }), { move: 450, after: 250 }); // demo only: nothing is sent
  r.camOut(0.7);

  r.mark("bookings");
  await r.click(rail("Bookings"), { move: 650, after: 700 });
  await r.click(page.getByRole("tab", { name: "All", exact: true }), { zoom: 1.3, move: 600, after: 900 });
  const row = page.locator("tr", { hasText: FARMER }).filter({ hasText: /Offered|Confirmed/ }).first();
  await r.hover(row, { zoom: 1.45, move: 700, camOn: row });
  await r.wait(1300);
  r.camOut(0.7);

  r.mark("approvals");
  await r.click(rail("Approvals"), { move: 650, after: 700 });
  await r.click(page.getByRole("tab", { name: "Approved", exact: true }), { zoom: 1.3, move: 550, after: 400 });
  await page.getByText("Nothing waiting for you").waitFor({ state: "detached", timeout: 8000 }).catch(() => {});
  await r.wait(1700);
  await r.stop();
})();
