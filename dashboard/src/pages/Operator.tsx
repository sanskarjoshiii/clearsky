import { BellRing, Check, ChevronLeft, ChevronRight, Minus, Phone, Plus, Route as RouteIcon } from "lucide-react";
import { useState } from "react";
import { useMarkDone, useOperatorAlerts, useOperatorMe, useRoute, useStats, useUpdateOperator } from "../api/hooks";
import type { Stop } from "../api/types";
import { MapView } from "../components/MapView";
import { TopBar } from "../components/Shell";
import { Button, Card, ConfirmDialog, cx, Empty, ErrorNote, Skeleton, Toggle, useToast } from "../components/ui";
import { addDays, fmtDayLong, fmtNum } from "../lib/format";

function StopCard({ stop, onDone }: { stop: Stop; onDone: () => void }) {
  const done = stop.status === "DONE";
  return (
    <li className={cx("rounded-[var(--radius-card)] border p-4", done ? "border-ok-line bg-ok-soft/40" : "border-line bg-canvas")}>
      <div className="flex items-start gap-3">
        <span
          className={cx(
            "flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-canvas",
            done ? "bg-ok" : "bg-agent",
          )}
        >
          {done ? <Check className="size-4" /> : stop.stop_order}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-base font-medium text-ink">{stop.farmer_name ?? "Farmer"}</div>
          <div className="text-[13px] text-muted">
            {stop.village_name} · {fmtNum(stop.acres)} acres · ~{fmtNum(stop.est_tonnes)} t
          </div>
        </div>
        <a
          href={`tel:${stop.farmer_phone}`}
          className="flex size-11 shrink-0 items-center justify-center rounded-full border border-line text-ink hover:bg-hover"
          aria-label={`Call ${stop.farmer_name ?? "farmer"}`}
        >
          <Phone className="size-[18px]" />
        </a>
      </div>
      {done ? (
        <div className="mt-3 text-sm font-medium text-ok">Field cleared · खेत साफ़ ✅</div>
      ) : (
        <Button variant="primary" size="lg" className="mt-3 w-full" onClick={onDone}>
          <Check className="size-5" /> Done · हो गया
        </Button>
      )}
    </li>
  );
}

/** Baler operator dashboard: deliberately simple and phone-first (PLAN.md Phase 7). */
export function OperatorPage() {
  const stats = useStats(false);
  const [date, setDate] = useState<string | null>(null);
  const day = date ?? stats.data?.today ?? null;
  const me = useOperatorMe();
  const route = useRoute(day ?? "");
  const alerts = useOperatorAlerts();
  const update = useUpdateOperator();
  const markDone = useMarkDone();
  const toast = useToast();
  const [confirm, setConfirm] = useState<Stop | null>(null);
  const baler = me.data;
  const stops = route.data?.stops ?? [];

  return (
    <>
      <TopBar crumbs={[{ label: "Route", icon: RouteIcon }, { label: baler?.operator_name ?? "Operator" }]} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1100px] flex-col gap-5 px-4 py-5 md:px-8 md:py-8">
          {me.error ? <ErrorNote error={me.error} onRetry={() => void me.refetch()} /> : null}

          {/* date + availability */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 rounded-[var(--radius-card)] border border-line bg-canvas p-1">
              <Button variant="ghost" size="sm" aria-label="Previous day" onClick={() => day && setDate(addDays(day, -1))}>
                <ChevronLeft className="size-4" />
              </Button>
              <div className="min-w-[132px] text-center text-sm font-medium">{day ? fmtDayLong(day) : "…"}</div>
              <Button variant="ghost" size="sm" aria-label="Next day" onClick={() => day && setDate(addDays(day, 1))}>
                <ChevronRight className="size-4" />
              </Button>
            </div>
            {date && date !== stats.data?.today ? (
              <Button size="sm" variant="ghost" onClick={() => setDate(null)}>
                Today · आज
              </Button>
            ) : null}
            {baler ? (
              <div className="flex w-full flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-[var(--radius-card)] border border-line bg-canvas px-3 py-2 sm:ml-auto sm:w-auto">
                <label className="flex items-center gap-2 text-sm">
                  <Toggle
                    checked={baler.active}
                    label="Available for new bookings"
                    disabled={update.isPending}
                    onChange={(v) => update.mutate({ active: v }, { onError: (e) => toast(e.message, "error") })}
                  />
                  {baler.active ? "Available · उपलब्ध" : "Off duty"}
                </label>
                <div className="flex items-center gap-1.5 text-sm">
                  <Button size="sm" variant="ghost" aria-label="Fewer acres per day" disabled={update.isPending || baler.acres_per_day <= 1}
                    onClick={() => update.mutate({ acres_per_day: baler.acres_per_day - 1 })}>
                    <Minus className="size-4" />
                  </Button>
                  <span className="tabular min-w-[64px] text-center">{fmtNum(baler.acres_per_day)} ac/day</span>
                  <Button size="sm" variant="ghost" aria-label="More acres per day" disabled={update.isPending || baler.acres_per_day >= 60}
                    onClick={() => update.mutate({ acres_per_day: baler.acres_per_day + 1 })}>
                    <Plus className="size-4" />
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

          {/* officer alerts flagged to this baler */}
          {(alerts.data ?? []).map((a) => (
            <div key={a.alert_id} className="flex items-start gap-3 rounded-[var(--radius-card)] border border-warn-line bg-warn-soft px-4 py-3 text-sm" role="status">
              <BellRing className="mt-0.5 size-4 shrink-0 text-warn" />
              <div>
                <div className="font-medium text-ink">
                  Officer alert: {a.village_name} needs balers{a.distance_km != null ? ` · ${fmtNum(a.distance_km)} km away` : ""}
                </div>
                <div className="text-ink-2">
                  {a.unbooked_acres != null ? `${fmtNum(a.unbooked_acres)} unbooked acres. ` : ""}Farmers were offered a booking on WhatsApp;
                  keep capacity free and new stops will appear here.
                </div>
              </div>
            </div>
          ))}

          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
            <Card
              title={<>Today's stops · आज के स्टॉप</>}
              actions={
                route.data ? (
                  <span className="text-[13px] text-muted tabular">
                    {route.data.remaining} left · {fmtNum(route.data.booked_acres)} ac
                  </span>
                ) : null
              }
              bodyClassName="p-3 sm:p-4"
            >
              {route.isLoading || !day ? <Skeleton className="h-40" /> : null}
              {route.error ? <ErrorNote error={route.error} onRetry={() => void route.refetch()} /> : null}
              {route.data && stops.length === 0 ? (
                <Empty title="No stops on this day">
                  New bookings from farmers near your base appear here automatically.
                  {baler?.next_stop_date && baler.next_stop_date !== day ? (
                    <div className="mt-3">
                      <Button variant="primary" size="sm" onClick={() => setDate(baler.next_stop_date ?? null)}>
                        Next stops: {fmtDayLong(baler.next_stop_date)}
                      </Button>
                    </div>
                  ) : null}
                </Empty>
              ) : null}
              <ul className="space-y-3">
                {stops.map((s) => (
                  <StopCard key={s.booking_id} stop={s} onDone={() => setConfirm(s)} />
                ))}
              </ul>
            </Card>
            <Card title="Route" bodyClassName="p-0">
              <MapView
                className="h-[300px] lg:h-[480px]"
                stops={stops}
                route={route.data?.route}
                base={baler ? { lat: baler.lat, lng: baler.lng } : null}
              />
            </Card>
          </div>
        </div>
      </div>
      <ConfirmDialog
        open={!!confirm}
        title={`Mark ${confirm?.farmer_name ?? "this field"} done?`}
        confirmLabel="Yes, field cleared"
        busy={markDone.isPending}
        onClose={() => setConfirm(null)}
        onConfirm={() =>
          confirm &&
          markDone.mutate(confirm.booking_id, {
            onSuccess: () => {
              toast("Field cleared. The farmer got a WhatsApp message.");
              setConfirm(null);
            },
            onError: (e) => toast(e.message, "error"),
          })
        }
      >
        The farmer is told on WhatsApp that the field is cleared, and the straw is counted for the buyer.
      </ConfirmDialog>
    </>
  );
}
