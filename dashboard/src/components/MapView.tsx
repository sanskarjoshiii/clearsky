import {
  LngLatBounds,
  Map as MLMap,
  Marker,
  NavigationControl,
  setWorkerUrl,
  type ExpressionSpecification,
  type GeoJSONSource,
  type MapLayerMouseEvent,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 runs tile/GeoJSON parsing in an ES-module worker; Vite bundles it (with its shared chunk)
// and hands us the URL. Without this, GeoJSON layers silently never render.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

setWorkerUrl(workerUrl);
import { useEffect, useRef } from "react";
import type { FieldRow, RiskLevel, Stop, Village } from "../api/types";
import { env } from "../env";
import { cx } from "./ui";

/** Map colours come from CSS variables (styles.css is the only place hex values live). */
function token(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/**
 * Default basemap: OpenFreeMap "positron" (free OpenStreetMap vector tiles, no API key), a quiet light
 * style that suits the white canvas. Set VITE_MAP_STYLE_URL to use Amazon Location instead.
 */
const DEFAULT_STYLE = "https://tiles.openfreemap.org/styles/positron";
/** Offline fallback if the style can't load: plain OSM raster tiles. */
const OSM_RASTER: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const SANGRUR: [number, number] = [75.95, 30.15];

function fieldsGeo(fields: FieldRow[], selected?: string | null): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: fields.map((f) => ({
      type: "Feature",
      id: f.field_id,
      geometry: { type: "Point", coordinates: [f.lng, f.lat] },
      properties: {
        id: f.field_id,
        level: f.risk_level,
        selected: f.field_id === selected ? 1 : 0,
        acres: f.acres,
        // booked/cleared = solid dot; still unbooked = ring in its risk colour (needs attention)
        open: f.status === "REGISTERED" || f.status === "HARVESTED" ? 1 : 0,
      },
    })),
  };
}

function villageLevel(v: Village): RiskLevel {
  const s = v.risk_max_score;
  return v.risk_red_fields > 0 || s >= 60 ? "RED" : v.risk_yellow_fields > 0 || s >= 40 ? "YELLOW" : "GREEN";
}

function villagesGeo(villages: Village[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: villages.map((v) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [v.lng, v.lat] },
      properties: { id: v.village_id, name: v.name, level: villageLevel(v), unbooked: v.risk_unbooked_acres },
    })),
  };
}

export interface MapViewProps {
  fields?: FieldRow[];
  villages?: Village[];
  heat?: GeoJSON.FeatureCollection | null;
  route?: [number, number][];
  stops?: Stop[];
  base?: { lat: number; lng: number } | null;
  selectedId?: string | null;
  focus?: { lat: number; lng: number; zoom?: number } | null;
  onFieldClick?: (id: string) => void;
  onVillageClick?: (id: string) => void;
  className?: string;
}

export function MapView({ fields = [], villages = [], heat, route, stops, base, selectedId, focus, onFieldClick, onVillageClick, className }: MapViewProps) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const ready = useRef(false);
  const onReady = useRef<(() => void) | null>(null);
  const fitted = useRef(false);
  const markers = useRef<Marker[]>([]);
  const handlers = useRef({ onFieldClick, onVillageClick });
  handlers.current = { onFieldClick, onVillageClick };

  // create once
  useEffect(() => {
    if (!el.current || map.current) return;
    const m = new MLMap({
      container: el.current,
      style: env.mapStyleUrl || DEFAULT_STYLE,
      center: SANGRUR,
      zoom: 9,
      attributionControl: { compact: true },
      cooperativeGestures: false,
    });
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.current = m;
    let fellBack = false;
    m.on("error", (e) => {
      console.warn("[map]", e.error?.message ?? e);
      // style JSON unreachable (offline / blocked) → plain OSM raster so the data layers still render
      if (!fellBack && !ready.current && !m.isStyleLoaded() && String(e.error?.message ?? "").match(/style|fetch|load/i)) {
        fellBack = true;
        m.setStyle(OSM_RASTER);
      }
    });
    const ok = token("--map-ok", "green");
    const warn = token("--map-warn", "orange");
    const risk = token("--map-risk", "red");
    const colorByLevel: ExpressionSpecification =["match", ["get", "level"], "RED", risk, "YELLOW", warn, ok];
    m.on("load", () => {
      m.addSource("heat", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "heat",
        type: "heatmap",
        source: "heat",
        // hidden unless there is FIRMS data: an idle heatmap still allocates float framebuffers, which
        // fail on some software-WebGL setups and stop the layers drawn after it
        layout: { visibility: "none" },
        paint: {
          "heatmap-radius": 18,
          "heatmap-opacity": 0.55,
          "heatmap-color": [
            "interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(0,0,0,0)", 0.3, token("--map-heat-1", "wheat"), 0.7, token("--map-heat-2", "orange"), 1, token("--map-heat-3", "red"),
          ],
        },
      });
      m.addSource("villages", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "villages",
        type: "circle",
        source: "villages",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "unbooked"], 0, 8, 60, 26],
          "circle-color": colorByLevel,
          "circle-opacity": 0.1,
          "circle-stroke-color": colorByLevel,
          "circle-stroke-width": 1,
          "circle-stroke-opacity": 0.45,
        },
      });
      m.addSource("route", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "route",
        type: "line",
        source: "route",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": token("--map-route", "purple"), "line-width": 3, "line-opacity": 0.85, "line-dasharray": [2, 1.5] },
      });
      m.addSource("fields", { type: "geojson", data: EMPTY });
      m.addLayer({
        id: "fields-halo",
        type: "circle",
        source: "fields",
        filter: ["==", ["get", "level"], "RED"],
        paint: { "circle-radius": 12, "circle-color": risk, "circle-opacity": 0.2 },
      });
      m.addLayer({
        id: "fields",
        type: "circle",
        source: "fields",
        paint: {
          "circle-radius": ["case", ["==", ["get", "selected"], 1], 8.5, ["==", ["get", "open"], 1], 6, 5],
          "circle-color": ["case", ["==", ["get", "open"], 1], token("--map-pin-stroke", "white"), colorByLevel],
          "circle-stroke-color": ["case", ["==", ["get", "selected"], 1], token("--map-base", "black"), ["==", ["get", "open"], 1], colorByLevel, token("--map-pin-stroke", "white")],
          "circle-stroke-width": ["case", ["==", ["get", "selected"], 1], 2.5, ["==", ["get", "open"], 1], 2.5, 1.5],
          "circle-color-transition": { duration: 600 },
        },
      });
      m.on("click", "fields", (e: MapLayerMouseEvent) => {
        const id = e.features?.[0]?.properties?.id as string | undefined;
        if (id) handlers.current.onFieldClick?.(id);
      });
      m.on("click", "villages", (e: MapLayerMouseEvent) => {
        if (m.queryRenderedFeatures(e.point, { layers: ["fields"] }).length) return;
        const id = e.features?.[0]?.properties?.id as string | undefined;
        if (id) handlers.current.onVillageClick?.(id);
      });
      for (const layer of ["fields", "villages"]) {
        m.on("mouseenter", layer, () => (m.getCanvas().style.cursor = "pointer"));
        m.on("mouseleave", layer, () => (m.getCanvas().style.cursor = ""));
      }
      ready.current = true;
      onReady.current?.();
      onReady.current = null;
      if (import.meta.env.DEV) (window as unknown as { __clearskyMap?: MLMap }).__clearskyMap = m;
    });
    // pulse the RED halo (cheap: one paint property per frame)
    let raf = 0;
    const t0 = performance.now();
    const tick = () => {
      if (ready.current && m.getLayer("fields-halo")) {
        const p = ((performance.now() - t0) % 1800) / 1800;
        m.setPaintProperty("fields-halo", "circle-radius", 7 + p * 11);
        m.setPaintProperty("fields-halo", "circle-opacity", 0.35 * (1 - p));
      }
      raf = requestAnimationFrame(tick);
    };
    if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      m.remove();
      map.current = null;
      ready.current = false;
    };
  }, []);

  // data updates
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      (m.getSource("fields") as GeoJSONSource | undefined)?.setData(fieldsGeo(fields, selectedId));
      (m.getSource("villages") as GeoJSONSource | undefined)?.setData(villagesGeo(villages));
      (m.getSource("heat") as GeoJSONSource | undefined)?.setData(heat ?? EMPTY);
      if (m.getLayer("heat")) m.setLayoutProperty("heat", "visibility", heat?.features.length ? "visible" : "none");
      (m.getSource("route") as GeoJSONSource | undefined)?.setData(
        route && route.length > 1 ? { type: "Feature", geometry: { type: "LineString", coordinates: route }, properties: {} } : EMPTY,
      );
      // fit once to whatever we have
      const pts: [number, number][] = [
        ...fields.map((f) => [f.lng, f.lat] as [number, number]),
        ...(stops ?? []).map((s) => [s.lng, s.lat] as [number, number]),
        ...(base ? [[base.lng, base.lat] as [number, number]] : []),
        ...(fields.length || stops?.length ? [] : villages.map((v) => [v.lng, v.lat] as [number, number])),
      ];
      const first = pts[0];
      if (!fitted.current && first) {
        const b = new LngLatBounds(first, first);
        pts.forEach((p) => b.extend(p));
        m.fitBounds(b, { padding: 48, maxZoom: 13, duration: 0 });
        fitted.current = true;
      }
    };
    if (ready.current) apply();
    else onReady.current = apply;
  }, [fields, villages, heat, route, stops, base, selectedId]);

  // numbered stop markers + baler base (HTML markers: raster styles have no glyphs for text layers)
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    markers.current.forEach((mk) => mk.remove());
    markers.current = [];
    if (base) {
      const node = document.createElement("div");
      node.className = "flex size-7 items-center justify-center rounded-[8px] bg-ink text-canvas text-[11px] font-semibold shadow";
      node.textContent = "⌂";
      node.setAttribute("aria-label", "Baler base");
      markers.current.push(new Marker({ element: node }).setLngLat([base.lng, base.lat]).addTo(m));
    }
    for (const s of stops ?? []) {
      const node = document.createElement("div");
      const done = s.status === "DONE";
      node.className = `flex size-7 items-center justify-center rounded-full border-2 border-canvas text-[12px] font-semibold shadow ${done ? "bg-ok text-canvas" : "bg-agent text-canvas"}`;
      node.textContent = done ? "✓" : String(s.stop_order);
      node.setAttribute("aria-label", `Stop ${s.stop_order} ${s.farmer_name ?? ""}`);
      markers.current.push(new Marker({ element: node }).setLngLat([s.lng, s.lat]).addTo(m));
    }
  }, [stops, base]);

  useEffect(() => {
    if (focus && map.current) map.current.flyTo({ center: [focus.lng, focus.lat], zoom: focus.zoom ?? 12, duration: 700 });
  }, [focus]);

  return <div ref={el} className={cx("relative w-full overflow-hidden", className)} role="region" aria-label="Map" />;
}
