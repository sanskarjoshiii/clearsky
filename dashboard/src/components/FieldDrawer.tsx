import { BellRing, X } from "lucide-react";
import { useField, useStats } from "../api/hooks";
import { daysBetween, fmtDay, fmtInr, fmtNum, fmtTime } from "../lib/format";
import { impactAmount } from "../lib/impact";
import { Button, Chip, ErrorNote, IconButton, RiskPill, Skeleton, StatusChip } from "./ui";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2 text-[13px] last:border-0">
      <span className="text-muted">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}

/** Field detail drawer: why it is at risk, who farms it (masked), and its booking. */
export function FieldDrawer({ id, today, onClose, onAlert }: { id: string; today?: string; onClose: () => void; onAlert: (villageId: string) => void }) {
  const q = useField(id);
  const factors = useStats(false).data?.impact_factors ?? {};
  const f = q.data;
  // a cleared field: the snapshot stored when its booking was done
  const cleared = f?.bookings.find((b) => b.status === "DONE" && b.impact);
  const avoided = Object.entries(factors).filter(([key]) => cleared?.impact?.[key] != null);
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/10 md:bg-transparent" onClick={onClose}>
      <aside
        className="flex h-full w-full max-w-[420px] animate-rise flex-col border-l border-line bg-canvas shadow-[var(--shadow-pop)]"
        onClick={(e) => e.stopPropagation()}
        aria-label="Field detail"
      >
        <header className="flex h-[52px] shrink-0 items-center gap-2 border-b border-line px-4">
          <span className="text-[15px] font-medium">Field</span>
          <span className="tabular text-[13px] text-muted">{id}</span>
          <IconButton label="Close" className="ml-auto" onClick={onClose}>
            <X className="size-4" />
          </IconButton>
        </header>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
          {q.isLoading ? <Skeleton className="h-40" /> : null}
          {q.error ? <ErrorNote error={q.error} onRetry={() => void q.refetch()} /> : null}
          {f ? (
            <>
              <div>
                <div className="flex items-center gap-2">
                  <RiskPill level={f.risk_level} score={f.risk_score} pulse />
                  {f.status === "BOOKED" && f.booking_state === "offered" ? <Chip>Offer sent</Chip> : <StatusChip status={f.status} />}
                  {f.source === "whatsapp" ? <Chip tone="agent">via WhatsApp</Chip> : null}
                </div>
                <h2 className="mt-3 text-[22px] font-semibold tracking-[var(--tracking-display)]">
                  {f.farmer_name ?? "Unknown farmer"} · {f.village_name}
                </h2>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {f.risk_reasons.map((r) => (
                    <Chip key={r}>{r}</Chip>
                  ))}
                </div>
              </div>

              <div>
                <Row label="Farmer phone">{f.farmer_phone}{f.synthetic ? <span className="ml-1 text-faint">(demo)</span> : null}</Row>
                <Row label="Paddy">{fmtNum(f.acres)} acres</Row>
                <Row label="Harvest">
                  {fmtDay(f.harvest_date)} {f.harvest_confirmed ? <span className="text-faint">· confirmed</span> : null}
                </Row>
                <Row label="Sowing deadline">
                  {fmtDay(f.sowing_deadline)}
                  {today ? <span className="text-faint"> · {daysBetween(today, f.sowing_deadline)} days left</span> : null}
                </Row>
                <Row label="Village fire history">{Math.round(f.village.fire_history_score * 100)} / 100</Row>
              </div>

              {cleared && avoided.length ? (
                <div aria-label="Pollution avoided">
                  <h3 className="mb-1 text-[13px] font-medium text-muted">Pollution avoided by clearing this field (estimate)</h3>
                  {avoided.map(([key, factor]) => (
                    <Row key={key} label={factor.label}>
                      <span className="tabular">{impactAmount(cleared.impact?.[key] ?? 0, factor.unit)}</span>
                      <span className="block text-xs text-faint">
                        {fmtNum(cleared.est_tonnes)} t straw × {fmtNum(factor.kg_per_tonne)} kg/t · {factor.source}
                      </span>
                    </Row>
                  ))}
                </div>
              ) : null}

              {f.bookings.length ? (
                <div>
                  <h3 className="mb-2 text-[13px] font-medium text-muted">Offers and bookings</h3>
                  {f.bookings.map((b) => (
                    <div key={b.booking_id} className="mb-2 rounded-[var(--radius-control)] border border-line p-3 text-[13px]">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {fmtDay(b.date)}
                          {b.stop_order ? ` · stop ${b.stop_order}` : ""}
                        </span>
                        <StatusChip status={b.status} />
                      </div>
                      {/* who was asked, when, and what they answered */}
                      {b.offered_at ? (
                        <div className="mt-1 text-xs text-faint">
                          Offered {fmtDay(b.offered_at)} {fmtTime(b.offered_at)}
                          {b.responded_at ? ` · answered ${fmtTime(b.responded_at)}` : b.status === "OFFERED" && b.expires_at ? ` · answer by ${fmtTime(b.expires_at)}` : ""}
                          {b.decline_reason ? ` · ${b.decline_reason.replace(/_/g, " ")}` : ""}
                          {b.decline_note ? ` (${b.decline_note})` : ""}
                        </div>
                      ) : null}
                      <div className="mt-1 text-muted">
                        {b.operator_name} ({b.chc_name}) → {b.buyer_name ?? "village storage"}
                      </div>
                      <div className="mt-1 text-muted tabular">
                        {fmtNum(b.est_tonnes)} t · payout {b.farmer_payout > 0 ? `${fmtInr(b.farmer_payout)} (demo estimate)` : "free clearance"}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {f.status === "REGISTERED" || f.status === "HARVESTED" ? (
                <Button variant="primary" className="w-full" onClick={() => onAlert(f.village_id)}>
                  <BellRing className="size-4" /> Alert {f.village_name}
                </Button>
              ) : null}
              {f.alerts.length ? (
                <p className="text-xs text-faint">
                  Last village alert {fmtDay(f.alerts[f.alerts.length - 1]?.created_at)} · {f.alerts[f.alerts.length - 1]?.farmers_notified} farmers notified
                </p>
              ) : null}
            </>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
