import { expect, test, type Page } from "@playwright/test";

/** Each role has its own app: it reaches every page of it and is turned away from the other two. */

async function blockedFrom(page: Page, path: string, home: RegExp, notice: string) {
  await page.goto(path);
  await expect(page).toHaveURL(home);
  await expect(page.getByText(notice)).toBeVisible();
}

test("admin reaches every admin page and is kept out of the baler and buyer apps", async ({ page }) => {
  await page.goto("/admin?as=officer.Sangrur");
  await expect(page.getByRole("heading", { name: "Burn Risk Radar" })).toBeVisible();
  const rail = page.getByRole("navigation", { name: "Admin" }).first();
  for (const [link, heading] of [
    ["Fields", "Fields"],
    ["Bookings", "Bookings"],
    ["Balers", "Balers"],
    ["Buyers", "Buyers"],
    ["Demo controls", "Demo controls"],
  ] as const) {
    await rail.getByRole("link", { name: link, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
  }
  await expect(rail.getByRole("link", { name: /Today|Deliveries/ })).toHaveCount(0);
  await page.goto("/admin/nope");
  await expect(page.getByText("Page not found")).toBeVisible();
  await expect(rail).toBeVisible(); // the 404 stays inside the admin layout

  await blockedFrom(page, "/baler/schedule", /\/admin$/, "That page is for balers.");
  await blockedFrom(page, "/buyer/demand", /\/admin$/, "That page is for buyers.");
});

test("baler reaches every baler page on a phone and is kept out of the other apps", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/baler?as=operator.B01");
  await expect(page.getByText("Today's stops")).toBeVisible();
  const tabs = page.getByRole("navigation", { name: "Baler" }).last();
  await tabs.getByRole("link", { name: /Requests/ }).click();
  await expect(page.getByRole("heading", { name: /Requests/ })).toBeVisible();
  await tabs.getByRole("link", { name: /Schedule/ }).click();
  await expect(page.getByRole("heading", { name: /Next 14 days/ })).toBeVisible();
  await tabs.getByRole("link", { name: /History/ }).click();
  await expect(page.getByRole("heading", { name: /Cleared fields/ })).toBeVisible();
  await tabs.getByRole("link", { name: /Profile/ }).click();
  await expect(page.getByRole("heading", { name: /Profile/ })).toBeVisible();
  await expect(page.getByText("Acres per day")).toBeVisible();

  // one-handed: tabs are at least 44 px tall and nothing scrolls sideways
  const box = await tabs.getByRole("link", { name: /Today/ }).boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(44);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await blockedFrom(page, "/admin/fields", /\/baler$/, "That page is for admins.");
  await blockedFrom(page, "/buyer", /\/baler$/, "That page is for buyers.");
});

test("buyer reaches every buyer page and is kept out of the other apps", async ({ page }) => {
  await page.goto("/buyer?as=buyer.BY03");
  await expect(page.getByText("Incoming straw by day")).toBeVisible();
  const rail = page.getByRole("navigation", { name: "Buyer" }).first();
  await rail.getByRole("link", { name: "Deliveries" }).click();
  await expect(page.getByRole("heading", { name: "Deliveries", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export CSV" })).toBeVisible();
  await rail.getByRole("link", { name: "Demand and price" }).click();
  await expect(page.getByText("Change history")).toBeVisible();
  await rail.getByRole("link", { name: "Profile" }).click();
  await expect(page.getByRole("heading", { name: "Profile", level: 1 })).toBeVisible();

  await blockedFrom(page, "/admin", /\/buyer$/, "That page is for admins.");
  await blockedFrom(page, "/baler/profile", /\/buyer$/, "That page is for balers.");
});

test("a signed-out deep link returns to the requested page after login", async ({ page }) => {
  await page.goto("/baler/schedule");
  await expect(page).toHaveURL(/\/baler\/login$/); // the baler app's own sign-in page
  await page.getByLabel("Email").fill("b01@clearsky.local");
  await page.getByLabel("Password").fill("clearsky-dev");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/baler\/schedule$/);
  await expect(page.getByRole("heading", { name: /Next 14 days/ })).toBeVisible();
});

test("old URLs redirect to the new apps", async ({ page }) => {
  await page.goto("/officer/fields?as=officer.Sangrur");
  await expect(page).toHaveURL(/\/admin\/fields\?as=officer\.Sangrur$/);
  await expect(page.getByRole("heading", { name: "Fields", level: 1 })).toBeVisible();
  await page.goto("/operator?as=operator.B01");
  await expect(page).toHaveURL(/\/baler\?as=operator\.B01$/);
  await expect(page.getByText("Today's stops")).toBeVisible();
});

test("each role has its own sign-in page and accounts don't work on another role's page", async ({ page }) => {
  const signIn = async (path: string, email: string, password = "clearsky-dev") => {
    await page.goto(path);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
  };

  // signed out, each app sends you to its own login; no page lists the other roles
  for (const [app, heading] of [
    ["/admin", "Admin sign in"],
    ["/baler", /Baler sign in/],
    ["/buyer", "Buyer sign in"],
  ] as const) {
    await page.goto(app);
    await expect(page).toHaveURL(new RegExp(`${app}/login$`));
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(page.getByRole("button", { name: "Enter" })).toHaveCount(0); // the old all-in-one picker is gone
  }
  await page.goto("/login");
  await expect(page.getByText(/admin/i)).toHaveCount(0); // the public entrance never mentions the admin
  await expect(page.getByRole("link", { name: /I am a baler/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /I am a buyer/ })).toBeVisible();
  await page.goto("/admin/login");
  await expect(page.getByRole("link", { name: "Create an account" })).toHaveCount(0); // nobody registers as admin

  // an account is refused on another role's page, with the same message as a wrong password
  await signIn("/baler/login", "admin@clearsky.local");
  await expect(page.getByText("Wrong email or password.")).toBeVisible();
  await expect(page).toHaveURL(/\/baler\/login$/);
  await signIn("/admin/login", "b01@clearsky.local");
  await expect(page.getByText("Wrong email or password.")).toBeVisible();
  await signIn("/buyer/login", "b01@clearsky.local");
  await expect(page.getByText("Wrong email or password.")).toBeVisible();
  await signIn("/admin/login", "admin@clearsky.local", "wrong-password");
  await expect(page.getByText("Wrong email or password.")).toBeVisible();
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/admin\/login$/); // still signed out after the refused attempts

  // the right account on the right page
  await signIn("/buyer/login", "by01@clearsky.local");
  await expect(page).toHaveURL(/\/buyer$/);
  await expect(page.getByText("Incoming straw by day")).toBeVisible();
  await signIn("/admin/login", "admin@clearsky.local");
  await expect(page.getByRole("heading", { name: "Burn Risk Radar" })).toBeVisible();
});
