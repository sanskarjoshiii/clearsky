import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import type { AppRole, Role } from "../api/types";
import { Skeleton, useToast } from "../components/ui";
import { APPS, homeFor, useAuth } from "./AuthProvider";

export function Loading() {
  return (
    <div className="flex h-dvh items-center justify-center bg-frame">
      <Skeleton className="h-10 w-40" />
    </div>
  );
}

/** A signed-in user opened another role's URL: say so once, then send them to their own home. */
function WrongApp({ own, wanted }: { own: Role; wanted: AppRole }) {
  const toast = useToast();
  useEffect(() => {
    // someone still waiting for approval gets the status page, which explains itself
    if (own !== "pending") toast(`That page is for ${APPS[wanted].plural}.`);
  }, [toast, own, wanted]);
  return <Navigate to={homeFor(own)} replace />;
}

/**
 * Gate for one role's app. Signed-out visitors go to the login page, which sends them back to the
 * URL they asked for (`state.from`); signed-in users of another role go to their own home, and
 * users who registered but are not approved yet go to `/pending`.
 */
export function RequireRole({ role }: { role: AppRole }) {
  const { me, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Loading />;
  if (!me) return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  if (me.role !== role) return <WrongApp own={me.role} wanted={role} />;
  return <Outlet />;
}
