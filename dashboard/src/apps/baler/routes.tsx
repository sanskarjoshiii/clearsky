import { Route, Routes } from "react-router";
import { AppNotFound } from "../../components/NotFound";
import { BalerLayout } from "./Layout";
import { History } from "./pages/History";
import { Profile } from "./pages/Profile";
import { Requests } from "./pages/Requests";
import { Schedule } from "./pages/Schedule";
import { Today } from "./pages/Today";

/** Baler app route tree (lazy chunk; mounted at /baler/* by App.tsx). */
export function Component() {
  return (
    <Routes>
      <Route element={<BalerLayout />}>
        <Route index element={<Today />} />
        <Route path="requests" element={<Requests />} />
        <Route path="schedule" element={<Schedule />} />
        <Route path="history" element={<History />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<AppNotFound home="/baler" />} />
      </Route>
    </Routes>
  );
}
