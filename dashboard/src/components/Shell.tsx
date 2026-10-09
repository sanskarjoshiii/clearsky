import {
  BarChart3,
  CalendarCheck,
  Factory,
  FlaskConical,
  LogOut,
  MessageCircle,
  Radar,
  Route as RouteIcon,
  Table2,
  Tractor,
  X,
} from "lucide-react";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router";
import { useDemoClock } from "../api/hooks";
import type { Role } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { fmtDay, initials } from "../lib/format";
import { Simulator } from "./Simulator";
import { cx, IconButton } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Radar;
  end?: boolean;
}

function navFor(role: Role, demo: boolean): NavItem[] {
  if (role === "officer") {
    return [
      { to: "/officer", label: "Burn Risk Radar", icon: Radar, end: true },
      { to: "/officer/fields", label: "Fields", icon: Table2 },
      { to: "/officer/bookings", label: "Bookings", icon: CalendarCheck },
      { to: "/officer/balers", label: "Balers", icon: Tractor },
      { to: "/officer/buyers", label: "Buyers", icon: Factory },
      ...(demo ? [{ to: "/officer/demo", label: "Demo controls", icon: FlaskConical }] : []),
      { to: "/impact", label: "Impact", icon: BarChart3 },
    ];
  }
  if (role === "buyer") return [{ to: "/buyer", label: "Straw supply", icon: Factory, end: true }];
  return [{ to: "/operator", label: "Today's route", icon: RouteIcon, end: true }];
}

const PanelContext = createContext<{ open: boolean; setOpen: (v: boolean) => void }>({ open: false, setOpen: () => undefined });
export const useSimPanel = () => useContext(PanelContext);

/** The clearsky logo (public/logo.png, already cut to a circle). */
export function Logo({ size = "size-9" }: { size?: string }) {
  return <img src="/logo.png" alt="clearsky" className={`${size} shrink-0 rounded-full`} draggable={false} />;
}

/** App frame: icon rail · floating canvas · docked farmer simulator (officer, simulator mode). */
export function Shell() {
  const { me, signOut } = useAuth();
  const demo = !!me?.config.demo_mode;
  const canSimulate = me?.role === "officer" && me.config.wa_mode === "simulator";
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
  if (!me) return null;
  const items = navFor(me.role, demo);
  const panelOpen = canSimulate && open;

  return (
    <PanelContext.Provider value={{ open: panelOpen, setOpen }}>
      <div className="flex h-screen w-full overflow-hidden bg-frame">
        {/* rail */}
        <nav className="hidden w-[60px] shrink-0 flex-col items-center gap-1 py-4 md:flex" aria-label="Main">
          <Logo />
          <div className="mt-5 flex flex-col gap-1">
            {items.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.end}
                title={it.label}
                aria-label={it.label}
                className={({ isActive }) =>
                  cx(
                    "flex size-10 items-center justify-center rounded-[10px] transition-colors",
                    isActive ? "bg-canvas text-ink shadow-[var(--shadow-canvas)]" : "text-faint hover:text-ink",
                  )
                }
              >
                <it.icon className="size-[19px]" strokeWidth={1.8} />
              </NavLink>
            ))}
          </div>
          <div className="mt-auto flex flex-col items-center gap-3">
            {canSimulate ? (
              <button
                onClick={() => setOpen(!open)}
                title="Farmer simulator (WhatsApp)"
                aria-label="Toggle farmer simulator"
                aria-pressed={open}
                className={cx(
                  "flex size-9 items-center justify-center rounded-full text-canvas transition-transform hover:scale-105",
                  "bg-[radial-gradient(circle_at_30%_30%,var(--color-agent-line),var(--color-agent)_55%,var(--color-agent-strong))]",
                  open && "ring-2 ring-agent-line ring-offset-2 ring-offset-frame",
                )}
              >
                <MessageCircle className="size-4" />
              </button>
            ) : null}
            <button
              onClick={() => void signOut()}
              title={`${me.display_name} · sign out`}
              aria-label="Sign out"
              className="group relative flex size-9 items-center justify-center rounded-full bg-agent-soft text-[13px] font-semibold text-agent-strong"
            >
              <span className="group-hover:hidden">{initials(me.display_name)}</span>
              <LogOut className="hidden size-4 group-hover:block" />
            </button>
          </div>
        </nav>

        {/* canvas */}
        <main className="flex min-w-0 flex-1 flex-col pb-[60px] md:py-2 md:pb-2 md:pr-2">
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-canvas md:rounded-[var(--radius-canvas)] md:shadow-[var(--shadow-canvas)]">
            <Outlet />
          </div>
        </main>

        {/* docked simulator */}
        {panelOpen ? (
          <aside className="fixed inset-0 z-40 flex flex-col bg-canvas md:static md:z-auto md:my-2 md:mr-2 md:w-[380px] md:shrink-0 md:rounded-[var(--radius-canvas)] md:shadow-[var(--shadow-canvas)]">
            <Simulator onClose={() => setOpen(false)} />
          </aside>
        ) : null}

        {/* phone bottom nav */}
        <nav className="fixed inset-x-0 bottom-0 z-30 flex h-[60px] items-stretch justify-around border-t border-line bg-canvas md:hidden" aria-label="Main">
          {items.slice(0, 5).map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.end}
              className={({ isActive }) => cx("flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px]", isActive ? "text-ink" : "text-faint")}
            >
              <it.icon className="size-5" strokeWidth={1.8} />
              <span className="truncate">{it.label.split(" ")[0]}</span>
            </NavLink>
          ))}
          {canSimulate ? (
            <button onClick={() => setOpen(true)} className="flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] text-agent">
              <MessageCircle className="size-5" />
              Farmer
            </button>
          ) : null}
          <button onClick={() => void signOut()} className="flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] text-faint">
            <LogOut className="size-5" />
            Sign out
          </button>
        </nav>
      </div>
    </PanelContext.Provider>
  );
}

/** Top bar inside the canvas: breadcrumbs + page actions + demo clock. */
export function TopBar({ crumbs, actions }: { crumbs: { label: string; icon?: typeof Radar }[]; actions?: ReactNode }) {
  const { me } = useAuth();
  const clock = useDemoClock(!!me?.config.demo_mode && me.role === "officer");
  const { open, setOpen } = useSimPanel();
  return (
    <header className="flex h-[52px] shrink-0 items-center gap-3 border-b border-line px-4 md:px-6">
      <div className="md:hidden">
        <Logo />
      </div>
      <ol className="flex min-w-0 items-center gap-2 text-[15px]">
        {crumbs.map((c, i) => (
          <li key={c.label} className="flex min-w-0 items-center gap-2">
            {i > 0 ? <span className="text-faint">/</span> : null}
            {c.icon ? <c.icon className="size-4 shrink-0 text-muted" strokeWidth={1.8} /> : null}
            <span className={cx("truncate", i === crumbs.length - 1 ? "text-ink" : "text-muted")}>{c.label}</span>
          </li>
        ))}
      </ol>
      <div className="ml-auto flex items-center gap-2">
        {actions}
        {clock.data?.simulated ? (
          <span className="hidden h-7 items-center rounded-full border border-line px-2.5 text-xs text-muted sm:inline-flex" title="Demo clock">
            Demo day · <span className="ml-1 font-medium text-ink">{fmtDay(clock.data.today)}</span>
          </span>
        ) : null}
        {open ? (
          <IconButton label="Close farmer simulator" onClick={() => setOpen(false)} className="hidden md:inline-flex">
            <X className="size-4" />
          </IconButton>
        ) : null}
      </div>
    </header>
  );
}

/** Scrollable page body with the reference's generous gutters. */
export function PageBody({ children, wide }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className={cx("mx-auto flex flex-col gap-6 px-4 py-6 md:px-10 md:py-9", wide ? "max-w-[1400px]" : "max-w-[1160px]")}>{children}</div>
    </div>
  );
}
