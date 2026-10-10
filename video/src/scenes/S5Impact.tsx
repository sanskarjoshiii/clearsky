import { CheckCircle2, Clock, Factory, Flame, IndianRupee, MessageCircle, PhoneCall } from "lucide-react";
import type { ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { C, PAD, W } from "../theme";
import { pop, ramp, rise } from "../lib/anim";
import { Logo, SceneShell } from "../components/ui";

export const S5_DUR = 180; // 6 s

const COL_W = (W - 2 * PAD - 24) / 2;
const STEP_H = 160;
const TOP = 268;

function Step({
  x,
  i,
  start,
  icon,
  title,
  sub,
  tone,
}: {
  x: number;
  i: number;
  start: number;
  icon: ReactNode;
  title: string;
  sub: string;
  tone: { bg: string; fg: string; line: string };
}) {
  const f = useCurrentFrame();
  const s = pop(f, start);
  const y = TOP + i * (STEP_H + 18);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: COL_W,
        height: STEP_H,
        borderRadius: 14,
        border: `1px solid ${tone.line}`,
        background: C.canvas,
        padding: 22,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        opacity: s,
        transform: `translateY(${(1 - s) * 16}px)`,
      }}
    >
      <div style={{ width: 52, height: 52, borderRadius: 12, background: tone.bg, color: tone.fg, display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 600, color: C.ink, letterSpacing: "-0.018em" }}>{title}</div>
        <div style={{ fontSize: 15, color: C.muted, marginTop: 3 }}>{sub}</div>
      </div>
    </div>
  );
}

export function S5Impact() {
  const f = useCurrentFrame();
  const L = PAD;
  const R = PAD + COL_W + 24;
  const beforeDim = 1 - 0.45 * ramp(f, 78, 92);
  const neutral = { bg: C.sunken, fg: C.ink2, line: C.line };
  const flicker = 1 + 0.08 * Math.sin(f * 0.9) + 0.05 * Math.sin(f * 2.3);

  return (
    <SceneShell dur={S5_DUR}>

      {/* column heads */}
      <div style={{ position: "absolute", left: L, top: 226, fontSize: 14, fontWeight: 600, letterSpacing: "0.14em", color: C.muted, ...rise(f, 4, 12, 6) }}>
        BEFORE
      </div>
      <div style={{ position: "absolute", left: R, top: 222, display: "flex", alignItems: "center", gap: 8, ...rise(f, 76, 12, 6) }}>
        <Logo size={22} />
        <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: "0.14em", color: C.ink }}>WITH CLEARSKY</span>
      </div>

      <div style={{ position: "absolute", inset: 0, opacity: beforeDim }}>
        <Step x={L} i={0} start={8} icon={<PhoneCall size={26} strokeWidth={1.8} />} title="Calls around" sub="No baler free, no answer" tone={neutral} />
        <Step
          x={L}
          i={1}
          start={30}
          icon={<Clock size={26} strokeWidth={1.8} style={{ transform: `rotate(${f * 9}deg)` }} />}
          title="Waits"
          sub="The sowing date closes in"
          tone={neutral}
        />
        <Step
          x={L}
          i={2}
          start={52}
          icon={<Flame size={28} strokeWidth={1.9} style={{ transform: `scale(${flicker})` }} />}
          title="Burns the field"
          sub="Smoke over the cities"
          tone={{ bg: C.riskSoft, fg: C.riskFill, line: C.riskLine }}
        />
      </div>

      <Step x={R} i={0} start={84} icon={<MessageCircle size={26} strokeWidth={1.9} />} title="One WhatsApp message" sub="Voice or text, in Hindi" tone={{ bg: C.agentSoft, fg: C.agent, line: C.agentLine }} />
      <Step x={R} i={1} start={106} icon={<CheckCircle2 size={26} strokeWidth={1.9} />} title="Pickup confirmed" sub="Nearest baler, booked" tone={{ bg: C.ink, fg: C.canvas, line: C.lineStrong }} />
      <Step
        x={R}
        i={2}
        start={128}
        icon={
          <span style={{ display: "inline-flex", alignItems: "center", gap: 2 }}>
            <Factory size={24} strokeWidth={1.9} />
            <IndianRupee size={18} strokeWidth={2.2} />
          </span>
        }
        title="Straw sold, farmer paid"
        sub="Fuel for industry, no smoke"
        tone={{ bg: C.straw2Soft, fg: C.data1, line: C.line }}
      />

      <div style={{ position: "absolute", left: PAD, right: PAD, top: 830, height: 1, background: C.line, opacity: ramp(f, 144, 158) }} />
      <div style={{ position: "absolute", left: PAD, right: PAD, top: 854, display: "flex", alignItems: "center", gap: 14, ...rise(f, 148, 14, 8) }}>
        <Logo size={44} />
        <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.024em", color: C.ink }}>Change what happens on the bad days.</div>
      </div>
    </SceneShell>
  );
}
