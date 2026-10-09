import { AlertTriangle, UserCheck, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useApplications, useReviewApplication } from "../../../api/hooks";
import type { Application, ApplicationStatus } from "../../../api/types";
import { DataTable } from "../../../components/DataTable";
import { MapView } from "../../../components/MapView";
import { PageBody, TopBar } from "../../../components/Shell";
import { Button, Card, Chip, Empty, ErrorNote, IconButton, PageTitle, Segmented, useToast } from "../../../components/ui";
import { fmtDay, fmtInr, fmtNum } from "../../../lib/format";

const ROLE_LABEL: Record<Application["role"], string> = { operator: "Baler", buyer: "Buyer" };
const STATUS_LABEL: Record<ApplicationStatus, string> = { PENDING: "Pending", APPROVED: "Approved", REJECTED: "Rejected", SUSPENDED: "Deactivated" };
const BUYER_TYPE: Record<string, string> = { pellet: "Pellet plant", cbg: "CBG plant", boiler: "Industrial boiler", biomass_power: "Biomass power" };

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2 text-[13px] last:border-0">
      <span className="text-muted">{label}</span>
      <span className="text-right text-ink">{children}</span>
    </div>
  );
}

/** Everything the applicant sent, a map pin, and the two decisions. */
function ApplicationDrawer({ app, onClose }: { app: Application; onClose: () => void }) {
  const review = useReviewApplication();
  const toast = useToast();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const pending = app.status === "PENDING";

  const approve = () =>
    review.mutate(
      { id: app.application_id, action: "approve" },
      {
        onSuccess: (r) => {
          toast(`Approved: ${app.org_name} is now ${ROLE_LABEL[app.role].toLowerCase()} ${r.application.entity_id ?? ""}.`);
          onClose();
        },
        onError: (e) => toast(e.message, "error"),
      },
    );
  const reject = () =>
    review.mutate(
      { id: app.application_id, action: "reject", reason: reason.trim() },
      {
        onSuccess: () => {
          toast("Rejected. The applicant sees your reason.");
          onClose();
        },
        onError: (e) => toast(e.message, "error"),
      },
    );

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/10 md:bg-transparent" onClick={onClose}>
      <aside
        className="flex h-full w-full max-w-[440px] animate-rise flex-col border-l border-line bg-canvas shadow-[var(--shadow-pop)]"
        onClick={(e) => e.stopPropagation()}
        aria-label="Application detail"
      >
        <header className="flex h-[52px] shrink-0 items-center gap-2 border-b border-line px-4">
          <span className="text-[15px] font-medium">Application</span>
          <span className="tabular text-[13px] text-muted">{app.application_id}</span>
          <IconButton label="Close" className="ml-auto" onClick={onClose}>
            <X className="size-4" />
          </IconButton>
        </header>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
          <div>
            <div className="flex items-center gap-2">
              <Chip>{ROLE_LABEL[app.role]}</Chip>
              <Chip>{STATUS_LABEL[app.status]}</Chip>
            </div>
            <h2 className="mt-3 text-[22px] font-semibold tracking-[var(--tracking-display)]">{app.org_name}</h2>
            <p className="text-sm text-muted">
              {app.name} · {app.village_name ?? app.village_id}
            </p>
          </div>

          {app.duplicates?.length ? (
            <div className="flex gap-2 rounded-[var(--radius-control)] border border-line bg-sunken px-3 py-2.5 text-[13px] text-ink-2" role="note">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <div>
                <div className="font-medium text-ink">Possible duplicate</div>
                {app.duplicates.map((d) => (
                  <div key={d}>{d}</div>
                ))}
              </div>
            </div>
          ) : null}

          <div>
            <Row label="Email">{app.email || "–"}</Row>
            <Row label="Phone">
              <a href={`tel:${app.phone}`} className="underline">
                {app.phone}
              </a>
            </Row>
            <Row label={app.role === "operator" ? "Custom hiring centre" : "Company"}>{app.org_name}</Row>
            <Row label={app.role === "operator" ? "Base village" : "Location"}>{app.village_name ?? app.village_id}</Row>
            {app.role === "operator" ? (
              <>
                <Row label="Capacity">{fmtNum(app.acres_per_day)} acres/day</Row>
                <Row label="Working radius">{fmtNum(app.radius_km)} km</Row>
                <Row label="Machines">{app.machine_details || "–"}</Row>
              </>
            ) : (
              <>
                <Row label="Plant type">{BUYER_TYPE[app.type ?? ""] ?? app.type ?? "–"}</Row>
                <Row label="Price">{fmtInr(app.price_per_tonne)} per tonne</Row>
                <Row label="Season demand">{fmtNum(app.demand_tonnes)} t</Row>
                <Row label="Collection radius">{fmtNum(app.max_radius_km)} km</Row>
              </>
            )}
            <Row label="Submitted">{fmtDay(app.created_at)}</Row>
            {app.reviewed_at ? <Row label="Reviewed">{fmtDay(app.reviewed_at)}</Row> : null}
            {app.entity_id ? (
              <Row label={app.role === "operator" ? "Baler id" : "Buyer id"}>
                <span className="tabular">{app.entity_id}</span>
              </Row>
            ) : null}
            {app.reject_reason ? <Row label="Reason given">{app.reject_reason}</Row> : null}
          </div>

          <div className="overflow-hidden rounded-[var(--radius-card)] border border-line">
            <MapView className="h-[220px]" base={{ lat: app.lat, lng: app.lng }} focus={{ lat: app.lat, lng: app.lng, zoom: 11 }} />
          </div>

          {pending ? (
            rejecting ? (
              <div className="space-y-2">
                <label className="block text-[13px] font-medium text-ink-2" htmlFor="reject-reason">
                  Reason (the applicant sees this)
                </label>
                <textarea
                  id="reject-reason"
                  rows={3}
                  maxLength={500}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full rounded-[var(--radius-control)] border border-line-strong bg-canvas px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none"
                />
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setRejecting(false)}>
                    Back
                  </Button>
                  <Button variant="primary" disabled={reason.trim().length < 3} loading={review.isPending} onClick={reject}>
                    Reject application
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <Button className="flex-1" onClick={() => setRejecting(true)} disabled={review.isPending}>
                  Reject
                </Button>
                <Button variant="primary" className="flex-1" loading={review.isPending} onClick={approve}>
                  Approve
                </Button>
              </div>
            )
          ) : null}
          {pending ? (
            <p className="text-xs text-faint">
              Approving creates the {ROLE_LABEL[app.role].toLowerCase()} record, so the matcher starts using it, and lets this person sign in to the {ROLE_LABEL[app.role].toLowerCase()} app.
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

/** Self-registered balers and buyers waiting for (or past) the admin's decision. */
export function Approvals() {
  const [filter, setFilter] = useState<"PENDING" | "APPROVED" | "REJECTED" | "all">("PENDING");
  const list = useApplications(filter === "all" ? undefined : filter);
  const [selected, setSelected] = useState<string | null>(null);
  const rows = list.data?.applications;
  const open = rows?.find((a) => a.application_id === selected) ?? null;
  const pending = list.data?.pending ?? 0;
  return (
    <>
      <TopBar crumbs={[{ label: "Accounts", icon: UserCheck }, { label: "Approvals" }]} />
      <PageBody wide>
        <PageTitle sub="Baler operators and industry buyers who registered themselves. Nobody can use their dashboard, and the matcher ignores them, until you approve.">
          Approvals
        </PageTitle>
        <div className="flex flex-wrap items-center gap-3">
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: "PENDING", label: pending ? `Pending · ${pending}` : "Pending" },
              { value: "APPROVED", label: "Approved" },
              { value: "REJECTED", label: "Rejected" },
              { value: "all", label: "All" },
            ]}
          />
          <span className="ml-auto text-[13px] text-muted tabular">{rows?.length ?? 0} applications</span>
        </div>
        {list.error ? <ErrorNote error={list.error} onRetry={() => void list.refetch()} /> : null}
        <Card bodyClassName="p-0">
          <DataTable<Application>
            rows={rows}
            loading={list.isLoading}
            rowKey={(a) => a.application_id}
            selectedKey={selected}
            onRowClick={(a) => setSelected(a.application_id)}
            empty={
              <Empty title={filter === "PENDING" ? "Nothing waiting for you" : "No applications"}>
                New applications from the Create account page appear here.
              </Empty>
            }
            columns={[
              { key: "name", header: "Name", render: (a) => <span className="font-medium">{a.name}</span> },
              { key: "role", header: "Role", render: (a) => <Chip>{ROLE_LABEL[a.role]}</Chip> },
              { key: "org", header: "Organisation", render: (a) => a.org_name },
              { key: "village", header: "Village", render: (a) => <Chip>{a.village_name ?? a.village_id}</Chip> },
              { key: "sent", header: "Submitted", render: (a) => fmtDay(a.created_at) },
              {
                key: "status",
                header: "Status",
                render: (a) => (
                  <span className="inline-flex items-center gap-1.5">
                    <Chip>{STATUS_LABEL[a.status]}</Chip>
                    {a.duplicates?.length ? <span className="text-xs text-muted">possible duplicate</span> : null}
                  </span>
                ),
              },
            ]}
          />
        </Card>
      </PageBody>
      {open ? <ApplicationDrawer key={open.application_id} app={open} onClose={() => setSelected(null)} /> : null}
    </>
  );
}
