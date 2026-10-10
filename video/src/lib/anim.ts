import { Easing, interpolate, spring } from "remotion";
import type { CSSProperties } from "react";

export const FPS = 30;

export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeIn = Easing.bezier(0.5, 0, 0.75, 0);

/** 0→1 (or from→to) between frames a and b, clamped. */
export function ramp(f: number, a: number, b: number, from = 0, to = 1, easing = easeOut): number {
  if (b <= a) return f >= a ? to : from;
  return interpolate(f, [a, b], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing,
  });
}

/** Fade + small rise, once. Product motion: no bounce. */
export function rise(f: number, start: number, dur = 16, dist = 14): CSSProperties {
  const p = ramp(f, start, start + dur);
  return { opacity: p, transform: `translateY(${(1 - p) * dist}px)` };
}

/** Critically damped pop for icons and nodes (settles, never wobbles). */
export function pop(f: number, start: number): number {
  return spring({ frame: f - start, fps: FPS, config: { damping: 26, stiffness: 180, mass: 0.9 } });
}

/** Position along a polyline at t ∈ [0, 1]. */
export function along(points: [number, number][], t: number): [number, number] {
  const segs: number[] = [];
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    const d = Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
    segs.push(d);
    total += d;
  }
  let dist = Math.max(0, Math.min(1, t)) * total;
  for (let i = 0; i < segs.length; i++) {
    if (dist <= segs[i] || i === segs.length - 1) {
      const k = segs[i] === 0 ? 0 : Math.min(1, dist / segs[i]);
      return [
        points[i][0] + (points[i + 1][0] - points[i][0]) * k,
        points[i][1] + (points[i + 1][1] - points[i][1]) * k,
      ];
    }
    dist -= segs[i];
  }
  return points[points.length - 1];
}

/** Deterministic random (mulberry32) so every render is identical. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
