import type { TrendPoint } from "../api/types";

const DAY = 86_400_000;
const day = (iso: string) => Date.parse(`${iso.slice(0, 10)}T00:00:00Z`) / DAY;

/**
 * Tiny cumulative trend for one table row (the reference's "Trend" column). A running total only
 * goes up, so it is drawn as steps: flat until a field is cleared, then a rise on that day.
 * Uses the straw data ramp, never a risk colour. `label` is read by screen readers.
 */
export function Sparkline({
  points,
  from,
  to,
  label,
  width = 96,
  height = 24,
}: {
  points: TrendPoint[];
  from: string;
  to: string;
  label: string;
  width?: number;
  height?: number;
}) {
  if (points.length < 2) return <span className="text-faint" aria-label={`${label}: no data`}>–</span>;
  const x0 = day(from);
  const span = Math.max(1, day(to) - x0);
  const max = Math.max(...points.map((p) => p.cumulative), 1e-9);
  const pad = 2;
  const x = (iso: string) => pad + (Math.min(Math.max(day(iso) - x0, 0), span) / span) * (width - 2 * pad);
  const y = (v: number) => height - pad - (v / max) * (height - 2 * pad);
  let d = `M ${x(points[0]!.date).toFixed(1)} ${y(points[0]!.cumulative).toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    const p = points[i]!;
    d += ` H ${x(p.date).toFixed(1)} V ${y(p.cumulative).toFixed(1)}`; // step: across, then up
  }
  d += ` H ${(width - pad).toFixed(1)}`; // hold the total to today
  const last = points[points.length - 1]!;
  return (
    <svg role="img" aria-label={label} width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block">
      <path d={`${d} V ${height - pad} H ${x(points[0]!.date).toFixed(1)} Z`} fill="var(--color-data-3)" opacity={0.25} />
      <path d={d} fill="none" stroke="var(--color-data-2)" strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={width - pad} cy={y(last.cumulative)} r={2} fill="var(--color-data-1)" />
    </svg>
  );
}
