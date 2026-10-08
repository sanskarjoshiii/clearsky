import { Navigate, Outlet, createBrowserRouter } from "react-router";
import type { Role } from "./api/types";
import { homeFor, useAuth } from "./auth/AuthProvider";
import { Shell } from "./components/Shell";
import { Skeleton } from "./components/ui";
import { BuyerPage } from "./pages/Buyer";
import { Impact } from "./pages/Impact";
import { Login } from "./pages/Login";
import { OperatorPage } from "./pages/Operator";
import { Demo } from "./pages/officer/Demo";
import { Radar } from "./pages/officer/Radar";
import { Balers, Bookings, Buyers, Fields } from "./pages/officer/Tables";

function Loading() {
  return (
    <div className="flex h-dvh items-center justify-center bg-frame">
      <Skeleton className="h-10 w-40" />
    </div>
  );
}

/** Signed-in users of the given role(s) only; others go to login or their own home. */
function RequireRole({ roles }: { roles: Role[] }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (!me) return <Navigate to="/login" replace />;
  if (!roles.includes(me.role)) return <Navigate to={homeFor(me.role)} replace />;
  return <Outlet />;
}

function Home() {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  return <Navigate to={me ? homeFor(me.role) : "/login"} replace />;
}

function NotFound() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-2 bg-frame text-center">
      <p className="text-lg font-medium">Page not found</p>
      <a href="/" className="text-sm text-muted underline">
        Go home
      </a>
    </div>
  );
}

export const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/login", element: <Login /> },
  { path: "/impact", element: <Impact /> },
  {
    element: <RequireRole roles={["officer"]} />,
    children: [
      {
        element: <Shell />,
        children: [
          { path: "/officer", element: <Radar /> },
          { path: "/officer/fields", element: <Fields /> },
          { path: "/officer/bookings", element: <Bookings /> },
          { path: "/officer/balers", element: <Balers /> },
          { path: "/officer/buyers", element: <Buyers /> },
          { path: "/officer/demo", element: <Demo /> },
        ],
      },
    ],
  },
  {
    element: <RequireRole roles={["buyer"]} />,
    children: [{ element: <Shell />, children: [{ path: "/buyer", element: <BuyerPage /> }] }],
  },
  {
    element: <RequireRole roles={["operator"]} />,
    children: [{ element: <Shell />, children: [{ path: "/operator", element: <OperatorPage /> }] }],
  },
  { path: "*", element: <NotFound /> },
]);
