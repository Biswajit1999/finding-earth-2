"use client";

import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";

const chapters = [
  ["01", "Population", "/population", "Observed counts → intrinsic posterior"],
  ["02", "Selection", "/selection", "What Kepler could detect"],
  ["03", "Climate", "/climate", "A habitable zone through time"],
  ["04", "Stellar environment", "/stellar-environment", "UV, XUV and escape scenarios"],
  ["05", "Atmospheres", "/atmospheres", "Measurements, reductions, scenarios"],
  ["06", "HWO atlas", "/hwo", "Direct-imaging trade cases"],
  ["07", "Missions", "/missions", "Six instruments, six evidence views"],
  ["08", "Information gain", "/information-gain", "What to measure next"],
  ["09", "Sensitivity", "/model-sensitivity", "How assumptions move the answer"],
  ["10", "Falsification", "/falsification", "Where the model fails"],
  ["11", "Evidence graph", "/evidence", "Every number back to source"],
] as const;

export function ObservatoryIndex() {
  const reduced = useReducedMotion();
  return (
    <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]" aria-labelledby="observatory-index-title">
      <div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
          <div className="lg:sticky lg:top-24 lg:self-start">
            <p className="eyebrow text-[var(--color-cyan)]">Exoearth Evidence Observatory</p>
            <h2 id="observatory-index-title" className="mt-3 max-w-[15ch] text-[length:var(--text-display)] font-light leading-[1.04]">The research, opened into eleven rooms</h2>
            <p className="mt-5 max-w-[52ch] text-sm leading-relaxed text-[var(--color-dim)]">The story now moves from what humanity detected, through the instruments and models that shape those detections, to the experiment that would reduce uncertainty next. Every room keeps observations, inference, scenarios and forecasts visibly separate.</p>
            <Link href="/perspective" className="link mt-6 inline-block text-sm">Read what I learned while building it →</Link>
          </div>
          <div className="grid gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-line)] sm:grid-cols-2">
            {chapters.map(([number, title, href, body], index) => (
              <motion.div key={href} initial={reduced ? false : { opacity: 0, y: 14 }} whileInView={reduced ? undefined : { opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.35 }} transition={{ duration: 0.34, delay: reduced ? 0 : (index % 2) * 0.04 }}>
                <Link href={href} className="group flex min-h-36 h-full items-start gap-5 bg-[var(--color-panel)] p-5 transition-colors hover:bg-[var(--color-raised)] focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-cyan)]">
                  <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-gold)]">{number}</span>
                  <span><span className="block text-base text-[var(--color-ivory)] transition-colors group-hover:text-[var(--color-cyan)]">{title}</span><span className="mt-2 block text-xs leading-relaxed text-[var(--color-muted)]">{body}</span><span aria-hidden className="mt-5 block text-xs text-[var(--color-cyan)] opacity-0 transition-opacity group-hover:opacity-100">Enter room →</span></span>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

