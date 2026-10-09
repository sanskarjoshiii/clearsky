import { Building2, LogOut } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useSupply } from "../../../api/hooks";
import { useAuth } from "../../../auth/AuthProvider";
import { PageBody, TopBar } from "../../../components/Shell";
import { Button, Card, ErrorNote, PageTitle, Skeleton } from "../../../components/ui";
import { fmtInr, fmtNum } from "../../../lib/format";
import { BUYER_TYPE } from "../Layout";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2.5 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}

/** Who this buyer is on clearsky. Plant details are set at registration; demand is edited on its own page. */
export function Profile() {
  const supply = useSupply();
  const { me, signOut } = useAuth();
  const b = supply.data?.buyer;
  return (
    <>
      <TopBar crumbs={[{ label: "Account", icon: Building2 }, { label: "Profile" }]} />
      <PageBody>
        <PageTitle sub="Your plant as the matcher sees it.">Profile</PageTitle>
        {supply.error ? <ErrorNote error={supply.error} onRetry={() => void supply.refetch()} /> : null}
        {b ? (
          <div className="grid gap-6 md:grid-cols-2">
            <Card title="Plant">
              <Row label="Name">{b.name}</Row>
              <Row label="Type">{BUYER_TYPE[b.type] ?? b.type}</Row>
              <Row label="Buyer id">
                <span className="tabular">{b.buyer_id}</span>
              </Row>
              <Row label="Location">
                <span className="tabular">
                  {b.lat.toFixed(3)}, {b.lng.toFixed(3)}
                </span>
              </Row>
            </Card>
            <Card
              title="Demand"
              actions={
                <Link to="/buyer/demand" className="text-[13px] text-muted hover:text-ink">
                  Edit
                </Link>
              }
            >
              <Row label="Season demand">{fmtNum(b.demand_tonnes)} t</Row>
              <Row label="Price (demo)">{fmtInr(b.price_per_tonne)} per tonne</Row>
              <Row label="Collection radius">{fmtNum(b.max_radius_km)} km</Row>
            </Card>
            <Card title="Account">
              <Row label="Signed in as">{me?.email || me?.display_name}</Row>
              <div className="pt-3">
                <Button onClick={() => void signOut()}>
                  <LogOut className="size-4" /> Sign out
                </Button>
              </div>
            </Card>
          </div>
        ) : supply.isLoading ? (
          <Skeleton className="h-64" />
        ) : null}
      </PageBody>
    </>
  );
}
