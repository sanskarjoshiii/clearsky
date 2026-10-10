import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router";
import { homeFor, useAuth } from "../../auth/AuthProvider";
import { Logo } from "../../components/Shell";
import { cx, Display, Reveal, SECTION, Starburst } from "./shared";

function Tilted({ src, className }: { src: string; className: string }) {
  return (
    <div className={cx("hidden overflow-hidden rounded-[20px] border-[6px] border-white shadow-[0_18px_40px_rgb(20_30_30/0.18)] lg:block", className)}>
      <img src={src} alt="" loading="lazy" className="size-full object-cover" />
    </div>
  );
}

export function Closing() {
  return (
    <section className="relative overflow-hidden py-24 sm:py-32">
      <Starburst className="absolute -bottom-40 left-1/2 size-[360px] -translate-x-1/2 text-lime-soft" points={14} inner={0.75} />
      <div className={cx(SECTION, "relative flex items-center justify-center gap-10")}>
        <Tilted src="/home/bale.jpg" className="h-40 w-52 -rotate-6 animate-float" />
        <Reveal className="max-w-[560px] text-center">
          <Display className="text-[clamp(34px,4.4vw,54px)] text-ink">
            Start A Smoke-Free
            <br />
            Season Today
          </Display>
          <p className="mx-auto mt-4 max-w-[440px] text-[15px] leading-relaxed text-muted">
            Balers and industry buyers register once and are approved by the district team. Farmers need nothing but WhatsApp.
          </p>
          <div className="mx-auto mt-8 flex w-full max-w-[460px] flex-col gap-2 rounded-[22px] bg-mist p-2 sm:flex-row sm:rounded-full">
            <Link to="/register" className="group inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-lime px-5 py-3 text-[14px] font-semibold text-forest transition-transform hover:-translate-y-px">
              Register as a baler <ArrowUpRight className="size-4" strokeWidth={2.2} />
            </Link>
            <Link to="/register" className="group inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-forest px-5 py-3 text-[14px] font-semibold text-white transition-transform hover:-translate-y-px">
              Register as a buyer <ArrowUpRight className="size-4" strokeWidth={2.2} />
            </Link>
          </div>
          <div className="mt-6 flex items-center justify-center gap-3">
            <div className="flex -space-x-2.5">
              {["/home/farmer.jpg", "/home/driver.jpg", "/home/industry.jpg"].map((s) => (
                <img key={s} src={s} alt="" className="size-8 rounded-full border-2 border-white object-cover" />
              ))}
            </div>
            <p className="text-left text-[12px] leading-tight text-muted">
              Farmers, balers and plants,
              <br />
              connected in one season.
            </p>
          </div>
        </Reveal>
        <Tilted src="/home/baler.jpg" className="h-40 w-52 rotate-6 animate-float [animation-delay:1.8s]" />
      </div>
    </section>
  );
}

export function Footer() {
  const { me } = useAuth();
  return (
    <footer className="px-3 pb-3 sm:px-5 sm:pb-5">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-6 rounded-[28px] bg-forest px-6 py-8 text-white sm:flex-row sm:items-center sm:justify-between sm:px-10">
        <div className="flex items-center gap-3">
          <Logo size="size-9" />
          <div>
            <div className="font-display text-[22px] font-extrabold tracking-[-0.03em]">clearsky</div>
            <div className="text-[12px] text-white/55">Straw pickup instead of stubble fires · AWS Environmental Hacks 2026</div>
          </div>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-white/75">
          <a href="#how" className="hover:text-white">
            How it works
          </a>
          <Link to="/impact" className="hover:text-white">
            Impact
          </Link>
          <Link to="/register" className="hover:text-white">
            Register
          </Link>
          <Link to={me ? homeFor(me.role) : "/login"} className="hover:text-white">
            {me ? "Open dashboard" : "Sign in"}
          </Link>
        </nav>
      </div>
    </footer>
  );
}
