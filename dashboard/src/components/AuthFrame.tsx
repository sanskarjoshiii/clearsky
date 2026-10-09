import type { ReactNode } from "react";
import { Logo } from "./Shell";

/** Centred card used by the public sign-in, registration and "under review" pages. */
export function AuthFrame({ children, wide }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-frame px-4 py-10">
      <div className={`w-full animate-rise rounded-[var(--radius-canvas)] bg-canvas p-6 shadow-[var(--shadow-canvas)] sm:p-8 ${wide ? "max-w-[640px]" : "max-w-[520px]"}`}>
        <div className="mb-7 flex items-center gap-3">
          <Logo size="size-11" />
          <div>
            <h1 className="text-[22px] font-semibold tracking-[var(--tracking-display)]">clearsky</h1>
            <p className="text-[13px] text-muted">Straw pickup instead of stubble fires</p>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
