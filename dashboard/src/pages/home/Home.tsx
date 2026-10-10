import { useEffect } from "react";
import { Closing, Footer } from "./Closing";
import { Hero } from "./Hero";
import { Numbers } from "./Numbers";
import { Roles } from "./Roles";
import { Steps } from "./Steps";
import { Story } from "./Story";

/**
 * Public home page at `/`: the front door for judges, balers, buyers and officers (farmers use
 * WhatsApp). Layout translated from the Oct-10 marketing reference; landing-only tokens (forest, lime,
 * mist, display font) live in styles.css and never appear in the role apps.
 */
export function Home() {
  useEffect(() => {
    document.title = "clearsky · Straw pickup instead of stubble fires";
    return () => {
      document.title = "clearsky";
    };
  }, []);
  return (
    <div className="min-h-dvh bg-white text-ink">
      <Hero />
      <Numbers />
      <Roles />
      <Story />
      <Steps />
      <Closing />
      <Footer />
    </div>
  );
}

export const Component = Home;
