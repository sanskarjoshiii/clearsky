import type { ImpactFactor, ImpactKg, ImpactTableData } from "../api/types";
import { fmtNum } from "./format";

/** Snapshots are stored in kg. CO₂ is shown in tonnes; everything else in kg. */
export function inUnit(kg: number, unit: string): number {
  return unit === "t" ? kg / 1000 : kg;
}

/** "40 kg" / "20 t" for one pollutant. */
export function impactAmount(kg: number, unit: string): string {
  return `${fmtNum(inUnit(kg, unit))} ${unit}`;
}

/**
 * The headline figure for one cleared field: the first pollutant that has a sourced factor,
 * e.g. "~40 kg PM2.5". Null when no factors are configured (the UI then shows nothing).
 */
export function headline(impact: ImpactKg | null | undefined, factors: Record<string, ImpactFactor> | undefined): string | null {
  if (!impact || !factors) return null;
  const key = Object.keys(factors).find((k) => impact[k] != null);
  const f = key ? factors[key] : undefined;
  return key && f ? `~${impactAmount(impact[key] ?? 0, f.unit)} ${f.label}` : null;
}

/**
 * Pollution avoided per cleared acre, per pollutant: the district's snapshots divided by the acres they cover.
 * Empty when no sourced factor is configured or nothing is cleared yet.
 */
export function perAcre(t: ImpactTableData | undefined): { key: string; label: string; unit: "kg" | "t"; kg: number; totalKg: number; source: string }[] {
  if (!t || !t.configured || t.district.acres <= 0) return [];
  return Object.entries(t.factors)
    .filter(([key]) => t.district.impact[key] != null)
    .map(([key, f]) => ({
      key,
      label: f.label,
      unit: f.unit,
      kg: (t.district.impact[key] ?? 0) / t.district.acres,
      totalKg: t.district.impact[key] ?? 0,
      source: f.source,
    }));
}
