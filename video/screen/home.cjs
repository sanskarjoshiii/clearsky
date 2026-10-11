// Home page (10 s slot): hero film -> live field data -> who it's for carousel.
const { Recorder } = require("./rec.cjs");
const BASE = process.env.BASE_URL || "https://clearsky.akkki.tech";

(async () => {
  const r = new Recorder("home");
  const page = await r.open();
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.waitForFunction(() => { const v = document.querySelector("video"); return v && v.readyState >= 3 && !v.paused; }, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  const top = async (sel) => page.evaluate((s) => document.querySelector(s).getBoundingClientRect().top, sel);

  await r.start();
  r.mark("hero");
  r.cam(960, 640, 1.06, 1.8); // slow push-in on the film and title
  await r.wait(1500);

  r.mark("field data");
  await r.click(page.getByRole("link", { name: "Field data" }), { zoom: 1.4, move: 700, after: 150 });
  r.camOut(0.8);
  await r.wait(900); // anchor glide (Lenis); box() waits for it to settle
  await r.hover(page.getByText("Acres this season"), { zoom: 1.45, move: 600 });
  await r.wait(700);
  await r.hover(page.getByText("Straw routed to industry"), { zoom: 1.45, move: 800 });
  await r.wait(600);
  r.camOut(0.8);

  r.mark("who");
  await r.moveTo(1420, 760, 400);
  await r.wheel((await top("#who")) - 40, 1350);
  await r.click(page.getByRole("button", { name: "Next" }), { zoom: 1.3, move: 650, after: 200, camOn: page.locator("#who [aria-live=polite]") });
  await r.wait(1300);
  await r.stop();
})();
