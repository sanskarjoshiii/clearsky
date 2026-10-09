import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import type { BookingStatus, FieldStatus, RiskLevel } from "../api/types";
import { titleCase } from "../lib/format";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ------------------------------------------------------------------ buttons

type Variant = "primary" | "secondary" | "ghost" | "agent";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-canvas hover:bg-ink-2 disabled:bg-faint",
  secondary: "bg-canvas text-ink border border-line-strong hover:bg-hover disabled:text-faint",
  ghost: "text-ink-2 hover:bg-hover disabled:text-faint",
  agent: "bg-agent text-canvas hover:bg-agent-strong disabled:bg-agent-line",
};
const SIZES = { sm: "h-7 px-2.5 text-[13px] gap-1.5", md: "h-9 px-3.5 text-sm gap-2", lg: "h-12 px-5 text-base gap-2" };

export function Button({
  variant = "secondary",
  size = "md",
  loading,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: keyof typeof SIZES; loading?: boolean }) {
  return (
    <button
      className={cx(
        "inline-flex select-none items-center justify-center rounded-[var(--radius-control)] font-medium transition-colors disabled:cursor-not-allowed",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
}

export function IconButton({
  label,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      aria-label={label}
      title={label}
      className={cx("inline-flex size-8 items-center justify-center rounded-[var(--radius-control)] text-muted hover:bg-hover hover:text-ink", className)}
      {...rest}
    >
      {children}
    </button>
  );
}

// ------------------------------------------------------------------ chips & pills

export function Chip({ children, tone = "neutral", className }: { children: ReactNode; tone?: "neutral" | "agent"; className?: string }) {
  return (
    <span
      className={cx(
        "inline-flex h-[22px] items-center whitespace-nowrap rounded-[var(--radius-chip)] px-1.5 text-xs font-medium",
        tone === "agent" ? "bg-agent-soft text-agent-strong" : "bg-sunken text-ink-2",
        className,
      )}
    >
      {children}
    </span>
  );
}

const RISK_STYLE: Record<RiskLevel, string> = {
  RED: "bg-risk-soft text-risk border-risk-line",
  YELLOW: "bg-warn-soft text-warn border-warn-line",
  GREEN: "bg-ok-soft text-ok border-ok-line",
};
const RISK_DOT: Record<RiskLevel, string> = { RED: "bg-risk-fill", YELLOW: "bg-warn-fill", GREEN: "bg-ok" };

/** Burn-risk level. The only place green/amber/red appear (plus map pins). */
export function RiskPill({ level, score, pulse }: { level: RiskLevel; score?: number; pulse?: boolean }) {
  return (
    <span className={cx("inline-flex h-[22px] items-center gap-1.5 rounded-full border px-2 text-xs font-medium tabular", RISK_STYLE[level])}>
      <span className={cx("size-1.5 rounded-full", RISK_DOT[level], pulse && level === "RED" && "animate-pulse-risk")} />
      {titleCase(level === "YELLOW" ? "AMBER" : level)}
      {score != null ? <span className="opacity-70">{score}</span> : null}
    </span>
  );
}

const STATUS_LABEL: Record<FieldStatus | BookingStatus, string> = {
  REGISTERED: "Registered",
  HARVESTED: "Harvested",
  BOOKED: "Booked",
  CLEARED: "Cleared",
  FIRE_REPORTED: "Fire reported",
  CONFIRMED: "Confirmed",
  DONE: "Done",
  CANCELLED: "Cancelled",
};

export function StatusChip({ status }: { status: FieldStatus | BookingStatus }) {
  return <Chip>{STATUS_LABEL[status]}</Chip>;
}

// ------------------------------------------------------------------ surfaces

export function Card({
  title,
  actions,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cx("min-w-0 rounded-[var(--radius-card)] border border-line bg-canvas", className)}>
      {title || actions ? (
        <header className="flex min-h-12 items-center justify-between gap-3 px-4 pt-3">
          <h2 className="text-[15px] font-medium tracking-[var(--tracking-title)] text-ink">{title}</h2>
          {actions ? <div className="flex items-center gap-1">{actions}</div> : null}
        </header>
      ) : null}
      <div className={bodyClassName ?? "p-4"}>{children}</div>
    </section>
  );
}

export interface KpiItem {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  badge?: ReactNode;
}

/** KPI strip: cells divided by hairlines inside one bordered box (the reference's metric row). */
export function KpiStrip({ items }: { items: KpiItem[] }) {
  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-[var(--radius-card)] border border-line bg-canvas md:grid-cols-[repeat(auto-fit,minmax(150px,1fr))]">
      {items.map((it) => (
        <div key={it.label} className="-mb-px -mr-px border-b border-r border-line px-4 py-3.5">
          <div className="flex items-center gap-2 text-[13px] text-muted">
            <span className="truncate">{it.label}</span>
            {it.badge}
          </div>
          <div className="tabular mt-1 text-[26px] font-semibold leading-tight tracking-[var(--tracking-title)] text-ink">{it.value}</div>
          {it.hint ? <div className="mt-0.5 truncate text-xs text-faint">{it.hint}</div> : null}
        </div>
      ))}
    </div>
  );
}

export function PageTitle({ children, sub, actions }: { children: ReactNode; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[30px] font-semibold leading-tight tracking-[var(--tracking-display)] text-ink sm:text-[38px]">{children}</h1>
        {sub ? <p className="mt-1.5 max-w-3xl text-sm text-muted">{sub}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

// ------------------------------------------------------------------ inputs

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[13px] font-medium text-ink-2">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-faint">{hint}</span> : null}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "h-9 w-full rounded-[var(--radius-control)] border border-line-strong bg-canvas px-3 text-sm text-ink placeholder:text-faint focus:border-ink focus:outline-none",
        props.className,
      )}
    />
  );
}

export function Toggle({ checked, onChange, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx(
        "relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50",
        checked ? "bg-ok" : "bg-line-strong",
      )}
    >
      <span className={cx("absolute left-0 top-0.5 size-5 rounded-full bg-canvas shadow transition-transform", checked ? "translate-x-[22px]" : "translate-x-0.5")} />
    </button>
  );
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-[var(--radius-control)] border border-line bg-sunken p-0.5" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={cx(
            "h-7 rounded-[6px] px-2.5 text-[13px] font-medium",
            value === o.value ? "bg-canvas text-ink shadow-[var(--shadow-canvas)]" : "text-muted hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ states

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-[var(--radius-control)] bg-sunken", className)} />;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <Inbox className="size-5 text-faint" aria-hidden />
      <p className="text-sm font-medium text-ink-2">{title}</p>
      {children ? <div className="max-w-sm text-[13px] text-muted">{children}</div> : null}
    </div>
  );
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : "Something went wrong";
  return (
    <div className="flex items-center gap-3 rounded-[var(--radius-control)] border border-risk-line bg-risk-soft px-3 py-2.5 text-[13px] text-risk" role="alert">
      <AlertTriangle className="size-4 shrink-0" aria-hidden />
      <span className="flex-1">{msg}</span>
      {onRetry ? (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------ dialog & toast

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  onConfirm,
  onClose,
  busy,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
  busy?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/20 p-4 sm:items-center" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md animate-rise rounded-[var(--radius-card)] bg-canvas p-5 shadow-[var(--shadow-pop)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-base font-semibold tracking-[var(--tracking-title)]">{title}</h3>
        <div className="mt-2 text-sm text-ink-2">{children}</div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} loading={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface Toast {
  id: number;
  text: string;
  tone: "info" | "error";
}
const ToastContext = createContext<(text: string, tone?: Toast["tone"]) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "info") => {
    const id = Date.now() + Math.random();
    // the same message is never stacked twice (e.g. a redirect notice fired by two renders)
    setToasts((t) => (t.some((x) => x.text === text) ? t : [...t, { id, text, tone }]));
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 left-1/2 z-[60] flex w-[min(92vw,420px)] -translate-x-1/2 flex-col gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cx(
              "pointer-events-auto animate-rise rounded-[var(--radius-control)] px-4 py-2.5 text-sm shadow-[var(--shadow-pop)]",
              t.tone === "error" ? "bg-risk-soft text-risk" : "bg-ink text-canvas",
            )}
          >
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
