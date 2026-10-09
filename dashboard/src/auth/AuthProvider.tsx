import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Me, Role } from "../api/types";
import { env } from "../env";
import { setDevToken, setUnauthorizedHandler } from "./token";

interface AuthState {
  me: Me | null;
  loading: boolean;
  signInDev: (role: Role, id: string) => Promise<Me>;
  signInCognito: (email: string, password: string) => Promise<Me>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);
let amplifyConfigured = false;

async function configureAmplify(): Promise<void> {
  if (amplifyConfigured || env.authMode !== "cognito") return;
  const { Amplify } = await import("aws-amplify");
  Amplify.configure({ Auth: { Cognito: { userPoolId: env.userPoolId, userPoolClientId: env.userPoolClientId } } });
  amplifyConfigured = true;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  const loadMe = useCallback(async (): Promise<Me | null> => {
    try {
      const m = await api<Me>("/api/me");
      setMe(m);
      return m;
    } catch {
      setMe(null);
      return null;
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setMe(null));
    void (async () => {
      await configureAmplify();
      // Dev auth only: "?as=operator.B01" signs in directly (quick role switching for demos/screenshots).
      const as = env.authMode === "dev" ? new URLSearchParams(window.location.search).get("as") : null;
      const [role, id] = as?.split(".") ?? [];
      if (role === "officer" || role === "buyer" || role === "operator") {
        try {
          const res = await api<{ token: string }>("/api/dev/login", { method: "POST", body: { role, id: id ?? role } });
          setDevToken(res.token);
        } catch {
          /* fall through to the login page */
        }
      }
      await loadMe();
      setLoading(false);
    })();
    return () => setUnauthorizedHandler(null);
  }, [loadMe]);

  const signInDev = useCallback(
    async (role: Role, id: string) => {
      const res = await api<{ token: string }>("/api/dev/login", { method: "POST", body: { role, id } });
      setDevToken(res.token);
      queryClient.clear();
      const m = await loadMe();
      if (!m) throw new Error("Sign-in failed");
      return m;
    },
    [loadMe, queryClient],
  );

  const signInCognito = useCallback(
    async (email: string, password: string) => {
      await configureAmplify();
      const { signIn, signOut } = await import("aws-amplify/auth");
      await signOut().catch(() => undefined);
      const result = await signIn({ username: email, password });
      if (!result.isSignedIn) throw new Error("Additional sign-in step required. Ask the team to reset your password.");
      queryClient.clear();
      const m = await loadMe();
      if (!m) throw new Error("This account has no clearsky role. Ask the team to add you to a group.");
      return m;
    },
    [loadMe, queryClient],
  );

  const signOutAll = useCallback(async () => {
    if (env.authMode === "dev") setDevToken(null);
    else {
      const { signOut } = await import("aws-amplify/auth");
      await signOut().catch(() => undefined);
    }
    queryClient.clear();
    setMe(null);
  }, [queryClient]);

  const value = useMemo(
    () => ({ me, loading, signInDev, signInCognito, signOut: signOutAll }),
    [me, loading, signInDev, signInCognito, signOutAll],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

/**
 * The three role apps. Code keeps the Cognito group names (officer / operator / buyer); people see
 * Admin / Baler / Buyer. `home` is the single source of each role's landing page.
 */
export const APPS: Record<Role, { home: string; label: string; plural: string }> = {
  officer: { home: "/admin", label: "Admin", plural: "admins" },
  operator: { home: "/baler", label: "Baler", plural: "balers" },
  buyer: { home: "/buyer", label: "Buyer", plural: "buyers" },
};

export function homeFor(role: Role): string {
  return APPS[role].home;
}

/** Which role's app a path belongs to (null for public pages). */
export function appOf(pathname: string): Role | null {
  const hit = (Object.keys(APPS) as Role[]).find((r) => pathname === APPS[r].home || pathname.startsWith(`${APPS[r].home}/`));
  return hit ?? null;
}

/** Where to send someone after sign-in: the page they asked for if it is theirs, else their home. */
export function landingFor(role: Role, from?: string | null): string {
  return from && appOf(from.split(/[?#]/)[0] ?? "") === role ? from : homeFor(role);
}
