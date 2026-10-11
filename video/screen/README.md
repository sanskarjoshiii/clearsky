# Demo screen recordings (website walkthrough)

Four clips for `docs/video_script.md` §5, recorded from the live site with a scripted Chrome:

| Clip | Script | Length | Notes |
|---|---|---|---|
| `demo-1-home.mp4` | `home.cjs` | 10 s | public, read-only |
| `demo-2-super-admin.mp4` | `admin.cjs` | 15 s | the village Alert dialog is opened and **cancelled** (nothing is sent) |
| `demo-3-baler.mp4` | `baler.cjs` (+ `baler-done.cjs`) | 15 s | phone frame; **Accept and Done are real actions** (the farmer gets WhatsApp messages, the buyer receives straw) |
| `demo-4-buyer.mp4` | `buyer.cjs` | 15 s | read-only (demand is never saved: saving re-matches live bookings) |

## How it works

- `rec.cjs` drives Chrome (Playwright, installed Chrome) at 1920×1080 (phone: 430×932) and captures every rendered frame through the DevTools screencast. It draws a cursor (fingertip on phone) with click ripples, moves it on eased curves, waits for smooth scrolling to settle before aiming, and logs camera targets. `take()` saves the capture even if a step fails, so a real action is never lost.
- `compose.py` resamples to 30 fps, glides the camera between targets (smootherstep), frames the screen (rounded, shadow, soft background; phone body for mobile captures) and fits the take to its slot: `--max-speed` (fastest playback), `--keep a-b,c-d` (cut idle seconds), `--max-zoom` (phones: 1.12).
- `probe-*.cjs`: dry runs that check every locator on the live site without clicking anything.

## Run

```bash
# logins (git-ignored): video/screen/accounts.local.json
# { "base": "https://clearsky.akkki.tech", "officer": {"email","password"}, "baler": {...}, "buyer": {...} }
node video/screen/home.cjs
python video/screen/compose.py D:/clearsky-video/screen/home out/demo-1-home.mp4 10 --frame
python video/screen/compose.py D:/clearsky-video/screen/admin out/demo-2-super-admin.mp4 15 --frame --max-speed 1.75
python video/screen/compose.py D:/clearsky-video/screen/buyer out/demo-4-buyer.mp4 15 --frame --max-speed 1.75
```

Captures go to `D:/clearsky-video/screen/<name>/` (C: is nearly full on the dev laptop). `FARMER` (default `संस्कार`) and `DAY` (default `13`) select the booking to follow.
