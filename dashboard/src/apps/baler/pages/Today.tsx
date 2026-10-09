import { BellRing, Check, ChevronLeft, ChevronRight, Phone } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { useMarkDone, useOperatorAlerts, useOperatorMe, useRoute, useStats, useUpdateOperator } from "../../../api/hooks";
import type { Stop } from "../../../api/types";
import { MapView } from "../../../components/MapView";
import { Button, Card, ConfirmDialog, cx, Empty, ErrorNote, Skeleton, Toggle, useToast } from "../../../components/ui";
import { addDays, fmtDayLong, fmtNum } from "../../../lib/format";
import { BalerPage } from "../Layout";

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

// 44 px touch target for the day stepper (design-system rule 7)
const STEP = "flex size-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] text-ink-2 hover:bg-hover";

/** Baler home: the day's stops with Call and Done, deliberately simple and phone-first. */
export function Today() {
  const stats = useStats(false);
  const [params, setParams] = useSearchParams();
  // the Schedule tab links here with ?date=YYYY-MM-DD
  const picked = params.get("date");
  const date = picked && /^\d{4}-\d{2}-\d{2}$/.test(picked) ? picked : null;
  const setDate = (d: string | null) => setParams(d ? { date: d } : {}, { replace: true });
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
      <BalerPage wide>
          {me.error ? <ErrorNote error={me.error} onRetry={() => void me.refetch()} /> : null}

          {/* date + availability */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-1 items-center gap-1 rounded-[var(--radius-card)] border border-line bg-canvas p-1 sm:flex-none">
              <button aria-label="Previous day" className={STEP} onClick={() => day && setDate(addDays(day, -1))}>
                <ChevronLeft className="size-5" />
              </button>
              <div className="min-w-[124px] flex-1 text-center text-sm font-medium">{day ? fmtDayLong(day) : "…"}</div>
              <button aria-label="Next day" className={STEP} onClick={() => day && setDate(addDays(day, 1))}>
                <ChevronRight className="size-5" />
              </button>
            </div>
            {date && date !== stats.data?.today ? (
              <Button variant="ghost" size="lg" onClick={() => setDate(null)}>
                Today · आज
              </Button>
            ) : null}
            {baler ? (
              <div className="flex min-h-11 w-full items-center rounded-[var(--radius-card)] border border-line bg-canvas px-3 py-2 sm:ml-auto sm:w-auto">
                <label className="flex items-center gap-2 text-sm">
                  <Toggle
                    checked={baler.active}
                    label="Available for new bookings"
                    disabled={update.isPending}
                    onChange={(v) => update.mutate({ active: v }, { onError: (e) => toast(e.message, "error") })}
                  />
                  {baler.active ? "Available · उपलब्ध" : "Off duty · छुट्टी"}
                </label>
              </div>
            ) : null}
          </div>

          {/* officer alerts flagged to this baler */}
          {(alerts.data ?? []).map((a) => (
            <div key={a.alert_id} className="flex items-start gap-3 rounded-[var(--radius-card)] border border-warn-line bg-warn-soft px-4 py-3 text-sm" role="status">
              <BellRing className="mt-0.5 size-4 shrink-0 text-warn" />
              <div>
                <div className="font-medium text-ink">
                  Admin alert: {a.village_name} needs balers{a.distance_km != null ? ` · ${fmtNum(a.distance_km)} km away` : ""}
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
                      <Button variant="primary" size="lg" onClick={() => setDate(baler.next_stop_date ?? null)}>
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
      </BalerPage>
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
