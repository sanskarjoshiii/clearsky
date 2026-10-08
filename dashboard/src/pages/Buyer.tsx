import { Factory } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSupply, useUpdateDemand } from "../api/hooks";
import type { Supply } from "../api/types";
import { DataTable } from "../components/DataTable";
import { PageBody, TopBar } from "../components/Shell";
import { Button, Card, Chip, Empty, ErrorNote, Field, Input, KpiStrip, PageTitle, Skeleton, StatusChip, useToast } from "../components/ui";
import { fmtDay, fmtInr, fmtNum } from "../lib/format";

const TYPE: Record<string, string> = { pellet: "Pellet plant", cbg: "CBG plant", boiler: "Industrial boiler", biomass_power: "Biomass power" };

function DemandForm({ supply }: { supply: Supply }) {
  const b = supply.buyer;
  const update = useUpdateDemand();
  const toast = useToast();
  const [form, setForm] = useState({ demand: String(b.demand_tonnes), price: String(b.price_per_tonne), radius: String(b.max_radius_km) });
  useEffect(() => setForm({ demand: String(b.demand_tonnes), price: String(b.price_per_tonne), radius: String(b.max_radius_km) }), [b.demand_tonnes, b.price_per_tonne, b.max_radius_km]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    update.mutate(
      { demand_tonnes: Number(form.demand), price_per_tonne: Number(form.price), max_radius_km: Number(form.radius) },
      { onSuccess: () => toast("Demand updated. New bookings use these values."), onError: (err) => toast(err.message, "error") },
    );
  };
  return (
    <form className="space-y-3.5" onSubmit={submit}>
      <Field label="Season demand (tonnes)" hint={`At least ${fmtNum(b.reserved_tonnes)} t already booked`}>
        <Input type="number" min={Math.ceil(b.reserved_tonnes)} step="1" required value={form.demand} onChange={(e) => setForm({ ...form, demand: e.target.value })} />
      </Field>
      <Field label="Price per tonne (₹, demo)">
        <Input type="number" min={1} step="10" required value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
      </Field>
      <Field label="Collection radius (km)">
        <Input type="number" min={1} max={300} required value={form.radius} onChange={(e) => setForm({ ...form, radius: e.target.value })} />
      </Field>
      <Button variant="primary" type="submit" loading={update.isPending} className="w-full">
        Save demand
      </Button>
      <p className="text-xs text-faint">Existing bookings keep the price they were booked at.</p>
    </form>
  );
}

export function BuyerPage() {
  const supply = useSupply();
  const s = supply.data;
  const b = s?.buyer;
  return (
    <>
      <TopBar crumbs={[{ label: "Supply", icon: Factory }, { label: b?.name ?? "Buyer" }]} />
      <PageBody wide>
        <PageTitle sub={b ? <>{TYPE[b.type]} · collects within {fmtNum(b.max_radius_km)} km · prices are demo values</> : undefined}>
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
              ]}
            />
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
              <Card title="Incoming straw by day">
                {s.forecast.length ? (
                  <div className="h-[300px]">
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
              <Card title="Demand and price">
                <DemandForm supply={s} />
              </Card>
            </div>
            <Card title="Deliveries" bodyClassName="p-0">
              <DataTable
                rows={s.deliveries}
                rowKey={(d) => d.booking_id}
                empty={<Empty title="No deliveries yet" />}
                columns={[
                  { key: "date", header: "Date", render: (d) => fmtDay(d.date) },
                  { key: "village", header: "From", render: (d) => <Chip>{d.village_name}</Chip> },
                  { key: "acres", header: "Acres", align: "right", render: (d) => fmtNum(d.acres) },
                  { key: "t", header: "Tonnes (est.)", align: "right", render: (d) => fmtNum(d.est_tonnes) },
                  { key: "km", header: "Distance", align: "right", render: (d) => `${fmtNum(d.distance_km)} km` },
                  { key: "price", header: "Price (demo)", align: "right", render: (d) => fmtInr(d.price_per_tonne) },
                  { key: "status", header: "Status", render: (d) => <StatusChip status={d.status} /> },
                ]}
              />
            </Card>
          </>
        ) : supply.isLoading ? (
          <Skeleton className="h-96" />
        ) : null}
      </PageBody>
    </>
  );
}
