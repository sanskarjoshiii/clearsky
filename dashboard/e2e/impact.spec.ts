import { expect, test } from "@playwright/test";

const API = "http://127.0.0.1:8787";
const OFFICER = { Authorization: "Bearer dev.officer.Sangrur" };

interface Stats {
  impact_configured: boolean;
  impact: Record<string, { kg: number; label: string }>;
}

/**
 * Issue #5: marking a field Done raises the public impact totals.
 *
 * clearsky ships with NO emission factors (the team must configure sourced values), so this test
 * only runs against a backend started with EMISSION_FACTORS set. playwright.config.ts starts its
 * own backend with clearly labelled TEST values; against any other server the test is skipped.
 */
test("marking a field Done increases the pollution-avoided total on /impact", async ({ page, request }) => {
  const before = (await (await request.get(`${API}/api/stats`)).json()) as Stats;
  test.skip(!before.impact_configured, "EMISSION_FACTORS is not configured on this backend");
  const key = Object.keys(before.impact)[0] ?? "pm25";
  const kgBefore = before.impact[key]?.kg ?? 0;

  // farmer books, the baler accepts and clears the field (through the API; the UI flow has its own tests)
  const phone = `+9199996${String(Date.now()).slice(-5)}`;
  const surname = "Y" + String(Date.now()).slice(-6).replace(/\d/g, (d) => "abcdefghij"[Number(d)] ?? "x");
  const farmer = `Deep ${surname}`;
  await request.post(`${API}/api/sim/message`, { headers: OFFICER, data: { phone, text: `Naam ${farmer}, Sunam, 6 acre, kal` } });
  const rows = ((await (await request.get(`${API}/api/bookings`, { headers: OFFICER })).json()) as {
    bookings: { booking_id: string; farmer_name: string; baler_id: string; status: string }[];
  }).bookings;
  const mine = rows.find((b) => b.farmer_name === farmer && b.status === "OFFERED");
  expect(mine).toBeTruthy();
  const baler = { Authorization: `Bearer dev.operator.${mine!.baler_id}` };
  expect((await request.post(`${API}/api/bookings/${mine!.booking_id}/accept`, { headers: baler })).ok()).toBeTruthy();
  const done = await request.post(`${API}/api/bookings/${mine!.booking_id}/done`, { headers: baler });
  expect(done.ok()).toBeTruthy();

  const after = (await (await request.get(`${API}/api/stats`)).json()) as Stats;
  expect(after.impact[key]!.kg).toBeGreaterThan(kgBefore);

  // the public page (no sign-in) shows the total, the table and where the numbers come from
  await page.goto("/impact");
  const label = after.impact[key]!.label;
  await expect(page.getByText(new RegExp(`${label.replace(".", "\\.")} avoided \\(.*estimate\\)`)).first()).toBeVisible();
  await expect(page.getByText("Pollution avoided, field by field (estimate)")).toBeVisible();
  await expect(page.getByRole("region", { name: "Methodology" })).toContainText("estimates, not measurements");
  await page.getByRole("button", { name: /Sunam: show \d+ cleared field/ }).click();
  await expect(page.getByText(`Deep ${surname[0]}.`)).toBeVisible(); // masked name on the public page
  await expect(page.getByText(farmer)).toHaveCount(0);
  await expect(page.getByText(phone)).toHaveCount(0);
});
