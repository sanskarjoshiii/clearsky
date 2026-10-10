import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

/**
 * Video tokens. Mirrors dashboard/src/styles.css so the explainer looks like the product the judges
 * see in the demo. Same rules (docs/design-system.md):
 *   violet = the WhatsApp agent / a machine acted · green/amber/red = burn risk only ·
 *   teal = straw · ink, not colour, for emphasis · hairlines, not shadows.
 * This file is the only place a hex value may appear in video/.
 */
export const C = {
  frame: "#fafafc",
  canvas: "#ffffff",
  sunken: "#f6f6f8",
  line: "#e8e8ea",
  lineStrong: "#d9d9dc",

  ink: "#1c1c1c",
  ink2: "#3a3a3c",
  muted: "#6f6f73",
  faint: "#9b9ba0",

  agent: "#5330b4",
  agentSoft: "#efebfc",
  agentLine: "#d4cdec",

  ok: "#1b7f3b",
  okFill: "#2f9e55",
  okSoft: "#e3f8ec",
  okLine: "#a9dfbf",
  warn: "#b7790a",
  warnFill: "#e8a317",
  warnSoft: "#fff4dc",
  risk: "#c93a3a",
  riskFill: "#d64545",
  riskSoft: "#fff0f1",
  riskLine: "#f3b9bd",

  data1: "#396799",
  data2: "#4da2a9",
  data3: "#79d7bd",
  straw2Soft: "#e6f4f4", // soft tint of the straw/teal ramp for icon wells
  wheat: "#f5e6c8",
  straw: "#cfae6a", // field dots on white (wheat is too light to read at 4 px)
  land: "#fcfaf5",
  smoke: "#6e6e75",
} as const;

/** AQI category ramp (India's six bands), light → dark. Only used on the AQI meter. */
export const AQI = [
  { label: "Good", color: "#a9dfbf" },
  { label: "Satisfactory", color: "#cde8a6" },
  { label: "Moderate", color: "#f0d18e" },
  { label: "Poor", color: "#e8a317" },
  { label: "Very poor", color: "#d64545" },
  { label: "Severe", color: "#8e1f2b" },
] as const;

export const SANS = loadInter("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin"] }).fontFamily;
export const MONO = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;

export const W = 960;
export const H = 1080;
export const PAD = 56;
export const TRACK_DISPLAY = "-0.032em";
export const TRACK_TITLE = "-0.018em";
