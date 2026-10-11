import { BarChart3, ExternalLink, Wind } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useBookings, useImpactTable, useStats } from "../../../api/hooks";
import type { BookingRow, ImpactTableData, Stats } from "../../../api/types";
import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../components/DataTable";
import { PageBody, TopBar } from "../../../components/Shell";
import { Card, Chip, Empty, ErrorNote, KpiStrip, PageTitle, Skeleton } from "../../../components/ui";
import { fmtDay, fmtInr, fmtInt, fmtNum } from "../../../lib/format";
import { headline, impactAmount, inUnit, perAcre } from "../../../lib/impact";

/** "Clear N acres → ~X kg PM2.5 not emitted": the per-acre rate, scaled by a slider. */
function PollutionPanel({ table, stats }: { table: ImpactTableData; stats: Stats }) {
  const rates = perAcre(table);
  const [acres, setAcres] = useState(10);
  if (!rates.length) {
    return (
      <Card title="Pollution prevented">
        <p className="text-sm text-muted">No field has been cleared yet. Each pickup marked Done adds what its straw would have emitted if burnt.</p>
      </Card>
    );
  }
  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          <Wind className="size-4 text-ok" /> Pollution prevented (estimate)
        </span>
      }
      bodyClassName="p-0"
    >
      <div className="grid grid-cols-1 border-t border-line sm:grid-cols-2 xl:grid-cols-[repeat(auto-fit,minmax(200px,1fr))]">
        {rates.map((r) => (
          <div key={r.key} className="-mb-px -mr-px border-b border-r border-line px-4 py-4">
            <div className="text-[13px] text-muted">{r.label} kept out of the air</div>
            <div className="tabular mt-1 text-[32px] font-semibold leading-tight tracking-[var(--tracking-title)] text-ok">{impactAmount(r.totalKg, r.unit)}</div>
            <div className="mt-1 text-xs text-ink-2 tabular">≈ {impactAmount(r.kg, r.unit)} per acre cleared</div>
          </div>
        ))}
      </div>
      <div className="px-4 py-4">
        <label className="flex flex-wrap items-center gap-3 text-sm text-ink-2" htmlFor="acre-slider">
          <span>If another</span>
          <span className="tabular rounded-full border border-ok-line bg-ok-soft px-2 py-0.5 font-medium text-ok">{acres} acres</span>
          <span>are cleared instead of burnt:</span>
        </label>
        <input
          id="acre-slider"
          type="range"
          min={1}
          max={Math.max(50, Math.ceil(stats.acres_registered - stats.acres_cleared))}
          value={acres}
          onChange={(e) => setAcres(Number(e.target.value))}
          className="mt-3 w-full accent-[var(--color-ok)]"
          aria-label="Acres"
        />
        <ul className="mt-3 flex flex-wrap gap-2 text-sm">
          {rates.map((r) => (
            <li key={r.key} className="tabular rounded-[var(--radius-control)] border border-line bg-sunken px-3 py-1.5">
              ~{impactAmount(r.kg * acres, r.unit)} <span className="text-muted">{r.label}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-faint">
          Per-acre rate from {fmtNum(table.district.acres)} cleared acres ({fmtNum(table.district.tonnes)} t of straw). Sources:{" "}
          {rates.map((r) => `${r.label}: ${r.source}`).join(" · ")}
        </p>
      </div>
    </Card>
  );
}

/** One stacked bar: of all registered acres, how many are cleared, booked, offered, still open. */
function AcresProgress({ s }: { s: Stats }) {
  const total = s.acres_registered;
  const cleared = s.acres_cleared;
  const booked = Math.max(0, s.acres_booked - s.acres_cleared);
  const offered = s.acres_offered;
  const open = Math.max(0, total - cleared - booked - offered);
  const parts = [
    { label: "Cleared", acres: cleared, cls: "bg-ok" },
    { label: "Booked, pickup pending", acres: booked, cls: "bg-data-2" },
    { label: "Offered to a baler", acres: offered, cls: "bg-warn-fill" },
    { label: "Not booked yet", acres: open, cls: "bg-risk-fill/70" },
  ];
  const pct = (n: number) => (total ? (n / total) * 100 : 0);
  return (
    <Card title={`Season progress · ${fmtInt(total)} registered acres`}>
      <div className="flex h-6 w-full overflow-hidden rounded-full bg-sunken" role="img" aria-label={`${Math.round(pct(cleared))}% of registered acres cleared`}>
        {parts.map((p) => (p.acres > 0 ? <div key={p.label} className={p.cls} style={{ width: `${pct(p.acres)}%` }} title={`${p.label}: ${fmtNum(p.acres)} ac`} /> : null))}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-[13px] md:grid-cols-4">
        {parts.map((p) => (
          <li key={p.label} className="flex items-start gap-2">
            <span className={`mt-1 size-2.5 shrink-0 rounded-full ${p.cls}`} />
            <span>
              <span className="text-ink-2">{p.label}</span>
              <span className="tabular block text-ink">
                {fmtNum(p.acres)} ac <span className="text-faint">· {Math.round(pct(p.acres))}%</span>
              </span>
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** Acres cleared per village (works with or without emission factors). */
function VillageBars({ table }: { table: ImpactTableData }) {
  const key = table.configured ? table.primary : null;
  const f = key ? table.factors[key] : undefined;
  const data = (table.groups ?? [])
    .map((g) => ({ village: g.label, acres: g.acres, avoided: key && f ? inUnit(g.impact[key] ?? 0, f.unit) : 0 }))
    .sort((a, b) => b.acres - a.acres)
    .slice(0, 10);
  if (!data.length) return null;
  return (
    <Card title="Acres cleared by village">
      <div style={{ height: Math.max(160, data.length * 36) }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid horizontal={false} stroke="var(--color-line)" strokeDasharray="3 3" />
            <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
            <YAxis type="category" dataKey="village" width={96} tickLine={false} axisLine={false} tick={{ fill: "var(--color-ink-2)", fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: "var(--color-sunken)" }}
              contentStyle={{ borderRadius: 8, border: "1px solid var(--color-line)", fontSize: 13 }}
              formatter={(v, _n, item) => {
                const extra = f ? ` · ~${fmtNum((item.payload as { avoided: number }).avoided)} ${f.unit} ${f.label}` : "";
                return [`${fmtNum(Number(v))} ac${extra}`, "Cleared"];
              }}
            />
            <Bar dataKey="acres" fill="var(--color-ok)" radius={[0, 4, 4, 0]} barSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

/** Admin impact: what the finished pickups achieved, for the officer. The public page is /impact. */
export function Impact() {
  const { me } = useAuth();
  const stats = useStats();
  const table = useImpactTable();
  const bookings = useBookings();
  const s = stats.data;
  const t = table.data;
  const done = useMemo(
    () =>
      (bookings.data ?? [])
        .filter((b) => b.status === "DONE")
        .sort((a, b) => (b.done_at ?? b.date).localeCompare(a.done_at ?? a.date))
        .slice(0, 12),
    [bookings.data],
  );
  const doneTonnes = (bookings.data ?? []).filter((b) => b.status === "DONE").reduce((n, b) => n + b.est_tonnes, 0);
  const donePayout = (bookings.data ?? []).filter((b) => b.status === "DONE").reduce((n, b) => n + b.farmer_payout, 0);

  return (
    <>
      <TopBar crumbs={[{ label: "Impact", icon: BarChart3 }, { label: me?.district ?? "All districts" }]} />
      <PageBody wide>
        <PageTitle
          sub="What the finished pickups achieved: every field marked Done is straw that was baled and taken away instead of burnt."
          actions={
            <Link to="/impact" className="flex items-center gap-1.5 text-sm text-muted hover:text-ink">
              Public impact page <ExternalLink className="size-3.5" />
            </Link>
          }
        >
          Impact
        </PageTitle>

        {stats.error ? <ErrorNote error={stats.error} onRetry={() => void stats.refetch()} /> : null}
        {table.error ? <ErrorNote error={table.error} onRetry={() => void table.refetch()} /> : null}

        {s ? (
          <KpiStrip
            items={[
              { label: "Acres cleared", value: fmtInt(s.acres_cleared), hint: `${s.bookings_done} pickups done` },
              { label: "Straw kept from fire", value: `${fmtInt(doneTonnes)} t`, hint: `${fmtInt(s.tonnes_delivered)} t delivered to buyers` },
              { label: "Paid to farmers", value: fmtInr(donePayout), hint: s.demo_prices ? "demo prices, not market rates" : "for cleared fields" },
              { label: "Saved after alert", value: s.fields_saved_after_alert, hint: `${s.alerts_sent} alerts sent` },
            ]}
          />
        ) : (
          <Skeleton className="h-[92px]" />
        )}

        {s && t ? (
          t.configured ? (
            <PollutionPanel table={t} stats={s} />
          ) : (
            <p className="rounded-[var(--radius-card)] border border-line bg-sunken px-4 py-3 text-[13px] text-ink-2" role="note">
              Pollution prevented appears here once emission factors are set: <code>EMISSION_FACTORS</code> with published values for open burning of rice
              straw, each with its citation. No unsourced number is ever shown.
            </p>
          )
        ) : (
          <Skeleton className="h-48" />
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {s ? <AcresProgress s={s} /> : <Skeleton className="h-40" />}
          {t ? <VillageBars table={t} /> : <Skeleton className="h-40" />}
        </div>

        <Card title="Recently cleared" bodyClassName="p-0">
          <DataTable<BookingRow>
            rows={done}
            loading={bookings.isLoading}
            rowKey={(b) => b.booking_id}
            empty={<Empty title="No pickups done yet">When a baler taps Done, the field shows up here with what it kept out of the air.</Empty>}
            columns={[
              { key: "date", header: "Cleared", render: (b) => fmtDay(b.date) },
              { key: "farmer", header: "Farmer", render: (b) => <span className="font-medium">{b.farmer_name ?? "–"}</span> },
              { key: "village", header: "Village", render: (b) => <Chip>{b.village_name ?? b.village_id}</Chip> },
              { key: "acres", header: "Acres", align: "right", render: (b) => fmtNum(b.acres) },
              { key: "tonnes", header: "Straw", align: "right", render: (b) => `${fmtNum(b.est_tonnes)} t` },
              {
                key: "avoided",
                header: "Avoided (est.)",
                align: "right",
                render: (b) => <span className="text-ok">{headline(b.impact, s?.impact_factors) ?? "–"}</span>,
              },
              { key: "payout", header: "Farmer paid", align: "right", render: (b) => fmtInr(b.farmer_payout) },
            ]}
          />
        </Card>
      </PageBody>
    </>
  );
}
