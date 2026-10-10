import { ArrowUpRight, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router";
import { homeFor, useAuth } from "../../auth/AuthProvider";
import { Logo } from "../../components/Shell";
import { Display, usePrefersReducedMotion } from "./shared";

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#who", label: "Who it's for" },
  { href: "#numbers", label: "Field data" },
  { href: "/impact", label: "Impact" },
];

function Nav() {
  const { me } = useAuth();
  const item = "rounded-full px-3 py-1.5 text-[13px] font-medium text-ink-2 transition-colors hover:bg-mist hover:text-ink";
  return (
    <nav className="flex items-center gap-3 rounded-full bg-white/95 py-2 pl-3 pr-2 shadow-[0_8px_30px_rgb(0_0_0/0.12)] backdrop-blur sm:pl-4">
      <Link to="/" className="flex items-center gap-2" aria-label="clearsky home">
        <Logo size="size-8" />
        <span className="font-display text-[22px] font-extrabold tracking-[-0.03em] text-ink">clearsky</span>
      </Link>
      <ul className="ml-auto hidden items-center gap-1 lg:flex">
        {NAV.map((n) => (
          <li key={n.href}>
            {n.href.startsWith("#") ? (
              <a href={n.href} className={item}>
                {n.label}
              </a>
            ) : (
              <Link to={n.href} className={item}>
                {n.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
      <div className="ml-auto flex items-center gap-1.5 lg:ml-4">
        <Link to={me ? homeFor(me.role) : "/login"} className="hidden rounded-full px-3 py-2 text-[13px] font-medium text-ink-2 hover:bg-mist hover:text-ink sm:block">
          {me ? "Open dashboard" : "Sign in"}
        </Link>
        <Link
          to="/register"
          className="group inline-flex items-center gap-1.5 rounded-full bg-lime px-4 py-2.5 text-[13px] font-semibold text-forest transition-transform hover:-translate-y-px"
        >
          <span className="sm:hidden">Join</span>
          <span className="hidden sm:inline">Join as baler or buyer</span>
          <ArrowUpRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" strokeWidth={2.2} />
        </Link>
      </div>
    </nav>
  );
}

function Control({ onClick, label, children }: { onClick: () => void; label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex size-9 items-center justify-center rounded-full bg-black/30 text-white backdrop-blur-md transition-colors hover:bg-black/45"
    >
      {children}
    </button>
  );
}

/**
 * The team's home film: a 4K/60 fps aerial flight over green fields (`home_page_video.mp4`, kept out of git),
 * served as two high-quality H.264 renditions with a dissolved loop seam: 2560×1440 for screens ≥ 1024 px
 * and 1280×720 for phones, both 60 fps, CRF 21 (SSIM vs the original 0.97). Only the page title sits on it;
 * the nav stays above it; the frame is 16:9 so nothing is cropped.
 */
// The current film has no audio track. Set to true if a version with music is added: the speaker button
// comes back (music stays opt-in because browsers only autoplay muted video).
const HAS_MUSIC = false;
const SRC_WIDE = "/home/hero-1440.mp4";
const SRC_SMALL = "/home/hero-720.mp4";

export function Hero() {
  const reduce = usePrefersReducedMotion();
  const video = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(!reduce);
  const [sound, setSound] = useState(false);
  // pick once per visit: phones don't download pixels they can't show
  const src = useMemo(() => (typeof window !== "undefined" && window.matchMedia?.("(min-width: 1024px)").matches ? SRC_WIDE : SRC_SMALL), []);

  useEffect(() => {
    const v = video.current;
    if (!v) return;
    if (playing) void v.play().catch(() => setPlaying(false));
    else v.pause();
  }, [playing]);

  useEffect(() => {
    const v = video.current;
    if (!v) return;
    v.muted = !sound;
    v.volume = 0.7;
    if (sound) setPlaying(true);
  }, [sound]);

  return (
    <header className="px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="relative mx-auto max-w-[1400px]">
        {/* the nav sits above the film, never on it: the film carries its own labels near the top */}
        <div className="mb-3 sm:mb-4">
          <div className="mx-auto max-w-[1080px]">
            <Nav />
          </div>
        </div>

        <div className="relative isolate mx-auto aspect-video max-h-[calc(100svh-110px)] w-full overflow-hidden rounded-[22px] bg-forest sm:rounded-[28px]">
          <video
            ref={video}
            className="absolute inset-0 size-full object-cover"
            src={src}
            poster="/home/hero-poster.jpg"
            muted
            loop
            playsInline
            autoPlay={!reduce}
            preload="auto"
            aria-label="Aerial view of farm fields"
          />

          {/* the title sits on the straw at the bottom edge, over a soft shade so it reads on any frame */}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 hidden h-[42%] bg-gradient-to-t from-black/50 via-black/15 to-transparent sm:block" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 hidden px-5 pb-8 text-center sm:block">
            <p
              className="mx-auto mb-2 inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[11px] font-medium text-white backdrop-blur-md sm:mb-3 sm:text-[12px]"
              style={{ animation: "rise 800ms cubic-bezier(.16,1,.3,1) 200ms both" }}
            >
              <span className="size-1.5 rounded-full bg-lime" /> Paddy season · Punjab
            </p>
            <Display as="h1" className="text-[clamp(48px,9vw,132px)] text-white [text-shadow:0_6px_40px_rgb(0_0_0/0.3)]">
              <span className="block" style={{ animation: "rise 1000ms cubic-bezier(.16,1,.3,1) 300ms both" }}>
                Straw, Not Smoke.
              </span>
            </Display>
          </div>
          <div className="absolute bottom-3 right-3 flex gap-2 sm:bottom-4 sm:right-4">
            {HAS_MUSIC ? (
              <Control onClick={() => setSound((s) => !s)} label={sound ? "Mute music" : "Play music"}>
                {sound ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
              </Control>
            ) : null}
            <Control onClick={() => setPlaying((p) => !p)} label={playing ? "Pause video" : "Play video"}>
              {playing ? <Pause className="size-4" fill="currentColor" /> : <Play className="size-4" fill="currentColor" />}
            </Control>
          </div>
        </div>

        <div className="px-1 pt-5 text-center sm:hidden">
          <p className="mb-2 inline-flex items-center gap-2 rounded-full bg-mist px-3 py-1 text-[11px] font-medium text-ink-2">
            <span className="size-1.5 rounded-full bg-lime" /> Paddy season · Punjab
          </p>
          <Display as="h1" className="text-[44px] text-ink">
            Straw, Not Smoke.
          </Display>
        </div>
      </div>
    </header>
  );
}
