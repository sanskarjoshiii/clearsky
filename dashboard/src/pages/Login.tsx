import { Factory, Landmark, Tractor } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useDevAccounts } from "../api/hooks";
import type { Role } from "../api/types";
import { landingFor, useAuth } from "../auth/AuthProvider";
import { Logo } from "../components/Shell";
import { Button, ErrorNote, Field, Input, Skeleton } from "../components/ui";
import { env } from "../env";

const ROLES: { role: Role; title: string; hint: string; icon: typeof Factory }[] = [
  { role: "officer", title: "Admin", hint: "District officer: Burn Risk Radar, alerts, every table", icon: Landmark },
  { role: "operator", title: "Baler", hint: "Today's stops, route, mark fields done", icon: Tractor },
  { role: "buyer", title: "Buyer", hint: "Industry: straw demand, price and incoming supply", icon: Factory },
];

/** The page the visitor asked for before being sent here (set by RequireRole). */
function useFrom(): string | null {
  const state = useLocation().state as { from?: string } | null;
  return state?.from ?? null;
}

function DevLogin() {
  const accounts = useDevAccounts(true);
  const { signInDev } = useAuth();
  const navigate = useNavigate();
  const from = useFrom();
  const [pick, setPick] = useState<Record<Role, string>>({ officer: "", operator: "", buyer: "" });
  const [busy, setBusy] = useState<Role | null>(null);
  const [error, setError] = useState<unknown>(null);

  const go = async (role: Role) => {
    const list = accounts.data?.[role] ?? [];
    const id = pick[role] || list[0]?.id || role;
    setBusy(role);
    setError(null);
    try {
      const me = await signInDev(role, id);
      navigate(landingFor(me.role, from), { replace: true });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  if (accounts.isLoading) return <Skeleton className="h-56" />;
  if (accounts.error)
    return (
      <ErrorNote error={new Error("The local API isn't reachable. Start it with: cd backend && uv run python scripts/dev_server.py")} onRetry={() => void accounts.refetch()} />
    );
  return (
    <div className="space-y-2.5">
      {ROLES.map(({ role, title, hint, icon: Icon }) => {
        const list = accounts.data?.[role] ?? [];
        return (
          <div key={role} className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line p-3.5 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-[8px] bg-sunken text-ink-2">
                <Icon className="size-[18px]" strokeWidth={1.8} />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium">{title}</div>
                <div className="truncate text-xs text-muted">{hint}</div>
              </div>
            </div>
            <div className="flex min-w-0 items-center gap-2">
              {list.length > 1 ? (
                <select
                  aria-label={`${title} account`}
                  value={pick[role]}
                  onChange={(e) => setPick({ ...pick, [role]: e.target.value })}
                  className="h-9 w-full min-w-0 max-w-[190px] rounded-[var(--radius-control)] border border-line-strong bg-canvas px-2 text-[13px]"
                >
                  {list.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.label}
                    </option>
                  ))}
                </select>
              ) : null}
              <Button variant="primary" loading={busy === role} onClick={() => void go(role)}>
                Enter
              </Button>
            </div>
          </div>
        );
      })}
      {error ? <ErrorNote error={error} /> : null}
      <p className="pt-1 text-xs text-faint">Local development sign-in (DEV_AUTH). The deployed dashboard uses Cognito email and password.</p>
    </div>
  );
}

function CognitoLogin() {
  const { signInCognito } = useAuth();
  const navigate = useNavigate();
  const from = useFrom();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await signInCognito(email.trim(), password);
      navigate(landingFor(me.role, from), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
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
      <p className="text-xs text-faint">Accounts are created by the clearsky team. Farmers don't need an account: they use WhatsApp.</p>
    </form>
  );
}

export function Login() {
  const { me, loading } = useAuth();
  const from = useFrom();
  if (!loading && me) return <Navigate to={landingFor(me.role, from)} replace />;
  return (
    <div className="flex min-h-dvh items-center justify-center bg-frame px-4 py-10">
      <div className="w-full max-w-[520px] animate-rise rounded-[var(--radius-canvas)] bg-canvas p-6 shadow-[var(--shadow-canvas)] sm:p-8">
        <div className="mb-7 flex items-center gap-3">
          <Logo size="size-11" />
          <div>
            <h1 className="text-[22px] font-semibold tracking-[var(--tracking-display)]">clearsky</h1>
            <p className="text-[13px] text-muted">Straw pickup instead of stubble fires</p>
          </div>
        </div>
        {env.authMode === "dev" ? <DevLogin /> : <CognitoLogin />}
      </div>
    </div>
  );
}
