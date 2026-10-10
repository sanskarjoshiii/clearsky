import type { CSSProperties, ReactNode } from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { C, MONO, PAD, TRACK_DISPLAY } from "../theme";
import { ramp, rise } from "../lib/anim";

/** Section header: mono number + eyebrow, then the headline revealed line by line from a mask. */
export function Headline({
  num,
  eyebrow,
  lines,
  start = 0,
  size = 46,
  top = 112,
}: {
  num: string;
  eyebrow: string;
  lines: string[];
  start?: number;
  size?: number;
  top?: number;
}) {
  const f = useCurrentFrame();
  return (
    <div style={{ position: "absolute", left: PAD, right: PAD, top }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, ...rise(f, start, 14, 8) }}>
        <span style={{ fontFamily: MONO, fontSize: 15, color: C.data1, fontWeight: 500 }}>{num}</span>
        <span style={{ width: 18, height: 1, background: C.lineStrong }} />
        <span
          style={{
            fontSize: 13,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: C.muted,
            fontWeight: 600,
          }}
        >
          {eyebrow}
        </span>
      </div>
      <div style={{ marginTop: 16 }}>
        {lines.map((l, i) => {
          const p = ramp(f, start + 4 + i * 6, start + 26 + i * 6);
          return (
            <div key={l} style={{ overflow: "hidden", paddingBottom: 4 }}>
              <div
                style={{
                  fontSize: size,
                  fontWeight: 600,
                  letterSpacing: TRACK_DISPLAY,
                  lineHeight: 1.06,
                  color: C.ink,
                  transform: `translateY(${(1 - p) * 105}%)`,
                }}
              >
                {l}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Tag chip in the style of the hackathon track card: hairline box, small square bullet. */
export function Chip({
  label,
  color = C.data1,
  style,
  size = 16,
  bullet = true,
}: {
  label: ReactNode;
  color?: string;
  style?: CSSProperties;
  size?: number;
  bullet?: boolean;
}) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        padding: `${size * 0.45}px ${size * 0.8}px`,
        border: `1px solid ${C.line}`,
        borderRadius: 6,
        background: C.canvas,
        fontSize: size,
        color: C.ink2,
        fontWeight: 500,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {bullet ? <span style={{ width: 8, height: 8, background: color, borderRadius: 1.5, flexShrink: 0 }} /> : null}
      {label}
    </div>
  );
}

export function Logo({ size = 30, style }: { size?: number; style?: CSSProperties }) {
  return (
    <Img
      src={staticFile("logo.png")}
      style={{ width: size, height: size, borderRadius: "50%", display: "block", ...style }}
    />
  );
}

/** Fades a scene in and out so cuts between scenes are soft. */
export function SceneShell({ dur, children }: { dur: number; children: ReactNode }) {
  const f = useCurrentFrame();
  const o = Math.min(ramp(f, 0, 8), 1 - ramp(f, dur - 10, dur));
  return <div style={{ position: "absolute", inset: 0, opacity: o }}>{children}</div>;
}

/** Icon inside a hairline circle. */
export function IconDisc({
  children,
  size = 56,
  bg = C.canvas,
  border = C.line,
  style,
}: {
  children: ReactNode;
  size?: number;
  bg?: string;
  border?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: bg,
        border: `1px solid ${border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
