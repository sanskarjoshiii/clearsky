import { ChevronRight } from "lucide-react";
import { Link } from "react-router";
import { useSchedule } from "../../../api/hooks";
import { Empty, ErrorNote, Skeleton } from "../../../components/ui";
import { fmtDayLong, fmtNum } from "../../../lib/format";
import { BalerPage } from "../Layout";

/** The next 14 days at a glance: stops and booked acres per day. A day opens its route. */
export function Schedule() {
  const schedule = useSchedule(14);
  const days = schedule.data ?? [];
  const busy = days.filter((d) => d.stops > 0);
  return (
    <BalerPage>
      <div>
        <h1 className="text-[22px] font-semibold tracking-[var(--tracking-display)]">Next 14 days · अगले 14 दिन</h1>
        <p className="mt-1 text-[13px] text-muted">
          {schedule.data ? `${busy.length} working days · ${busy.reduce((a, d) => a + d.stops, 0)} stops` : "Stops booked to you, day by day."}
        </p>
      </div>
      {schedule.error ? <ErrorNote error={schedule.error} onRetry={() => void schedule.refetch()} /> : null}
      {schedule.isLoading ? <Skeleton className="h-64" /> : null}
      {schedule.data && busy.length === 0 ? (
        <Empty title="Nothing booked yet">New bookings from farmers near your base appear here automatically.</Empty>
      ) : null}
      <ul className="overflow-hidden rounded-[var(--radius-card)] border border-line">
        {days.map((d) => {
          const pct = Math.min(1, d.booked_acres / Math.max(1, d.capacity_acres));
          return (
            <li key={d.date} className="border-b border-line last:border-0">
              <Link to={`/baler?date=${d.date}`} className="flex min-h-[60px] items-center gap-3 px-4 py-2.5 hover:bg-hover" aria-label={`${fmtDayLong(d.date)}: ${d.stops} stops`}>
                <div className="w-[104px] shrink-0 text-sm font-medium text-ink">{fmtDayLong(d.date)}</div>
                <div className="min-w-0 flex-1">
                  {d.stops ? (
                    <>
                      <div className="flex items-baseline justify-between gap-2 text-[13px]">
                        <span className="text-ink">
                          {d.stops} stop{d.stops === 1 ? "" : "s"}
                          {d.done ? <span className="text-muted"> · {d.done} done</span> : null}
                        </span>
                        <span className="tabular text-muted">
                          {fmtNum(d.booked_acres)} / {fmtNum(d.capacity_acres)} ac
                        </span>
                      </div>
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sunken">
                        <div className="h-full rounded-full bg-data-2" style={{ width: `${pct * 100}%` }} />
                      </div>
                      <div className="mt-1 truncate text-xs text-faint">{d.villages.join(" · ")}</div>
                    </>
                  ) : (
                    <span className="text-[13px] text-faint">Free · खाली</span>
                  )}
                </div>
                <ChevronRight className="size-4 shrink-0 text-faint" />
              </Link>
            </li>
          );
        })}
      </ul>
    </BalerPage>
  );
}
