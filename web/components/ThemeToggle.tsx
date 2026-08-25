"use client";

import { useEffect, useState } from "react";

/**
 * Sun/moon toggle between the site's two readings of the same design
 * tokens (see globals.css). Starts in the "dark" visual state on every
 * render so server and client markup match on hydration, then syncs to
 * whatever the anti-FOUC script in the root layout already applied to
 * <html> a frame earlier -- this can only run after mount, since
 * `document` doesn't exist during the static-export prerender pass.
 */
export function ThemeToggle() {
  const [isLight, setIsLight] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLight(document.documentElement.getAttribute("data-theme") === "light");
  }, []);

  const toggle = () => {
    const next = !isLight;
    setIsLight(next);
    if (next) {
      document.documentElement.setAttribute("data-theme", "light");
      localStorage.setItem("theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("theme", "dark");
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
      title={isLight ? "Switch to dark mode" : "Switch to light mode"}
      className="cursor-pointer rounded border border-[var(--color-line-strong)] p-1.5 text-[var(--color-dim)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
    >
      {isLight ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"
            stroke="currentColor"
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth={1.8} />
          <path
            d="M12 2v2.5M12 19.5V22M4.22 4.22l1.77 1.77M18.01 18.01l1.77 1.77M2 12h2.5M19.5 12H22M4.22 19.78l1.77-1.77M18.01 5.99l1.77-1.77"
            stroke="currentColor"
            strokeWidth={1.8}
            strokeLinecap="round"
          />
        </svg>
      )}
    </button>
  );
}
