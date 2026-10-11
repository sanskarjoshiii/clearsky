// Screen recorder for the demo videos: drives Chrome, captures every rendered frame through the Chrome
// DevTools screencast, draws a visible cursor with click ripples, and logs camera (zoom) targets.
// compose.py turns the frames + log into a 1920x1080 video with smooth zooms.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.resolve(__dirname, "../../dashboard/node_modules/@playwright/test"));

// Chrome's screencast always delivers frames at the CSS viewport size, so record a native 1080p layout.
const VIEW = { width: 1920, height: 1080 };
const DSF = 1;

// Cursor + click ripple, drawn in the page so it is part of every frame (and zooms with it).
const OVERLAY = `
(() => {
  const install = () => {
    if (document.getElementById("__cur")) return;
    const st = document.createElement("style");
    st.textContent = \`
      #__cur{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;
        transform:translate(-100px,-100px);filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));transition:scale .12s}
      #__cur.down{scale:.86}
      html.__touch #__cur{width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;background:rgba(20,20,30,.22);
        border:2px solid rgba(255,255,255,.95);filter:none;box-shadow:0 2px 8px rgba(0,0,0,.25)}
      html.__touch #__cur svg{display:none}
      .__rip{position:fixed;z-index:2147483646;pointer-events:none;width:14px;height:14px;margin:-7px 0 0 -7px;
        border-radius:50%;border:2.5px solid rgba(83,48,180,.9);background:rgba(83,48,180,.18);
        animation:__rip .65s cubic-bezier(.2,.7,.2,1) forwards}
      @keyframes __rip{to{transform:scale(4.2);opacity:0}}
      html{scrollbar-width:none}*::-webkit-scrollbar{display:none}\`;
    document.documentElement.appendChild(st);
    const c = document.createElement("div");
    c.id = "__cur";
    c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2.5 4 19l4.6-4.3 2.9 6.6 2.7-1.2-2.9-6.5 6.3-.3z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    if (window.__touchCursor) document.documentElement.classList.add("__touch");
    const pos = window.__curPos || { x: -100, y: -100 };
    c.style.transform = "translate(" + pos.x + "px," + pos.y + "px)";
    addEventListener("mousemove", (e) => { window.__curPos = { x: e.clientX, y: e.clientY }; c.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)"; }, true);
    addEventListener("mousedown", (e) => {
      c.classList.add("down");
      const r = document.createElement("div"); r.className = "__rip";
      r.style.left = e.clientX + "px"; r.style.top = e.clientY + "px";
      document.documentElement.appendChild(r); setTimeout(() => r.remove(), 700);
    }, true);
    addEventListener("mouseup", () => c.classList.remove("down"), true);
  };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", install); else install();
  new MutationObserver(install).observe(document, { childList: true, subtree: false });
})();`;

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const PHONE = { width: 430, height: 932 };

class Recorder {
  constructor(name, { mobile = false, outRoot = "D:/clearsky-video/screen" } = {}) {
    this.name = name;
    this.mobile = mobile;
    this.view = mobile ? PHONE : VIEW;
    this.dir = path.join(outRoot, name);
    fs.rmSync(this.dir, { recursive: true, force: true });
    fs.mkdirSync(path.join(this.dir, "frames"), { recursive: true });
    this.frames = [];
    this.events = [];
    this.mouse = { x: this.view.width * 0.72, y: this.view.height * 0.62 };
    this.pending = [];
  }

  async open(storageState) {
    this.browser = await chromium.launch({ channel: "chrome", args: ["--autoplay-policy=no-user-gesture-required", "--hide-scrollbars"] });
    this.ctx = await this.browser.newContext({
      viewport: this.view, deviceScaleFactor: DSF, locale: "en-IN", storageState,
      ...(this.mobile ? { isMobile: true, hasTouch: true, userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36" } : {}),
    });
    if (this.mobile) await this.ctx.addInitScript("window.__touchCursor = true;");
    await this.ctx.addInitScript(OVERLAY);
    this.page = await this.ctx.newPage();
    return this.page;
  }

  async start() {
    this.cdp = await this.ctx.newCDPSession(this.page);
    let i = 0;
    this.cdp.on("Page.screencastFrame", async (f) => {
      const file = `f${String(i++).padStart(5, "0")}.jpg`;
      this.frames.push({ file, t: f.metadata.timestamp });
      this.pending.push(fs.promises.writeFile(path.join(this.dir, "frames", file), Buffer.from(f.data, "base64")));
      try { await this.cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch {}
    });
    await this.cdp.send("Page.startScreencast", { format: "jpeg", quality: 95, maxWidth: this.view.width * DSF, maxHeight: this.view.height * DSF, everyNthFrame: 1 });
    await this.page.mouse.move(this.mouse.x, this.mouse.y);
    this.t0 = Date.now() / 1000;
    this.cam(this.view.width / 2, this.view.height / 2, 1);
  }

  now() { return Date.now() / 1000; }
  mark(label) { this.events.push({ t: this.now(), type: "mark", label }); }
  /** Camera target from now on: centre (css px) and zoom factor. */
  cam(cx, cy, scale, ease = 0.9) { this.events.push({ t: this.now(), type: "cam", cx, cy, scale, ease }); }
  camOut(ease = 0.9) { this.cam(this.view.width / 2, this.view.height / 2, 1, ease); }
  async wait(ms) { await this.page.waitForTimeout(ms); }

  async moveTo(x, y, ms = 650) {
    const { x: x0, y: y0 } = this.mouse;
    const steps = Math.max(8, Math.round(ms / 16));
    for (let k = 1; k <= steps; k++) {
      const e = easeInOut(k / steps);
      const arc = Math.sin(Math.PI * (k / steps)) * Math.min(40, Math.hypot(x - x0, y - y0) * 0.08);
      await this.page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e - arc);
      await this.page.waitForTimeout(ms / steps);
    }
    this.mouse = { x, y };
  }

  /** Wait until the page (window or the app's scroll surface) has stopped moving: smooth scrolling
   * keeps gliding after the wheel, and a zoom aimed mid-glide would miss its target. */
  async settle(maxMs = 2500) {
    const read = () => this.page.evaluate(() => {
      const s = document.querySelector("[data-scroll-surface]");
      return Math.round(window.scrollY) + ":" + Math.round(s ? s.scrollTop : 0);
    });
    let last = await read();
    let still = 0;
    for (let waited = 0; waited < maxMs && still < 3; waited += 70) {
      await this.page.waitForTimeout(70);
      const now = await read();
      still = now === last ? still + 1 : 0;
      last = now;
    }
  }

  async box(target) {
    const loc = typeof target === "string" ? this.page.locator(target).first() : target;
    await loc.waitFor({ state: "visible", timeout: 20000 });
    await this.settle();
    const b = await loc.boundingBox();
    return { loc, b, cx: b.x + b.width / 2, cy: b.y + b.height / 2 };
  }

  /** Camera centre for a zoom: an explicit point, the centre of another element, or the target itself. */
  async aim(cx, cy, camAt, camOn) {
    if (camOn) { const o = await this.box(camOn); return { x: o.cx, y: o.cy }; }
    return { x: camAt?.x ?? cx, y: camAt?.y ?? cy };
  }

  /** Move to an element and click it; optional zoom toward it (or toward `camOn`) first. */
  async click(target, { zoom = 0, move = 650, hold = 120, after = 350, camAt, camOn } = {}) {
    const { b, cx, cy } = await this.box(target);
    if (zoom) { const a = await this.aim(cx, cy, camAt, camOn); this.cam(a.x, a.y, zoom); }
    await this.moveTo(cx, cy, move);
    this.events.push({ t: this.now(), type: "click", x: cx, y: cy });
    await this.page.mouse.down();
    await this.wait(hold);
    await this.page.mouse.up();
    await this.wait(after);
    return b;
  }

  async hover(target, { zoom = 0, move = 650, camAt, camOn } = {}) {
    const { b, cx, cy } = await this.box(target);
    if (zoom) { const a = await this.aim(cx, cy, camAt, camOn); this.cam(a.x, a.y, zoom); }
    await this.moveTo(cx, cy, move);
    return b;
  }

  async type(text, delay = 55) { await this.page.keyboard.type(text, { delay }); }

  /** Wheel-scroll by dy css px (pages with Lenis glide). */
  async wheel(dy, settle = 1300) { await this.page.mouse.wheel(0, dy); await this.wait(settle); }

  async stop() {
    await this.wait(250);
    this.tEnd = this.now(); // a still screen sends no frames, so remember when the take really ended
    await this.cdp.send("Page.stopScreencast");
    await Promise.all(this.pending);
    const manifest = { name: this.name, view: this.view, mobile: this.mobile, dsf: DSF, t0: this.t0, tEnd: this.tEnd, frames: this.frames, events: this.events };
    fs.writeFileSync(path.join(this.dir, "manifest.json"), JSON.stringify(manifest));
    await this.browser.close();
    console.log(`${this.name}: ${this.frames.length} frames over ${(this.now() - this.t0).toFixed(1)} s -> ${this.dir}`);
  }
}

/** Run a take; the capture and its log are saved even if a step fails, so real actions are never lost. */
async function take(rec, steps) {
  try { await steps(); } catch (e) { console.error(`${rec.name}: step failed: ${e.message.split("\n")[0]}`); process.exitCode = 1; }
  finally { if (rec.cdp) await rec.stop(); }
}

module.exports = { Recorder, take, VIEW, DSF };
