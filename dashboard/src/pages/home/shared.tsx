import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

export function cx(...c: (string | false | null | undefined)[]): string {
  return c.filter(Boolean).join(" ");
}

export function usePrefersReducedMotion(): boolean {
  const [reduce, setReduce] = useState(() => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!mq) return;
    const on = () => setReduce(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduce;
}

/** True once the element has scrolled into view (stays true). */
export function useInView<T extends Element>(margin = "0px 0px -12% 0px"): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    if (typeof IntersectionObserver === "undefined") {
      setSeen(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setSeen(true);
          io.disconnect();
        }
      },
      { rootMargin: margin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [margin, seen]);
  return [ref, seen];
}

/** Fade + small rise, once, when scrolled into view. */
export function Reveal({ children, delay = 0, className, as: Tag = "div" }: { children: ReactNode; delay?: number; className?: string; as?: "div" | "li" | "section" }) {
  const [ref, seen] = useInView<HTMLDivElement>();
  const style: CSSProperties = {
    opacity: seen ? 1 : 0,
    transform: seen ? "none" : "translateY(18px)",
    transition: `opacity 700ms cubic-bezier(.16,1,.3,1) ${delay}ms, transform 700ms cubic-bezier(.16,1,.3,1) ${delay}ms`,
  };
  return (
    <Tag ref={ref as never} className={className} style={style}>
      {children}
    </Tag>
  );
}

/** The soft many-pointed star from the reference, used as a quiet background shape. */
export function Starburst({ className, points = 12, inner = 0.72, style }: { className?: string; points?: number; inner?: number; style?: CSSProperties }) {
  const d: string[] = [];
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? 50 : 50 * inner;
    const a = (Math.PI * i) / points - Math.PI / 2;
    d.push(`${(50 + r * Math.cos(a)).toFixed(2)},${(50 + r * Math.sin(a)).toFixed(2)}`);
  }
  return (
    <svg viewBox="0 0 100 100" aria-hidden className={className} style={style}>
      <polygon points={d.join(" ")} fill="currentColor" strokeLinejoin="round" stroke="currentColor" strokeWidth={3} />
    </svg>
  );
}

export function Display({ children, className, as: Tag = "h2" }: { children: ReactNode; className?: string; as?: "h1" | "h2" | "h3" }) {
  return <Tag className={cx("font-display font-extrabold leading-[1.02] tracking-[-0.025em]", className)}>{children}</Tag>;
}

export const SECTION = "mx-auto w-full max-w-[1240px] px-4 sm:px-6";
