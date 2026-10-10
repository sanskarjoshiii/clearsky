import { Activity, AudioLines, CalendarClock, Check, Database, HardDrive, Layers, MessageCircle, Radar, ShieldCheck, Volume2, Waypoints, X } from "lucide-react";
import type { ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { content } from "../content";
import { C, MONO, PAD, W } from "../theme";
import { easeInOut, pop, ramp, rise } from "../lib/anim";
import { Chip, SceneShell } from "../components/ui";

export const S4_DUR = 330; // 11 s

const ROW_W = W - 2 * PAD;
const ROW_H = 160;
const LABEL_W = 188;
const AREA_X = PAD + LABEL_W; // tiles start here
const AREA_W = ROW_W - LABEL_W - 22;
const GAP = 30;
const TILE_H = 92;

const Lambda = () => <span style={{ fontFamily: MONO, fontSize: 22, fontWeight: 500, lineHeight: 1 }}>λ</span>;

type TileSpec = { icon: ReactNode; name: string; sub: string; w?: number; accent?: string };

function Tile({ spec, x, y, w, appear, hot }: { spec: TileSpec; x: number; y: number; w: number; appear: number; hot: boolean }) {
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: TILE_H,
        borderRadius: 10,
        background: C.canvas,
        border: `1px solid ${hot ? C.ink : C.line}`,
        padding: "13px 14px",
        opacity: appear,
        transform: `scale(${0.92 + 0.08 * appear})`,
        boxShadow: hot ? "0 6px 18px rgb(20 20 30 / 0.08)" : "none",
      }}
    >
      <div style={{ height: 24, display: "flex", alignItems: "center", color: spec.accent ?? C.ink }}>{spec.icon}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: C.ink, marginTop: 7, whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>{spec.name}</div>
      <div style={{ fontSize: 12.5, color: C.muted, marginTop: 1, whiteSpace: "nowrap" }}>{spec.sub}</div>
    </div>
  );
}

function Lane({
  idx,
  top,
  start,
  end,
  title,
  sub,
  tiles,
  children,
}: {
  idx: number;
  top: number;
  start: number;
  end: number;
  title: string;
  sub: string;
  tiles?: TileSpec[];
  children?: ReactNode;
}) {
  const f = useCurrentFrame();
  const active = f >= start && f < end;
  const r = rise(f, start, 16, 14);
  const done = f >= end;
  const n = tiles?.length ?? 0;
  const tw = n ? (AREA_W - GAP * (n - 1)) / n : 0;
  const ty = top + (ROW_H - TILE_H) / 2;
  const packet = ramp(f, start + 16, start + 16 + n * 14, 0, 1, easeInOut);

  return (
    <>
      <div
        style={{
          position: "absolute",
          left: PAD,
          top,
          width: ROW_W,
          height: ROW_H,
          borderRadius: 14,
          background: active ? C.canvas : C.frame,
          border: `1px solid ${active ? C.lineStrong : C.line}`,
          ...r,
          opacity: (r.opacity as number) * (done ? 0.62 : 1),
        }}
      >
        <div style={{ position: "absolute", left: 22, top: 0, bottom: 0, width: LABEL_W - 34, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ fontFamily: MONO, fontSize: 13, color: C.data1 }}>{String(idx).padStart(2, "0")}</div>
          <div style={{ fontSize: 19, fontWeight: 600, color: C.ink, marginTop: 4, letterSpacing: "-0.018em" }}>{title}</div>
          <div style={{ fontSize: 13.5, color: C.muted, marginTop: 2 }}>{sub}</div>
        </div>
      </div>
      <div style={{ position: "absolute", inset: 0, opacity: done ? 0.62 : 1 }}>
        {tiles?.map((t, i) => {
          const x = AREA_X + i * (tw + GAP);
          const a = pop(f, start + 6 + i * 5);
          const hot = active && packet >= i / Math.max(1, n - 1) - 0.02 && packet <= (i + 0.9) / Math.max(1, n - 1);
          return <Tile key={t.name + i} spec={t} x={x} y={ty} w={tw} appear={a} hot={hot} />;
        })}
        {tiles ? (
          <svg width={W} height={1080} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
            {tiles.slice(1).map((_, i) => {
              const x0 = AREA_X + (i + 1) * tw + i * GAP + 4;
              const x1 = x0 + GAP - 8;
              const y = ty + TILE_H / 2;
              const d = ramp(f, start + 10 + i * 5, start + 22 + i * 5);
              return (
                <g key={i} opacity={d}>
                  <line x1={x0} y1={y} x2={x0 + (x1 - x0) * d} y2={y} stroke={C.ink2} strokeWidth={1.6} />
                  <polygon points={`${x1 - 6},${y - 4} ${x1},${y} ${x1 - 6},${y + 4}`} fill={C.ink2} />
                </g>
              );
            })}
            {active && packet > 0 && packet < 1 ? (
              <circle
                cx={AREA_X + tw / 2 + packet * (n - 1) * (tw + GAP)}
                cy={ty - 10}
                r={6}
                fill={C.agent}
                stroke={C.canvas}
                strokeWidth={2.5}
              />
            ) : null}
          </svg>
        ) : null}
        {children}
      </div>
    </>
  );
}

/** Two bookings race for the baler's last slot; the DynamoDB transaction lets exactly one win. */
function BookingRace({ top, start }: { top: number; start: number }) {
  const f = useCurrentFrame();
  const y = top + (ROW_H - TILE_H) / 2;
  const reqW = 128;
  const dbW = 214;
  const dbX = AREA_X + reqW + GAP;
  const outX = dbX + dbW + GAP;
  const go = ramp(f, start + 14, start + 34, 0, 1, easeInOut);
  const decide = ramp(f, start + 36, start + 46);
  const out = (i: number) => rise(f, start + 44 + i * 6, 12, 6);
  const req = (label: string, dy: number, i: number) => (
    <div
      style={{
        position: "absolute",
        left: AREA_X + go * 18,
        top: y + dy,
        width: reqW,
        height: 40,
        borderRadius: 8,
        border: `1px solid ${C.line}`,
        background: C.canvas,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "0 12px",
        fontSize: 14,
        fontWeight: 600,
        color: C.ink2,
        ...rise(f, start + 4 + i * 4, 12, 6),
      }}
    >
      <span style={{ width: 8, height: 8, borderRadius: 2, background: C.data2 }} />
      {label}
    </div>
  );
  return (
    <>
      {req("Booking A", 0, 0)}
      {req("Booking B", 52, 1)}
      <Tile
        spec={{ icon: <Database size={22} strokeWidth={1.8} />, name: "Amazon DynamoDB", sub: "TransactWriteItems" }}
        x={dbX}
        y={y}
        w={dbW}
        appear={pop(f, start + 8)}
        hot={go > 0.3 && decide < 1}
      />
      <div style={{ position: "absolute", left: dbX + dbW - 92, top: y + 14, fontFamily: MONO, fontSize: 11.5, color: C.muted, opacity: pop(f, start + 8) }}>
        1 slot left
      </div>
      <div style={{ position: "absolute", left: outX, top: y, width: AREA_X + AREA_W - outX }}>
        <div style={{ height: 40, display: "flex", alignItems: "center", gap: 10, fontSize: 15, fontWeight: 600, color: C.ink, ...out(0) }}>
          <span style={{ width: 22, height: 22, borderRadius: "50%", background: C.ink, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Check size={13} strokeWidth={3} color={C.canvas} />
          </span>
          A booked
        </div>
        <div style={{ height: 40, marginTop: 12, display: "flex", alignItems: "center", gap: 10, fontSize: 15, color: C.muted, ...out(1) }}>
          <span style={{ width: 22, height: 22, borderRadius: "50%", border: `1.5px solid ${C.faint}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <X size={13} strokeWidth={2.6} color={C.faint} />
          </span>
          B → next free baler
        </div>
      </div>
    </>
  );
}

export function S4Aws() {
  const f = useCurrentFrame();
  const icon = (I: typeof Layers) => <I size={22} strokeWidth={1.8} />;
  const tops = [146, 318, 490, 662];
  const starts = [10, 86, 160, 242, 292];
  return (
    <SceneShell dur={S4_DUR}>

      <Lane
        idx={1}
        top={tops[0]}
        start={starts[0]}
        end={starts[1]}
        title="Every message"
        sub="answered fast, then queued"
        tiles={[
          { icon: <MessageCircle size={22} strokeWidth={1.8} />, name: "WhatsApp", sub: "Cloud API", accent: C.agent },
          { icon: icon(Waypoints), name: "API Gateway", sub: "HTTP API" },
          { icon: <Lambda />, name: "AWS Lambda", sub: "webhook" },
          { icon: icon(Layers), name: "Amazon SQS", sub: "queue + DLQ" },
        ]}
      />
      <Lane
        idx={2}
        top={tops[1]}
        start={starts[1]}
        end={starts[2]}
        title="Voice"
        sub="Hindi in, Hindi out"
        tiles={[
          { icon: icon(AudioLines), name: content.aws.transcribe ? "Amazon Transcribe" : "Speech-to-text", sub: "voice note → text" },
          { icon: <Lambda />, name: "AWS Lambda", sub: `AI agent · ${content.aws.llm}`, accent: C.agent },
          { icon: icon(Volume2), name: "Amazon Polly", sub: "reply as Hindi voice" },
        ]}
      />
      <Lane idx={3} top={tops[2]} start={starts[2]} end={starts[3]} title="Bookings" sub="never double-booked">
        <BookingRace top={tops[2]} start={starts[2]} />
      </Lane>
      <Lane
        idx={4}
        top={tops[3]}
        start={starts[3]}
        end={S4_DUR + 1}
        title="Every hour"
        sub="burn risk re-scored"
        tiles={[
          { icon: icon(CalendarClock), name: "EventBridge Scheduler", sub: "hourly · IST" },
          { icon: <Lambda />, name: "AWS Lambda", sub: "risk scorer + NASA FIRMS" },
          { icon: icon(Radar), name: "Burn Risk Radar", sub: "officer dashboard" },
        ]}
      />

      <div style={{ position: "absolute", left: PAD, right: PAD, top: 862, display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <span style={{ ...rise(f, starts[4], 12, 6), fontSize: 13, letterSpacing: "0.14em", color: C.muted, fontWeight: 600, marginRight: 4 }}>ALSO</span>
        {[
          { I: ShieldCheck, t: "Amazon Cognito · role sign-in" },
          { I: HardDrive, t: "Amazon S3 · voice & data" },
          { I: Activity, t: "Amazon CloudWatch · alarms" },
        ].map(({ I, t }, i) => (
          <div key={t} style={rise(f, starts[4] + 4 + i * 5, 12, 6)}>
            <Chip
              bullet={false}
              size={14.5}
              label={
                <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                  <I size={16} strokeWidth={1.8} color={C.ink2} /> {t}
                </span>
              }
            />
          </div>
        ))}
      </div>
    </SceneShell>
  );
}
