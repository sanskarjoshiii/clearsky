import { expect, test, type APIRequestContext } from "@playwright/test";

const API = "http://127.0.0.1:8787";
const OFFICER = { Authorization: "Bearer dev.officer.Sangrur" };

interface Row {
  booking_id: string;
  farmer_name: string;
  baler_id: string;
  date: string;
  status: string;
  attempt?: number;
}

async function bookingsOf(request: APIRequestContext, farmer: string): Promise<Row[]> {
  const res = await request.get(`${API}/api/bookings`, { headers: OFFICER });
  return ((await res.json()) as { bookings: Row[] }).bookings.filter((b) => b.farmer_name === farmer);
}

/** Issue #3: farmer books → the first baler declines → the second baler accepts → the farmer sees the confirmation. */
test("a declined request goes to the next baler, and the farmer is confirmed when that baler accepts", async ({ page, request }) => {
  const phone = `+9199997${String(Date.now()).slice(-5)}`;
  const surname = "Z" + String(Date.now()).slice(-6).replace(/\d/g, (d) => "abcdefghij"[Number(d)] ?? "x");
  const farmer = `Karan ${surname}`;
  const sent = (await (
    await request.post(`${API}/api/sim/message`, { headers: OFFICER, data: { phone, text: `Naam ${farmer}, Sunam, 5 acre, kal` } })
  ).json()) as { sent: string[] };
  expect(sent.sent[0]).toContain("📨"); // request sent, not confirmed

  const first = (await bookingsOf(request, farmer)).find((b) => b.status === "OFFERED");
  expect(first).toBeTruthy();

  // baler 1 declines with a reason
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/baler/requests?as=operator.${first!.baler_id}`);
  const card = page.locator("li", { hasText: farmer });
  await expect(card).toBeVisible();
  await expect(card.getByTitle("Time left to answer")).toContainText(/min/);
  await card.getByRole("button", { name: /Decline/ }).click();
  await card.getByRole("radio", { name: "Too far" }).click();
  await card.getByRole("button", { name: "Confirm decline" }).click();
  await expect(page.getByText("Declined. The field goes to another baler.")).toBeVisible();
  await expect(card).toHaveCount(0);

  // the matcher offered it to a different baler; baler 1 never gets it again
  const rows = await bookingsOf(request, farmer);
  expect(rows.find((b) => b.booking_id === first!.booking_id)?.status).toBe("DECLINED");
  const second = rows.find((b) => b.status === "OFFERED");
  expect(second).toBeTruthy();
  expect(second!.baler_id).not.toBe(first!.baler_id);
  expect(second!.attempt).toBe(2);

  // baler 2 accepts
  await page.goto(`/baler/requests?as=operator.${second!.baler_id}`);
  const card2 = page.locator("li", { hasText: farmer });
  await expect(card2).toBeVisible();
  await card2.getByRole("button", { name: /Accept/ }).click();
  await expect(page.getByText(/^Accepted\./)).toBeVisible();

  // the farmer's WhatsApp (the admin's simulator panel) shows the confirmation
  await page.setViewportSize({ width: 1440, height: 950 });
  await page.goto("/admin?as=officer.Sangrur&sim=1");
  const panel = page.locator("aside").filter({ hasText: "Farmer on WhatsApp" });
  await panel.getByLabel("Farmer phone number").fill(phone);
  await expect(panel.getByText(new RegExp(`✅ ${farmer} ji, .* ko baler .* aapka khet saaf karne aayega`))).toBeVisible();

  // the admin sees the timeline: declined by one baler, confirmed with the next
  await page.goto("/admin/bookings");
  await page.getByRole("tab", { name: "All", exact: true }).click();
  await page.getByRole("tab", { name: "With declined / expired" }).click();
  const mine = page.locator("tr", { hasText: farmer });
  await expect(mine).toHaveCount(2);
  await expect(mine.filter({ hasText: "Declined" })).toContainText("too far");
  await expect(mine.filter({ hasText: "Confirmed" })).toHaveCount(1);
});
