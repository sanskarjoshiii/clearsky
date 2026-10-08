const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-10-25" → "25 Oct" (dates are calendar dates in IST; never shifted by the browser timezone). */
export function fmtDay(iso: string | null | undefined): string {
  if (!iso) return "–";
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${Number(d)} ${MONTHS[Number(m) - 1] ?? ""}`;
}

export function fmtDayLong(iso: string): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}

export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(`${b.slice(0, 10)}T00:00:00Z`) - Date.parse(`${a.slice(0, 10)}T00:00:00Z`)) / 86_400_000);
}

const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 });
const int = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export const fmtNum = (n: number | null | undefined): string => (n == null ? "–" : num.format(n));
export const fmtInt = (n: number | null | undefined): string => (n == null ? "–" : int.format(n));
export const fmtInr = (n: number | null | undefined): string => (n == null ? "–" : `₹${int.format(n)}`);

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export const titleCase = (s: string): string => s.charAt(0) + s.slice(1).toLowerCase();
