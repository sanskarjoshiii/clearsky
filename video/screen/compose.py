"""Turn a recorder capture (frames + manifest.json) into a 1920x1080, 30 fps MP4 with smooth zooms.

Usage: python compose.py <capture_dir> <out.mp4> <seconds> [--start S] [--frame]

- Frames are resampled to a constant 30 fps (each output frame shows the latest captured frame).
- Camera events ("cam": centre + zoom) are eased with a smooth cubic over each event's `ease` seconds.
- --frame: Screen Studio-style presentation (screen inset on a soft background, rounded corners, shadow).
- If the capture is longer than <seconds>, it is time-compressed evenly (never more than 1.6x) so the
  video fits its slot exactly; shorter captures hold the last frame.
"""

from __future__ import annotations

import argparse
import bisect
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

FFMPEG = r"C:\Users\prema\AppData\Local\Programs\Python\Python314\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
OUT_W, OUT_H, FPS = 1920, 1080, 30


def smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)  # smootherstep


def _lerp(a: tuple[float, ...], b: tuple[float, ...], k: float) -> tuple[float, float, float]:
    return tuple(x + (y - x) * k for x, y in zip(a, b))  # type: ignore[return-value]


def camera_at(events: list[dict], t: float, view: dict) -> tuple[float, float, float]:
    """Camera (centre x, centre y, zoom) at time t. A new target starts from wherever the camera is at
    that moment, so a zoom that interrupts another one never jumps."""
    centre = (view["width"] / 2, view["height"] / 2, 1.0)
    start, target, t_start, ease = centre, centre, None, 1.0
    for e in (e for e in events if e["type"] == "cam"):
        if e["t"] > t:
            break
        k = 1.0 if t_start is None else smooth((e["t"] - t_start) / ease)
        start = _lerp(start, target, k)
        target, t_start, ease = (e["cx"], e["cy"], e["scale"]), e["t"], max(0.05, e.get("ease", 0.9))
    k = 1.0 if t_start is None else smooth((t - t_start) / ease)
    return _lerp(start, target, k)


def frame_template() -> tuple[Image.Image, Image.Image, tuple[int, int, int, int]]:
    """Background, rounded mask and inset box for the framed look."""
    pad_x, pad_y = 64, 36
    box = (pad_x, pad_y, OUT_W - pad_x, OUT_H - pad_y)
    w, h = box[2] - box[0], box[3] - box[1]
    bg = Image.new("RGB", (OUT_W, OUT_H))
    top, bot = (232, 238, 228), (205, 222, 200)
    d = ImageDraw.Draw(bg)
    for y in range(OUT_H):
        k = y / (OUT_H - 1)
        d.line([(0, y), (OUT_W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bot)))
    shadow = Image.new("L", (OUT_W, OUT_H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + 10, box[2], box[3] + 14), 22, fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    bg.paste((20, 40, 30), (0, 0), shadow)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=255)
    return bg, mask, box


def phone_template() -> tuple[Image.Image, Image.Image, tuple[int, int, int, int]]:
    """Background with a phone body; returns the background, the screen mask and the screen box."""
    sh = 990
    sw = round(sh * 430 / 932)
    bez = 13
    x0, y0 = (OUT_W - sw) // 2, (OUT_H - sh) // 2
    box = (x0, y0, x0 + sw, y0 + sh)
    bg = Image.new("RGB", (OUT_W, OUT_H))
    top, bot = (232, 238, 228), (205, 222, 200)
    d = ImageDraw.Draw(bg)
    for y in range(OUT_H):
        k = y / (OUT_H - 1)
        d.line([(0, y), (OUT_W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bot)))
    body = (box[0] - bez, box[1] - bez, box[2] + bez, box[3] + bez)
    shadow = Image.new("L", (OUT_W, OUT_H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((body[0], body[1] + 14, body[2], body[3] + 18), 62, fill=120)
    bg.paste((20, 40, 30), (0, 0), shadow.filter(ImageFilter.GaussianBlur(30)))
    ImageDraw.Draw(bg).rounded_rectangle(body, 60, fill=(22, 24, 28))
    ImageDraw.Draw(bg).rounded_rectangle((body[0] + 2, body[1] + 2, body[2] - 2, body[3] - 2), 58, outline=(70, 74, 82), width=2)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, sh - 1), 46, fill=255)
    return bg, mask, box


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("out")
    ap.add_argument("seconds", type=float)
    ap.add_argument("--start", type=float, default=0.0, help="skip this many seconds of the capture")
    ap.add_argument("--frame", action="store_true")
    ap.add_argument("--max-speed", type=float, default=1.6, help="fastest allowed playback to fit the slot")
    ap.add_argument("--max-zoom", type=float, default=0.0, help="cap every zoom (phone screens: ~1.12)")
    ap.add_argument("--keep", default="", help="only these capture segments, seconds from start: 0.5-5.9,7.7-9")
    a = ap.parse_args()

    cap = Path(a.capture)
    m = json.loads((cap / "manifest.json").read_text())
    view, dsf = m["view"], m["dsf"]
    frames = sorted(m["frames"], key=lambda f: f["t"])
    times = [f["t"] for f in frames]
    t_end = max(times[-1], m.get("tEnd", 0), max((e["t"] for e in m["events"]), default=times[-1]))
    if a.keep:  # cut idle moments: play only these segments, back to back
        segs = [(m["t0"] + float(x), m["t0"] + float(y)) for x, y in (s.split("-") for s in a.keep.split(","))]
    else:
        segs = [(m["t0"] + a.start, t_end)]
    length = sum(y - x for x, y in segs)

    def capture_time(u: float) -> float:
        for x, y in segs:
            if u <= y - x:
                return x + u
            u -= y - x
        return segs[-1][1]

    speed = min(a.max_speed, max(1.0, length / a.seconds))
    if length / speed > a.seconds + 0.05:
        print(f"note: capture {length:.1f}s > {a.seconds}s even at {a.max_speed}x; the end is cut", file=sys.stderr)

    phone = bool(m.get("mobile"))
    if phone or a.frame:
        bg, mask, box = phone_template() if phone else frame_template()
        sw, sh = box[2] - box[0], box[3] - box[1]
    else:
        sw, sh = OUT_W, OUT_H

    enc = subprocess.Popen(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
         "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out],
        stdin=subprocess.PIPE,
    )
    assert enc.stdin is not None
    cache: dict[str, Image.Image] = {}
    n = round(a.seconds * FPS)
    for i in range(n):
        t = capture_time((i / FPS) * speed)
        j = max(0, bisect.bisect_right(times, t) - 1)
        f = frames[j]["file"]
        if f not in cache:
            cache.clear()
            cache[f] = Image.open(cap / "frames" / f).convert("RGB")
        src = cache[f]
        W, H = src.size
        px = W / view["width"]  # frame pixels per css px (Chrome may deliver 1x or 2x frames)
        cx, cy, s = camera_at(m["events"], t, view)
        if a.max_zoom:
            s = min(s, a.max_zoom)
        cw, ch = W / s, H / s
        x0 = min(max(cx * px - cw / 2, 0), W - cw)
        y0 = min(max(cy * px - ch / 2, 0), H - ch)
        shot = src.resize((sw, sh), Image.Resampling.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
        if phone or a.frame:
            out = bg.copy()
            out.paste(shot, (box[0], box[1]), mask)
        else:
            out = shot
        enc.stdin.write(out.tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"{a.out}: {n / FPS:.1f}s at {FPS} fps (capture played at {speed:.2f}x)")
    return enc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
