import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useImpactTable, useStats } from "../api/hooks";
import type { ImpactTableData } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { ImpactTable } from "../components/ImpactTable";
import { Logo } from "../components/Shell";
import { Card, ErrorNote, Segmented, Skeleton } from "../components/ui";
import { fmtDay, fmtInr, fmtInt, fmtNum } from "../lib/format";
import { inUnit } from "../lib/impact";

/** Count up once from the previous value (reduced motion: jump straight to the value). */
function useCountUp(value: number, ms = 1200): number {
  const [shown, setShown] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(a + (value - a) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
      else from.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return shown;
}

function Counter({ label, value, format, note }: { label: string; value: number; format: (n: number) => string; note?: string }) {
  const n = useCountUp(value);
  return (
    <div className="border-b border-r border-line px-6 py-8 sm:px-8 sm:py-10">
      <div className="text-sm text-muted">{label}</div>
      <div className="tabular mt-2 text-[44px] font-semibold leading-none tracking-[var(--tracking-display)] text-ink sm:text-[64px]">{format(n)}</div>
      {note ? <div className="mt-2 text-xs text-faint">{note}</div> : null}
    </div>
  );
}

/** Running total over the season for the headline pollutant. */
function SeasonChart({ data }: { data: ImpactTableData }) {
  const key = data.primary;
  const f = key ? data.factors[key] : undefined;
  if (!f || data.district.trend.length < 2) return null;
  const points = [
    ...data.district.trend.map((p) => ({ day: fmtDay(p.date), value: inUnit(p.cumulative, f.unit) })),
    { day: fmtDay(data.season.to), value: inUnit(data.district.trend[data.district.trend.length - 1]!.cumulative, f.unit) },
  ];
  return (
    <Card title={`${f.label} avoided over the season (${f.unit}, estimate)`}>
      <div className="h-[260px]">
        <ResponsiveContainer>
          <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid vertical={false} stroke="var(--color-line)" strokeDasharray="3 3" />
            <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} minTickGap={24} />
            <YAxis tickLine={false} axisLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: "1px solid var(--color-line)", fontSize: 13 }}
              formatter={(v) => [`${fmtNum(Number(v))} ${f.unit}`, `${f.label} avoided`]}
            />
            <Area type="stepAfter" dataKey="value" stroke="var(--color-data-1)" strokeWidth={2} fill="var(--color-data-3)" fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

/** Where every number comes from: the formula, each factor and its citation. */
function Methodology({ data }: { data: ImpactTableData }) {
  return (
    <section className="rounded-[var(--radius-card)] border border-line px-5 py-4 text-[13px] text-ink-2" aria-label="Methodology">
      <h2 className="text-[15px] font-medium tracking-[var(--tracking-title)] text-ink">How this is estimated</h2>
      <p className="mt-2">
        Straw that is baled and taken away is straw that is not burnt in the field. For each cleared field: <span className="text-ink">{data.formula}</span>.
        Straw tonnes come from the field's acres. {data.burn_fraction < 1 ? `Only ${Math.round(data.burn_fraction * 100)}% of the straw is assumed to have been burnt otherwise. ` : "The figures show what burning that straw would have emitted. "}
        These are <strong className="font-medium text-ink">estimates, not measurements</strong>.
      </p>
      <ul className="mt-3 space-y-1.5">
        {Object.entries(data.factors).map(([key, f]) => (
          <li key={key}>
            <span className="font-medium text-ink">{f.label}</span>: {fmtNum(f.kg_per_tonne)} kg per tonne of rice straw burnt. Source:{" "}
            {f.url ? (
              <a href={f.url} target="_blank" rel="noreferrer" className="underline">
                {f.source}
              </a>
            ) : (
              f.source
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Public impact page, built for screen recording (PLAN.md Phase 7) and for the pollution-avoided table (issue #5). */
export function Impact() {
  const stats = useStats();
  const { me } = useAuth();
  const [mode, setMode] = useState<"pollutant" | "week">("pollutant");
  const table = useImpactTable(mode === "week" ? "week" : "season");
  const s = stats.data;
  const t = table.data;
  const configured = !!s?.impact_configured;
  return (
    <div className="min-h-dvh bg-frame p-2 sm:p-4">
      <div className="mx-auto flex min-h-[calc(100dvh-1rem)] max-w-[1280px] flex-col rounded-[var(--radius-canvas)] bg-canvas shadow-[var(--shadow-canvas)]">
        <header className="flex items-center justify-between px-6 pt-6 sm:px-10 sm:pt-9">
          <div className="flex items-center gap-2 text-sm text-muted">
            <Logo size="size-8" />
            <span className="size-2 rounded-full bg-ok" /> Live · clearsky, Sangrur
          </div>
          {me ? (
            <Link to="/" className="text-sm text-muted hover:text-ink">
              Back to dashboard
            </Link>
          ) : null}
        </header>
        <div className="px-6 pb-8 pt-6 sm:px-10">
          <h1 className="max-w-4xl text-[36px] font-semibold leading-[1.05] tracking-[var(--tracking-display)] sm:text-[60px]">
            Straw picked up, not burnt.
          </h1>
          <p className="mt-3 max-w-2xl text-base text-muted">
            Every acre here was booked by a farmer on WhatsApp and cleared by a baler before the wheat-sowing deadline.
          </p>
        </div>
        {stats.error ? (
          <div className="px-6 sm:px-10">
            <ErrorNote error={stats.error} onRetry={() => void stats.refetch()} />
          </div>
        ) : null}
        {s ? (
          <div className="mx-6 mb-6 grid grid-cols-1 overflow-hidden rounded-[var(--radius-card)] border-l border-t border-line sm:mx-10 sm:grid-cols-2 lg:grid-cols-3">
            <Counter label="Acres booked for pickup" value={s.acres_booked} format={fmtInt} />
            <Counter label="Acres cleared" value={s.acres_cleared} format={fmtInt} />
            <Counter label="Tonnes of straw routed to industry" value={s.tonnes_booked} format={fmtInt} />
            <Counter label="Farmers on WhatsApp" value={s.farmers} format={fmtInt} />
            <Counter label="Fields saved after an officer alert" value={s.fields_saved_after_alert} format={fmtInt} />
            <Counter label="Estimated farmer payouts" value={s.payouts_estimated_inr} format={fmtInr} note="demo prices, not market rates" />
            {Object.entries(s.impact).map(([key, v]) => (
              <Counter
                key={key}
                label={`${v.label} avoided (${v.unit}, estimate)`}
                value={v.value}
                format={v.value >= 100 ? fmtInt : fmtNum}
                note={`Source: ${v.source}`}
              />
            ))}
          </div>
        ) : (
          <div className="mx-6 mb-6 sm:mx-10">
            <Skeleton className="h-80" />
          </div>
        )}

        {configured && t ? (
          <div className="mx-6 mb-8 flex flex-col gap-6 sm:mx-10">
            <SeasonChart data={t} />
            <Card
              title="Pollution avoided, field by field (estimate)"
              bodyClassName="p-0"
              actions={
                <Segmented
                  value={mode}
                  onChange={setMode}
                  options={[
                    { value: "pollutant", label: "By pollutant" },
                    { value: "week", label: "By week" },
                  ]}
                />
              }
            >
              {t.district.fields ? (
                <ImpactTable data={t} mode={mode} />
              ) : (
                <p className="px-4 py-8 text-center text-sm text-muted">No field has been cleared yet. Each cleared field appears here with what it kept out of the air.</p>
              )}
            </Card>
            <Methodology data={t} />
          </div>
        ) : null}
        {table.error && configured ? (
          <div className="mx-6 mb-6 sm:mx-10">
            <ErrorNote error={table.error} onRetry={() => void table.refetch()} />
          </div>
        ) : null}
        {s && !configured && me?.role === "officer" ? (
          <p className="mx-6 mb-8 rounded-[var(--radius-card)] border border-line bg-sunken px-4 py-3 text-[13px] text-ink-2 sm:mx-10" role="note">
            Add emission factors (with sources) to show pollution avoided: set <code>EMISSION_FACTORS</code> to published values for open burning of
            rice straw, each with its citation. Nothing is shown until then, so no unsourced number ever appears here.
          </p>
        ) : null}
      </div>
    </div>
  );
}

/** Lazy route entry (App.tsx): keeps the chart library out of the main bundle. */
export const Component = Impact;
