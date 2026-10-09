import { BellRing, Flame, Radar as RadarIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { useFields, useLayer, useSendAlert, useStats, useVillages } from "../../../api/hooks";
import type { FieldRow, Village } from "../../../api/types";
import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../components/DataTable";
import { FieldDrawer } from "../../../components/FieldDrawer";
import { MapView } from "../../../components/MapView";
import { PageBody, TopBar } from "../../../components/Shell";
import {
  Button,
  Card,
  Chip,
  ConfirmDialog,
  cx,
  Empty,
  ErrorNote,
  KpiStrip,
  PageTitle,
  RiskPill,
  Skeleton,
  Toggle,
  useToast,
} from "../../../components/ui";
import { daysBetween, fmtDay, fmtInt, fmtNum } from "../../../lib/format";

/** Confirm + send a village alert. Shared by the radar, the drawer and the fields table. */
export function useAlertVillage(villages: Village[] | undefined) {
  const [target, setTarget] = useState<string | null>(null);
  const send = useSendAlert();
  const toast = useToast();
  const village = villages?.find((v) => v.village_id === target);
  const dialog = (
    <ConfirmDialog
      open={!!target}
      title={`Alert ${village?.name ?? "village"}?`}
      confirmLabel="Send WhatsApp offer"
      busy={send.isPending}
      onClose={() => setTarget(null)}
      onConfirm={() =>
        target &&
        send.mutate(target, {
          onSuccess: (r) => {
            toast(
              r.cooldown
                ? `Already alerted in the last 30 minutes (${r.farmers_notified} farmers).`
                : `Offer sent to ${r.farmers_notified} farmer${r.farmers_notified === 1 ? "" : "s"} · ${r.balers_flagged.length} baler${r.balers_flagged.length === 1 ? "" : "s"} flagged`,
            );
            setTarget(null);
          },
          onError: (e) => toast(e.message, "error"),
        })
      }
    >
      Every farmer in {village?.name ?? "this village"} with an unbooked field gets a one-tap booking offer on WhatsApp
      ({fmtNum(village?.risk_unbooked_acres ?? 0)} unbooked acres). Nearby balers with free capacity see the village on their
      dashboard.
    </ConfirmDialog>
  );
  return { open: setTarget, dialog };
}

function VillageRow({ v, onAlert, onFocus, active }: { v: Village; onAlert: () => void; onFocus: () => void; active: boolean }) {
  const level = v.risk_red_fields > 0 ? "RED" : v.risk_yellow_fields > 0 ? "YELLOW" : "GREEN";
  return (
    <li className={cx("flex items-center gap-3 px-4 py-2.5", active && "bg-agent-soft/40")}>
      <button className="min-w-0 flex-1 text-left" onClick={onFocus}>
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-ink">{v.name}</span>
          <span className="truncate text-xs text-faint">{v.block}</span>
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted tabular">
          <RiskPill level={level} />
          {v.risk_red_fields ? <span>{v.risk_red_fields} red</span> : null}
          {v.risk_yellow_fields ? <span>{v.risk_yellow_fields} amber</span> : null}
          <span>{fmtNum(v.risk_unbooked_acres)} ac unbooked</span>
        </div>
      </button>
      <Button size="sm" onClick={onAlert} disabled={v.risk_unbooked_acres <= 0} title={`Alert ${v.name}`} aria-label={`Alert ${v.name}`}>
        <BellRing className="size-3.5" /> Alert
      </Button>
    </li>
  );
}

export function Radar() {
  const { me } = useAuth();
  const stats = useStats();
  const villages = useVillages();
  const fields = useFields();
  const [heatOn, setHeatOn] = useState(false);
  const heat = useLayer("firms", heatOn);
  const [selected, setSelected] = useState<string | null>(null);
  const [villageFilter, setVillageFilter] = useState<string | null>(null);
  const alert = useAlertVillage(villages.data);
  const today = stats.data?.today ?? me?.config.today;

  const shown = useMemo(
    () => (fields.data ?? []).filter((f) => !villageFilter || f.village_id === villageFilter),
    [fields.data, villageFilter],
  );
  const atRisk = useMemo(
    () => shown.filter((f) => (f.status === "REGISTERED" || f.status === "HARVESTED") && f.risk_level !== "GREEN").slice(0, 25),
    [shown],
  );
  const focusVillage = villages.data?.find((v) => v.village_id === villageFilter);
  const rankedVillages = (villages.data ?? []).filter((v) => v.risk_unbooked_acres > 0 || v.risk_max_score > 0).slice(0, 14);
  const s = stats.data;
  const bookedPct = s && s.acres_registered ? Math.round((s.acres_booked / s.acres_registered) * 100) : null;

  return (
    <>
      <TopBar crumbs={[{ label: "Radar", icon: RadarIcon }, { label: me?.district ?? "All districts" }]} />
      <PageBody wide>
        <PageTitle
          sub={
            <>
              Fields that are harvested but not booked are where fires start. Alert a village to send every farmer there a one-tap
              WhatsApp booking. {today ? <>Today is <span className="text-ink">{fmtDay(today)}</span>.</> : null}
            </>
          }
        >
          Burn Risk Radar
        </PageTitle>

        {stats.error ? <ErrorNote error={stats.error} onRetry={() => void stats.refetch()} /> : null}
        {s ? (
          <KpiStrip
            items={[
              { label: "Acres registered", value: fmtInt(s.acres_registered), hint: `${s.fields} fields · ${s.farmers} farmers` },
              {
                label: "Acres booked",
                value: fmtInt(s.acres_booked),
                badge: bookedPct != null ? <span className="rounded-full border border-ok-line bg-ok-soft px-1.5 text-[11px] text-ok">{bookedPct}%</span> : null,
                hint: `${s.bookings} bookings`,
              },
              { label: "Acres cleared", value: fmtInt(s.acres_cleared), hint: `${s.bookings_done} pickups done` },
              {
                label: "Red fields",
                value: <span className={s.red_fields ? "text-risk" : undefined}>{s.red_fields}</span>,
                hint: `${s.yellow_fields} amber`,
              },
              { label: "Straw routed", value: `${fmtInt(s.tonnes_booked)} t`, hint: `${fmtInt(s.tonnes_delivered)} t delivered` },
              { label: "Saved after alert", value: s.fields_saved_after_alert, hint: `${s.alerts_sent} alerts sent` },
            ]}
          />
        ) : (
          <Skeleton className="h-[92px]" />
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card
            title={focusVillage ? `${focusVillage.name}` : "Sangrur district"}
            bodyClassName="p-0"
            actions={
              <>
                {villageFilter ? (
                  <Button size="sm" variant="ghost" onClick={() => setVillageFilter(null)}>
                    Show all
                  </Button>
                ) : null}
                <label className="flex items-center gap-2 pl-2 text-[13px] text-muted">
                  <Flame className="size-3.5" /> Fire history
                  <Toggle checked={heatOn} onChange={setHeatOn} label="Show FIRMS fire history" />
                </label>
              </>
            }
          >
            <div className="relative">
              <MapView
                className="h-[420px] md:h-[540px]"
                fields={shown}
                villages={villages.data ?? []}
                heat={heatOn ? heat.data?.geojson ?? null : null}
                selectedId={selected}
                focus={focusVillage ? { lat: focusVillage.lat, lng: focusVillage.lng, zoom: 12.5 } : null}
                onFieldClick={setSelected}
                onVillageClick={setVillageFilter}
              />
              <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap items-center gap-1.5 rounded-[var(--radius-control)] bg-canvas/90 p-1.5 text-[11px] text-muted shadow-[var(--shadow-canvas)]">
                <RiskPill level="RED" />
                <RiskPill level="YELLOW" />
                <RiskPill level="GREEN" />
                <span className="ml-1 flex items-center gap-1">
                  <span className="size-2.5 rounded-full border-2 border-ok bg-canvas" /> not booked
                </span>
                <span className="flex items-center gap-1">
                  <span className="size-2.5 rounded-full bg-ok" /> booked
                </span>
              </div>
              {heatOn && heat.data && !heat.data.available ? (
                <div className="absolute left-3 top-3 rounded-[var(--radius-control)] bg-canvas/95 px-3 py-2 text-xs text-muted shadow-[var(--shadow-canvas)]">
                  No FIRMS layer yet: add FIRMS_MAP_KEY and run make firms.
                </div>
              ) : null}
            </div>
          </Card>

          <Card title="Villages by risk" bodyClassName="p-0">
            {villages.isLoading ? <Skeleton className="m-4 h-64" /> : null}
            {villages.data && rankedVillages.length === 0 ? <Empty title="No unbooked fields">Every registered field is booked.</Empty> : null}
            <ul className="divide-y divide-line">
              {rankedVillages.map((v) => (
                <VillageRow
                  key={v.village_id}
                  v={v}
                  active={v.village_id === villageFilter}
                  onFocus={() => setVillageFilter(v.village_id === villageFilter ? null : v.village_id)}
                  onAlert={() => alert.open(v.village_id)}
                />
              ))}
            </ul>
          </Card>
        </div>

        <Card title={`Fields at risk${focusVillage ? ` · ${focusVillage.name}` : ""}`} bodyClassName="p-0">
          <DataTable<FieldRow>
            rows={atRisk}
            loading={fields.isLoading}
            rowKey={(f) => f.field_id}
            selectedKey={selected}
            onRowClick={(f) => setSelected(f.field_id)}
            empty={<Empty title="No fields at risk">Amber and red fields appear here when harvest is near and no booking exists.</Empty>}
            columns={[
              { key: "risk", header: "Risk", render: (f) => <RiskPill level={f.risk_level} score={f.risk_score} /> },
              { key: "farmer", header: "Farmer", render: (f) => <span className="font-medium">{f.farmer_name ?? "–"}</span> },
              { key: "village", header: "Village", render: (f) => <Chip>{f.village_name}</Chip> },
              { key: "acres", header: "Acres", align: "right", render: (f) => fmtNum(f.acres) },
              { key: "harvest", header: "Harvest", render: (f) => fmtDay(f.harvest_date) },
              {
                key: "sowing",
                header: "Days to sowing",
                align: "right",
                render: (f) => (today ? daysBetween(today, f.sowing_deadline) : "–"),
              },
              { key: "why", header: "Why", render: (f) => <span className="text-muted">{f.risk_reasons.slice(0, 3).join(" · ")}</span> },
            ]}
          />
        </Card>
      </PageBody>

      {selected ? (
        <FieldDrawer
          id={selected}
          today={today}
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
