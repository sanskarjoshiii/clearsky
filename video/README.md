# clearsky video: explainer animation (section 3)

The animation that plays on the right half of the screen while the presenter explains clearsky (`docs/video_script.md` §3). Built with [Remotion](https://www.remotion.dev) (React → MP4), in the dashboard's design language.

- **Size:** 960×1080 (8:9, one half of a 1920×1080 frame) · 30 fps
- **Five separate clips**, one per part of the talk, each exactly as long as its voice-over slot. No titles or captions: the presenter says them; the clips carry only the animated pieces and the text inside them. Each clip fades in and out softly.

| Clip (output file) | Source | Length | Video time | Shows |
|---|---|---|---|---|
| `3a-problem.mp4` | `src/scenes/S1Problem.tsx` | 12 s | 0:25–0:37 | Punjab (Amritsar, Jalandhar, Ludhiana, Bathinda, Patiala) → fields ignite → smoke drifts to Delhi → AQI meter → chips *Stubble burning · AQI · Pollution exposure* |
| `3b-idea.mp4` | `src/scenes/S2Idea.tsx` | 9 s | 0:37–0:46 | Farmer, baler and industry with no link → clearsky hub → request, straw and payment flow |
| `3c-how-it-works.mp4` | `src/scenes/S3How.tsx` | 12 s | 0:46–0:58 | AI agent parses Gurpreet's voice note (Khanna) → matcher books the nearest free baler and a buyer → risk score *Track* and village alert *Warn* |
| `3d-aws.mp4` | `src/scenes/S4Aws.tsx` | 11 s | 0:58–1:09 | Lanes: messages (API Gateway, Lambda, SQS) → voice (Transcribe, Polly) → bookings (DynamoDB transaction race) → hourly (EventBridge Scheduler) |
| `3e-before-after.mp4` | `src/scenes/S5Impact.tsx` | 6 s | 1:09–1:15 | Before (calls, waiting, fire) vs with clearsky (one message, confirmed, paid) → "Change what happens on the bad days." |

## Before rendering: `src/content.ts`

- `problemStat`: an optional **sourced** number for the Delhi air-quality card (value, label, source). Leave it `null` until the team has a citation; no number is shown then.
- `aws.transcribe` / `aws.llm`: name only the services switched on in the deployed stack.
- `farmer`: the demo farmer's message and details.

Colours and fonts live in `src/theme.ts` (mirrors `dashboard/src/styles.css`). The map uses simplified state outlines from [geohacker/india](https://github.com/geohacker/india) (`src/data/geo.json`) and approximate city-centre coordinates.

## Commands

```bash
cd video
npm install
npm run studio                       # live preview + scrubbing in the browser
npm run render                       # → out/3a-problem.mp4 … out/3e-before-after.mp4
npx remotion render S3c-How out/3c.mp4               # one clip (ids: S3a-Problem, S3b-Idea, S3c-How, S3d-AWS, S3e-Difference)
npx remotion still S3a-Problem out/f.png --frame=300 # one frame
npx remotion render S3a-Problem out/x.mp4 --scale=2  # 1920×2160 master for 4K edits
```

On the dev laptop C: is nearly full: `node_modules` is a junction to `D:\clearsky-video\node_modules`, and renders should go to D: (set `TEMP`/`TMP` to a folder on D: first).
