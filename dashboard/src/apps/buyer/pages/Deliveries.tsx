import { Download, Truck } from "lucide-react";
import { useStats, useSupply } from "../../../api/hooks";
import type { Supply } from "../../../api/types";
import { DataTable } from "../../../components/DataTable";
import { PageBody, TopBar } from "../../../components/Shell";
import { Button, Card, Chip, Empty, ErrorNote, PageTitle, StatusChip } from "../../../components/ui";
import { fmtDay, fmtInr, fmtNum } from "../../../lib/format";
import { headline } from "../../../lib/impact";

type Delivery = Supply["deliveries"][number];

const CSV_COLUMNS: [string, (d: Delivery) => string | number][] = [
  ["booking_id", (d) => d.booking_id],
  ["date", (d) => d.date],
  ["village", (d) => d.village_name],
  ["acres", (d) => d.acres],
  ["tonnes_estimate", (d) => d.est_tonnes],
  ["distance_km", (d) => d.distance_km],
  ["price_per_tonne_demo", (d) => d.price_per_tonne ?? ""],
  ["status", (d) => d.status],
];

/** RFC 4180 CSV: quote every text cell and double any quote inside it. */
export function deliveriesCsv(rows: Delivery[]): string {
  const cell = (v: string | number) => (typeof v === "number" ? String(v) : `"${v.replace(/"/g, '""')}"`);
  const lines = [CSV_COLUMNS.map(([h]) => h).join(","), ...rows.map((r) => CSV_COLUMNS.map(([, get]) => cell(get(r))).join(","))];
  return lines.join("\r\n") + "\r\n";
}

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** Every pickup routed to this buyer, with a CSV export for their own records. */
export function Deliveries() {
  const supply = useSupply();
  const factors = useStats(false).data?.impact_factors;
  const hasImpact = !!factors && Object.keys(factors).length > 0;
  const rows = supply.data?.deliveries ?? [];
  return (
    <>
      <TopBar crumbs={[{ label: "Supply", icon: Truck }, { label: "Deliveries" }]} />
      <PageBody wide>
        <PageTitle
          sub="Pickups whose straw is routed to you. Tonnes are estimates from the field size; prices are demo values."
          actions={
            <Button disabled={!rows.length} onClick={() => download(`clearsky-deliveries-${supply.data?.buyer.buyer_id ?? "buyer"}.csv`, deliveriesCsv(rows))}>
              <Download className="size-4" /> Export CSV
            </Button>
          }
        >
          Deliveries
        </PageTitle>
        {supply.error ? <ErrorNote error={supply.error} onRetry={() => void supply.refetch()} /> : null}
        <Card bodyClassName="p-0">
          <DataTable<Delivery>
            rows={supply.data?.deliveries}
            loading={supply.isLoading}
            rowKey={(d) => d.booking_id}
            empty={<Empty title="No deliveries yet">As farmers book pickups nearby, they appear here.</Empty>}
            columns={[
              { key: "date", header: "Date", render: (d) => fmtDay(d.date) },
              { key: "village", header: "From", render: (d) => <Chip>{d.village_name}</Chip> },
              { key: "acres", header: "Acres", align: "right", render: (d) => fmtNum(d.acres) },
              { key: "t", header: "Tonnes (est.)", align: "right", render: (d) => fmtNum(d.est_tonnes) },
              { key: "km", header: "Distance", align: "right", render: (d) => `${fmtNum(d.distance_km)} km` },
              { key: "price", header: "Price (demo)", align: "right", render: (d) => fmtInr(d.price_per_tonne) },
              { key: "status", header: "Status", render: (d) => <StatusChip status={d.status} /> },
              ...(hasImpact
                ? [
                    {
                      key: "avoided",
                      header: "Avoided (est.)",
                      align: "right" as const,
                      render: (d: Delivery) => headline(d.impact, factors) ?? <span className="text-faint">–</span>,
                    },
                  ]
                : []),
            ]}
          />
        </Card>
      </PageBody>
    </>
  );
}
