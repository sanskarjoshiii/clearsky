import { Route, Routes } from "react-router";
import { AppNotFound } from "../../components/NotFound";
import { BuyerLayout } from "./Layout";
import { Deliveries } from "./pages/Deliveries";
import { Demand } from "./pages/Demand";
import { Overview } from "./pages/Overview";
import { Profile } from "./pages/Profile";

/** Buyer app route tree (lazy chunk; mounted at /buyer/* by App.tsx). */
export function Component() {
  return (
    <Routes>
      <Route element={<BuyerLayout />}>
        <Route index element={<Overview />} />
        <Route path="deliveries" element={<Deliveries />} />
        <Route path="demand" element={<Demand />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<AppNotFound home="/buyer" />} />
      </Route>
    </Routes>
  );
}
