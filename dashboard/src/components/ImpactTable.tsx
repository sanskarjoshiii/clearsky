import { ChevronDown, ChevronRight, Hash, Sigma } from "lucide-react";
import { useState } from "react";
import type { ImpactFieldRow, ImpactGroup, ImpactKg, ImpactTableData } from "../api/types";
import { fmtDay, fmtNum } from "../lib/format";
import { impactAmount } from "../lib/impact";
import { Sparkline } from "./Sparkline";
import { cx } from "./ui";

const PAGE = 8; // villages shown before "Show more"

interface Col {
  key: string;
  header: string;
  cell: (impact: ImpactKg, byWeek?: Record<string, ImpactKg>) => string;
}

/**
 * Pollution avoided per cleared field, in the style of the reference "model" table
 * (designs/modelling-1.jpg): group header chips (one per village, collapsible, district total on
 * top), a variable row per cleared field, a Trend sparkline, a lavender Formula pill that shows the
 * calculation, and one column per pollutant (or per week of the season).
 *
 * Read-only and public: farmer names arrive masked from the API. Every figure is an estimate.
 */
export function ImpactTable({ data, mode = "pollutant" }: { data: ImpactTableData; mode?: "pollutant" | "week" }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [pages, setPages] = useState(1);
  const factors = data.factors;
  const keys = Object.keys(factors);
  const primary = data.primary && factors[data.primary] ? data.primary : keys[0];
  if (!primary) return null; // no sourced factors: there is nothing honest to show
  const pf = factors[primary]!;

  const cols: Col[] =
    mode === "week"
      ? data.weeks.map((w) => ({
          key: w,
          header: `Week of ${fmtDay(w)}`,
          cell: (_impact, byWeek) => (byWeek?.[w]?.[primary] != null ? impactAmount(byWeek[w]![primary]!, pf.unit) : "–"),
        }))
      : keys.map((k) => ({
          key: k,
          header: `${factors[k]!.label} (${factors[k]!.unit})`,
          cell: (impact) => (impact[k] != null ? impactAmount(impact[k]!, factors[k]!.unit) : "–"),
        }));

  const formulaTitle = `${pf.label}: ${fmtNum(pf.kg_per_tonne)} kg per tonne of rice straw burnt in the open${
    data.burn_fraction < 1 ? ` × burn fraction ${data.burn_fraction}` : ""
  }. Source: ${pf.source}`;
  const formula = (tonnes: number) => (
    <span
      title={formulaTitle}
      className="inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-[var(--radius-chip)] bg-agent-soft px-1.5 text-xs font-medium text-agent-strong"
    >
      <Hash className="size-3" aria-hidden /> {fmtNum(tonnes)} t straw × {pf.label} factor
    </span>
  );
  const trendLabel = (name: string, impact: ImpactKg) =>
    `${name}: ${impact[primary] != null ? impactAmount(impact[primary]!, pf.unit) : "no"} ${pf.label} avoided so far (estimate)`;

  const td = "whitespace-nowrap border-r border-line px-3 last:border-r-0";
  const num = cx(td, "text-right tabular");

  const summaryRow = (g: ImpactGroup, id: string, expandable: boolean) => {
    const isOpen = !!open[id];
    return (
      <tr key={id} className="h-10 border-b border-line bg-sunken/60 text-ink">
        <th scope="row" className={cx(td, "text-left font-normal")}>
          {expandable ? (
            <button
              type="button"
              aria-expanded={isOpen}
              aria-label={`${g.label}: ${isOpen ? "hide" : "show"} ${g.fields} cleared field${g.fields === 1 ? "" : "s"}`}
              onClick={() => setOpen({ ...open, [id]: !isOpen })}
              className="inline-flex items-center gap-1.5 rounded-[var(--radius-chip)] border border-line bg-canvas px-1.5 py-0.5 text-[13px] font-medium hover:bg-hover"
            >
              {isOpen ? <ChevronDown className="size-3.5" aria-hidden /> : <ChevronRight className="size-3.5" aria-hidden />}
              {g.label}
              <span className="font-normal text-muted">
                {g.fields} field{g.fields === 1 ? "" : "s"}
              </span>
            </button>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-[var(--radius-chip)] border border-line bg-canvas px-1.5 py-0.5 text-[13px] font-medium">
              <Sigma className="size-3.5 text-muted" aria-hidden />
              {g.label}
              <span className="font-normal text-muted">
                {g.fields} field{g.fields === 1 ? "" : "s"}
              </span>
            </span>
          )}
        </th>
        <td className={num}>{fmtNum(g.acres)}</td>
        <td className={td} />
        <td className={td}>
          <Sparkline points={g.trend} from={data.season.from} to={data.season.to} label={trendLabel(g.label, g.impact)} />
        </td>
        <td className={td}>{formula(g.tonnes)}</td>
        {cols.map((c) => (
          <td key={c.key} className={cx(num, "font-medium")}>
            {c.cell(g.impact, g.by_week)}
          </td>
        ))}
      </tr>
    );
  };

  const fieldRow = (r: ImpactFieldRow, key: string) => (
    <tr key={key} className="h-10 border-b border-line text-ink">
      <th scope="row" className={cx(td, "pl-9 text-left font-normal")}>
        <span className="inline-flex items-center gap-1.5">
          <Hash className="size-3.5 text-faint" aria-hidden />
          {r.label}
        </span>
      </th>
      <td className={num}>{fmtNum(r.acres)}</td>
      <td className={cx(td, "text-muted")}>{fmtDay(r.cleared_date)}</td>
      <td className={td}>
        <Sparkline points={r.trend} from={data.season.from} to={data.season.to} label={trendLabel(r.label, r.impact)} />
      </td>
      <td className={td}>{formula(r.tonnes)}</td>
      {cols.map((c) => (
        <td key={c.key} className={num}>
          {c.cell(r.impact, r.by_week)}
        </td>
      ))}
    </tr>
  );

  const groups = data.groups ?? [];
  const shown = groups.slice(0, pages * PAGE);
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-[13px]">
          <caption className="sr-only">Estimated pollution avoided per cleared field, grouped by village</caption>
          <thead>
            <tr className="h-9 border-b border-line text-left text-muted">
              <th scope="col" className={cx(td, "font-normal")}>
                {data.rows ? "Cleared field" : "Village / cleared field"}
              </th>
              <th scope="col" className={cx(td, "text-right font-normal")}>
                Acres
              </th>
              <th scope="col" className={cx(td, "font-normal")}>
                Cleared
              </th>
              <th scope="col" className={cx(td, "font-normal")}>
                Trend
              </th>
              <th scope="col" className={cx(td, "font-normal")}>
                Formula
              </th>
              {cols.map((c) => (
                <th key={c.key} scope="col" className={cx(td, "text-right font-normal")}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summaryRow(data.district, "district", false)}
            {data.rows ? data.rows.map((r, i) => fieldRow(r, `f${i}`)) : null}
            {shown.flatMap((g) => {
              const id = g.village_id ?? g.label;
              return [summaryRow(g, id, true), ...(open[id] ? (g.rows ?? []).map((r, i) => fieldRow(r, `${id}-${i}`)) : [])];
            })}
          </tbody>
        </table>
      </div>
      {groups.length > shown.length ? (
        <div className="border-t border-line px-3 py-2">
          <button type="button" className="text-[13px] text-muted underline hover:text-ink" onClick={() => setPages(pages + 1)}>
            Show {Math.min(PAGE, groups.length - shown.length)} more villages
          </button>
        </div>
      ) : null}
    </div>
  );
}
