import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useStats } from "../api/hooks";
import { useAuth } from "../auth/AuthProvider";
import { ErrorNote, Skeleton } from "../components/ui";
import { fmtInr, fmtInt } from "../lib/format";

/** Count up once from the previous value (reduced motion: jump straight to the value). */
function useCountUp(value: number, ms = 1200): number {
  const [shown, setShown] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(a + (value - a) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
      else from.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return shown;
}

function Counter({ label, value, format, note }: { label: string; value: number; format: (n: number) => string; note?: string }) {
  const n = useCountUp(value);
  return (
    <div className="border-b border-r border-line px-6 py-8 sm:px-8 sm:py-10">
      <div className="text-sm text-muted">{label}</div>
      <div className="tabular mt-2 text-[44px] font-semibold leading-none tracking-[var(--tracking-display)] text-ink sm:text-[64px]">{format(n)}</div>
      {note ? <div className="mt-2 text-xs text-faint">{note}</div> : null}
    </div>
  );
}

/** Public impact page, built for screen recording (PLAN.md Phase 7). */
export function Impact() {
  const stats = useStats();
  const { me } = useAuth();
  const s = stats.data;
  return (
    <div className="min-h-dvh bg-frame p-2 sm:p-4">
      <div className="mx-auto flex min-h-[calc(100dvh-1rem)] max-w-[1280px] flex-col rounded-[var(--radius-canvas)] bg-canvas shadow-[var(--shadow-canvas)]">
        <header className="flex items-center justify-between px-6 pt-6 sm:px-10 sm:pt-9">
          <div className="flex items-center gap-2 text-sm text-muted">
            <span className="size-2 rounded-full bg-ok" /> Live · ClearSky, Sangrur
          </div>
          {me ? (
            <Link to="/" className="text-sm text-muted hover:text-ink">
              Back to dashboard
            </Link>
          ) : null}
        </header>
        <div className="px-6 pb-8 pt-6 sm:px-10">
          <h1 className="max-w-4xl text-[36px] font-semibold leading-[1.05] tracking-[var(--tracking-display)] sm:text-[60px]">
            Straw picked up, not burnt.
          </h1>
          <p className="mt-3 max-w-2xl text-base text-muted">
            Every acre here was booked by a farmer on WhatsApp and cleared by a baler before the wheat-sowing deadline.
          </p>
        </div>
        {stats.error ? (
          <div className="px-6 sm:px-10">
            <ErrorNote error={stats.error} onRetry={() => void stats.refetch()} />
          </div>
        ) : null}
        {s ? (
          <div className="mx-6 mb-6 grid grid-cols-1 overflow-hidden rounded-[var(--radius-card)] border-l border-t border-line sm:mx-10 sm:grid-cols-2 lg:grid-cols-3">
            <Counter label="Acres booked for pickup" value={s.acres_booked} format={fmtInt} />
            <Counter label="Acres cleared" value={s.acres_cleared} format={fmtInt} />
            <Counter label="Tonnes of straw routed to industry" value={s.tonnes_booked} format={fmtInt} />
            <Counter label="Farmers on WhatsApp" value={s.farmers} format={fmtInt} />
            <Counter label="Fields saved after an officer alert" value={s.fields_saved_after_alert} format={fmtInt} />
            <Counter label="Estimated farmer payouts" value={s.payouts_estimated_inr} format={fmtInr} note="demo prices, not market rates" />
            {s.pm25_avoided_kg != null ? (
              <Counter label="PM2.5 avoided (kg, estimate)" value={s.pm25_avoided_kg} format={fmtInt} note="published emission factor, cited in the README" />
            ) : null}
          </div>
        ) : (
          <div className="mx-6 mb-6 sm:mx-10">
            <Skeleton className="h-80" />
          </div>
        )}
      </div>
    </div>
  );
}
