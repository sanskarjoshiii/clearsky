import { LogOut, MessageCircle, X, type LucideIcon } from "lucide-react";
import { createContext, useContext, useRef, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router";
import { useDemoClock } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { fmtDay, initials } from "../lib/format";
import { useSmoothScroll } from "../lib/smoothScroll";
import { cx, IconButton } from "./ui";

export interface NavItem {
  to: string;
  label: string;
  /** Short label for the phone bottom bar (defaults to the first word of `label`). */
  short?: string;
  icon: LucideIcon;
  end?: boolean;
  badge?: number;
}

const PanelContext = createContext<{ open: boolean; setOpen: (v: boolean) => void }>({ open: false, setOpen: () => undefined });
export const SimPanelProvider = PanelContext.Provider;
export const useSimPanel = () => useContext(PanelContext);

/** The clearsky logo (public/logo.png, already cut to a circle). */
export function Logo({ size = "size-9" }: { size?: string }) {
  return <img src="/logo.png" alt="clearsky" className={`${size} shrink-0 rounded-full`} draggable={false} />;
}

function Badge({ n }: { n: number }) {
  return (
    <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-ink px-1 text-[10px] font-semibold leading-none text-canvas tabular">
      {n > 99 ? "99+" : n}
    </span>
  );
}

/**
 * Desktop-first app frame shared by the admin and buyer apps: icon rail · floating canvas · optional
 * docked panel. Each app passes its own navigation, so no role ever sees another role's items.
 * `panel` (admin only: the farmer simulator) is shown when the sim panel context says it is open.
 */
export function RailLayout({ items, panel, label }: { items: NavItem[]; panel?: ReactNode; label: string }) {
  const { me, signOut } = useAuth();
  const { open, setOpen } = useSimPanel();
  if (!me) return null;
  const canSimulate = panel !== undefined;
  const panelOpen = canSimulate && open;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-frame">
      {/* rail */}
      <nav className="hidden w-[60px] shrink-0 flex-col items-center gap-1 py-4 md:flex" aria-label={label}>
        <Logo />
        <div className="mt-5 flex flex-col gap-1">
          {items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.end}
              title={it.label}
              aria-label={it.badge ? `${it.label} (${it.badge})` : it.label}
              className={({ isActive }) =>
                cx(
                  "relative flex size-10 items-center justify-center rounded-[10px] transition-colors",
                  isActive ? "bg-canvas text-ink shadow-[var(--shadow-canvas)]" : "text-faint hover:text-ink",
                )
              }
            >
              <it.icon className="size-[19px]" strokeWidth={1.8} />
              {it.badge ? <Badge n={it.badge} /> : null}
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

      {/* docked panel */}
      {panelOpen ? (
        <aside className="fixed inset-0 z-40 flex flex-col bg-canvas md:static md:z-auto md:my-2 md:mr-2 md:w-[380px] md:shrink-0 md:rounded-[var(--radius-canvas)] md:shadow-[var(--shadow-canvas)]">
          {panel}
        </aside>
      ) : null}

      {/* phone bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex h-[60px] items-stretch justify-around border-t border-line bg-canvas md:hidden" aria-label={label}>
        {items.slice(0, canSimulate ? 4 : 5).map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.end}
            className={({ isActive }) => cx("flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 text-[11px]", isActive ? "text-ink" : "text-faint")}
          >
            <span className="relative">
              <it.icon className="size-5" strokeWidth={1.8} />
              {it.badge ? <Badge n={it.badge} /> : null}
            </span>
            <span className="max-w-full truncate">{it.short ?? it.label.split(" ")[0]}</span>
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
  );
}

/** Top bar inside the canvas: breadcrumbs + page actions + demo clock. */
export function TopBar({ crumbs, actions }: { crumbs: { label: string; icon?: LucideIcon }[]; actions?: ReactNode }) {
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
  const scroller = useRef<HTMLDivElement>(null);
  useSmoothScroll(scroller);
  return (
    <div ref={scroller} data-scroll-surface className="min-h-0 flex-1 overflow-y-auto">
      <div className={cx("mx-auto flex flex-col gap-6 px-4 py-6 md:px-10 md:py-9", wide ? "max-w-[1400px]" : "max-w-[1160px]")}>{children}</div>
    </div>
  );
}
