import { CalendarDays, History, Route as RouteIcon, UserRound, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router";
import { useOperatorMe } from "../../api/hooks";
import { Logo } from "../../components/Shell";
import { cx } from "../../components/ui";

interface Tab {
  to: string;
  label: string;
  hi: string;
  icon: LucideIcon;
  end?: boolean;
  badge?: number;
}

const TABS: Tab[] = [
  { to: "/baler", label: "Today", hi: "आज", icon: RouteIcon, end: true },
  { to: "/baler/schedule", label: "Schedule", hi: "आगे", icon: CalendarDays },
  { to: "/baler/history", label: "History", hi: "पूरे हुए", icon: History },
  { to: "/baler/profile", label: "Profile", hi: "प्रोफ़ाइल", icon: UserRound },
];

function TabLink({ tab, compact }: { tab: Tab; compact?: boolean }) {
  return (
    <NavLink
      to={tab.to}
      end={tab.end}
      className={({ isActive }) =>
        compact
          ? cx("flex h-9 items-center gap-2 rounded-[var(--radius-control)] px-3 text-sm font-medium", isActive ? "bg-sunken text-ink" : "text-muted hover:text-ink")
          : cx("flex min-h-[60px] min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-0.5 text-[11px] font-medium", isActive ? "text-ink" : "text-faint")
      }
    >
      <span className="relative">
        <tab.icon className={compact ? "size-4" : "size-[22px]"} strokeWidth={1.8} />
        {tab.badge ? (
          <span className="absolute -right-2 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-ink px-1 text-[10px] font-semibold leading-none text-canvas tabular">
            {tab.badge}
          </span>
        ) : null}
      </span>
      <span className="max-w-full truncate leading-tight">{tab.label}</span>
      {compact ? null : <span className="max-w-full truncate text-[10px] font-normal leading-tight text-faint">{tab.hi}</span>}
    </NavLink>
  );
}

/**
 * Baler app: phone-first. A slim top bar and a bottom tab bar with big targets and Hindi labels;
 * on wide screens the same tabs move into the top bar.
 */
export function BalerLayout() {
  const me = useOperatorMe();
  const baler = me.data;
  return (
    <div className="flex h-dvh w-full flex-col bg-frame">
      <header className="flex h-[52px] shrink-0 items-center gap-3 border-b border-line bg-canvas px-4">
        <Logo size="size-8" />
        <div className="min-w-0">
          <div className="truncate text-[15px] font-medium leading-tight text-ink">{baler?.operator_name ?? "Baler"}</div>
          {baler ? (
            <div className="truncate text-xs leading-tight text-muted">
              {baler.active ? "Available · उपलब्ध" : "Off duty · छुट्टी"}
              {baler.chc_name ? ` · ${baler.chc_name}` : ""}
            </div>
          ) : null}
        </div>
        <nav className="ml-auto hidden items-center gap-1 md:flex" aria-label="Baler">
          {TABS.map((t) => (
            <TabLink key={t.to} tab={t} compact />
          ))}
        </nav>
      </header>
      <main className="min-h-0 flex-1 overflow-y-auto bg-canvas pb-[64px] md:pb-0">
        <Outlet />
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-30 flex items-stretch border-t border-line bg-canvas md:hidden" aria-label="Baler">
        {TABS.map((t) => (
          <TabLink key={t.to} tab={t} />
        ))}
      </nav>
    </div>
  );
}

/** Page column for baler screens: one comfortable thumb-width column, wider on desktop. */
export function BalerPage({ children, wide }: { children: ReactNode; wide?: boolean }) {
  return <div className={cx("mx-auto flex flex-col gap-4 px-4 py-4 md:gap-5 md:px-8 md:py-7", wide ? "max-w-[1100px]" : "max-w-[720px]")}>{children}</div>;
}
