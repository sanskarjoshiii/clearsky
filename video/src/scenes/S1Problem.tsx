import { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { content } from "../content";
import { AQI, C, MONO, PAD, W } from "../theme";
import { easeInOut, ramp, rise, rng } from "../lib/anim";
import { CITIES, STATES, inside, projector, ringLength, ringPath } from "../lib/geo";
import { Chip, SceneShell } from "../components/ui";

export const S1_DUR = 360; // 12 s

const BOX = { x: PAD, y: 50, w: W - 2 * PAD, h: 820 };
const BOUNDS = { lon0: 73.6, lon1: 77.9, lat0: 28.25, lat1: 32.65 };
const p = projector(BOX, BOUNDS);

const PUNJAB = STATES["Punjab"][0];
const NEIGHBOURS = ["Haryana", "Himachal Pradesh", "Rajasthan", "Delhi"] as const;
const IGNITE_FROM = 118;
const IGNITE_SPAN = 92;
const LABELLED = ["Amritsar", "Jalandhar", "Ludhiana", "Bathinda", "Patiala"] as const;

type FieldDot = { x: number; y: number; t: number; s: number; burns: boolean };

function makeFields(): FieldDot[] {
  const r = rng(42);
  const origins = [
    [75.0, 30.25],
    [75.85, 30.85],
    [74.95, 31.45],
  ];
  const out: FieldDot[] = [];
  let guard = 0;
  while (out.length < 360 && guard++ < 20000) {
    const lon = 73.85 + r() * 3.1;
    const lat = 29.5 + r() * 3.05;
    if (!inside(lon, lat, PUNJAB)) continue;
    if (lat > 32.0 && lon > 75.4) continue; // hilly north-east: few paddy fields
    const [x, y] = p(lon, lat);
    const d = Math.min(...origins.map(([ox, oy]) => Math.hypot(lon - ox, lat - oy)));
    out.push({ x, y, burns: r() < 0.72, t: IGNITE_FROM + Math.min(1, d / 1.1) * IGNITE_SPAN * 0.75 + r() * IGNITE_SPAN * 0.25, s: 3.4 + r() * 1.6 });
  }
  return out;
}

type Puff = { x0: number; y0: number; x1: number; y1: number; t0: number; r: number; wob: number };

function makePuffs(fields: FieldDot[]): Puff[] {
  const r = rng(7);
  const [dx, dy] = p(...CITIES.Delhi);
  const burning = fields.filter((f) => f.burns && f.y > p(0, 31.4)[1]); // southern & central fields feed the plume
  return Array.from({ length: 20 }, (_, i) => {
    const src = burning[Math.floor(r() * burning.length)];
    return {
      x0: src.x,
      y0: src.y,
      x1: dx - 30 + r() * 80,
      y1: dy - 40 + r() * 60,
      t0: 158 + i * 5.5,
      r: 34 + r() * 30,
      wob: r() * Math.PI * 2,
    };
  });
}

export function S1Problem() {
  const f = useCurrentFrame();
  const fields = useMemo(makeFields, []);
  const puffs = useMemo(() => makePuffs(fields), [fields]);
  const punjabPath = useMemo(() => ringPath(PUNJAB, p), []);
  const punjabLen = useMemo(() => ringLength(PUNJAB, p), []);
  const [dx, dy] = p(...CITIES.Delhi);

  const draw = ramp(f, 8, 62, 0, 1, easeInOut);
  const landFill = ramp(f, 40, 70);
  const neighbours = ramp(f, 20, 50);

  // AQI marker: 0 (Good) → 5.5 (Severe band centre)
  const aqi = ramp(f, 236, 300, 0, 5.5, easeInOut);
  const aqiIdx = Math.min(AQI.length - 1, Math.floor(aqi));
  const card = rise(f, 228, 18, 10);

  // wind arrow
  const [wx0, wy0] = p(75.55, 30.05);
  const [wx1, wy1] = [dx - 26, dy - 34];
  const wind = ramp(f, 186, 222);

  return (
    <SceneShell dur={S1_DUR}>

      <svg width={W} height={1080} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id="soft" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="22" />
          </filter>
          <mask id="mapmask" maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={1080}>
            <rect x={BOX.x + 10} y={BOX.y + 20} width={BOX.w - 20} height={BOX.h - 30} rx={30} fill="white" filter="url(#soft)" />
          </mask>
          <filter id="blur" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="13" />
          </filter>
          <radialGradient id="haze">
            <stop offset="0%" stopColor={C.smoke} stopOpacity="0.3" />
            <stop offset="100%" stopColor={C.smoke} stopOpacity="0" />
          </radialGradient>
        </defs>

        <g mask="url(#mapmask)">
          {/* neighbouring states: context only */}
          {NEIGHBOURS.map((n) =>
            STATES[n].map((ring, i) => (
              <path
                key={`${n}${i}`}
                d={ringPath(ring, p)}
                fill="none"
                stroke={C.line}
                strokeWidth={1.2}
                opacity={neighbours}
              />
            )),
          )}
          <text
            x={p(75.55, 29.15)[0]}
            y={p(75.55, 29.15)[1]}
            fontSize={13}
            fill={C.faint}
            letterSpacing="0.16em"
            opacity={neighbours * 0.9}
          >
            HARYANA
          </text>

          {/* Punjab */}
          <path d={punjabPath} fill={C.land} opacity={landFill} />
          <path
            d={punjabPath}
            fill="none"
            stroke={C.ink2}
            strokeWidth={1.6}
            strokeLinejoin="round"
            strokeDasharray={punjabLen}
            strokeDashoffset={punjabLen * (1 - draw)}
          />
          <text
            x={p(74.0, 32.15)[0]}
            y={p(74.0, 32.15)[1]}
            fontSize={14}
            fill={C.muted}
            letterSpacing="0.2em"
            fontWeight={600}
            opacity={ramp(f, 50, 70)}
          >
            PUNJAB
          </text>

          {/* fields */}
          {fields.map((d, i) => {
            const appear = ramp(f, 46 + (i % 40) * 0.9, 62 + (i % 40) * 0.9);
            const lit = d.burns ? ramp(f, d.t, d.t + 10) : 0;
            const halo = d.burns ? ramp(f, d.t, d.t + 24) : 0;
            const s = d.s + lit * 1.2;
            return (
              <g key={i} opacity={appear}>
                {halo > 0 && halo < 1 ? (
                  <circle cx={d.x} cy={d.y} r={3 + halo * 10} fill="none" stroke={C.riskFill} strokeWidth={1} opacity={(1 - halo) * 0.5} />
                ) : null}
                <rect
                  x={d.x - s / 2}
                  y={d.y - s / 2}
                  width={s}
                  height={s}
                  rx={1}
                  fill={lit > 0 ? mix(C.straw, C.riskFill, lit) : C.straw}
                />
              </g>
            );
          })}

          {/* smoke */}
          <g filter="url(#blur)">
            {puffs.map((s, i) => {
              const t = ramp(f, s.t0, s.t0 + 130, 0, 1, easeInOut);
              if (t <= 0) return null;
              const nx = -(s.y1 - s.y0);
              const ny = s.x1 - s.x0;
              const nl = Math.hypot(nx, ny) || 1;
              const w = Math.sin(t * Math.PI * 1.6 + s.wob) * 22 * (1 - t);
              const x = s.x0 + (s.x1 - s.x0) * t + (nx / nl) * w;
              const y = s.y0 + (s.y1 - s.y0) * t + (ny / nl) * w;
              const o = ramp(f, s.t0, s.t0 + 22) * (0.15 + 0.03 * t);
              return <circle key={i} cx={x} cy={y} r={s.r * (0.45 + t * 0.75)} fill={C.smoke} opacity={o} />;
            })}
          </g>
          <circle cx={dx} cy={dy - 10} r={40 + ramp(f, 230, 330) * 80} fill="url(#haze)" opacity={ramp(f, 228, 320) * 0.85} />

          {/* wind direction */}
          <g opacity={wind * (1 - ramp(f, 300, 330))}>
            <line
              x1={wx0}
              y1={wy0}
              x2={wx0 + (wx1 - wx0) * wind}
              y2={wy0 + (wy1 - wy0) * wind}
              stroke={C.ink2}
              strokeWidth={1.4}
              strokeDasharray="5 6"
            />
            <polygon
              points="0,-5 10,0 0,5"
              fill={C.ink2}
              transform={`translate(${wx0 + (wx1 - wx0) * wind},${wy0 + (wy1 - wy0) * wind}) rotate(${(Math.atan2(wy1 - wy0, wx1 - wx0) * 180) / Math.PI})`}
            />
          </g>
        </g>

        {/* cities */}
        {LABELLED.map((name, i) => {
          const [lon, lat] = CITIES[name];
          const [x, y] = p(lon, lat);
          const o = ramp(f, 58 + i * 5, 74 + i * 5);
          const right = name !== "Patiala";
          return (
            <g key={name} opacity={o}>
              <circle cx={x} cy={y} r={3.6} fill={C.ink} stroke={C.canvas} strokeWidth={2} />
              <text
                x={x + (right ? 9 : -9)}
                y={y + 5}
                textAnchor={right ? "start" : "end"}
                fontSize={15}
                fontWeight={500}
                fill={C.ink2}
                stroke={C.canvas}
                strokeWidth={4}
                paintOrder="stroke"
              >
                {name}
              </text>
            </g>
          );
        })}
        <g opacity={ramp(f, 84, 100)}>
          <circle cx={dx} cy={dy} r={6} fill={C.ink} stroke={C.canvas} strokeWidth={2.5} />
          <circle cx={dx} cy={dy} r={11} fill="none" stroke={C.ink} strokeWidth={1} opacity={0.35} />
          <text x={dx - 16} y={dy + 6} textAnchor="end" fontSize={18} fontWeight={600} fill={C.ink} stroke={C.canvas} strokeWidth={4} paintOrder="stroke">
            Delhi
          </text>
        </g>

      </svg>

      {/* Delhi air-quality card */}
      <div
        style={{
          position: "absolute",
          left: W - PAD - 232,
          top: dy - 262,
          width: 232,
          padding: "16px 16px 14px",
          background: C.canvas,
          border: `1px solid ${C.line}`,
          borderRadius: 10,
          boxShadow: "0 8px 24px rgb(20 20 30 / 0.06)",
          ...card,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontSize: 13, color: C.muted, fontWeight: 600, letterSpacing: "0.08em" }}>AIR QUALITY</span>
          <span style={{ fontFamily: MONO, fontSize: 12, color: C.faint }}>AQI</span>
        </div>
        <div style={{ fontSize: 22, fontWeight: 600, color: C.ink, marginTop: 6, letterSpacing: "-0.02em" }}>
          {AQI[aqiIdx].label}
        </div>
        <div style={{ position: "relative", marginTop: 12, display: "flex", gap: 2 }}>
          {AQI.map((a) => (
            <div key={a.label} style={{ flex: 1, height: 8, background: a.color, borderRadius: 1 }} />
          ))}
          <div
            style={{
              position: "absolute",
              top: -5,
              left: `calc(${(aqi / AQI.length) * 100}% - 1.5px)`,
              width: 3,
              height: 18,
              background: C.ink,
              borderRadius: 2,
              boxShadow: `0 0 0 2px ${C.canvas}`,
            }}
          />
        </div>
        {content.problemStat ? (
          <div style={{ marginTop: 12, borderTop: `1px solid ${C.line}`, paddingTop: 10 }}>
            <div style={{ fontSize: 20, fontWeight: 600, color: C.ink }}>{content.problemStat.value}</div>
            <div style={{ fontSize: 13, color: C.ink2 }}>{content.problemStat.label}</div>
            <div style={{ fontSize: 10.5, color: C.faint, marginTop: 4 }}>Source: {content.problemStat.source}</div>
          </div>
        ) : (
          <div style={{ fontSize: 13, color: C.muted, marginTop: 10, lineHeight: 1.35 }}>Smoke from the fields reaches the cities.</div>
        )}
      </div>

      <BottomBand f={f} />
    </SceneShell>
  );
}

/** Harvest-to-sowing squeeze, then the Air-track chips. */
function BottomBand({ f }: { f: number }) {
  const show = ramp(f, 54, 72) * (1 - ramp(f, 236, 252));
  const squeeze = ramp(f, 78, 150, 0, 1, easeInOut);
  const hEnd = 0.4 + 0.16 * squeeze;
  const sStart = 0.8 - 0.16 * squeeze;
  const width = W - 2 * PAD;
  const chips = ["Stubble burning", "AQI", "Pollution exposure"];

  return (
    <>
      <div style={{ position: "absolute", left: PAD, width, top: 908, opacity: show }}>
        <div style={{ position: "relative", height: 70 }}>
          <div
            style={{
              position: "absolute",
              left: `${hEnd * 100}%`,
              width: `${(sStart - hEnd) * 100}%`,
              top: 0,
              textAlign: "center",
              fontSize: 14,
              fontWeight: 600,
              color: C.ink,
              opacity: ramp(f, 96, 116),
              whiteSpace: "nowrap",
            }}
          >
            only weeks to clear the straw
          </div>
          <div
            style={{
              position: "absolute",
              left: `${hEnd * 100}%`,
              width: `${(sStart - hEnd) * 100}%`,
              top: 22,
              height: 8,
              borderLeft: `1.5px solid ${C.ink}`,
              borderRight: `1.5px solid ${C.ink}`,
              borderTop: `1.5px solid ${C.ink}`,
              opacity: ramp(f, 96, 116),
            }}
          />
          <div style={{ position: "absolute", top: 36, left: 0, right: 0, height: 30, background: C.sunken, borderRadius: 6 }} />
          <div
            style={{
              position: "absolute",
              top: 36,
              left: 0,
              width: `${hEnd * 100}%`,
              height: 30,
              background: C.straw,
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              paddingLeft: 12,
              fontSize: 14,
              fontWeight: 600,
              color: C.canvas,
            }}
          >
            Paddy harvest
          </div>
          <div
            style={{
              position: "absolute",
              top: 36,
              left: `${sStart * 100}%`,
              right: 0,
              height: 30,
              background: C.data1,
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              paddingRight: 12,
              fontSize: 14,
              fontWeight: 600,
              color: C.canvas,
            }}
          >
            Wheat sowing
          </div>
        </div>
      </div>

      <div style={{ position: "absolute", left: PAD, right: PAD, top: 924, display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ ...rise(f, 252, 14, 8), fontSize: 13, letterSpacing: "0.14em", color: C.muted, fontWeight: 600, marginRight: 4 }}>
          AIR TRACK
        </span>
        {chips.map((c, i) => (
          <div key={c} style={rise(f, 258 + i * 7, 14, 10)}>
            <Chip label={c} color={i === 0 ? C.riskFill : C.data1} />
          </div>
        ))}
      </div>
    </>
  );
}

function mix(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `rgb(${pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(",")})`;
}
