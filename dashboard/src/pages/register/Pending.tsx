import { Clock, LogOut, PauseCircle, XCircle } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { useMyApplication } from "../../api/hooks";
import type { Application } from "../../api/types";
import { homeFor, useAuth } from "../../auth/AuthProvider";
import { Loading } from "../../auth/RequireRole";
import { AuthFrame } from "../../components/AuthFrame";
import { Button, ErrorNote, Skeleton } from "../../components/ui";
import { fmtDay, fmtNum } from "../../lib/format";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2 text-[13px] last:border-0">
      <span className="text-muted">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}

export function ApplicationSummary({ app }: { app: Application }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line px-4 py-1">
      <Row label="Applying as">{app.role === "operator" ? "Baler operator" : "Industry buyer"}</Row>
      <Row label="Name">{app.name}</Row>
      <Row label={app.role === "operator" ? "Custom hiring centre" : "Company"}>{app.org_name}</Row>
      <Row label="Village">{app.village_name ?? app.village_id}</Row>
      <Row label="Phone">{app.phone}</Row>
      {app.role === "operator" ? (
        <Row label="Capacity">
          {fmtNum(app.acres_per_day)} acres/day · {fmtNum(app.radius_km)} km radius
        </Row>
      ) : (
        <Row label="Demand">
          {fmtNum(app.demand_tonnes)} t · within {fmtNum(app.max_radius_km)} km
        </Row>
      )}
      <Row label="Sent">{fmtDay(app.created_at)}</Row>
    </div>
  );
}

function Status({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-sunken text-ink-2">{icon}</span>
      <div>
        <h2 className="text-lg font-semibold tracking-[var(--tracking-title)]">{title}</h2>
        <div className="mt-1 text-sm text-ink-2">{children}</div>
      </div>
    </div>
  );
}

/**
 * Where a registered user waits for the officer's decision. It polls; on approval it picks up the
 * new role (a fresh Cognito token) and moves the user to their dashboard without contacting anyone.
 */
export function Pending() {
  const { me, loading, activate, signOut } = useAuth();
  const navigate = useNavigate();
  const mine = useMyApplication(me?.role === "pending");
  const [error, setError] = useState<unknown>(null);
  const activating = useRef(false);
  const app = mine.data;

  useEffect(() => {
    if (app?.status !== "APPROVED" || activating.current) return;
    activating.current = true;
    activate(app)
      .then((m) => {
        if (m && m.role !== "pending") navigate(homeFor(m.role), { replace: true });
        else activating.current = false; // token not updated yet: the next poll tries again
      })
      .catch((e: unknown) => {
        setError(e);
        activating.current = false;
      });
  }, [app, activate, navigate]);

  if (loading) return <Loading />;
  if (!me) return <Navigate to="/login" replace />;
  if (me.role !== "pending") return <Navigate to={homeFor(me.role)} replace />;
  if (mine.data === null) return <Navigate to="/register" replace />; // signed up but never applied

  return (
    <AuthFrame>
      {mine.isLoading ? <Skeleton className="h-48" /> : null}
      {mine.error ? <ErrorNote error={mine.error} onRetry={() => void mine.refetch()} /> : null}
      {app ? (
        <div className="space-y-5">
          {app.status === "PENDING" ? (
            <Status icon={<Clock className="size-[18px]" />} title="Under review">
              The district officer is checking your application. This page updates by itself; you don't need to do anything.
            </Status>
          ) : null}
          {app.status === "APPROVED" ? (
            <Status icon={<Clock className="size-[18px]" />} title="Approved">
              Opening your dashboard…
            </Status>
          ) : null}
          {app.status === "REJECTED" ? (
            <Status icon={<XCircle className="size-[18px]" />} title="Not approved">
              <p>The district officer did not approve this application.</p>
              <p className="mt-2 rounded-[var(--radius-control)] border border-line bg-sunken px-3 py-2 text-ink">Reason: {app.reject_reason}</p>
            </Status>
          ) : null}
          {app.status === "SUSPENDED" ? (
            <Status icon={<PauseCircle className="size-[18px]" />} title="Account switched off">
              The district officer has deactivated this account. Contact the district office to turn it back on.
            </Status>
          ) : null}
          <ApplicationSummary app={app} />
          {error ? <ErrorNote error={error} /> : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            {app.status === "REJECTED" ? (
              <Link to="/register?edit=1" className="inline-flex h-9 items-center rounded-[var(--radius-control)] bg-ink px-3.5 text-sm font-medium text-canvas hover:bg-ink-2">
                Edit and resubmit
              </Link>
            ) : (
              <span />
            )}
            <Button variant="ghost" onClick={() => void signOut()}>
              <LogOut className="size-4" /> Sign out
            </Button>
          </div>
        </div>
      ) : null}
    </AuthFrame>
  );
}
