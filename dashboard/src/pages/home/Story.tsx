import { ArrowDown } from "lucide-react";
import { cx, Display, Reveal, SECTION, Starburst } from "./shared";

function Photo({ src, label, className, delay }: { src: string; label: string; className?: string; delay: number }) {
  return (
    <Reveal delay={delay} className={cx("group relative overflow-hidden rounded-[22px] bg-mist", className)}>
      <img
        src={src}
        alt=""
        loading="lazy"
        className="size-full object-cover transition-transform duration-[1600ms] ease-out group-hover:scale-[1.05]"
      />
      <span className="absolute bottom-3 left-3 rounded-full bg-white px-3 py-1.5 text-[12px] font-medium text-ink shadow-[0_4px_14px_rgb(0_0_0/0.12)]">{label}</span>
    </Reveal>
  );
}

/** Circular text that turns slowly, with an arrow in the middle (the reference's "eco friendly" badge). */
function SpinBadge() {
  const text = "no fire · no smoke · clear skies · ";
  return (
    <a href="#how" aria-label="How it works" className="group relative flex size-[132px] items-center justify-center">
      <svg viewBox="0 0 120 120" className="absolute inset-0 size-full animate-spin-slow text-ink-2" aria-hidden>
        <defs>
          <path id="badge-circle" d="M60,60 m-46,0 a46,46 0 1,1 92,0 a46,46 0 1,1 -92,0" />
        </defs>
        <text fontSize="10.4" fontWeight="500" letterSpacing="2.2" fill="currentColor">
          <textPath href="#badge-circle">{text.repeat(2)}</textPath>
        </text>
      </svg>
      <span className="flex size-11 items-center justify-center rounded-full bg-lime text-forest transition-transform group-hover:scale-110">
        <ArrowDown className="size-5" strokeWidth={2.4} />
      </span>
    </a>
  );
}

export function Story() {
  return (
    <section className="relative overflow-hidden py-20 sm:py-28">
      <Starburst className="absolute -left-40 top-24 size-[420px] text-mist" points={14} inner={0.78} />
      <Starburst className="absolute -right-48 bottom-0 size-[460px] text-mist" points={14} inner={0.78} />
      <div className={cx(SECTION, "relative")}>
        <Reveal className="mx-auto max-w-[760px] text-center">
          <Display className="text-[clamp(34px,4.6vw,56px)] text-ink">
            Straw Is Fuel.
            <br />
            The Fire Was Never Needed.
          </Display>
          <p className="mx-auto mt-4 max-w-[560px] text-[15px] leading-relaxed text-muted">
            After the paddy harvest, farmers have only weeks before wheat. clearsky books a baler to clear the field and sends the straw to a plant that pays for it.
            The farmer earns instead of burning.
          </p>
        </Reveal>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_1fr] lg:items-start lg:gap-6">
          <Photo src="/home/farmer.jpg" label="Farmer books on WhatsApp" className="aspect-[4/3.4] lg:mt-0" delay={0} />
          <div className="hidden justify-center lg:flex lg:pt-8">
            <SpinBadge />
          </div>
          <Photo src="/home/baler.jpg" label="Nearest baler clears the field" className="aspect-[4/4.6] lg:mt-28" delay={150} />
          <Photo src="/home/industry.jpg" label="Industry buys the straw" className="aspect-[4/3.6] sm:col-span-2 lg:col-span-1 lg:mt-0" delay={300} />
        </div>
      </div>
    </section>
  );
}
