import { Route, Routes } from "react-router";
import { useAuth } from "../../auth/AuthProvider";
import { AppNotFound } from "../../components/NotFound";
import { AdminLayout } from "./Layout";
import { Approvals } from "./pages/Approvals";
import { Demo } from "./pages/Demo";
import { Radar } from "./pages/Radar";
import { Balers, Bookings, Buyers, Fields } from "./pages/Tables";

/** Admin app route tree (lazy chunk; mounted at /admin/* by App.tsx). */
export function Component() {
  const { me } = useAuth();
  return (
    <Routes>
      <Route element={<AdminLayout />}>
        <Route index element={<Radar />} />
        <Route path="fields" element={<Fields />} />
        <Route path="bookings" element={<Bookings />} />
        <Route path="balers" element={<Balers />} />
        <Route path="buyers" element={<Buyers />} />
        <Route path="approvals" element={<Approvals />} />
        {me?.config.demo_mode ? <Route path="demo" element={<Demo />} /> : null}
        <Route path="*" element={<AppNotFound home="/admin" />} />
      </Route>
    </Routes>
  );
}
