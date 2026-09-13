"use client";

import { motion, useReducedMotion } from "motion/react";

const horizons = [
  {
    code: "01 · CONTINUOUS",
    title: "Keep the evidence alive",
    body: "Refresh public archives on schedule, preserve every source hash, and publish clear diffs when the catalogue or a conclusion changes.",
    signal: "Archive updates → validated releases",
  },
  {
    code: "02 · NEXT MODEL",
    title: "Connect the uncertainties",
    body: "Build joint stellar-and-planet posteriors, add instrument likelihoods and compare information gain per unit of observing time.",
    signal: "Separate errors → joint decisions",
  },
  {
    code: "03 · NEXT EVIDENCE",
    title: "Move closer to atmospheres",
    body: "Add target-specific ephemerides, XUV histories and retrieval evidence while keeping reductions and natural alternatives attached.",
    signal: "Scenarios → testable evidence",
  },
  {
    code: "04 · LONG HORIZON",
    title: "Grow with new observatories",
    body: "Version adapters for Gaia DR4, PLATO, Roman, ELT and HWO products only when public data exist, then revisit distant-world and contact limits.",
    signal: "Forecasts → observations",
  },
] as const;

export function FutureRoadmap() {
  const reduced = useReducedMotion();

  return (
    <section
      id="future-roadmap"
      aria-labelledby="future-roadmap-title"
      className="future-roadmap relative overflow-hidden border-y border-[var(--color-line)]"
    >
      <div className="future-grid" aria-hidden />
      <div className="mx-auto grid max-w-[1400px] gap-12 px-4 py-24 sm:px-6 lg:grid-cols-[0.78fr_1.22fr] lg:items-start">
        <div className="relative lg:sticky lg:top-28">
          <p className="eyebrow text-[var(--color-cyan)]">Author roadmap · living project</p>
          <h2
            id="future-roadmap-title"
            className="mt-3 max-w-[13ch] text-[length:var(--text-display)] font-light leading-[1.02]"
          >
            What I plan to build next
          </h2>
          <p className="mt-6 max-w-[48ch] text-sm leading-relaxed text-[var(--color-dim)]">
            The next version should earn more confidence, not add a more confident score. My plan is to shorten the path from a changing archive record to a reproducible decision about the next useful observation.
          </p>

          <div className="relative mt-10 h-52 w-52" aria-hidden>
            <motion.div
              className="future-orbit future-orbit-outer"
              animate={reduced ? undefined : { rotate: 360 }}
              transition={{ duration: 28, ease: "linear", repeat: Infinity }}
            />
            <motion.div
              className="future-orbit future-orbit-inner"
              animate={reduced ? undefined : { rotate: -360 }}
              transition={{ duration: 19, ease: "linear", repeat: Infinity }}
            />
            <div className="future-core">
              <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.2em] text-[var(--color-muted)]">NORTH STAR</span>
              <strong className="mt-1 text-sm font-medium text-[var(--color-ivory)]">Better evidence</strong>
            </div>
          </div>
        </div>

        <div className="relative">
          <motion.div
            className="future-beam"
            initial={reduced ? false : { scaleY: 0 }}
            whileInView={reduced ? undefined : { scaleY: 1 }}
            viewport={{ once: true, amount: 0.15 }}
            transition={{ duration: 1.15, ease: [0.22, 1, 0.36, 1] }}
            aria-hidden
          />
          <div className="space-y-4">
            {horizons.map((item, index) => (
              <motion.article
                key={item.code}
                initial={reduced ? false : { opacity: 0, x: 24 }}
                whileInView={reduced ? undefined : { opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.35 }}
                transition={{ duration: 0.5, delay: index * 0.06 }}
                className="future-card group relative ml-7 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line)] p-6 sm:p-7"
              >
                <span className="future-node" aria-hidden />
                <div className="grid gap-5 sm:grid-cols-[9rem_1fr]">
                  <div>
                    <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] text-[var(--color-gold)]">
                      {item.code}
                    </p>
                    <p className="mt-3 font-[family-name:var(--font-mono)] text-[10px] leading-relaxed text-[var(--color-muted)]">
                      {item.signal}
                    </p>
                  </div>
                  <div>
                    <h3 className="font-[family-name:var(--font-display)] text-2xl font-light text-[var(--color-ivory)]">
                      {item.title}
                    </h3>
                    <p className="mt-3 max-w-[58ch] text-sm leading-relaxed text-[var(--color-dim)]">
                      {item.body}
                    </p>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
