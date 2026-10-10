import { AbsoluteFill, Composition } from "remotion";
import type { ComponentType, ReactNode } from "react";
import { S1Problem, S1_DUR } from "./scenes/S1Problem";
import { S2Idea, S2_DUR } from "./scenes/S2Idea";
import { S3How, S3_DUR } from "./scenes/S3How";
import { S4Aws, S4_DUR } from "./scenes/S4Aws";
import { S5Impact, S5_DUR } from "./scenes/S5Impact";
import { C, H, SANS, W } from "./theme";

/**
 * Section 3 of docs/video_script.md, one clip per part. No titles: the presenter says them;
 * the clips carry only the supporting animation.
 */
export const CLIPS: { id: string; file: string; dur: number; Comp: ComponentType }[] = [
  { id: "S3a-Problem", file: "3a-problem", dur: S1_DUR, Comp: S1Problem },
  { id: "S3b-Idea", file: "3b-idea", dur: S2_DUR, Comp: S2Idea },
  { id: "S3c-How", file: "3c-how-it-works", dur: S3_DUR, Comp: S3How },
  { id: "S3d-AWS", file: "3d-aws", dur: S4_DUR, Comp: S4Aws },
  { id: "S3e-Difference", file: "3e-before-after", dur: S5_DUR, Comp: S5Impact },
];

function Canvas({ children }: { children: ReactNode }) {
  return (
    <AbsoluteFill style={{ background: C.frame, fontFamily: SANS, color: C.ink }}>
      <div style={{ position: "absolute", inset: 14, borderRadius: 24, background: C.canvas, boxShadow: `0 0 0 1px ${C.line}` }} />
      {children}
    </AbsoluteFill>
  );
}

export function Root() {
  return (
    <>
      {CLIPS.map(({ id, dur, Comp }) => (
        <Composition
          key={id}
          id={id}
          component={() => (
            <Canvas>
              <Comp />
            </Canvas>
          )}
          durationInFrames={dur}
          fps={30}
          width={W}
          height={H}
        />
      ))}
    </>
  );
}
