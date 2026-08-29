"use client";

/**
 * The opening.
 *
 * The thesis of the hero is that this is a real dataset, not an illustration.
 * The field behind the title is the actual exported catalogue of systems with
 * measured distances, and the counts that appear are read from the same file
 * the rest of the site uses.
 *
 * Motion is restrained and gated on prefers-reduced-motion: the field stops
 * rotating, the count-up resolves immediately, and the WebGL canvas is replaced
 * by a static render.
 */

import { Canvas } from "@react-three/fiber";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";

import { StarField } from "@/components/three/StarField";
import type { SummaryFile, UniverseFile } from "@/lib/types";
import { compactInt } from "@/lib/format";

function useCountUp(target: number, enabled: boolean, duration = 1400) {
  const [value, setValue] = useState(enabled ? 0 : target);

  useEffect(() => {
    if (!enabled) {
      // Synchronizing to an external signal (the OS-level prefers-reduced-motion
      // media query, via useReducedMotion()), not deriving state from a prop --
      // the value must jump to its resolved target the moment that preference
      // changes, which cannot be expressed as a plain render-time computation.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setValue(target);
      return;
    }

    // No "already started" ref guard here, deliberately. StrictMode invokes
    // effects twice in development: a latched ref would be set on the first
    // pass, the cleanup would cancel that frame, and the second pass would
    // return early without scheduling a new one -- leaving every counter frozen
    // at zero. Re-running the animation is harmless; never running it is not.
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / duration);
      setValue(Math.round(target * (1 - Math.pow(1 - t, 3)))); // ease-out cubic
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    // Safety net: if rAF never fires (a backgrounded or non-compositing tab),
    // resolve to the true value rather than leaving a zero on screen. A wrong
    // number is worse than an unanimated one.
    const settle = window.setTimeout(() => setValue(target), duration + 400);

    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(settle);
    };
  }, [target, enabled, duration]);

  return value;
}

function Stat({
  value,
  label,
  sub,
  animate,
  delay,
}: {
  value: number;
  label: string;
  sub: string;
  animate: boolean;
  delay: number;
}) {
  const shown = useCountUp(value, animate);
  return (
    <motion.div
      initial={animate ? { opacity: 0, y: 12 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
      className="border-l border-[var(--color-line-strong)] pl-3.5"
    >
      <p className="font-[family-name:var(--font-mono)] text-[1.55rem] leading-none tabular-nums text-[var(--color-ivory)] sm:text-[1.9rem]">
        {compactInt(shown)}
      </p>
      <p className="mt-1.5 text-[12px] font-medium leading-tight text-[var(--color-dim)]">
        {label}
      </p>
      <p className="mt-0.5 text-[11px] leading-tight text-[var(--color-muted)]">{sub}</p>
    </motion.div>
  );
}

export function Hero({
  summary,
  universe,
}: {
  summary: SummaryFile;
  universe: UniverseFile;
}) {
  const reduced = useReducedMotion();
  const animate = !reduced;
  const [webglFailed, setWebglFailed] = useState(false);

  const hz = summary.habitable_zone;
  const nSmallHz = Number(hz["n_conservative_hz_and_below_1p6_re"] ?? 0);
  const nSmallHzMeasured = Number(
    hz["n_conservative_hz_and_below_1p6_re_with_measured_mass"] ?? 0,
  );

  return (
    <section className="relative isolate overflow-hidden border-b border-[var(--color-line)]">
      {/* ---------- the real sky ---------- */}
      <div className="absolute inset-0 -z-10" aria-hidden>
        {!webglFailed && (
          <Canvas
            camera={{ position: [0, 0.55, 3.4], fov: 52 }}
            dpr={[1, 1.75]}
            gl={{ antialias: true, powerPreference: "high-performance" }}
            onCreated={({ gl }) => {
              gl.setClearColor("#07090e", 1);
            }}
            onError={() => setWebglFailed(true)}
            frameloop={reduced ? "demand" : "always"}
          >
            <Suspense fallback={null}>
              <StarField
                data={universe}
                colourMode="index"
                rotate={!reduced}
                rotationSpeed={0.014}
                pointScale={1}
                brightness={1.65}
              />
            </Suspense>
          </Canvas>
        )}
        {/* Legibility scrim. The text must win over the field. */}
        <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-void)] via-[var(--color-void)]/80 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[var(--color-void)] to-transparent" />
      </div>

      <div className="mx-auto max-w-[1400px] px-4 pb-16 pt-20 sm:px-6 sm:pb-24 sm:pt-28 lg:pt-36">
        <motion.p
          initial={animate ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.7 }}
          className="eyebrow"
        >
          A reproducible search across the public astronomical archives
        </motion.p>

        <motion.h1
          initial={animate ? { opacity: 0, y: 18 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
          className="mt-4 max-w-[16ch] text-[length:var(--text-hero)] font-light leading-[0.94]"
        >
          Finding{" "}
          <span className="italic text-[var(--color-gold)]">Earth 2.0</span>
          <br />
          in distant worlds
        </motion.h1>

        <motion.p
          initial={animate ? { opacity: 0, y: 14 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-6 max-w-[54ch] text-[15px] leading-relaxed text-[var(--color-dim)] sm:text-base"
        >
          Searching distant worlds with real astronomical data. Every planet
          behind this text is a system with a measured distance, drawn at its
          true position on the sky. Nothing here is an illustration.
        </motion.p>

        {/* ---------- derived statistics ---------- */}
        <div className="mt-12 grid max-w-3xl grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-4">
          <Stat
            value={summary.population.n_confirmed_planets}
            label="confirmed planets"
            sub={`across ${compactInt(summary.population.n_unique_host_systems)} systems`}
            animate={animate}
            delay={0.3}
          />
          <Stat
            value={summary.scale.total_source_records}
            label="source records"
            sub={`${summary.scale.n_datasets_retrieved} archive tables`}
            animate={animate}
            delay={0.38}
          />
          <Stat
            value={Number(summary.atmosphere["transmission_measurement_rows"] ?? 0)}
            label="spectral measurements"
            sub={`${summary.atmosphere["planets_with_transmission_spectra"]} planets with spectra`}
            animate={animate}
            delay={0.46}
          />
          <Stat
            value={Number(hz["n_in_conservative_hz_nominal"] ?? 0)}
            label="in the conservative HZ"
            sub={`${compactInt(Number(hz["n_in_optimistic_hz_nominal"] ?? 0))} optimistic`}
            animate={animate}
            delay={0.54}
          />
        </div>

        {/* ---------- the finding ---------- */}
        <motion.div
          initial={animate ? { opacity: 0, y: 16 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.68 }}
          className="mt-12 max-w-2xl border-l-2 border-[var(--color-gold)] py-1 pl-5"
        >
          <p className="text-[15px] leading-relaxed text-[var(--color-ivory)]">
            Of {compactInt(summary.population.n_confirmed_planets)} confirmed
            planets, only{" "}
            <strong className="font-[family-name:var(--font-mono)] text-[var(--color-gold)]">
              {nSmallHz}
            </strong>{" "}
            are both inside the conservative habitable zone and small enough to be
            plausibly rocky — and only{" "}
            <strong className="font-[family-name:var(--font-mono)] text-[var(--color-gold)]">
              {nSmallHzMeasured}
            </strong>{" "}
            of those has a mass that was actually measured rather than predicted
            from its radius.
          </p>
          <p className="mt-2.5 text-[13px] leading-relaxed text-[var(--color-muted)]">
            The search is not limited by how many planets we know about. It is
            limited by how few we have measured well.
          </p>
        </motion.div>

        <motion.div
          initial={animate ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.82 }}
          className="mt-10 flex flex-wrap items-center gap-3"
        >
          <Link
            href="/atlas"
            className="cursor-pointer rounded-[var(--radius-md)] bg-[var(--color-ivory)] px-5 py-2.5 text-[13px] font-medium text-[var(--color-void)] transition-opacity hover:opacity-88"
          >
            Explore the catalogue
          </Link>
          <Link
            href="/research"
            className="cursor-pointer rounded-[var(--radius-md)] border border-[var(--color-line-strong)] px-5 py-2.5 text-[13px] text-[var(--color-ivory)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
          >
            Read the research
          </Link>
          <Link
            href="/universe"
            className="cursor-pointer px-2 py-2.5 text-[13px] text-[var(--color-dim)] underline decoration-[var(--color-line-strong)] underline-offset-4 transition-colors hover:text-[var(--color-cyan)]"
          >
            Open the 3D map →
          </Link>
        </motion.div>

        <p className="mt-8 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-faint)]">
          {compactInt(universe.n_points)} systems rendered ·{" "}
          {compactInt(universe.n_excluded_no_distance)} excluded for having no
          measured distance · radial axis log-compressed
        </p>
      </div>
    </section>
  );
}
