"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";

/**
 * Navigation grouped by what a reader is trying to do, not by page count.
 * Nine top-level destinations would be a wall; three named groups plus the
 * article is navigable.
 */
const GROUPS: { label: string; items: { href: string; label: string; hint: string }[] }[] = [
  {
    label: "Explore",
    items: [
      { href: "/universe", label: "Universe", hint: "3D map of every system with a measured distance" },
      { href: "/galaxy", label: "Galaxy", hint: "Where the Sun sits in the Milky Way, and how far we've reached" },
      { href: "/atlas", label: "Candidate Atlas", hint: "Filter and sort the full analysed catalogue" },
      { href: "/ranking", label: "Ranking", hint: "Re-weight the composite index yourself" },
      { href: "/compare", label: "Compare Worlds", hint: "Put candidates side by side" },
    ],
  },
  {
    label: "Laboratories",
    items: [
      { href: "/spectral-lab", label: "Spectral Lab", hint: "Published atmospheric spectra" },
      { href: "/transit-lab", label: "Transit Lab", hint: "Light curves and fitted transits" },
      { href: "/rv-lab", label: "RV Lab", hint: "Radial velocities and activity cross-checks" },
      { href: "/follow-up", label: "Follow-up Lab", hint: "Compare observation-readiness pathways" },
    ],
  },
  {
    label: "Method",
    items: [
      { href: "/methods", label: "Methods", hint: "Equations, assumptions, citations" },
      { href: "/data", label: "Data", hint: "Archives, queries, provenance" },
      { href: "/limitations", label: "Limitations", hint: "What this cannot establish" },
      { href: "/references", label: "References", hint: "Full bibliography" },
    ],
  },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close menus on navigation: synchronizing to the router's pathname, an
  // external signal, not deriving state from a prop this component owns.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOpen(null);
    setMobileOpen(false);
  }, [pathname]);

  // Escape closes any open menu.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(null);
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-line)] bg-[var(--color-void)]/88 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-2 px-4 sm:px-6">
        <Link
          href="/"
          className="group flex shrink-0 items-baseline gap-2"
          aria-label="Finding Earth 2.0 — home"
        >
          <span
            aria-hidden
            className="inline-block size-[7px] rounded-full bg-[var(--color-gold)] transition-transform duration-300 group-hover:scale-125"
          />
          <span className="font-[family-name:var(--font-display)] text-[15px] font-medium tracking-tight">
            Finding Earth 2.0
          </span>
        </Link>

        {/* ---------- desktop navigation ---------- */}
        <nav aria-label="Main" className="ml-4 hidden items-center gap-1 lg:flex">
          {GROUPS.map((g) => (
            <div
              key={g.label}
              className="relative"
              onMouseEnter={() => setOpen(g.label)}
              onMouseLeave={() => setOpen(null)}
            >
              <button
                type="button"
                aria-expanded={open === g.label}
                aria-haspopup="true"
                onClick={() => setOpen(open === g.label ? null : g.label)}
                className={`cursor-pointer rounded px-3 py-1.5 text-[13px] transition-colors ${
                  g.items.some((i) => isActive(i.href))
                    ? "text-[var(--color-ivory)]"
                    : "text-[var(--color-dim)] hover:text-[var(--color-ivory)]"
                }`}
              >
                {g.label}
                <span aria-hidden className="ml-1.5 text-[9px] text-[var(--color-muted)]">
                  ▾
                </span>
              </button>

              {open === g.label && (
                <div className="absolute left-0 top-full w-[300px] pt-1">
                  <ul className="panel-raised overflow-hidden py-1 shadow-2xl shadow-black/60">
                    {g.items.map((i) => (
                      <li key={i.href}>
                        <Link
                          href={i.href}
                          className={`block px-3 py-2 transition-colors hover:bg-[var(--color-panel)] ${
                            isActive(i.href) ? "bg-[var(--color-panel)]" : ""
                          }`}
                        >
                          <span
                            className={`block text-[13px] ${
                              isActive(i.href)
                                ? "text-[var(--color-cyan)]"
                                : "text-[var(--color-ivory)]"
                            }`}
                          >
                            {i.label}
                          </span>
                          <span className="mt-0.5 block text-[11px] leading-snug text-[var(--color-muted)]">
                            {i.hint}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}

          <Link
            href="/research"
            className={`cursor-pointer rounded px-3 py-1.5 text-[13px] transition-colors ${
              isActive("/research")
                ? "text-[var(--color-ivory)]"
                : "text-[var(--color-dim)] hover:text-[var(--color-ivory)]"
            }`}
          >
            Research article
          </Link>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />

          <a
            href="https://github.com/Biswajit1999/finding-earth-2"
            target="_blank"
            rel="noreferrer noopener"
            className="hidden cursor-pointer rounded border border-[var(--color-line-strong)] px-2.5 py-1 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-dim)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)] sm:block"
          >
            Source
          </a>

          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            className="cursor-pointer rounded border border-[var(--color-line-strong)] px-2.5 py-1.5 text-[11px] text-[var(--color-dim)] lg:hidden"
          >
            {mobileOpen ? "Close" : "Menu"}
          </button>
        </div>
      </div>

      {/* ---------- mobile navigation ---------- */}
      {mobileOpen && (
        <nav
          id="mobile-nav"
          aria-label="Main"
          className="max-h-[calc(100dvh-3.5rem)] overflow-y-auto border-t border-[var(--color-line)] bg-[var(--color-deep)] px-4 py-3 lg:hidden"
        >
          {GROUPS.map((g) => (
            <div key={g.label} className="mb-4">
              <p className="eyebrow mb-1.5">{g.label}</p>
              <ul>
                {g.items.map((i) => (
                  <li key={i.href}>
                    <Link
                      href={i.href}
                      className={`block border-b border-[var(--color-line)] py-2 text-[14px] ${
                        isActive(i.href)
                          ? "text-[var(--color-cyan)]"
                          : "text-[var(--color-ivory)]"
                      }`}
                    >
                      {i.label}
                      <span className="mt-0.5 block text-[11px] text-[var(--color-muted)]">
                        {i.hint}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <Link
            href="/research"
            className="block py-2 text-[14px] text-[var(--color-ivory)]"
          >
            Research article
          </Link>
          <Link href="/about" className="block py-2 text-[14px] text-[var(--color-ivory)]">
            About
          </Link>
        </nav>
      )}
    </header>
  );
}
