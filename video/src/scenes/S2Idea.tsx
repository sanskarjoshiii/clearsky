import { Factory, IndianRupee, MessageCircle, Tractor, Wheat } from "lucide-react";
import type { ComponentType } from "react";
import { useCurrentFrame } from "remotion";
import { C, W } from "../theme";
import { along, easeInOut, pop, ramp, rise } from "../lib/anim";
import { Chip, IconDisc, Logo, SceneShell } from "../components/ui";

export const S2_DUR = 270; // 9 s

type Pt = [number, number];
const HUB: Pt = [480, 528];
const NODES: { id: string; at: Pt; title: string; sub: string; Icon: ComponentType<{ size?: number; strokeWidth?: number; color?: string }> }[] = [
  { id: "farmer", at: [190, 330], title: "Farmer", sub: "Straw to clear before sowing", Icon: Wheat },
  { id: "baler", at: [770, 330], title: "Baler", sub: "Machine idle, needs work", Icon: Tractor },
  { id: "industry", at: [480, 748], title: "Industry", sub: "Needs straw as fuel", Icon: Factory },
];
const R = 62;

function toward(a: Pt, b: Pt, gap: number): Pt {
  const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
  return [a[0] + ((b[0] - a[0]) / d) * gap, a[1] + ((b[1] - a[1]) / d) * gap];
}

export function S2Idea() {
  const f = useCurrentFrame();
  const [farmer, baler, industry] = NODES.map((n) => n.at);

  // act 1: no link (dashed stubs that stop short)
  const stubs = ramp(f, 58, 96, 0, 1, easeInOut) * (1 - ramp(f, 112, 126));
  const pairs: [Pt, Pt][] = [
    [farmer, baler],
    [baler, industry],
    [industry, farmer],
  ];

  // act 2: clearsky hub + spokes
  const hub = pop(f, 116);
  const spoke = ramp(f, 128, 160, 0, 1, easeInOut);

  // act 3: three flows through the hub
  const flows = [
    { from: farmer, to: baler, start: 156, dur: 40, color: C.agent, label: "Pickup request", kind: "dot" as const },
    { from: farmer, to: industry, start: 178, dur: 46, color: C.data2, label: "Straw", kind: "bale" as const },
    { from: industry, to: farmer, start: 200, dur: 46, color: C.ink, label: "Payment", kind: "coin" as const },
  ];

  return (
    <SceneShell dur={S2_DUR}>

      <svg width={W} height={1080} style={{ position: "absolute", inset: 0 }}>
        {pairs.map(([a, b], i) => {
          const s = toward(a, b, R + 10);
          const e = toward(b, a, R + 10);
          const len = Math.hypot(e[0] - s[0], e[1] - s[1]);
          const reach = 0.36 * stubs;
          return (
            <g key={i} stroke={C.lineStrong} strokeWidth={2} strokeDasharray="6 7" strokeLinecap="round" opacity={reach > 0.01 ? 1 : 0}>
              <line x1={s[0]} y1={s[1]} x2={s[0] + ((e[0] - s[0]) * reach * len) / len} y2={s[1] + ((e[1] - s[1]) * reach * len) / len} />
              <line x1={e[0]} y1={e[1]} x2={e[0] + ((s[0] - e[0]) * reach * len) / len} y2={e[1] + ((s[1] - e[1]) * reach * len) / len} />
            </g>
          );
        })}

        {NODES.map((n) => {
          const s = toward(HUB, n.at, 58);
          const e = toward(n.at, HUB, R + 8);
          return (
            <line
              key={n.id}
              x1={s[0]}
              y1={s[1]}
              x2={s[0] + (e[0] - s[0]) * spoke}
              y2={s[1] + (e[1] - s[1]) * spoke}
              stroke={C.ink2}
              strokeWidth={2}
              strokeLinecap="round"
              opacity={spoke > 0 ? 1 : 0}
            />
          );
        })}
        {f >= 116 ? (
          <circle cx={HUB[0]} cy={HUB[1]} r={52 + ramp(f, 118, 150) * 34} fill="none" stroke={C.ink} strokeWidth={1} opacity={(1 - ramp(f, 118, 150)) * 0.4} />
        ) : null}
      </svg>


      {NODES.map((n, i) => {
        const s = pop(f, 16 + i * 9);
        return (
          <div key={n.id}>
            <IconDisc
              size={R * 2}
              style={{
                position: "absolute",
                left: n.at[0] - R,
                top: n.at[1] - R,
                transform: `scale(${0.6 + 0.4 * s})`,
                opacity: s,
              }}
            >
              <n.Icon size={50} strokeWidth={1.5} color={C.ink} />
            </IconDisc>
            <div
              style={{
                position: "absolute",
                left: n.at[0] - 140,
                width: 280,
                top: n.at[1] + R + 14,
                textAlign: "center",
                ...rise(f, 26 + i * 9, 14, 8),
              }}
            >
              <div style={{ fontSize: 22, fontWeight: 600, color: C.ink, letterSpacing: "-0.018em" }}>{n.title}</div>
              <div style={{ fontSize: 15, color: C.muted, marginTop: 3 }}>{n.sub}</div>
            </div>
          </div>
        );
      })}

      {/* flows */}
      {flows.map((fl, i) => {
        const items = fl.kind === "bale" ? 3 : 1;
        return Array.from({ length: items }, (_, k) => {
          const t = ramp(f, fl.start + k * 9, fl.start + k * 9 + fl.dur, 0, 1, easeInOut);
          if (t <= 0 || t >= 1) return null;
          const [x, y] = along([toward(fl.from, HUB, R + 6), HUB, toward(fl.to, HUB, R + 6)], t);
          const o = Math.min(ramp(t, 0, 0.08), 1 - ramp(t, 0.92, 1));
          return <Token key={`${i}-${k}`} kind={fl.kind} x={x} y={y} color={fl.color} opacity={o} />;
        });
      })}

      {/* hub */}
      <div
        style={{
          position: "absolute",
          left: HUB[0] - 52,
          top: HUB[1] - 52,
          width: 104,
          height: 104,
          borderRadius: "50%",
          background: C.canvas,
          boxShadow: `0 0 0 1px ${C.line}, 0 10px 30px rgb(20 20 30 / 0.08)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${0.5 + 0.5 * hub})`,
          opacity: hub,
        }}
      >
        <Logo size={84} />
      </div>

      {/* WhatsApp tag on the farmer */}
      <div style={{ position: "absolute", left: farmer[0] - 96, top: farmer[1] - R - 52, ...rise(f, 150, 14, 8) }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "7px 12px",
            borderRadius: 999,
            background: C.agentSoft,
            border: `1px solid ${C.agentLine}`,
            color: C.agent,
            fontSize: 15,
            fontWeight: 600,
          }}
        >
          <MessageCircle size={16} strokeWidth={2.2} /> Only needs WhatsApp
        </div>
      </div>

      <div style={{ position: "absolute", left: 0, right: 0, top: 920, display: "flex", justifyContent: "center", gap: 12 }}>
        {flows.map((fl) => (
          <div key={fl.label} style={rise(f, fl.start, 14, 8)}>
            <Chip label={fl.label} color={fl.color} size={15} />
          </div>
        ))}
      </div>
    </SceneShell>
  );
}

function Token({ kind, x, y, color, opacity }: { kind: "dot" | "bale" | "coin"; x: number; y: number; color: string; opacity: number }) {
  if (kind === "bale")
    return (
      <div
        style={{
          position: "absolute",
          left: x - 15,
          top: y - 10,
          width: 30,
          height: 20,
          borderRadius: 4,
          background: color,
          opacity,
          boxShadow: `inset 0 -5px 0 rgb(0 0 0 / 0.08), 0 0 0 3px ${C.canvas}`,
        }}
      />
    );
  if (kind === "coin")
    return (
      <div
        style={{
          position: "absolute",
          left: x - 16,
          top: y - 16,
          width: 32,
          height: 32,
          borderRadius: "50%",
          background: color,
          color: C.canvas,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity,
          boxShadow: `0 0 0 3px ${C.canvas}`,
        }}
      >
        <IndianRupee size={17} strokeWidth={2.4} />
      </div>
    );
  return (
    <div
      style={{
        position: "absolute",
        left: x - 10,
        top: y - 10,
        width: 20,
        height: 20,
        borderRadius: "50%",
        background: color,
        opacity,
        boxShadow: `0 0 0 4px ${C.agentSoft}`,
      }}
    />
  );
}
