import { SlidersHorizontal } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useDemandHistory, useSupply, useUpdateDemand } from "../../../api/hooks";
import type { DemandChange, Supply } from "../../../api/types";
import { DataTable } from "../../../components/DataTable";
import { PageBody, TopBar } from "../../../components/Shell";
import { Button, Card, Empty, ErrorNote, Field, Input, PageTitle, Skeleton, useToast } from "../../../components/ui";
import { fmtDay, fmtInr, fmtNum, fmtTime } from "../../../lib/format";

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
        <Input type="number" min={1} step="1" required value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
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

/** How much straw this buyer wants, at what price and from how far, plus the trail of past edits. */
export function Demand() {
  const supply = useSupply();
  const history = useDemandHistory();
  return (
    <>
      <TopBar crumbs={[{ label: "Supply", icon: SlidersHorizontal }, { label: "Demand and price" }]} />
      <PageBody>
        <PageTitle sub="The matcher sends straw to the buyer with the best price after transport, within your radius, until your demand is full.">
          Demand and price
        </PageTitle>
        {supply.error ? <ErrorNote error={supply.error} onRetry={() => void supply.refetch()} /> : null}
        <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <Card title="Current values">{supply.data ? <DemandForm supply={supply.data} /> : <Skeleton className="h-64" />}</Card>
          <Card title="Change history" bodyClassName="p-0">
            <DataTable<DemandChange>
              rows={history.data}
              loading={history.isLoading}
              rowKey={(c) => c.at}
              empty={<Empty title="No changes yet">Each time you save the form, the new values are recorded here.</Empty>}
              columns={[
                { key: "at", header: "Changed", render: (c) => `${fmtDay(c.at)} · ${fmtTime(c.at)}` },
                { key: "demand", header: "Demand t", align: "right", render: (c) => fmtNum(c.demand_tonnes) },
                { key: "price", header: "Price ₹/t (demo)", align: "right", render: (c) => fmtInr(c.price_per_tonne) },
                { key: "radius", header: "Radius", align: "right", render: (c) => `${fmtNum(c.max_radius_km)} km` },
              ]}
            />
          </Card>
        </div>
      </PageBody>
    </>
  );
}
