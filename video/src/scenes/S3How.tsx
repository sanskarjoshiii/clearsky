import { BellRing, CalendarClock, Check, Factory, Play, Satellite } from "lucide-react";
import type { ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { content } from "../content";
import { C, MONO, PAD, W } from "../theme";
import { easeInOut, pop, ramp, rise, rng } from "../lib/anim";
import { Chip, SceneShell } from "../components/ui";

export const S3_DUR = 360; // 12 s

const CARD_W = W - 2 * PAD;
const CARD_H = 232;
const TOPS = [148, 420, 692];

function Card({
  n,
  top,
  start,
  dimAt,
  title,
  tags,
  children,
}: {
  n: number;
  top: number;
  start: number;
  dimAt?: number;
  title: string;
  tags: ReactNode;
  children: ReactNode;
}) {
  const f = useCurrentFrame();
  const r = rise(f, start, 18, 18);
  const dim = dimAt ? 1 - 0.5 * ramp(f, dimAt, dimAt + 14) : 1;
  const active = dimAt ? 1 - ramp(f, dimAt, dimAt + 14) : 1;
  return (
    <div
      style={{
        position: "absolute",
        left: PAD,
        top,
        width: CARD_W,
        height: CARD_H,
        borderRadius: 14,
        background: C.canvas,
        border: `1px solid ${active > 0.5 && f >= start ? C.lineStrong : C.line}`,
        boxShadow: active > 0.5 ? "0 10px 30px rgb(20 20 30 / 0.06)" : "none",
        ...r,
        opacity: (r.opacity as number) * dim,
      }}
    >
      <div style={{ position: "absolute", left: 22, right: 22, top: 20, display: "flex", alignItems: "center", gap: 12 }}>
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: "50%",
            background: C.ink,
            color: C.canvas,
            fontFamily: MONO,
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {n}
        </div>
        <div style={{ fontSize: 21, fontWeight: 600, letterSpacing: "-0.018em", flex: 1 }}>{title}</div>
        <div style={{ display: "flex", gap: 8 }}>{tags}</div>
      </div>
      <div style={{ position: "absolute", left: 22, right: 22, top: 70, bottom: 20 }}>{children}</div>
    </div>
  );
}

/* ---------- 1 · the agent ---------- */

function AgentCard() {
  const f = useCurrentFrame();
  const msg = content.farmer.message;
  const typed = Math.floor(ramp(f, 40, 96, 0, msg.length, (t) => t));
  const bars = Array.from({ length: 34 }, (_, i) => 0.25 + 0.75 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.6)));
  const play = ramp(f, 24, 96, 0, 1, (t) => t);
  const rows: [string, string, number][] = [
    ["Name", content.farmer.name, 92],
    ["Village", content.farmer.village, 84],
    ["Acres", content.farmer.acres, 56],
    ["Harvest", content.farmer.harvest, 72],
  ];
  return (
    <div style={{ display: "flex", gap: 26, height: "100%" }}>
      <div style={{ width: 430 }}>
        <div
          style={{
            height: 54,
            borderRadius: 12,
            background: C.sunken,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "0 14px",
            ...rise(f, 20, 12, 8),
          }}
        >
          <div style={{ width: 30, height: 30, borderRadius: "50%", background: C.ink, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Play size={14} color={C.canvas} fill={C.canvas} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 3, flex: 1, height: 30 }}>
            {bars.map((b, i) => {
              const played = i / bars.length < play;
              const live = played && i / bars.length > play - 0.08 ? 1 + 0.25 * Math.sin(f * 0.9 + i) : 1;
              return <div key={i} style={{ flex: 1, height: `${b * 100 * Math.min(1.15, live)}%`, borderRadius: 2, background: played ? C.ink : C.lineStrong }} />;
            })}
          </div>
          <span style={{ fontFamily: MONO, fontSize: 13, color: C.muted }}>0:06</span>
        </div>
        <div style={{ marginTop: 14, fontSize: 17, lineHeight: 1.4, color: C.ink2, minHeight: 48, ...rise(f, 36, 10, 4) }}>
          “{msg.slice(0, typed)}
          {typed < msg.length && f >= 40 ? <span style={{ color: C.agent }}>▍</span> : "”"}
        </div>
        <div style={{ marginTop: 6, fontSize: 13.5, color: C.muted, ...rise(f, 70, 12, 4) }}>Hindi · Punjabi · Hinglish · voice notes</div>
      </div>
      <div style={{ flex: 1, borderLeft: `1px solid ${C.line}`, paddingLeft: 22, display: "flex", flexDirection: "column", justifyContent: "space-between", paddingBottom: 4 }}>
        {rows.map(([k, v, at]) => {
          const on = pop(f, at);
          return (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 10, height: 30 }}>
              <span style={{ width: 72, fontSize: 14, color: C.muted }}>{k}</span>
              <span style={{ flex: 1, fontSize: 17, fontWeight: 600, color: C.ink, opacity: on }}>{v}</span>
              <div
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: on > 0.05 ? C.agent : C.sunken,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transform: `scale(${0.7 + 0.3 * on})`,
                }}
              >
                {on > 0.05 ? <Check size={13} strokeWidth={3} color={C.canvas} /> : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- 2 · the matcher ---------- */

function MatchCard() {
  const f = useCurrentFrame();
  const MW = 380;
  const MH = 140;
  const field: [number, number] = [150, 74];
  const balers: { at: [number, number]; free: boolean }[] = [
    { at: [228, 44], free: true },
    { at: [60, 30], free: false },
    { at: [300, 112], free: true },
    { at: [88, 118], free: false },
    { at: [348, 32], free: true },
  ];
  const nearest = balers[0].at;
  const plant: [number, number] = [336, 82];
  const ring = ramp(f, 136, 172, 0, 1, easeInOut);
  const pick = ramp(f, 170, 186);
  const buyer = ramp(f, 186, 202);
  const r = rng(3);
  const grid = Array.from({ length: 70 }, () => [r() * MW, r() * MH] as const);

  return (
    <div style={{ display: "flex", gap: 26, height: "100%" }}>
      <div style={{ position: "relative", width: MW, height: MH, borderRadius: 10, background: C.sunken, overflow: "hidden", ...rise(f, 128, 12, 6) }}>
        <svg width={MW} height={MH} style={{ position: "absolute", inset: 0 }}>
          {grid.map(([x, y], i) => (
            <rect key={i} x={x} y={y} width={3} height={3} rx={0.6} fill={C.straw} opacity={0.45} />
          ))}
          <circle cx={field[0]} cy={field[1]} r={ring * 104} fill={C.ink} fillOpacity={0.035} stroke={C.ink} strokeOpacity={0.25} strokeDasharray="4 5" />
          <line
            x1={field[0]}
            y1={field[1]}
            x2={field[0] + (nearest[0] - field[0]) * pick}
            y2={field[1] + (nearest[1] - field[1]) * pick}
            stroke={C.ink}
            strokeWidth={2}
          />
          <line
            x1={field[0]}
            y1={field[1]}
            x2={field[0] + (plant[0] - field[0]) * buyer}
            y2={field[1] + (plant[1] - field[1]) * buyer}
            stroke={C.data2}
            strokeWidth={2}
            strokeDasharray="5 5"
          />
          {balers.map((b, i) => {
            const isPick = i === 0 && pick > 0.5;
            return (
              <g key={i} opacity={ramp(f, 140 + i * 3, 150 + i * 3)}>
                <circle cx={b.at[0]} cy={b.at[1]} r={isPick ? 9 : 6} fill={b.free ? C.ink : C.canvas} stroke={b.free ? C.canvas : C.faint} strokeWidth={2} />
              </g>
            );
          })}
          <rect x={field[0] - 8} y={field[1] - 8} width={16} height={16} rx={3} fill={C.straw} stroke={C.canvas} strokeWidth={2.5} />
          <text x={(field[0] + nearest[0]) / 2 - 18} y={(field[1] + nearest[1]) / 2 - 8} fontSize={13} fontWeight={600} fill={C.ink} opacity={pick} stroke={C.sunken} strokeWidth={4} paintOrder="stroke">
            6 km
          </text>
        </svg>
        <div style={{ position: "absolute", left: plant[0] - 15, top: plant[1] - 15, width: 30, height: 30, borderRadius: 8, background: C.canvas, border: `1px solid ${C.line}`, display: "flex", alignItems: "center", justifyContent: "center", opacity: buyer }}>
          <Factory size={17} color={C.data1} strokeWidth={1.8} />
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between", paddingBottom: 2 }}>
        <Row k="Baler" v="Nearest free one · 6 km" o={pick} />
        <Row k="Buyer" v="Pellet plant that needs straw" o={buyer} />
        <div style={{ ...rise(f, 206, 12, 6) }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 8, background: C.ink, color: C.canvas, fontSize: 15, fontWeight: 600 }}>
            <Check size={16} strokeWidth={2.6} /> Booked · capacity reserved
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v, o }: { k: string; v: string; o: number }) {
  return (
    <div style={{ opacity: o, transform: `translateY(${(1 - o) * 6}px)` }}>
      <div style={{ fontSize: 13, color: C.muted, letterSpacing: "0.06em", fontWeight: 600 }}>{k.toUpperCase()}</div>
      <div style={{ fontSize: 17, fontWeight: 600, color: C.ink, marginTop: 2 }}>{v}</div>
    </div>
  );
}

/* ---------- 3 · risk: track & warn ---------- */

function RiskCard() {
  const f = useCurrentFrame();
  const hist = ramp(f, 246, 286, 0, 0.82, easeInOut);
  const days = Math.round(ramp(f, 250, 296, 9, 3, (t) => t));
  const score = ramp(f, 262, 312, 0, 1, easeInOut);
  const level = score < 0.4 ? { c: C.okFill, t: "Green" } : score < 0.66 ? { c: C.warnFill, t: "Amber" } : { c: C.riskFill, t: "Red" };
  const alert = rise(f, 312, 14, 10);
  const booked = ramp(f, 334, 346);

  const GX = 64;
  const GY = 72;
  const GR = 56;
  const arc = (a0: number, a1: number) => {
    const p = (a: number) => [GX + GR * Math.cos(Math.PI * (1 - a)), GY - GR * Math.sin(Math.PI * (1 - a))];
    const [x0, y0] = p(a0);
    const [x1, y1] = p(a1);
    return `M${x0},${y0} A${GR},${GR} 0 0 1 ${x1},${y1}`;
  };
  const na = Math.PI * (1 - score);

  return (
    <div style={{ display: "flex", gap: 22, height: "100%", alignItems: "stretch" }}>
      <div style={{ width: 268, display: "flex", flexDirection: "column", justifyContent: "center", gap: 18, ...rise(f, 240, 12, 6) }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14.5, color: C.ink2, fontWeight: 500 }}>
            <Satellite size={17} strokeWidth={1.8} /> NASA fire history
          </div>
          <div style={{ marginTop: 8, height: 8, borderRadius: 4, background: C.sunken }}>
            <div style={{ width: `${hist * 100}%`, height: "100%", borderRadius: 4, background: C.ink2 }} />
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14.5, color: C.ink2, fontWeight: 500 }}>
          <CalendarClock size={17} strokeWidth={1.8} /> Days to sowing
          <span style={{ marginLeft: "auto", fontFamily: MONO, fontSize: 20, color: C.ink, fontWeight: 500 }}>{days}</span>
        </div>
      </div>

      <div style={{ width: 128, position: "relative", ...rise(f, 256, 12, 6) }}>
        <svg width={128} height={110} style={{ position: "absolute", top: 8 }}>
          <path d={arc(0, 0.4)} stroke={C.okFill} strokeWidth={10} fill="none" />
          <path d={arc(0.415, 0.65)} stroke={C.warnFill} strokeWidth={10} fill="none" />
          <path d={arc(0.665, 1)} stroke={C.riskFill} strokeWidth={10} fill="none" />
          <line x1={GX} y1={GY} x2={GX + (GR - 16) * Math.cos(na)} y2={GY - (GR - 16) * Math.sin(na)} stroke={C.ink} strokeWidth={3} strokeLinecap="round" />
          <circle cx={GX} cy={GY} r={5} fill={C.ink} />
        </svg>
        <div style={{ position: "absolute", top: 94, left: 0, right: 0, textAlign: "center" }}>
          <div style={{ fontSize: 12, color: C.muted, fontWeight: 600, letterSpacing: "0.08em" }}>BURN RISK</div>
          <div style={{ fontSize: 17, fontWeight: 700, color: level.c }}>{level.t}</div>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
        <div style={{ borderRadius: 12, background: C.agentSoft, border: `1px solid ${C.agentLine}`, padding: "12px 14px", ...alert }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.agent, fontWeight: 600, fontSize: 15 }}>
            <BellRing size={16} strokeWidth={2.2} /> Village alert on WhatsApp
          </div>
          <div style={{ fontSize: 14.5, color: C.ink2, marginTop: 4 }}>Pickup offered before the fire</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 15, color: C.ink2, opacity: ramp(f, 326, 338) }}>
          <span style={{ width: 14, height: 14, borderRadius: "50%", background: booked > 0.5 ? C.okFill : C.riskFill, boxShadow: `0 0 0 4px ${booked > 0.5 ? C.okSoft : C.riskSoft}` }} />
          {booked > 0.5 ? "Booked: red turns green" : "Field at risk"}
        </div>
      </div>
    </div>
  );
}

export function S3How() {
  return (
    <SceneShell dur={S3_DUR}>
      <Card n={1} top={TOPS[0]} start={14} dimAt={124} title="Understands the farmer" tags={<Chip label="AI agent" color={C.agent} size={14} />}>
        <AgentCard />
      </Card>
      <Card n={2} top={TOPS[1]} start={122} dimAt={234} title="Books the nearest free baler" tags={<Chip label="Matcher" color={C.ink} size={14} />}>
        <MatchCard />
      </Card>
      <Card
        n={3}
        top={TOPS[2]}
        start={232}
        title="Tracks fields about to burn"
        tags={
          <>
            <Chip label="Track" color={C.riskFill} size={14} />
            <Chip label="Warn" color={C.agent} size={14} />
          </>
        }
      >
        <RiskCard />
      </Card>
    </SceneShell>
  );
}
