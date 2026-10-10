import { useEffect, useState } from "react";
import { cx, Display, Reveal, SECTION, Starburst, useInView, usePrefersReducedMotion } from "./shared";

const STEPS = [
  {
    title: "Farmer sends one message",
    text: "Name, village, acres and harvest date, typed or as a voice note. The AI agent understands Hindi, Punjabi and Hinglish.",
    img: "/home/farmer.jpg",
  },
  {
    title: "The nearest free baler accepts",
    text: "The matcher picks a baler with capacity that day and a buyer that pays best after transport, then offers the job. The farmer is told once it is accepted.",
    img: "/home/driver.jpg",
  },
  {
    title: "Field cleared, straw sold",
    text: "The baler taps Done, the farmer gets a WhatsApp message, and the bales go to the plant. The field never needed a match.",
    img: "/home/bale.jpg",
  },
  {
    title: "Risk drops on the radar",
    text: "Fields likely to burn are scored every hour. Officers alert a village in one click, and the red dots turn green as fields get booked.",
    img: "/home/baler.jpg",
  },
];

const DWELL = 5200;

export function Steps() {
  const [active, setActive] = useState(0);
  const [ref, seen] = useInView<HTMLDivElement>();
  const reduce = usePrefersReducedMotion();

  useEffect(() => {
    if (!seen || reduce) return;
    const t = setTimeout(() => setActive((a) => (a + 1) % STEPS.length), DWELL);
    return () => clearTimeout(t);
  }, [active, seen, reduce]);

  return (
    <section id="how" className="scroll-mt-6 px-3 pt-5 sm:px-5">
      <div ref={ref} className="relative isolate mx-auto max-w-[1400px] overflow-hidden rounded-[28px] bg-forest py-16 text-white sm:py-20">
        <Starburst className="absolute -left-32 top-1/3 -z-10 size-[380px] text-forest-2" points={12} inner={0.62} />
        <div className={cx(SECTION, "grid gap-12 lg:grid-cols-[1fr_1.15fr] lg:items-center")}>
          <div>
            <Reveal className="relative">
              <Display className="text-[clamp(30px,3.8vw,46px)] sm:pr-28">
                From One Message
                <br />
                To A Clear Field
              </Display>
              <img src="/home/bale.jpg" alt="" className="absolute right-0 top-1 hidden h-16 w-24 rotate-3 rounded-[14px] object-cover shadow-[0_10px_30px_rgb(0_0_0/0.35)] sm:block" />
            </Reveal>

            <ol className="relative mt-10 space-y-2">
              <span className="absolute bottom-6 left-[19px] top-6 w-px bg-white/15" aria-hidden />
              {STEPS.map((s, k) => {
                const on = k === active;
                return (
                  <li key={s.title}>
                    <button type="button" onClick={() => setActive(k)} aria-current={on ? "step" : undefined} className="group relative flex w-full gap-5 rounded-[16px] p-1 text-left">
                      <span
                        className={cx(
                          "relative z-10 flex size-10 shrink-0 items-center justify-center rounded-full border text-[13px] font-semibold tabular transition-colors duration-500",
                          on ? "border-white bg-white text-forest" : "border-lime/60 bg-forest text-lime group-hover:border-lime",
                        )}
                      >
                        {String(k + 1).padStart(2, "0")}
                      </span>
                      <span className="pt-2">
                        <span className={cx("block text-[17px] font-semibold transition-colors duration-500", on ? "text-white" : "text-white/55 group-hover:text-white/80")}>{s.title}</span>
                        <span
                          className="grid transition-[grid-template-rows,opacity] duration-500 ease-out"
                          style={{ gridTemplateRows: on ? "1fr" : "0fr", opacity: on ? 1 : 0 }}
                        >
                          <span className="overflow-hidden">
                            <span className="block max-w-[420px] pt-1.5 text-[14px] leading-relaxed text-white/70">{s.text}</span>
                            <span className="mt-3 block h-[2px] w-full max-w-[420px] overflow-hidden rounded-full bg-white/10">
                              <span
                                key={`${active}-${seen}`}
                                className="block h-full rounded-full bg-lime"
                                style={{ animation: on && seen && !reduce ? `grow ${DWELL}ms linear both` : undefined, width: reduce ? "100%" : undefined }}
                              />
                            </span>
                          </span>
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>

          <div className="relative aspect-[4/3.1] overflow-hidden rounded-[22px] bg-forest-2">
            {STEPS.map((s, k) => (
              <img
                key={s.img}
                src={s.img}
                alt=""
                loading="lazy"
                className="absolute inset-0 size-full object-cover transition-[opacity,transform] duration-[1200ms] ease-out"
                style={{ opacity: k === active ? 1 : 0, transform: k === active ? "scale(1.04)" : "scale(1)" }}
              />
            ))}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/45 to-transparent p-5">
              <span className="rounded-full bg-white px-3 py-1.5 text-[12px] font-medium text-ink">Step {String(active + 1).padStart(2, "0")}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
