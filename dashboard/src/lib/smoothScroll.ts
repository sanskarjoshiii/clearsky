import Lenis from "lenis";
import "lenis/dist/lenis.css";
import { useEffect, useRef, type RefObject } from "react";

/**
 * Smooth scrolling (Lenis) for every scroll surface of the site.
 *
 * The site has three kinds of scroll surface, each with its own Lenis instance:
 *   - the window: public pages (home, impact, sign-in, register) via <SmoothScroll /> in main.tsx;
 *   - the admin/buyer page body (`PageBody`) and the baler `<main>`: `useSmoothScroll(ref)`.
 * Those inner surfaces carry `data-scroll-surface`, so the window instance leaves their wheel events
 * alone. Anything that must keep native scrolling opts out: maps (the wheel zooms them), dialogs, and any
 * element with `data-lenis-prevent` (drawers, the farmer chat). Touch keeps native momentum (no syncTouch),
 * and people who ask for reduced motion get plain native scrolling.
 */

const NATIVE = "[data-lenis-prevent], .maplibregl-map, [role=dialog]";

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/** Lenis' classic ease-out (exponential): fast start, long soft landing. */
const easeOutExpo = (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t));

function create(wrapper?: HTMLElement): Lenis {
  const skip = wrapper ? NATIVE : `${NATIVE}, [data-scroll-surface]`;
  // Public pages get the long, clearly-felt glide (Chrome on Windows already animates the wheel a little, so
  // a light lerp feels like nothing changed); the dashboards stay quicker, because they are work tools.
  const feel = wrapper ? { lerp: 0.1 } : { duration: 1.2, easing: easeOutExpo };
  return new Lenis({
    ...(wrapper ? { wrapper, content: (wrapper.firstElementChild as HTMLElement | null) ?? wrapper, eventsTarget: wrapper } : {}),
    autoRaf: true,
    ...feel,
    smoothWheel: true,
    wheelMultiplier: 1,
    allowNestedScroll: true, // inner scrollers (tables, panels) still scroll natively
    anchors: { offset: -16 }, // in-page links such as #how glide instead of jumping
    stopInertiaOnNavigate: true,
    prevent: (node) => !!node.closest?.(skip),
  });
}

/**
 * Smooth-scroll one element that scrolls (`overflow-y: auto`). Returns the Lenis instance ref, so a
 * layout can jump to the top on navigation. Put `data-scroll-surface` on the same element.
 */
export function useSmoothScroll(wrapper: RefObject<HTMLElement | null>): RefObject<Lenis | null> {
  const lenis = useRef<Lenis | null>(null);
  useEffect(() => {
    const el = wrapper.current;
    if (!el || prefersReducedMotion()) return;
    lenis.current = create(el);
    return () => {
      lenis.current?.destroy();
      lenis.current = null;
    };
  }, [wrapper]);
  return lenis;
}

/** Window-level smooth scrolling for the pages that scroll the document. Mounted once, at the root. */
export function SmoothScroll(): null {
  useEffect(() => {
    if (prefersReducedMotion()) return;
    const lenis = create();
    return () => lenis.destroy();
  }, []);
  return null;
}
