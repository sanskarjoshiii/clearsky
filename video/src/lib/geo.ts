import raw from "../data/geo.json";

/** Simplified state outlines (lon, lat), from geohacker/india (state boundaries). */
type Ring = [number, number][];
export const STATES = raw as unknown as Record<string, Ring[]>;

export type Box = { x: number; y: number; w: number; h: number };
export type Bounds = { lon0: number; lon1: number; lat0: number; lat1: number };
export type Project = (lon: number, lat: number) => [number, number];

/** Equirectangular projection, scaled by cos(lat) and fitted (centred) into the box. */
export function projector(box: Box, b: Bounds): Project {
  const kx = Math.cos((((b.lat0 + b.lat1) / 2) * Math.PI) / 180);
  const s = Math.min(box.w / ((b.lon1 - b.lon0) * kx), box.h / (b.lat1 - b.lat0));
  const ox = box.x + (box.w - (b.lon1 - b.lon0) * kx * s) / 2;
  const oy = box.y + (box.h - (b.lat1 - b.lat0) * s) / 2;
  return (lon, lat) => [ox + (lon - b.lon0) * kx * s, oy + (b.lat1 - lat) * s];
}

export function ringPath(ring: Ring, p: Project): string {
  return (
    ring
      .map(([lo, la], i) => {
        const [x, y] = p(lo, la);
        return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join("") + "Z"
  );
}

export function ringLength(ring: Ring, p: Project): number {
  let len = 0;
  for (let i = 1; i < ring.length; i++) {
    const [x0, y0] = p(...ring[i - 1]);
    const [x1, y1] = p(...ring[i]);
    len += Math.hypot(x1 - x0, y1 - y0);
  }
  return len;
}

export function inside(lon: number, lat: number, ring: Ring): boolean {
  let hit = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

/** Well-known places (approximate city-centre coordinates) so judges recognise the map. */
export const CITIES = {
  Amritsar: [74.872, 31.634],
  Jalandhar: [75.576, 31.326],
  Ludhiana: [75.857, 30.901],
  Patiala: [76.386, 30.34],
  Bathinda: [74.945, 30.211],
  Chandigarh: [76.779, 30.733],
  Khanna: [76.222, 30.705],
  Delhi: [77.209, 28.614],
} as const satisfies Record<string, [number, number]>;
