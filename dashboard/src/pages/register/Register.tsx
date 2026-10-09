import { Factory, Tractor, type LucideIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { useMyApplication } from "../../api/hooks";
import { PENDING_HOME, homeFor, loginFor, useAuth } from "../../auth/AuthProvider";
import { Loading } from "../../auth/RequireRole";
import { AuthFrame } from "../../components/AuthFrame";
import { Button, cx, ErrorNote, Field, Input, Skeleton } from "../../components/ui";
import { env } from "../../env";
import { ApplicationForm } from "./ApplicationForm";

type ApplyRole = "operator" | "buyer";
const ROLE_KEY = "clearsky.applyRole";

const CHOICES: { role: ApplyRole; title: string; hi?: string; hint: string; icon: LucideIcon }[] = [
  { role: "operator", title: "Baler operator", hi: "बेलर चलाने वाले", hint: "A custom hiring centre with a baler. Farmers' pickups are booked to you.", icon: Tractor },
  { role: "buyer", title: "Industry buyer", hint: "A plant that takes paddy straw: pellets, CBG, boiler, biomass power.", icon: Factory },
];

function readRole(): ApplyRole | null {
  try {
    const r = sessionStorage.getItem(ROLE_KEY);
    return r === "operator" || r === "buyer" ? r : null;
  } catch {
    return null;
  }
}

/** Step 1: what are you applying as? Two big cards. */
function RoleCards({ value, onPick }: { value: ApplyRole | null; onPick: (r: ApplyRole) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="I am applying as">
      {CHOICES.map(({ role, title, hi, hint, icon: Icon }) => (
        <button
          key={role}
          type="button"
          role="radio"
          aria-checked={value === role}
          onClick={() => onPick(role)}
          className={cx(
            "flex min-h-[124px] flex-col items-start gap-2 rounded-[var(--radius-card)] border p-4 text-left transition-colors",
            value === role ? "border-ink bg-sunken" : "border-line hover:bg-hover",
          )}
        >
          <span className="flex size-9 items-center justify-center rounded-[8px] bg-sunken text-ink-2">
            <Icon className="size-[18px]" strokeWidth={1.8} />
          </span>
          <span className="text-[15px] font-medium text-ink">
            {title}
            {hi ? <span className="font-normal text-muted"> · {hi}</span> : null}
          </span>
          <span className="text-xs text-muted">{hint}</span>
        </button>
      ))}
    </div>
  );
}

/** Step 2 (deployed): Cognito sign-up with an emailed 6-digit code. Passwords never touch our API. */
function CognitoAccount({ onDone }: { onDone: () => void }) {
  const { signUp, confirmSignUp, resendCode } = useAuth();
  const [stage, setStage] = useState<"details" | "code">("details");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [note, setNote] = useState("");

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const create = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      await signUp(email.trim(), password);
      setStage("code");
    });
  };
  const verify = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      await confirmSignUp(email.trim(), code.trim(), password);
      onDone();
    });
  };

  if (stage === "details")
    return (
      <form className="space-y-4" onSubmit={create}>
        <Field label="Email">
          <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" hint="At least 10 characters with a capital letter, a small letter and a number">
          <Input type="password" autoComplete="new-password" required minLength={10} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error ? <ErrorNote error={error} /> : null}
        <Button variant="primary" type="submit" className="w-full" loading={busy}>
          Create account
        </Button>
        <button type="button" className="text-xs text-muted underline" onClick={() => email.trim() && password && setStage("code")}>
          I already have a code
        </button>
      </form>
    );
  return (
    <form className="space-y-4" onSubmit={verify}>
      <p className="text-sm text-ink-2">
        We emailed a 6-digit code to <span className="font-medium">{email}</span>.
      </p>
      <Field label="Verification code">
        <Input inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value)} />
      </Field>
      {error ? <ErrorNote error={error} /> : null}
      {note ? <p className="text-xs text-muted">{note}</p> : null}
      <Button variant="primary" type="submit" className="w-full" loading={busy}>
        Verify and continue
      </Button>
      <div className="flex justify-between text-xs text-muted">
        <button type="button" className="underline" onClick={() => setStage("details")}>
          Change email
        </button>
        <button
          type="button"
          className="underline"
          onClick={() =>
            void run(async () => {
              await resendCode(email.trim());
              setNote("A new code is on its way.");
            })
          }
        >
          Send the code again
        </button>
      </div>
    </form>
  );
}

/** Step 2 (local dev, DEV_AUTH): no Cognito, so the account is the email plus the shared dev password. */
function DevAccount({ role, onDone }: { role: ApplyRole; onDone: () => void }) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const go = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(role, email.trim(), password);
      onDone();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="space-y-4" onSubmit={(e) => void go(e)}>
      <Field label="Email" hint="You sign in with this email later">
        <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label="Password">
        <Input type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </Field>
      {error ? <ErrorNote error={error} /> : null}
      <Button variant="primary" type="submit" className="w-full" loading={busy}>
        Create account
      </Button>
      <p className="text-xs text-faint">
        Local development (DEV_AUTH): use the dev password (DEV_PASSWORD). The deployed dashboard lets you choose your own password and verifies the email.
      </p>
    </form>
  );
}

/**
 * Self-registration for baler operators and industry buyers.
 * Role choice → account (Cognito sign-up + email code) → application form → /pending until the officer decides.
 */
export function Register() {
  const { me, loading } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const editing = params.get("edit") === "1";
  const asked = params.get("role"); // from "Create an account" on the baler or buyer sign-in page
  const [role, setRoleState] = useState<ApplyRole | null>(() => (asked === "operator" || asked === "buyer" ? asked : readRole()));
  const mine = useMyApplication(me?.role === "pending", false);
  const setRole = (r: ApplyRole) => {
    setRoleState(r);
    try {
      sessionStorage.setItem(ROLE_KEY, r);
    } catch {
      /* the choice just won't survive a reload */
    }
  };

  if (loading) return <Loading />;
  if (me && me.role !== "pending") return <Navigate to={homeFor(me.role)} replace />;
  // signed in and waiting: the status page takes over unless a rejected applicant is editing
  const app = mine.data;
  if (me && app && !(app.status === "REJECTED" && editing)) return <Navigate to={PENDING_HOME} replace />;

  const signedIn = !!me;
  const chosen = role ?? (editing && app ? app.role : null);
  return (
    <AuthFrame wide>
      <h2 className="text-lg font-semibold tracking-[var(--tracking-title)]">{signedIn ? "Your application" : "Create an account"}</h2>
      <p className="mb-5 mt-1 text-sm text-muted">
        For baler operators and industries that buy straw. Farmers don't need an account: they use WhatsApp.
      </p>
      {signedIn && mine.isLoading ? (
        <Skeleton className="h-56" />
      ) : (
        <div className="space-y-6">
          <RoleCards value={chosen} onPick={setRole} />
          {chosen ? (
            signedIn ? (
              <ApplicationForm key={chosen} role={chosen} previous={editing ? app : null} onSubmitted={() => navigate(PENDING_HOME, { replace: true })} />
            ) : env.authMode === "dev" ? (
              <DevAccount role={chosen} onDone={() => undefined} />
            ) : (
              <CognitoAccount onDone={() => undefined} />
            )
          ) : (
            <p className="text-sm text-muted">Choose what you are applying as to continue.</p>
          )}
        </div>
      )}
      {!signedIn ? (
        <p className="mt-6 text-sm text-muted">
          Already have an account?{" "}
          <Link to={chosen ? loginFor(chosen) : "/login"} className="text-ink underline">
            Sign in
          </Link>
        </p>
      ) : null}
    </AuthFrame>
  );
}
