import { BarChart3, CalendarCheck, Factory, FlaskConical, Radar, Table2, Tractor } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { RailLayout, SimPanelProvider, type NavItem } from "../../components/Shell";
import { Simulator } from "../../components/Simulator";

/** Admin (district officer) app: icon rail · canvas · docked farmer simulator while WA_MODE=simulator. */
export function AdminLayout() {
  const { me } = useAuth();
  const canSimulate = me?.config.wa_mode === "simulator";
  const [open, setOpen] = useState<boolean>(() => {
    try {
      if (new URLSearchParams(window.location.search).get("sim") === "1") return true;
      return localStorage.getItem("clearsky.simOpen") === "1";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("clearsky.simOpen", open ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [open]);

  const items: NavItem[] = [
    { to: "/admin", label: "Burn Risk Radar", short: "Radar", icon: Radar, end: true },
    { to: "/admin/fields", label: "Fields", icon: Table2 },
    { to: "/admin/bookings", label: "Bookings", icon: CalendarCheck },
    { to: "/admin/balers", label: "Balers", icon: Tractor },
    { to: "/admin/buyers", label: "Buyers", icon: Factory },
    ...(me?.config.demo_mode ? [{ to: "/admin/demo", label: "Demo controls", short: "Demo", icon: FlaskConical }] : []),
    { to: "/impact", label: "Impact", icon: BarChart3 },
  ];

  return (
    <SimPanelProvider value={{ open: canSimulate && open, setOpen }}>
      <RailLayout label="Admin" items={items} panel={canSimulate ? <Simulator onClose={() => setOpen(false)} /> : undefined} />
    </SimPanelProvider>
  );
}
