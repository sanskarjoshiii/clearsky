import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { cx, Display, Reveal, SECTION, Starburst, usePrefersReducedMotion } from "./shared";

/** Tiny animated stand-in for the officer's Burn Risk Radar (no screenshot needed). */
function MiniRadar() {
  // positions in % of the round scope (all inside the circle)
  const dots = [
    [30, 34, "bg-ok"],
    [42, 66, "bg-warn-fill"],
    [62, 40, "bg-risk-fill"],
    [70, 68, "bg-ok"],
    [34, 80, "bg-ok"],
    [78, 30, "bg-warn-fill"],
    [52, 16, "bg-ok"],
  ] as const;
  return (
    <div className="relative flex size-full items-center justify-center overflow-hidden bg-forest-2">
      {/* a true circle, centred: the sweep can never show corners */}
      <div className="relative aspect-square h-[86%] max-w-[86%] rounded-full bg-[radial-gradient(circle,rgb(255_255_255/0.05),transparent_70%)]">
        <div className="absolute inset-0 rounded-full border border-white/15" />
        <div className="absolute inset-[18%] rounded-full border border-white/10" />
        <div className="absolute inset-[36%] rounded-full border border-white/10" />
        <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-white/[0.07]" />
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-white/[0.07]" />

        {/* sweep: clipped to the circle; bright leading edge at 12 o'clock, tail fading behind it */}
        <div className="absolute inset-0 overflow-hidden rounded-full">
          <div className="absolute inset-0 animate-spin-slow [animation-duration:4.5s]">
            <div className="absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_0deg,transparent_290deg,rgb(150_214_49/0.06)_300deg,rgb(150_214_49/0.42)_360deg)]" />
            <div className="absolute bottom-1/2 left-1/2 h-1/2 w-[2px] -translate-x-1/2 rounded-full bg-gradient-to-t from-lime/20 to-lime shadow-[0_0_8px_rgb(150_214_49/0.8)]" />
          </div>
        </div>

        {dots.map(([x, y, c], i) => (
          <span
            key={i}
            className={cx("absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white/70", c, c === "bg-risk-fill" && "animate-pulse-risk")}
            style={{ left: `${x}%`, top: `${y}%` }}
          />
        ))}
        <span className="absolute left-1/2 top-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-lime" />
      </div>
    </div>
  );
}

type Role = { title: string; tag: string; text: string; cta: { label: string; to: string }; media: ReactNode; thumb: ReactNode };

const img = (src: string) => <img src={src} alt="" loading="lazy" className="size-full object-cover" />;

const ROLES: Role[] = [
  {
    title: "Farmers",
    tag: "One message · Hindi, Punjabi, voice",
    text: "Send name, village, acres and harvest date on WhatsApp, typed or spoken. The agent books the pickup and confirms when a baler accepts. No app, no account.",
    cta: { label: "How it works", to: "#how" },
    media: img("/home/farmer.jpg"),
    thumb: img("/home/farmer.jpg"),
  },
  {
    title: "Baler operators",
    tag: "Requests with place, acres and pay",
    text: "A phone-first dashboard: accept or decline requests, see the day as a route, and tap Done when a field is cleared. Idle machines get work nearby.",
    cta: { label: "Register as a baler", to: "/register" },
    media: img("/home/driver.jpg"),
    thumb: img("/home/driver.jpg"),
  },
  {
    title: "Industry buyers",
    tag: "Straw matched by price and distance",
    text: "Set the tonnes you need, your price and pickup radius. clearsky routes straw to the buyer that pays best after transport and shows every delivery on its way.",
    cta: { label: "Register as a buyer", to: "/register" },
    media: img("/home/industry.jpg"),
    thumb: img("/home/industry.jpg"),
  },
  {
    title: "District officers",
    tag: "Burn Risk Radar, re-scored hourly",
    text: "Every field scored from satellite fire history and days to sowing. One click sends a village a pickup offer on WhatsApp before anything is burnt.",
    cta: { label: "See the live impact", to: "/impact" },
    media: <MiniRadar />,
    thumb: <MiniRadar />,
  },
];

/** Role at any index, wrapping around (the list is never empty). */
function roleAt(k: number): Role {
  const n = ROLES.length;
  return ROLES[((k % n) + n) % n] as Role;
}

function Side({ role, onClick, align }: { role: Role; onClick: () => void; align: "left" | "right" }) {
  return (
    <button type="button" onClick={onClick} className={cx("group hidden w-[170px] flex-col gap-3 text-white/45 transition-colors hover:text-white/80 lg:flex", align === "right" && "items-end text-right")}>
      <span className="text-[14px] font-medium">{role.title}</span>
      <span className="block size-16 overflow-hidden rounded-[10px] opacity-70 transition-opacity group-hover:opacity-100">{role.thumb}</span>
    </button>
  );
}

function Cta({ to, label }: { to: string; label: string }) {
  const cls = "inline-flex items-center gap-2 rounded-full border border-white/25 px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-white/10";
  return to.startsWith("#") ? (
    <a href={to} className={cls}>
      {label}
    </a>
  ) : (
    <Link to={to} className={cls}>
      {label}
    </Link>
  );
}

export function Roles() {
  const [i, setI] = useState(0);
  const [hold, setHold] = useState(false);
  const reduce = usePrefersReducedMotion();
  const n = ROLES.length;
  const go = (d: number) => setI((x) => (x + d + n) % n);

  useEffect(() => {
    if (hold || reduce) return;
    const t = setInterval(() => setI((x) => (x + 1) % n), 7000);
    return () => clearInterval(t);
  }, [hold, reduce, n]);

  const r = roleAt(i);
  return (
    <section id="who" className="scroll-mt-6 px-3 sm:px-5">
      <div
        className="relative isolate mx-auto max-w-[1400px] overflow-hidden rounded-[28px] bg-forest py-16 text-white sm:py-20"
        onMouseEnter={() => setHold(true)}
        onMouseLeave={() => setHold(false)}
        onFocus={() => setHold(true)}
        onBlur={() => setHold(false)}
      >
        <Starburst className="absolute -right-24 -top-28 -z-10 hidden size-[300px] text-lime sm:block" points={12} inner={0.62} />
        <Starburst className="absolute -bottom-36 -left-28 -z-10 size-[340px] text-forest-2" points={12} inner={0.62} />
        <div className={SECTION}>
          <Reveal>
            <Display className="max-w-[700px] text-[clamp(32px,4.2vw,52px)]">One Platform, Everyone Gains</Display>
          </Reveal>

          <div className="mt-12 flex items-start gap-8 lg:gap-12" aria-roledescription="carousel" aria-label="Who clearsky is for">
            <Side role={roleAt(i - 1)} onClick={() => go(-1)} align="left" />

            <div key={i} className="flex flex-1 flex-col gap-6 sm:flex-row sm:items-start" style={{ animation: "rise 600ms cubic-bezier(.16,1,.3,1) both" }} aria-live="polite">
              <div className="aspect-[4/3] w-full shrink-0 overflow-hidden rounded-[18px] sm:w-[300px]">{r.media}</div>
              <div className="max-w-[360px]">
                <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-white/50">
                  {String(i + 1).padStart(2, "0")} / {String(n).padStart(2, "0")}
                </p>
                <h3 className="mt-2 font-display text-[28px] font-extrabold tracking-[-0.02em]">{r.title}</h3>
                <p className="mt-2 text-[14px] font-semibold text-lime">{r.tag}</p>
                <p className="mt-3 text-[14px] leading-relaxed text-white/75">{r.text}</p>
                <div className="mt-6">
                  <Cta to={r.cta.to} label={r.cta.label} />
                </div>
              </div>
            </div>

            <Side role={roleAt(i + 1)} onClick={() => go(1)} align="right" />
          </div>

          <div className="mt-10 flex items-center justify-between">
            <div className="flex gap-1.5" role="tablist" aria-label="Choose a role">
              {ROLES.map((x, k) => (
                <button
                  key={x.title}
                  type="button"
                  role="tab"
                  aria-selected={k === i}
                  aria-label={x.title}
                  onClick={() => setI(k)}
                  className={cx("h-1.5 rounded-full transition-all duration-500", k === i ? "w-8 bg-lime" : "w-3 bg-white/25 hover:bg-white/45")}
                />
              ))}
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => go(-1)} aria-label="Previous" className="flex size-12 items-center justify-center rounded-full bg-forest-2 text-white transition-colors hover:bg-white/15">
                <ArrowLeft className="size-5" />
              </button>
              <button type="button" onClick={() => go(1)} aria-label="Next" className="flex size-12 items-center justify-center rounded-full bg-lime text-forest transition-transform hover:scale-105">
                <ArrowRight className="size-5" strokeWidth={2.4} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
