import { Navigate, createBrowserRouter, useLocation } from "react-router";
import { Loading, RequireRole } from "./auth/RequireRole";
import { Login, RoleLogin } from "./pages/Login";
import { Pending } from "./pages/register/Pending";
import { Register } from "./pages/register/Register";

/** Old links (runbook, bookmarks, `?as=` dev links) keep working: /officer/* → /admin/*, /operator → /baler. */
function Moved({ from, to }: { from: string; to: string }) {
  const { pathname, search, hash } = useLocation();
  return <Navigate to={`${to}${pathname.slice(from.length)}${search}${hash}`} replace />;
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

/**
 * One router, three lazy role apps. Each app is its own chunk (`apps/<role>/routes.tsx`), so a buyer
 * never downloads the map and a baler never downloads the charts. The apps render their own nested
 * routes, layout and 404.
 */
export const router = createBrowserRouter([
  // public home page (lazy: its video and sections stay out of the role apps)
  { path: "/", lazy: () => import("./pages/home/Home"), hydrateFallbackElement: <Loading /> },
  // Separate sign-in per role. /login only offers baler and buyer; the admin address is not linked anywhere.
  { path: "/login", element: <Login /> },
  { path: "/admin/login", element: <RoleLogin key="officer" role="officer" /> },
  { path: "/baler/login", element: <RoleLogin key="operator" role="operator" /> },
  { path: "/buyer/login", element: <RoleLogin key="buyer" role="buyer" /> },
  // lazy: the impact page draws a chart, and the chart library stays out of the main bundle
  { path: "/impact", lazy: () => import("./pages/Impact"), hydrateFallbackElement: <Loading /> },
  // self-registration: /register is public (sign-up + application form); /pending is the waiting room
  { path: "/register", element: <Register /> },
  { path: "/pending", element: <Pending /> },
  {
    element: <RequireRole role="officer" />,
    children: [{ path: "/admin/*", lazy: () => import("./apps/admin/routes"), hydrateFallbackElement: <Loading /> }],
  },
  {
    element: <RequireRole role="operator" />,
    children: [{ path: "/baler/*", lazy: () => import("./apps/baler/routes"), hydrateFallbackElement: <Loading /> }],
  },
  {
    element: <RequireRole role="buyer" />,
    children: [{ path: "/buyer/*", lazy: () => import("./apps/buyer/routes"), hydrateFallbackElement: <Loading /> }],
  },
  { path: "/officer/*", element: <Moved from="/officer" to="/admin" /> },
  { path: "/operator/*", element: <Moved from="/operator" to="/baler" /> },
  { path: "*", element: <NotFound /> },
]);
