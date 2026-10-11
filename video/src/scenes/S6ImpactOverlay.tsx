import { Check, CloudFog, Factory, Wind } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { C } from "../theme";
import { along, easeInOut, pop, ramp, rng } from "../lib/anim";

/**
 * Transparent 10 s overlay (1920×1080, no background) for the line:
 * "Our system reduces stubble burning by sending straw to industries instead of burning it in the fields.
 *  This means less smoke, cleaner air, and fewer people exposed to harmful pollution."
 * Beats: 0–4 s field → straw → industry · 4–6.5 s less smoke, cleaner air · 6.5–10 s fewer people exposed.
 * Everything sits on white cards with soft shadows so it reads on top of any footage.
 */
export const S6_DUR = 300;

const CARD: CSSProperties = {
  position: "absolute",
  background: C.canvas,
  borderRadius: 24,
  boxShadow: "0 24px 60px rgb(10 25 20 / 0.28), 0 2px 6px rgb(10 25 20 / 0.12)",
};

const FIELD = { x: 240, y: 250, w: 460, h: 320 };
const PLANT = { x: 1220, y: 250, w: 460, h: 320 };
const ARC: [number, number][] = [];
for (let i = 0; i <= 40; i++) {
  const t = i / 40;
  const x0 = FIELD.x + FIELD.w - 40;
  const x1 = PLANT.x + 40;
  const y = 410 - Math.sin(Math.PI * t) * 150;
  ARC.push([x0 + (x1 - x0) * t, y]);
}
const arcPath = ARC.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");
const arcLen = ARC.reduce((s, p, i) => (i ? s + Math.hypot(p[0] - ARC[i - 1][0], p[1] - ARC[i - 1][1]) : 0), 0);

function Card({ box, start, children }: { box: { x: number; y: number; w: number; h: number }; start: number; children: ReactNode }) {
  const f = useCurrentFrame();
  const s = pop(f, start);
  return (
    <div style={{ ...CARD, left: box.x, top: box.y, width: box.w, height: box.h, opacity: Math.min(1, s * 1.4), transform: `scale(${0.85 + 0.15 * s})` }}>
      {children}
    </div>
  );
}

function Flame({ x, y, s, f }: { x: number; y: number; s: number; f: number }) {
  if (s <= 0.01) return null;
  const flick = 1 + 0.08 * Math.sin(f * 0.9 + x) + 0.05 * Math.sin(f * 2.1 + y);
  return (
    <g transform={`translate(${x} ${y}) scale(${s * flick})`}>
      <path d="M0,-34 C14,-18 20,-6 18,6 C16,20 6,26 0,26 C-6,26 -16,20 -18,6 C-20,-8 -8,-14 -4,-24 C-2,-14 4,-12 6,-8 C8,-18 4,-26 0,-34Z" fill={C.riskFill} />
      <path d="M0,-6 C6,2 8,8 7,13 C6,19 2,22 0,22 C-3,22 -7,19 -7,13 C-7,7 -3,4 0,-6Z" fill={C.warnFill} />
    </g>
  );
}

function Bale({ x, y, s = 1 }: { x: number; y: number; s?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <rect x={-22} y={-14} width={44} height={28} rx={6} fill={C.straw} />
      <rect x={-22} y={-14} width={44} height={28} rx={6} fill="none" stroke="#a88a4a" strokeWidth={2} />
      <line x1={-8} y1={-14} x2={-8} y2={14} stroke="#a88a4a" strokeWidth={2} />
      <line x1={8} y1={-14} x2={8} y2={14} stroke="#a88a4a" strokeWidth={2} />
    </g>
  );
}

/** The field card: straw rows, fires that die out, bales that appear where the fire was. */
function FieldCard() {
  const f = useCurrentFrame();
  const fire = ramp(f, 8, 22) * (1 - ramp(f, 46, 66, 0, 1, easeInOut));
  const sweep = ramp(f, 46, 74, 0, 1, easeInOut); // a baler pass clears the rows
  const spots: [number, number][] = [[130, 170], [235, 150], [335, 175]];
  return (
    <Card box={FIELD} start={0}>
      <svg width={FIELD.w} height={FIELD.h} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <clipPath id="fieldclip"><rect x={24} y={70} width={FIELD.w - 48} height={FIELD.h - 96} rx={16} /></clipPath>
        </defs>
        <g clipPath="url(#fieldclip)">
          <rect x={24} y={70} width={FIELD.w - 48} height={FIELD.h - 96} fill={C.wheat} />
          {Array.from({ length: 11 }, (_, i) => (
            <line key={i} x1={24} y1={86 + i * 21} x2={FIELD.w - 24} y2={70 + i * 21} stroke={C.straw} strokeWidth={5} strokeLinecap="round" opacity={0.85} />
          ))}
          {/* scorched patch while burning */}
          <ellipse cx={230} cy={170} rx={150 * fire} ry={60 * fire} fill="#3a2a22" opacity={0.18 * fire} />
          {/* baler pass: a clean green band sweeping across */}
          <rect x={24} y={70} width={(FIELD.w - 48) * sweep} height={FIELD.h - 96} fill={C.okSoft} opacity={0.55} />
        </g>
        {spots.map(([x, y], i) => <Flame key={i} x={x} y={y} s={fire} f={f} />)}
        {spots.map(([x, y], i) => {
          const s = pop(f, 60 + i * 5);
          const leaves = ramp(f, 80 + i * 14, 92 + i * 14);
          return s > 0.02 ? <g key={`b${i}`} opacity={1 - leaves}><Bale x={x} y={y + 12} s={s} /></g> : null;
        })}
      </svg>
      <div style={{ position: "absolute", left: 28, top: 20, display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 24, fontWeight: 700, color: C.ink, letterSpacing: "-0.02em" }}>Paddy field</span>
        <span
          style={{
            fontSize: 15,
            fontWeight: 600,
            padding: "4px 10px",
            borderRadius: 999,
            color: f < 52 ? C.risk : C.ok,
            background: f < 52 ? C.riskSoft : C.okSoft,
          }}
        >
          {f < 52 ? "burning" : "straw baled"}
        </span>
      </div>
    </Card>
  );
}

/** Industry card: receives the bales and counts them in. */
function PlantCard() {
  const f = useCurrentFrame();
  const got = [0, 1, 2].map((i) => ramp(f, 104 + i * 14, 110 + i * 14));
  return (
    <Card box={PLANT} start={6}>
      <div style={{ position: "absolute", left: 28, top: 20, fontSize: 24, fontWeight: 700, color: C.ink, letterSpacing: "-0.02em" }}>Industry</div>
      <div style={{ position: "absolute", left: 28, top: 54, fontSize: 17, color: C.muted }}>straw used as fuel</div>
      <div
        style={{
          position: "absolute",
          left: 28,
          top: 104,
          width: 150,
          height: 150,
          borderRadius: 28,
          background: C.straw2Soft,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${1 + 0.06 * Math.sin(Math.PI * ramp(f, 104, 146))})`,
        }}
      >
        <Factory size={86} strokeWidth={1.6} color={C.data1} />
      </div>
      <div style={{ position: "absolute", left: 200, top: 116, display: "flex", flexDirection: "column", gap: 14 }}>
        {got.map((g, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, opacity: 0.25 + 0.75 * g }}>
            <svg width={44} height={28}><Bale x={22} y={14} /></svg>
            <span
              style={{
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: g > 0.5 ? C.okFill : C.line,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transform: `scale(${0.6 + 0.4 * g})`,
              }}
            >
              {g > 0.5 ? <Check size={16} strokeWidth={3} color="#fff" /> : null}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Dashed route from field to industry, with bales travelling along it. */
function Route() {
  const f = useCurrentFrame();
  const draw = ramp(f, 62, 84, 0, 1, easeInOut);
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
      <path d={arcPath} fill="none" stroke="#ffffff" strokeWidth={9} strokeLinecap="round" opacity={0.9 * draw}
        strokeDasharray={arcLen} strokeDashoffset={arcLen * (1 - draw)} />
      <path d={arcPath} fill="none" stroke={C.data2} strokeWidth={4} strokeLinecap="round"
        strokeDasharray="2 14" strokeDashoffset={-f * 1.2} opacity={draw}
        style={{ clipPath: "none" }} />
      {[0, 1, 2].map((i) => {
        const t = ramp(f, 80 + i * 14, 108 + i * 14, 0, 1, easeInOut);
        if (t <= 0 || t >= 1) return null;
        const [x, y] = along(ARC, t);
        return (
          <g key={i} style={{ filter: "drop-shadow(0 6px 10px rgb(10 25 20 / 0.35))" }}>
            <circle cx={x} cy={y} r={30} fill="#fff" />
            <Bale x={x} y={y} s={0.9} />
          </g>
        );
      })}
    </svg>
  );
}

/** Grey smoke above the field while it burns; it clears once the straw is baled. */
function Smoke() {
  const f = useCurrentFrame();
  const r = rng(11);
  const puffs = Array.from({ length: 14 }, (_, i) => ({ x: 380 + r() * 260, d: r() * 40, s: 38 + r() * 36, k: i }));
  const on = ramp(f, 10, 40) * (1 - ramp(f, 120, 168, 0, 1, easeInOut));
  if (on <= 0.01) return null;
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <defs><filter id="sm" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14" /></filter></defs>
      <g filter="url(#sm)">
        {puffs.map((p) => {
          const rise = ((f * 1.3 + p.d * 6 + p.k * 17) % 150) / 150;
          return <circle key={p.k} cx={p.x + Math.sin(rise * 4 + p.k) * 16} cy={250 - rise * 190} r={p.s * (0.7 + rise * 0.6)} fill="#5f6066" opacity={on * 0.42 * (1 - rise * 0.7)} />;
        })}
      </g>
    </svg>
  );
}

function Pill({ x, start, icon, title, sub, children }: { x: number; start: number; icon: ReactNode; title: string; sub: string; children?: ReactNode }) {
  const f = useCurrentFrame();
  const s = pop(f, start);
  return (
    <div
      style={{
        ...CARD,
        left: x,
        top: 640,
        width: 460,
        height: 200,
        borderRadius: 22,
        opacity: Math.min(1, s * 1.4),
        transform: `translateY(${(1 - s) * 30}px)`,
        padding: 26,
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {icon}
        <div>
          <div style={{ fontSize: 30, fontWeight: 700, color: C.ink, letterSpacing: "-0.02em", lineHeight: 1.1 }}>{title}</div>
          <div style={{ fontSize: 17, color: C.muted, marginTop: 4 }}>{sub}</div>
        </div>
      </div>
      {children}
    </div>
  );
}

function IconWell({ children, bg }: { children: ReactNode; bg: string }) {
  return <div style={{ width: 64, height: 64, borderRadius: 18, background: bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{children}</div>;
}

/** People under grey haze; the haze lifts and each one turns healthy. */
function People() {
  const f = useCurrentFrame();
  const clear = ramp(f, 214, 262, 0, 1, easeInOut);
  return (
    <div style={{ position: "relative", marginTop: 22, height: 72 }}>
      <svg width={408} height={72}>
        {Array.from({ length: 8 }, (_, i) => {
          const k = ramp(f, 214 + i * 5, 232 + i * 5);
          const col = k > 0.5 ? C.ok : "#8a8b90";
          const x = 24 + i * 51;
          return (
            <g key={i} transform={`translate(${x} 0)`}>
              <circle cx={0} cy={36} r={22 * k} fill={C.okSoft} />
              <circle cx={0} cy={22} r={9} fill={col} />
              <path d="M-15,58 C-15,42 -8,35 0,35 C8,35 15,42 15,58Z" fill={col} />
            </g>
          );
        })}
      </svg>
      <div style={{ position: "absolute", inset: "-6px -4px", borderRadius: 14, background: "rgb(110 110 118 / 0.55)", filter: "blur(6px)", opacity: 1 - clear }} />
    </div>
  );
}

export function S6ImpactOverlay() {
  const f = useCurrentFrame();
  const airFlow = (f % 60) / 60;
  return (
    <div style={{ position: "absolute", inset: 0, fontFamily: "inherit" }}>
      <Smoke />
      <Route />
      <FieldCard />
      <PlantCard />

      <Pill x={240} start={132} icon={<IconWell bg={C.sunken}><CloudFog size={36} strokeWidth={1.8} color={C.ink2} /></IconWell>} title="Less smoke" sub="no fire in the field">
        <div style={{ marginTop: 26, height: 12, borderRadius: 6, background: C.sunken, overflow: "hidden" }}>
          <div style={{ width: `${100 - 82 * ramp(f, 140, 190, 0, 1, easeInOut)}%`, height: "100%", borderRadius: 6, background: "#7d7e84" }} />
        </div>
      </Pill>
      <Pill x={730} start={165} icon={<IconWell bg={C.straw2Soft}><Wind size={36} strokeWidth={1.8} color={C.data1} /></IconWell>} title="Cleaner air" sub="for the whole region">
        <svg width={408} height={40} style={{ marginTop: 18 }}>
          {[0, 1, 2].map((i) => (
            <path
              key={i}
              d={`M0,${10 + i * 11} C100,${2 + i * 11} 200,${18 + i * 11} 408,${8 + i * 11}`}
              fill="none"
              stroke={C.data2}
              strokeWidth={3}
              strokeLinecap="round"
              strokeDasharray="60 300"
              strokeDashoffset={-((airFlow + i * 0.3) % 1) * 360}
              opacity={ramp(f, 172, 186)}
            />
          ))}
        </svg>
      </Pill>
      <Pill x={1220} start={200} icon={<IconWell bg={C.okSoft}><Check size={36} strokeWidth={2.4} color={C.ok} /></IconWell>} title="Fewer people exposed" sub="to harmful pollution">
        <People />
      </Pill>
    </div>
  );
}
