import { CalendarCheck, Factory, Search, Table2, Tractor } from "lucide-react";
import { useMemo, useState } from "react";
import { useBalers, useBookings, useBuyers, useFields, useReassignOffer, useSetBalerActive, useStats, useVillages } from "../../../api/hooks";
import type { Baler, BookingRow, Buyer, FieldRow } from "../../../api/types";
import { DataTable } from "../../../components/DataTable";
import { FieldDrawer } from "../../../components/FieldDrawer";
import { PageBody, TopBar } from "../../../components/Shell";
import { Button, Card, Chip, ConfirmDialog, ErrorNote, Input, PageTitle, RiskPill, Segmented, StatusChip, useToast } from "../../../components/ui";
import { addDays, fmtDay, fmtInr, fmtNum } from "../../../lib/format";
import { useAlertVillage } from "./Radar";

function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="relative w-full max-w-sm">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-faint" />
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="pl-8" aria-label={placeholder} />
    </div>
  );
}

// ------------------------------------------------------------------ fields

export function Fields() {
  const fields = useFields();
  const villages = useVillages();
  const stats = useStats(false);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"all" | "open" | "BOOKED" | "CLEARED">("all");
  const [level, setLevel] = useState<"all" | "RED" | "YELLOW" | "GREEN">("all");
  const [selected, setSelected] = useState<string | null>(null);
  const alert = useAlertVillage(villages.data);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (fields.data ?? []).filter(
      (f) =>
        (status === "all" || (status === "open" ? f.status === "REGISTERED" || f.status === "HARVESTED" : f.status === status)) &&
        (level === "all" || f.risk_level === level) &&
        (!needle || `${f.farmer_name} ${f.village_name} ${f.field_id}`.toLowerCase().includes(needle)),
    );
  }, [fields.data, q, status, level]);

  return (
    <>
      <TopBar crumbs={[{ label: "Database", icon: Table2 }, { label: "Fields" }]} />
      <PageBody wide>
        <PageTitle sub="Every registered paddy field. Farmers' numbers are masked; open a row for the risk reasons and booking.">Fields</PageTitle>
        <div className="flex flex-wrap items-center gap-3">
          <SearchBox value={q} onChange={setQ} placeholder="Search farmer, village or field id" />
          <Segmented
            value={status}
            onChange={setStatus}
            options={[
              { value: "all", label: "All" },
              { value: "open", label: "Unbooked" },
              { value: "BOOKED", label: "Booked" },
              { value: "CLEARED", label: "Cleared" },
            ]}
          />
          <Segmented
            value={level}
            onChange={setLevel}
            options={[
              { value: "all", label: "Any risk" },
              { value: "RED", label: "Red" },
              { value: "YELLOW", label: "Amber" },
              { value: "GREEN", label: "Green" },
            ]}
          />
          <span className="ml-auto text-[13px] text-muted tabular">{rows.length} fields</span>
        </div>
        {fields.error ? <ErrorNote error={fields.error} onRetry={() => void fields.refetch()} /> : null}
        <Card bodyClassName="p-0">
          <DataTable<FieldRow>
            numbered
            rows={rows}
            loading={fields.isLoading}
            rowKey={(f) => f.field_id}
            selectedKey={selected}
            onRowClick={(f) => setSelected(f.field_id)}
            columns={[
              { key: "farmer", header: "Farmer", render: (f) => <span className="font-medium">{f.farmer_name ?? "–"}</span> },
              { key: "phone", header: "Phone", render: (f) => <span className="text-muted tabular">{f.farmer_phone}</span> },
              { key: "village", header: "Village", render: (f) => <Chip>{f.village_name}</Chip> },
              { key: "acres", header: "Acres", align: "right", render: (f) => fmtNum(f.acres) },
              { key: "harvest", header: "Harvest", render: (f) => fmtDay(f.harvest_date) },
              { key: "sow", header: "Sow by", render: (f) => fmtDay(f.sowing_deadline) },
              {
                key: "status",
                header: "Status",
                render: (f) => (f.status === "BOOKED" && f.booking_state === "offered" ? <Chip>Offer sent</Chip> : <StatusChip status={f.status} />),
              },
              { key: "risk", header: "Risk", render: (f) => <RiskPill level={f.risk_level} score={f.risk_score} /> },
              {
                key: "source",
                header: "Source",
                render: (f) => (f.source === "whatsapp" ? <Chip tone="agent">via WhatsApp</Chip> : <Chip>demo seed</Chip>),
              },
            ]}
          />
        </Card>
      </PageBody>
      {selected ? (
        <FieldDrawer
          id={selected}
          today={stats.data?.today}
          onClose={() => setSelected(null)}
          onAlert={(vid) => {
            setSelected(null);
            alert.open(vid);
          }}
        />
      ) : null}
      {alert.dialog}
    </>
  );
}

// ------------------------------------------------------------------ bookings

export const DECLINE_LABEL: Record<string, string> = {
  machine_unavailable: "machine not available",
  too_far: "too far",
  day_full: "already full that day",
  other: "other",
  "reassigned by officer": "reassigned by admin",
};

export function Bookings() {
  const stats = useStats(false);
  const today = stats.data?.today;
  const [when, setWhen] = useState<"today" | "tomorrow" | "all">("tomorrow");
  const date = when === "all" || !today ? undefined : when === "today" ? today : addDays(today, 1);
  const bookings = useBookings(date);
  const reassign = useReassignOffer();
  const toast = useToast();
  const [show, setShow] = useState<"open" | "all">("open");
  // "open" = work that is still going to happen; "all" adds declined / expired offers (the history)
  const rows = (bookings.data ?? []).filter((b) =>
    show === "open" ? b.status === "OFFERED" || b.status === "CONFIRMED" || b.status === "DONE" : b.status !== "CANCELLED",
  );
  const firm = rows.filter((b) => b.status === "CONFIRMED" || b.status === "DONE");
  const waiting = rows.filter((b) => b.status === "OFFERED").length;
  return (
    <>
      <TopBar crumbs={[{ label: "Database", icon: CalendarCheck }, { label: "Bookings" }]} />
      <PageBody wide>
        <PageTitle sub="Pickups the matcher has offered to balers, ordered by day, baler and stop. A pickup is confirmed when the baler accepts; a declined or unanswered offer moves to the next baler. Payouts are demo estimates.">
          Bookings
        </PageTitle>
        <div className="flex flex-wrap items-center gap-3">
          <Segmented
            value={when}
            onChange={setWhen}
            options={[
              { value: "today", label: today ? `Today · ${fmtDay(today)}` : "Today" },
              { value: "tomorrow", label: today ? `Tomorrow · ${fmtDay(addDays(today, 1))}` : "Tomorrow" },
              { value: "all", label: "All" },
            ]}
          />
          <Segmented
            value={show}
            onChange={setShow}
            options={[
              { value: "open", label: "Open" },
              { value: "all", label: "With declined / expired" },
            ]}
          />
          <span className="ml-auto text-[13px] text-muted tabular">
            {firm.length} confirmed · {fmtNum(firm.reduce((a, b) => a + b.est_tonnes, 0))} t{waiting ? ` · ${waiting} waiting for a baler` : ""}
          </span>
        </div>
        {bookings.error ? <ErrorNote error={bookings.error} onRetry={() => void bookings.refetch()} /> : null}
        <Card bodyClassName="p-0">
          <DataTable<BookingRow>
            rows={rows}
            loading={bookings.isLoading}
            rowKey={(b) => b.booking_id}
            columns={[
              { key: "date", header: "Date", render: (b) => fmtDay(b.date) },
              { key: "baler", header: "Baler", render: (b) => <span className="font-medium">{b.operator_name}</span> },
              { key: "stop", header: "Stop", align: "right", render: (b) => (b.stop_order ? b.stop_order : <span className="text-faint">–</span>) },
              { key: "farmer", header: "Farmer", render: (b) => b.farmer_name ?? "–" },
              { key: "village", header: "Village", render: (b) => <Chip>{b.village_name ?? b.village_id}</Chip> },
              { key: "acres", header: "Acres", align: "right", render: (b) => fmtNum(b.acres) },
              { key: "t", header: "Tonnes", align: "right", render: (b) => fmtNum(b.est_tonnes) },
              { key: "buyer", header: "Straw to", render: (b) => b.buyer_name ?? <span className="text-faint">village storage</span> },
              { key: "pay", header: "Payout (demo)", align: "right", render: (b) => (b.farmer_payout > 0 ? fmtInr(b.farmer_payout) : "free") },
              {
                key: "status",
                header: "Status",
                render: (b) => (
                  <span className="inline-flex items-center gap-1.5">
                    <StatusChip status={b.status} />
                    {b.attempt && b.attempt > 1 && b.status === "OFFERED" ? <span className="text-xs text-muted">baler {b.attempt}</span> : null}
                    {b.status === "DECLINED" && b.decline_reason ? <span className="text-xs text-muted">{DECLINE_LABEL[b.decline_reason] ?? b.decline_reason}</span> : null}
                  </span>
                ),
              },
              {
                key: "act",
                header: "",
                render: (b) =>
                  b.status === "OFFERED" ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Reassign ${b.farmer_name ?? b.booking_id}`}
                      disabled={reassign.isPending}
                      onClick={() =>
                        reassign.mutate(b.booking_id, {
                          onSuccess: (r) => toast(r.next?.kind === "booked" ? `Offered to ${r.next.operator_name ?? "the next baler"}.` : "No other baler is free: the field is on the radar."),
                          onError: (e) => toast(e.message, "error"),
                        })
                      }
                    >
                      Reassign
                    </Button>
                  ) : null,
              },
            ]}
          />
        </Card>
      </PageBody>
    </>
  );
}

// ------------------------------------------------------------------ balers

function WeekBars({ baler }: { baler: Baler }) {
  const days = baler.week ?? [];
  return (
    <div className="flex h-6 items-end gap-[3px]" aria-label="Booked acres, next 7 days">
      {days.map((d) => {
        const pct = Math.min(1, d.booked_acres / Math.max(1, baler.acres_per_day));
        return (
          <div key={d.date} title={`${fmtDay(d.date)}: ${fmtNum(d.booked_acres)} / ${fmtNum(baler.acres_per_day)} ac`} className="flex h-full w-2.5 items-end rounded-[2px] bg-sunken">
            <div className="w-full rounded-[2px] bg-data-2" style={{ height: `${Math.max(pct * 100, d.booked_acres > 0 ? 12 : 0)}%` }} />
          </div>
        );
      })}
    </div>
  );
}

export function Balers() {
  const balers = useBalers();
  const setActive = useSetBalerActive();
  const toast = useToast();
  const [target, setTarget] = useState<Baler | null>(null);
  return (
    <>
      <TopBar crumbs={[{ label: "Database", icon: Tractor }, { label: "Balers" }]} />
      <PageBody wide>
        <PageTitle sub="Custom hiring centre balers. Operators manage their own capacity and route on their dashboard; you can switch a baler off so it gets no new bookings.">
          Balers
        </PageTitle>
        {balers.error ? <ErrorNote error={balers.error} onRetry={() => void balers.refetch()} /> : null}
        <Card bodyClassName="p-0">
          <DataTable<Baler>
            numbered
            rows={balers.data}
            loading={balers.isLoading}
            rowKey={(b) => b.baler_id}
            columns={[
              { key: "id", header: "Baler", render: (b) => <span className="tabular text-muted">{b.baler_id}</span> },
              { key: "op", header: "Operator", render: (b) => <span className="font-medium">{b.operator_name}</span> },
              { key: "chc", header: "CHC", render: (b) => <span className="text-muted">{b.chc_name}</span> },
              { key: "base", header: "Base", render: (b) => <Chip>{b.base_village_name ?? b.base_village_id}</Chip> },
              { key: "cap", header: "Acres/day", align: "right", render: (b) => fmtNum(b.acres_per_day) },
              { key: "radius", header: "Radius", align: "right", render: (b) => `${fmtNum(b.radius_km)} km` },
              { key: "week", header: "Next 7 days", render: (b) => <WeekBars baler={b} /> },
              { key: "stops", header: "Upcoming stops", align: "right", render: (b) => b.upcoming_stops ?? 0 },
              { key: "active", header: "Status", render: (b) => <Chip>{b.active ? "Available" : "Off duty"}</Chip> },
              {
                key: "act",
                header: "",
                render: (b) => (
                  <Button size="sm" variant="ghost" aria-label={`${b.active ? "Deactivate" : "Reactivate"} ${b.baler_id}`} onClick={() => setTarget(b)}>
                    {b.active ? "Deactivate" : "Reactivate"}
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      </PageBody>
      <ConfirmDialog
        open={!!target}
        title={target?.active ? `Deactivate ${target.operator_name}?` : `Reactivate ${target?.operator_name ?? "baler"}?`}
        confirmLabel={target?.active ? "Deactivate" : "Reactivate"}
        busy={setActive.isPending}
        onClose={() => setTarget(null)}
        onConfirm={() =>
          target &&
          setActive.mutate(
            { baler_id: target.baler_id, active: !target.active },
            {
              onSuccess: () => {
                toast(target.active ? "Baler deactivated: no new bookings." : "Baler reactivated.");
                setTarget(null);
              },
              onError: (e) => toast(e.message, "error"),
            },
          )
        }
      >
        {target?.active
          ? "The matcher stops sending new bookings to this baler, and a self-registered operator can no longer sign in to the baler app. Stops already confirmed stay on the route."
          : "The baler gets new bookings again, and the operator can sign in."}
      </ConfirmDialog>
    </>
  );
}

// ------------------------------------------------------------------ buyers

const BUYER_TYPE: Record<Buyer["type"], string> = { pellet: "Pellet plant", cbg: "CBG plant", boiler: "Industrial boiler", biomass_power: "Biomass power" };

export function Buyers() {
  const buyers = useBuyers();
  return (
    <>
      <TopBar crumbs={[{ label: "Database", icon: Factory }, { label: "Buyers" }]} />
      <PageBody wide>
        <PageTitle sub="Industries that take the straw. Names and prices are fictional demo values, not market prices.">Buyers</PageTitle>
        {buyers.error ? <ErrorNote error={buyers.error} onRetry={() => void buyers.refetch()} /> : null}
        <Card bodyClassName="p-0">
          <DataTable<Buyer>
            rows={buyers.data}
            loading={buyers.isLoading}
            rowKey={(b) => b.buyer_id}
            columns={[
              { key: "name", header: "Buyer", render: (b) => <span className="font-medium">{b.name}</span> },
              { key: "type", header: "Type", render: (b) => <Chip>{BUYER_TYPE[b.type]}</Chip> },
              { key: "price", header: "Price ₹/t (demo)", align: "right", render: (b) => fmtInr(b.price_per_tonne) },
              { key: "demand", header: "Demand t", align: "right", render: (b) => fmtNum(b.demand_tonnes) },
              { key: "reserved", header: "Booked t", align: "right", render: (b) => fmtNum(b.reserved_tonnes) },
              { key: "received", header: "Delivered t", align: "right", render: (b) => fmtNum(b.received_tonnes) },
              { key: "remaining", header: "Remaining t", align: "right", render: (b) => fmtNum(b.remaining_tonnes) },
              { key: "radius", header: "Radius", align: "right", render: (b) => `${fmtNum(b.max_radius_km)} km` },
            ]}
          />
        </Card>
      </PageBody>
    </>
  );
}
