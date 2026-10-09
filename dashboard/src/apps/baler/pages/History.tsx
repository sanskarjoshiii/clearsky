import { Check } from "lucide-react";
import { useBalerHistory } from "../../../api/hooks";
import { Empty, ErrorNote, KpiStrip, Skeleton } from "../../../components/ui";
import { fmtDay, fmtNum } from "../../../lib/format";
import { impactAmount } from "../../../lib/impact";
import { BalerPage } from "../Layout";

/** Fields this baler has cleared this season, with totals. */
export function History() {
  const history = useBalerHistory();
  const h = history.data;
  const first = h ? Object.entries(h.totals.impact)[0] : undefined; // headline pollutant for the rows
  return (
    <BalerPage>
      <div>
        <h1 className="text-[22px] font-semibold tracking-[var(--tracking-display)]">Cleared fields · साफ़ किए खेत</h1>
        {h ? (
          <p className="mt-1 text-[13px] text-muted">
            {fmtDay(h.from)} – {fmtDay(h.to)}
          </p>
        ) : null}
      </div>
      {history.error ? <ErrorNote error={history.error} onRetry={() => void history.refetch()} /> : null}
      {history.isLoading ? <Skeleton className="h-64" /> : null}
      {h ? (
        <>
          <KpiStrip
            items={[
              { label: "Fields cleared", value: h.totals.fields },
              { label: "Acres", value: fmtNum(h.totals.acres) },
              { label: "Straw baled", value: `${fmtNum(h.totals.tonnes)} t`, hint: "estimate" },
              // season total of what this baler's work kept out of the air (only with sourced factors)
              ...Object.values(h.totals.impact).map((v) => ({
                label: `${v.label} avoided`,
                value: `${fmtNum(v.value)} ${v.unit}`,
                hint: "estimate",
              })),
            ]}
          />
          {h.rows.length === 0 ? (
            <Empty title="No cleared fields yet">Fields you mark Done on the Today tab are listed here.</Empty>
          ) : (
            <ul className="overflow-hidden rounded-[var(--radius-card)] border border-line">
              {h.rows.map((r) => (
                <li key={r.booking_id} className="flex min-h-[56px] items-center gap-3 border-b border-line px-4 py-2.5 last:border-0">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sunken text-ink-2">
                    <Check className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-ink">{r.farmer_name ?? "Farmer"}</div>
                    <div className="truncate text-[13px] text-muted">
                      {r.village_name} · {fmtDay(r.date)}
                    </div>
                  </div>
                  <div className="shrink-0 text-right text-[13px] tabular text-muted">
                    <div className="text-ink">{fmtNum(r.acres)} ac</div>
                    <div>~{fmtNum(r.est_tonnes)} t</div>
                    {first && r.impact[first[0]] != null ? (
                      <div>
                        ~{impactAmount(r.impact[first[0]]!, first[1].unit)} {first[1].label}
                      </div>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </BalerPage>
  );
}
