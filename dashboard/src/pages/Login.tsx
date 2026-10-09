import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import type { AppRole } from "../api/types";
import { APPS, landingFor, loginFor, useAuth } from "../auth/AuthProvider";
import { Loading } from "../auth/RequireRole";
import { AuthFrame } from "../components/AuthFrame";
import { Button, ErrorNote, Field, Input } from "../components/ui";
import { env } from "../env";

const COPY: Record<AppRole, { title: string; sub: string }> = {
  officer: { title: "Admin sign in", sub: "District officers only." },
  operator: { title: "Baler sign in · बेलर लॉगिन", sub: "For custom hiring centres and baler operators." },
  buyer: { title: "Buyer sign in", sub: "For industries that take paddy straw." },
};

const DEV_HINT: Record<AppRole, string> = {
  officer: "admin@clearsky.local",
  operator: "b01@clearsky.local (any baler id)",
  buyer: "by01@clearsky.local (any buyer id)",
};

/** The page the visitor asked for before being sent here (set by RequireRole). */
function useFrom(): string | null {
  const state = useLocation().state as { from?: string } | null;
  return state?.from ?? null;
}

/**
 * Sign-in for ONE role, at that role's own address (/admin/login, /baler/login, /buyer/login).
 * An account only works on its own page: nothing here mentions or links to the other roles, and an
 * admin account entered on the baler page is refused like a wrong password.
 */
export function RoleLogin({ role }: { role: AppRole }) {
  const { me, loading, signIn } = useAuth();
  const navigate = useNavigate();
  const from = useFrom();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  if (loading) return <Loading />;
  if (me?.role === role) return <Navigate to={landingFor(role, from)} replace />;
  // registered here but not approved yet: the waiting room, never another role's app
  if (me?.role === "pending" && role !== "officer") return <Navigate to="/pending" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const signedIn = await signIn(role, email.trim(), password);
      navigate(landingFor(signedIn.role, from), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFrame>
      <h2 className="text-lg font-semibold tracking-[var(--tracking-title)]">{COPY[role].title}</h2>
      <p className="mb-5 mt-1 text-sm text-muted">{COPY[role].sub}</p>
      <form className="space-y-4" onSubmit={(e) => void submit(e)}>
        <Field label="Email">
          <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password">
          <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error ? <ErrorNote error={error} /> : null}
        <Button variant="primary" className="w-full" loading={busy} type="submit">
          Sign in
        </Button>
      </form>
      {role !== "officer" ? (
        <p className="mt-6 border-t border-line pt-4 text-sm text-muted">
          New here?{" "}
          <Link to={`/register?role=${role}`} className="text-ink underline">
            Create an account
          </Link>
        </p>
      ) : null}
      {env.authMode === "dev" ? (
        <p className="mt-4 text-xs text-faint">
          Local development: {DEV_HINT[role]}, password from DEV_PASSWORD. The deployed dashboard uses each person's own Cognito password.
        </p>
      ) : null}
    </AuthFrame>
  );
}

/**
 * /login: the public entrance for balers and buyers. The admin sign-in is not listed here; district
 * officers use their own address.
 */
export function Login() {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (me) return <Navigate to={landingFor(me.role)} replace />;
  return (
    <AuthFrame>
      <h2 className="text-lg font-semibold tracking-[var(--tracking-title)]">Sign in</h2>
      <p className="mb-5 mt-1 text-sm text-muted">Farmers don't need an account: they use WhatsApp.</p>
      <div className="space-y-2.5">
        {(["operator", "buyer"] as const).map((role) => (
          <Link
            key={role}
            to={loginFor(role)}
            className="flex min-h-14 items-center justify-between rounded-[var(--radius-card)] border border-line px-4 py-3 text-sm hover:bg-hover"
          >
            <span>
              <span className="block font-medium text-ink">I am a {APPS[role].label.toLowerCase()}</span>
              <span className="block text-xs text-muted">{COPY[role].sub}</span>
            </span>
            <span className="text-muted" aria-hidden>
              →
            </span>
          </Link>
        ))}
      </div>
      <p className="mt-6 border-t border-line pt-4 text-sm text-muted">
        New here?{" "}
        <Link to="/register" className="text-ink underline">
          Create an account
        </Link>
      </p>
    </AuthFrame>
  );
}
