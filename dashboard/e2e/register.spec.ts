import { expect, test } from "@playwright/test";

/** Self-registration (dev auth): apply as a baler → the admin approves → the applicant lands on the baler app. */
test("a new baler registers, the admin approves, and the baler reaches their own app", async ({ page, browser }) => {
  const tag = Date.now().toString().slice(-6);
  const org = `E2E Hiring Centre ${tag}`;

  const email = `asha${tag}@example.test`;

  await page.goto("/baler/login");
  await page.getByRole("link", { name: "Create an account" }).click();
  await expect(page).toHaveURL(/\/register\?role=operator$/);
  await expect(page.getByRole("radio", { name: /Baler operator/ })).toBeChecked(); // came from the baler page
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("clearsky-dev");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.getByLabel(/Your name/).fill("Asha Kaur");
  await page.getByLabel(/Mobile number/).fill(`+919812${tag}`);
  await page.getByLabel(/Custom hiring centre/).fill(org);
  await page.getByLabel("Village", { exact: true }).fill("bhavanigarh"); // fuzzy: a common misspelling
  await page.getByRole("button", { name: /Bhawanigarh/ }).click();
  await page.getByLabel(/Acres per day/).fill("18");
  await page.getByLabel(/Working radius/).fill("20");
  await page.getByRole("button", { name: /Send for approval/ }).click();

  await expect(page).toHaveURL(/\/pending$/);
  await expect(page.getByRole("heading", { name: "Under review" })).toBeVisible();
  // not approved yet: every role app sends them back to the waiting page
  await page.goto("/baler");
  await expect(page).toHaveURL(/\/pending$/);
  await page.goto("/admin/approvals");
  await expect(page).toHaveURL(/\/pending$/);

  // the admin, in another browser session
  const adminContext = await browser.newContext({ baseURL: "http://localhost:5173", viewport: { width: 1440, height: 950 } });
  const admin = await adminContext.newPage();
  await admin.goto("/admin?as=officer.Sangrur");
  await expect(admin.getByRole("link", { name: /Approvals \(\d+\)/ }).first()).toBeVisible(); // "N pending" badge
  await admin.getByRole("link", { name: /Approvals/ }).first().click();
  await admin.getByText(org).click();
  const drawer = admin.getByLabel("Application detail");
  await expect(drawer.getByText("Asha Kaur")).toBeVisible();
  await drawer.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(admin.getByText(/^Approved: /)).toBeVisible();
  await adminContext.close();

  // the waiting page notices by itself and opens the baler app
  await expect(page).toHaveURL(/\/baler$/, { timeout: 20_000 });
  await expect(page.getByText("Asha Kaur")).toBeVisible();
  await expect(page.getByText("Today's stops")).toBeVisible();

  // later: the same email signs in on the baler page, and only there
  await page.getByRole("link", { name: /Profile/ }).first().click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/baler\/login$/);
  await page.goto("/buyer/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("clearsky-dev");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Wrong email or password.")).toBeVisible();
  await page.goto("/baler/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("clearsky-dev");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/baler$/);
  await expect(page.getByText("Asha Kaur")).toBeVisible();
});

test("a rejected applicant sees the reason and can edit and resubmit", async ({ page, request }) => {
  const tag = Date.now().toString().slice(-6);
  const org = `E2E Biofuels ${tag}`;
  await page.goto(`/register?as=pending.e2e${tag}`);
  await page.getByRole("radio", { name: /Industry buyer/ }).click();
  await page.getByLabel(/Your name/).fill("Ravi Mehta");
  await page.getByLabel(/Mobile number/).fill(`+919813${tag}`);
  await page.getByLabel(/Company/).fill(org);
  await page.getByLabel("Village", { exact: true }).fill("Sunam");
  await page.getByRole("button", { name: /Sunam/ }).first().click();
  await page.getByLabel(/Price/).fill("1700");
  await page.getByLabel(/Season demand/).fill("400");
  await page.getByLabel(/Collection radius/).fill("40");
  await page.getByRole("button", { name: /Send for approval/ }).click();
  await expect(page.getByRole("heading", { name: "Under review" })).toBeVisible();

  const officer = { Authorization: "Bearer dev.officer.Sangrur" };
  const list = (await (await request.get("http://127.0.0.1:8787/api/applications?status=pending", { headers: officer })).json()) as {
    applications: { application_id: string; org_name: string }[];
  };
  const mine = list.applications.find((a) => a.org_name === org);
  expect(mine).toBeTruthy();
  const res = await request.post(`http://127.0.0.1:8787/api/applications/${mine!.application_id}/reject`, {
    headers: officer,
    data: { reason: "Plant licence number missing" },
  });
  expect(res.ok()).toBeTruthy();

  await expect(page.getByRole("heading", { name: "Not approved" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Reason: Plant licence number missing")).toBeVisible();
  await page.getByRole("link", { name: "Edit and resubmit" }).click();
  await expect(page.getByLabel(/Company/)).toHaveValue(org); // pre-filled from the rejected application
  await page.getByRole("button", { name: /Send for approval/ }).click();
  await expect(page.getByRole("heading", { name: "Under review" })).toBeVisible();
});
