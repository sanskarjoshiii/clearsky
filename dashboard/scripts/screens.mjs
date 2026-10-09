// Dev helper: capture the main screens (desktop + phone) from the local stack into a folder.
// Usage: node scripts/screens.mjs <outDir>
import { chromium } from "@playwright/test";

const out = process.argv[2] ?? "screens";
const shots = [
  { name: "radar", path: "/admin?as=officer.Sangrur&sim=1", w: 1440, h: 1000 },
  { name: "fields", path: "/admin/fields?as=officer.Sangrur", w: 1440, h: 900 },
  { name: "buyer", path: "/buyer?as=buyer.BY03", w: 1440, h: 1000 },
  { name: "operator-phone", path: "/baler?as=operator.B01", w: 390, h: 844, next: true },
  { name: "impact", path: "/impact", w: 1440, h: 900 },
];
const browser = await chromium.launch({ channel: "chrome", headless: true });
for (const s of shots) {
  const page = await browser.newPage({ viewport: { width: s.w, height: s.h } });
  await page.goto(`http://localhost:5173${s.path}`);
  await page.waitForLoadState("networkidle").catch(() => undefined);
  if (s.next) {
    const btn = page.getByRole("button", { name: /Next stops/ });
    if (await btn.isVisible().catch(() => false)) await btn.click();
  }
  await page.waitForTimeout(3500);
  await page.screenshot({ path: `${out}/${s.name}.png` });
  await page.close();
  console.log(`${s.name} ✓`);
}
await browser.close();
