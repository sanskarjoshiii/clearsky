import { Factory } from "lucide-react";
import { Link } from "react-router";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSupply } from "../../../api/hooks";
import { PageBody, TopBar } from "../../../components/Shell";
import { Card, Empty, ErrorNote, KpiStrip, PageTitle, Skeleton } from "../../../components/ui";
import { fmtDay, fmtInr, fmtNum } from "../../../lib/format";
import { BUYER_TYPE } from "../Layout";

/** Buyer home: how much straw is coming, and when. */
export function Overview() {
  const supply = useSupply();
  const s = supply.data;
  const b = s?.buyer;
  return (
    <>
      <TopBar crumbs={[{ label: "Supply", icon: Factory }, { label: b?.name ?? "Buyer" }]} />
      <PageBody wide>
        <PageTitle sub={b ? <>{BUYER_TYPE[b.type]} · collects within {fmtNum(b.max_radius_km)} km · prices are demo values</> : undefined}>
          {b?.name ?? "Straw supply"}
        </PageTitle>
        {supply.error ? <ErrorNote error={supply.error} onRetry={() => void supply.refetch()} /> : null}
        {s && b ? (
          <>
            <KpiStrip
              items={[
                { label: "Season demand", value: `${fmtNum(b.demand_tonnes)} t` },
                { label: "Booked to you", value: `${fmtNum(b.reserved_tonnes)} t`, hint: `${s.deliveries.length} pickups` },
                { label: "Delivered", value: `${fmtNum(b.received_tonnes)} t` },
                { label: "Still needed", value: `${fmtNum(b.remaining_tonnes)} t` },
                { label: "Your price", value: fmtInr(b.price_per_tonne), hint: "per tonne (demo)" },
                ...Object.values(s.impact)
                  .slice(0, 1)
                  .map((v) => ({
                    label: `${v.label} avoided`,
                    value: `${fmtNum(v.value)} ${v.unit}`,
                    hint: "by straw you received (estimate)",
                  })),
              ]}
            />
            <Card
              title="Incoming straw by day"
              actions={
                <Link to="/buyer/deliveries" className="text-[13px] text-muted hover:text-ink">
                  All deliveries
                </Link>
              }
            >
              {s.forecast.length ? (
                <div className="h-[320px]">
                  <ResponsiveContainer>
                    <BarChart data={s.forecast.map((d) => ({ ...d, day: fmtDay(d.date) }))} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                      <CartesianGrid vertical={false} stroke="var(--color-line)" strokeDasharray="3 3" />
                      <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
                      <YAxis tickLine={false} axisLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} unit=" t" />
                      <Tooltip
                        cursor={{ fill: "var(--color-hover)" }}
                        contentStyle={{ borderRadius: 8, border: "1px solid var(--color-line)", fontSize: 13 }}
                        formatter={(v) => `${fmtNum(Number(v))} t`}
                      />
                      <Legend iconType="square" iconSize={10} wrapperStyle={{ fontSize: 13, color: "var(--color-ink-2)" }} />
                      <Bar dataKey="delivered" name="Delivered" stackId="t" fill="var(--color-data-1)" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="booked" name="Booked (incoming)" stackId="t" fill="var(--color-data-3)" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <Empty title="No bookings routed to you yet">As farmers book pickups nearby, incoming tonnes appear here by day.</Empty>
              )}
            </Card>
          </>
        ) : supply.isLoading ? (
          <Skeleton className="h-96" />
        ) : null}
      </PageBody>
    </>
  );
}
