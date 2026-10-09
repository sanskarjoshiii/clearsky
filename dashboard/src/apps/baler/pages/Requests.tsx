import { Check, Clock, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useAcceptOffer, useDeclineOffer, useOperatorMe, useRequests } from "../../../api/hooks";
import type { OfferRequest } from "../../../api/types";
import { MapView } from "../../../components/MapView";
import { Button, cx, Empty, ErrorNote, Skeleton, useToast } from "../../../components/ui";
import { fmtDay, fmtDayLong, fmtNum } from "../../../lib/format";
import { BalerPage } from "../Layout";

/** "1 h 12 min" until the offer expires, re-rendered every half minute. */
function useCountdown(expiresAt: string | null, serverNow: string | undefined): string {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((n) => n + 1), 30_000);
    return () => window.clearInterval(id);
  }, []);
  if (!expiresAt) return "";
  // the server clock can be a demo date: count from the server's "now", plus the time since it was read
  const base = serverNow ? Date.parse(serverNow) + tick * 30_000 : Date.now();
  const mins = Math.max(0, Math.round((Date.parse(expiresAt) - base) / 60_000));
  if (mins <= 0) return "expiring";
  return mins >= 60 ? `${Math.floor(mins / 60)} h ${mins % 60} min` : `${mins} min`;
}

function RequestCard({
  r,
  serverNow,
  reasons,
}: {
  r: OfferRequest;
  serverNow?: string;
  reasons: { value: string; label: string }[];
}) {
  const accept = useAcceptOffer();
  const decline = useDeclineOffer();
  const toast = useToast();
  const left = useCountdown(r.expires_at, serverNow);
  const [declining, setDeclining] = useState(false);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const busy = accept.isPending || decline.isPending;

  const doAccept = () =>
    accept.mutate(r.booking_id, {
      onSuccess: () => toast(`Accepted. ${r.farmer_name ?? "The farmer"} got a WhatsApp confirmation.`),
      onError: (e) => toast(e.message, "error"),
    });
  const doDecline = () =>
    decline.mutate(
      { id: r.booking_id, reason, note: note.trim() || undefined },
      { onSuccess: () => toast("Declined. The field goes to another baler."), onError: (e) => toast(e.message, "error") },
    );

  return (
    <li className="rounded-[var(--radius-card)] border border-line bg-canvas p-4" aria-label={`Request from ${r.farmer_name ?? "farmer"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-base font-medium text-ink">{r.farmer_name ?? "Farmer"}</div>
          <div className="text-[13px] text-muted">
            {r.village_name} · {fmtNum(r.distance_km)} km from base
          </div>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-line px-2 py-0.5 text-xs text-muted tabular" title="Time left to answer">
          <Clock className="size-3" /> {left}
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
        {[
          ["Pickup · दिन", fmtDayLong(r.date)],
          ["Acres · एकड़", `${fmtNum(r.acres)} ac`],
          ["Straw", `~${fmtNum(r.est_tonnes)} t`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-[var(--radius-control)] bg-sunken px-2 py-2">
            <dt className="text-[11px] text-muted">{label}</dt>
            <dd className="mt-0.5 text-sm font-medium text-ink tabular">{value}</dd>
          </div>
        ))}
      </dl>
      {r.harvest_date ? <p className="mt-2 text-xs text-faint">Harvest {fmtDay(r.harvest_date)}</p> : null}

      {declining ? (
        <div className="mt-3 space-y-2">
          <div className="text-[13px] font-medium text-ink-2">Why not? · कारण</div>
          <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Reason for declining">
            {reasons.map((o) => (
              <button
                key={o.value}
                type="button"
                role="radio"
                aria-checked={reason === o.value}
                onClick={() => setReason(o.value)}
                className={cx(
                  "min-h-11 rounded-[var(--radius-control)] border px-2 text-[13px] font-medium",
                  reason === o.value ? "border-ink bg-sunken text-ink" : "border-line text-ink-2 hover:bg-hover",
                )}
              >
                {o.label}
              </button>
            ))}
          </div>
          <input
            aria-label="Note (optional)"
            placeholder="Note (optional)"
            maxLength={300}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="h-11 w-full rounded-[var(--radius-control)] border border-line-strong bg-canvas px-3 text-sm placeholder:text-faint focus:border-ink focus:outline-none"
          />
          <div className="flex gap-2">
            <Button size="lg" className="flex-1" onClick={() => setDeclining(false)} disabled={busy}>
              Back
            </Button>
            <Button size="lg" variant="primary" className="flex-1" disabled={!reason} loading={decline.isPending} onClick={doDecline}>
              Confirm decline
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          <Button size="lg" className="flex-1" onClick={() => setDeclining(true)} disabled={busy}>
            <X className="size-5" /> Decline · मना करें
          </Button>
          <Button size="lg" variant="primary" className="flex-1" loading={accept.isPending} disabled={busy} onClick={doAccept}>
            <Check className="size-5" /> Accept · स्वीकार
          </Button>
        </div>
      )}
    </li>
  );
}

/** Fields the matcher wants this baler to take. Nothing is on the route until it is accepted here. */
export function Requests() {
  const requests = useRequests();
  const me = useOperatorMe();
  const rows = requests.data?.requests ?? [];
  const baler = me.data;
  return (
    <BalerPage wide>
      <div>
        <h1 className="text-[22px] font-semibold tracking-[var(--tracking-display)]">Requests · नए काम</h1>
        <p className="mt-1 text-[13px] text-muted">
          Farmers near you asked for a pickup. Accept to put it on your route; if you can't, decline so another baler gets it in time.
        </p>
      </div>
      {requests.error ? <ErrorNote error={requests.error} onRetry={() => void requests.refetch()} /> : null}
      {requests.isLoading ? <Skeleton className="h-48" /> : null}
      {requests.data && rows.length === 0 ? (
        <Empty title="No requests waiting · कोई नया काम नहीं">New requests appear here by themselves. Accepted work is on the Today and Schedule tabs.</Empty>
      ) : null}
      {rows.length ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
          <ul className="space-y-3">
            {rows.map((r) => (
              <RequestCard key={r.booking_id} r={r} serverNow={requests.data?.now} reasons={requests.data?.reasons ?? []} />
            ))}
          </ul>
          <div className="overflow-hidden rounded-[var(--radius-card)] border border-line">
            <MapView
              className="h-[260px] lg:h-[420px]"
              base={baler ? { lat: baler.lat, lng: baler.lng } : null}
              stops={rows.map((r, i) => ({
                booking_id: r.booking_id,
                field_id: r.field_id,
                stop_order: i + 1,
                status: "OFFERED",
                acres: r.acres,
                est_tonnes: r.est_tonnes,
                lat: r.lat,
                lng: r.lng,
                farmer_name: r.farmer_name,
                farmer_phone: "",
                village_name: r.village_name,
              }))}
            />
          </div>
        </div>
      ) : null}
    </BalerPage>
  );
}
