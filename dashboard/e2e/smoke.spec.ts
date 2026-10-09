import { expect, test, type APIRequestContext } from "@playwright/test";

const API = "http://127.0.0.1:8787";
const OFFICER = { Authorization: "Bearer dev.officer.Sangrur" };

async function bookViaWhatsApp(request: APIRequestContext, phone: string, text: string) {
  const res = await request.post(`${API}/api/sim/message`, { headers: OFFICER, data: { phone, text } });
  expect(res.ok()).toBeTruthy();
  return (await res.json()) as { sent: string[] };
}

test("officer signs in, sees the radar map and alerts a village", async ({ page }) => {
  await page.goto("/login");
  const officerRow = page.locator("div", { hasText: "District officer" }).filter({ has: page.getByRole("button", { name: "Enter" }) }).last();
  await officerRow.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByRole("heading", { name: "Burn Risk Radar" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Map" }).locator("canvas")).toBeVisible();
  await expect(page.getByText("Villages by risk")).toBeVisible();

  await page.getByRole("button", { name: /^Alert / }).first().click();
  await page.getByRole("button", { name: "Send WhatsApp offer" }).click();
  await expect(page.getByText(/Offer sent to \d+ farmer|Already alerted/)).toBeVisible();
});

test("farmer books in the WhatsApp simulator", async ({ page }) => {
  const phone = `+9199999${String(Date.now()).slice(-5)}`;
  await page.goto("/admin?as=officer.Sangrur&sim=1");
  const panel = page.locator("aside").filter({ hasText: "Farmer on WhatsApp" });
  await expect(panel).toBeVisible();
  await panel.getByLabel("Farmer phone number").fill(phone);
  await panel.getByLabel("Farmer message").fill("Naam Simran, Bhawanigarh, 6 acre, 24 tareekh");
  await panel.getByRole("button", { name: "Send" }).click();
  // the request goes to a baler first; the ✅ confirmation comes when the baler accepts
  await expect(panel.getByText(/📨 Simran ji, 6 acre ke khet ki request/)).toBeVisible();
});

test("baler accepts the request, sees the stop on the route and marks it done", async ({ page, request }) => {
  const phone = `+9199998${String(Date.now()).slice(-5)}`;
  // unique, letters-only surname so reruns against the same dev server never collide
  const surname = "Q" + String(Date.now()).slice(-6).replace(/\d/g, (d) => "abcdefghij"[Number(d)] ?? "x");
  const farmer = `Jaspal ${surname}`;
  const { sent } = await bookViaWhatsApp(request, phone, `Naam ${farmer}, Sunam, 4 acre, kal`);
  expect(sent[0]).toContain("📨");
  const bookings = (await (await request.get(`${API}/api/bookings`, { headers: OFFICER })).json()) as {
    bookings: { farmer_name: string; baler_id: string; date: string; status: string }[];
  };
  const mine = bookings.bookings.find((b) => b.farmer_name === farmer && b.status === "OFFERED");
  expect(mine).toBeTruthy();

  // the baler answers the request
  await page.goto(`/baler/requests?as=operator.${mine!.baler_id}`);
  const card = page.locator("li", { hasText: farmer });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: /Accept/ }).click();
  await expect(page.getByText(/^Accepted\./)).toBeVisible();
  await expect(card).toHaveCount(0);

  // now it is a stop on the route for that day
  await page.goto(`/baler?date=${mine!.date}`);
  await expect(page.getByText("Today's stops")).toBeVisible();
  const stop = page.locator("li", { hasText: farmer });
  await expect(stop).toBeVisible();
  await stop.getByRole("button", { name: /Done/ }).click();
  await page.getByRole("button", { name: "Yes, field cleared" }).click();
  await expect(stop.getByText(/Field cleared/)).toBeVisible();
});
