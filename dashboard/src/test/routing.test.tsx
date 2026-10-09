import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AppRole, Me, Role } from "../api/types";
import { appOf, homeFor, landingFor } from "../auth/AuthProvider";
import { RequireRole } from "../auth/RequireRole";
import { ToastProvider } from "../components/ui";

const auth: { me: Me | null; loading: boolean } = { me: null, loading: false };
vi.mock("../auth/AuthProvider", async (original) => ({
  ...(await original<typeof import("../auth/AuthProvider")>()),
  useAuth: () => auth,
}));

const user = (role: Role): Me => ({
  sub: "u1",
  role,
  email: "u@example.test",
  district: null,
  buyer_id: null,
  baler_id: null,
  dev: true,
  display_name: "Test user",
  config: { wa_mode: "simulator", demo_mode: true, llm_provider: "rules", today: "2026-10-20" },
});

function LoginProbe() {
  const state = useLocation().state as { from?: string } | null;
  return <p>login page, from {state?.from ?? "nowhere"}</p>;
}

function open(path: string, me: Me | null) {
  auth.me = me;
  const app = (role: AppRole, base: string, text: string) => ({
    element: <RequireRole role={role} />,
    children: [{ path: `${base}/*`, element: <p>{text}</p> }],
  });
  const router = createMemoryRouter(
    [
      { path: "/login", element: <LoginProbe /> },
      { path: "/pending", element: <p>pending page</p> },
      app("officer", "/admin", "admin page"),
      app("operator", "/baler", "baler page"),
      app("buyer", "/buyer", "buyer page"),
    ],
    { initialEntries: [path] },
  );
  render(
    <ToastProvider>
      <RouterProvider router={router} />
    </ToastProvider>,
  );
}

describe("RequireRole", () => {
  beforeEach(() => {
    auth.loading = false;
  });

  it("sends a signed-out visitor to login and remembers the page they asked for", async () => {
    open("/baler/requests?x=1", null);
    expect(await screen.findByText("login page, from /baler/requests?x=1")).toBeInTheDocument();
  });

  it("lets the right role in", async () => {
    open("/buyer/demand", user("buyer"));
    expect(await screen.findByText("buyer page")).toBeInTheDocument();
  });

  it("sends a signed-in user on another role's URL to their own home, with a notice", async () => {
    open("/admin/fields", user("operator"));
    expect(await screen.findByText("baler page")).toBeInTheDocument();
    expect(screen.getByText("That page is for admins.")).toBeInTheDocument();
    expect(screen.queryByText("admin page")).not.toBeInTheDocument();
  });

  it("sends a registered user who is not approved yet to /pending, without a wrong-app notice", async () => {
    open("/baler/requests", user("pending"));
    expect(await screen.findByText("pending page")).toBeInTheDocument();
    expect(screen.queryByText(/That page is for/)).not.toBeInTheDocument();
    expect(screen.queryByText("baler page")).not.toBeInTheDocument();
  });

  it("shows nothing protected while the session is still loading", () => {
    auth.loading = true;
    open("/admin", user("officer"));
    expect(screen.queryByText("admin page")).not.toBeInTheDocument();
  });
});

describe("role homes", () => {
  it("maps each role to its own app", () => {
    expect([homeFor("officer"), homeFor("operator"), homeFor("buyer")]).toEqual(["/admin", "/baler", "/buyer"]);
    expect(appOf("/admin/fields")).toBe("officer");
    expect(appOf("/baler")).toBe("operator");
    expect(appOf("/buyers")).toBeNull();
    expect(appOf("/impact")).toBeNull();
  });

  it("returns to the requested page only when it belongs to the signed-in role", () => {
    expect(landingFor("operator", "/baler/requests?x=1")).toBe("/baler/requests?x=1");
    expect(landingFor("operator", "/admin/fields")).toBe("/baler");
    expect(landingFor("buyer", null)).toBe("/buyer");
    expect(homeFor("pending")).toBe("/pending");
    expect(landingFor("pending", "/admin/approvals")).toBe("/pending");
  });
});
