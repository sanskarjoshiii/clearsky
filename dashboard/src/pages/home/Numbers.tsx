import { ArrowRight, MessageCircle } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useStats } from "../../api/hooks";
import type { Stats } from "../../api/types";
import { fmtInt, fmtNum } from "../../lib/format";
import { cx, Display, SECTION, useInView } from "./shared";

const dash = "–";

function Card({ title, children, className, delay = 0 }: { title: string; children: ReactNode; className?: string; delay?: number }) {
  return (
    <div className={cx("w-full rounded-[18px] bg-mist p-4 shadow-[0_1px_0_rgb(0_0_0/0.03)] lg:w-[230px]", className)}>
      <div className="lg:animate-float" style={{ animationDelay: `${delay}ms` }}>
        {children}
        <p className="mt-3 text-[12px] font-medium text-ink-2">{title}</p>
      </div>
    </div>
  );
}

function AcresBars({ s }: { s?: Stats }) {
  const reg = s?.acres_registered ?? 0;
  const bars = [
    { k: "Registered", v: reg },
    { k: "Booked", v: s?.acres_booked ?? 0, hot: true },
    { k: "Cleared", v: s?.acres_cleared ?? 0 },
  ];
  const pct = (v: number) => (reg > 0 ? Math.round((v / reg) * 100) : 0);
  return (
    <div className="flex h-[104px] items-end justify-center gap-3 rounded-[12px] bg-white px-3 pt-3">
      {bars.map((b) => (
        <div key={b.k} className="flex h-full w-12 flex-col items-center justify-end gap-1">
          <span className={cx("text-[10.5px] font-semibold tabular", b.hot ? "text-forest" : "text-faint")}>{s ? `${pct(b.v)}%` : dash}</span>
          <div className="relative w-full overflow-hidden rounded-t-[6px] bg-mist" style={{ height: "70%" }}>
            <div
              className={cx("absolute inset-x-0 bottom-0 rounded-t-[6px] transition-[height] duration-1000 ease-out", b.hot ? "bg-lime" : "bg-line-strong")}
              style={{ height: `${Math.max(4, pct(b.v))}%` }}
            />
          </div>
          <span className="text-[9.5px] text-muted">{b.k}</span>
        </div>
      ))}
    </div>
  );
}

function StrawRing({ s }: { s?: Stats }) {
  const booked = s?.tonnes_booked ?? 0;
  const delivered = s?.tonnes_delivered ?? 0;
  const share = booked > 0 ? Math.min(1, delivered / booked) : 0;
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex w-full items-center justify-center rounded-[12px] bg-white py-3">
      <svg viewBox="0 0 90 90" className="size-[104px] -rotate-90">
        <circle cx="45" cy="45" r={r} fill="none" stroke="var(--color-mist)" strokeWidth="11" />
        <circle
          cx="45"
          cy="45"
          r={r}
          fill="none"
          stroke="var(--color-lime)"
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - Math.max(0.04, share))}
          style={{ transition: "stroke-dashoffset 1200ms cubic-bezier(.16,1,.3,1)" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="font-display text-[17px] font-extrabold text-forest tabular">{s ? fmtNum(booked) : dash}</div>
        <div className="text-[9.5px] text-muted">tonnes booked</div>
      </div>
    </div>
  );
}

function RiskPie({ s }: { s?: Stats }) {
  const red = s?.red_fields ?? 0;
  const amber = s?.yellow_fields ?? 0;
  const total = s?.fields ?? 0;
  const green = Math.max(0, total - red - amber);
  const a = total ? (red / total) * 360 : 0;
  const b = total ? a + (amber / total) * 360 : 0;
  const bg = total
    ? `conic-gradient(var(--color-risk-fill) 0 ${a}deg, var(--color-warn-fill) ${a}deg ${b}deg, var(--color-ok) ${b}deg 360deg)`
    : "var(--color-line)";
  return (
    <div className="flex items-center gap-3 rounded-[12px] bg-white p-3">
      <div className="size-[72px] shrink-0 rounded-full" style={{ background: bg }}>
        <div className="m-[18px] size-9 rounded-full bg-white" />
      </div>
      <ul className="space-y-1 text-[11px] text-ink-2">
        {[
          ["bg-risk-fill", "Red", red],
          ["bg-warn-fill", "Amber", amber],
          ["bg-ok", "Green", green],
        ].map(([dot, k, v]) => (
          <li key={k as string} className="flex items-center gap-1.5">
            <span className={cx("size-2 rounded-full", dot as string)} />
            <span className="w-11">{k}</span>
            <span className="font-semibold tabular">{s ? fmtInt(v as number) : dash}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Reach({ s }: { s?: Stats }) {
  return (
    <div className="rounded-[12px] bg-white p-3">
      <div className="flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-full bg-lime-soft text-forest">
          <MessageCircle className="size-4" strokeWidth={2.2} />
        </span>
        <span className="font-display text-[28px] font-extrabold leading-none text-forest tabular">{s ? fmtInt(s.farmers) : dash}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[10.5px] text-muted">
        <div>
          <div className="text-[14px] font-semibold text-ink tabular">{s ? fmtInt(s.alerts_sent) : dash}</div>
          village alerts sent
        </div>
        <div>
          <div className="text-[14px] font-semibold text-ink tabular">{s ? fmtInt(s.fields_saved_after_alert) : dash}</div>
          booked after an alert
        </div>
      </div>
    </div>
  );
}

/** Faint curving guide lines from the four cards toward the headline (the reference's background lines). */
function Lines({ on }: { on: boolean }) {
  const paths = [
    "M150 120 C 300 120, 330 260, 470 300",
    "M1050 100 C 900 120, 880 250, 730 290",
    "M150 520 C 300 520, 330 400, 470 360",
    "M1050 540 C 900 520, 880 410, 730 370",
  ];
  return (
    <svg viewBox="0 0 1200 640" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 hidden size-full lg:block" aria-hidden>
      {paths.map((d, i) => (
        <path
          key={i}
          d={d}
          fill="none"
          stroke="var(--color-line-strong)"
          strokeWidth="1.2"
          strokeDasharray="1400"
          style={{ strokeDashoffset: on ? 0 : 1400, transition: `stroke-dashoffset 1800ms cubic-bezier(.16,1,.3,1) ${i * 120}ms` }}
        />
      ))}
    </svg>
  );
}

export function Numbers() {
  const stats = useStats(true);
  const s = stats.data;
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <section id="numbers" className={cx(SECTION, "scroll-mt-6 py-20 sm:py-28")}>
      <div ref={ref} className="relative lg:h-[640px]">
        <Lines on={seen} />
        <div className="relative z-10 mx-auto flex max-w-[560px] flex-col items-center text-center lg:absolute lg:inset-x-0 lg:top-1/2 lg:-translate-y-1/2">
          <Display className="text-[clamp(36px,5vw,58px)] text-ink">
            Clear Fields,
            <br />
            Cleaner Air.
          </Display>
          <p className="mt-4 max-w-[460px] text-[15px] leading-relaxed text-muted">
            Every booked field is straw that goes to industry instead of into the sky. These numbers come live from the platform.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-5">
            <Link to="/impact" className="group inline-flex items-center gap-2 rounded-full bg-forest px-5 py-3 text-[14px] font-semibold text-white transition-transform hover:-translate-y-px">
              See live impact <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <div className="text-left text-[12px] leading-tight text-muted">
              <div className="font-semibold text-ink">Pilot · Sangrur district</div>
              Punjab, paddy season{s?.today ? ` ${s.today.slice(0, 4)}` : ""}
            </div>
          </div>
          {s?.demo_prices ? <p className="mt-4 text-[11px] text-faint">Demo season data while the pilot runs.</p> : null}
        </div>

        <div className="relative z-10 mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:absolute lg:inset-0 lg:mt-0 lg:block">
          <Card title="Acres this season" className="lg:absolute lg:left-[2%] lg:top-[2%]" delay={0}>
            <AcresBars s={s} />
          </Card>
          <Card title="Straw routed to industry" className="lg:absolute lg:right-[1%] lg:top-0" delay={1200}>
            <div className="relative flex w-full items-center justify-center">
              <StrawRing s={s} />
            </div>
          </Card>
          <Card title="Fields by burn risk" className="lg:absolute lg:bottom-[4%] lg:left-0" delay={2400}>
            <RiskPie s={s} />
          </Card>
          <Card title="Farmers on WhatsApp" className="lg:absolute lg:bottom-0 lg:right-[2%]" delay={3600}>
            <Reach s={s} />
          </Card>
        </div>
      </div>
    </section>
  );
}
