/**
 * Everything the team may need to change before rendering, in one place.
 * Rule (CLAUDE.md): no invented real-world statistics. A number appears on screen only if it is set
 * here WITH its source.
 */
export type SourcedStat = { value: string; label: string; source: string };

export const content = {
  /** Optional sourced figure shown on the Delhi air-quality card in scene 1. null = no number shown. */
  problemStat: null as SourcedStat | null,

  /** The demo farmer used in scene 3 (same message the live demo sends). Khanna is in Ludhiana district. */
  farmer: {
    name: "Gurpreet",
    village: "Khanna",
    acres: "8 acres",
    harvest: "24 Oct",
    message: "Mera 8 acre dhaan 24 tareekh ko katega, Khanna. Naam Gurpreet.",
  },

  /** Name only the AWS services switched on in the deployed stack. */
  aws: {
    transcribe: true, // false → the voice tile reads "Speech-to-text API"
    llm: "LLM via API key", // e.g. "Amazon Bedrock" if the agent runs on Bedrock
  },
};
