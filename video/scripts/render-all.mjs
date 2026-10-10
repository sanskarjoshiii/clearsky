// Renders each section-3 clip to its own MP4: out/3a-problem.mp4 ? out/3e-before-after.mp4
// Usage: node scripts/render-all.mjs [outDir]
import { execFileSync } from "node:child_process";

const out = process.argv[2] ?? "out";
const clips = [
  ["S3a-Problem", "3a-problem"],
  ["S3b-Idea", "3b-idea"],
  ["S3c-How", "3c-how-it-works"],
  ["S3d-AWS", "3d-aws"],
  ["S3e-Difference", "3e-before-after"],
];
for (const [id, file] of clips) {
  console.log(`rendering ${id} -> ${out}/${file}.mp4`);
  execFileSync("npx", ["remotion", "render", id, `${out}/${file}.mp4`], { stdio: "inherit", shell: true });
}
