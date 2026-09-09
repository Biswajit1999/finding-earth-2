"use client";

import { motion, useReducedMotion } from "motion/react";

const lessons = [
  {
    number: "01",
    title: "The catalogue is shaped by the telescope",
    body: "A list of discoveries is not a census of the Galaxy. Transit geometry, observing windows, noise, pipeline recovery and vetting decide which planets become visible to us.",
  },
  {
    number: "02",
    title: "A value in a table is not always a measurement",
    body: "Masses and other parameters can be inferred, calculated by an archive, or copied through composite records. I learned to ask where every number came from before using it.",
  },
  {
    number: "03",
    title: "Earth-like is a bundle of separate questions",
    body: "Size, irradiation, composition, atmosphere, observability and biology require different evidence. Combining them too early creates confidence the observations do not support.",
  },
  {
    number: "04",
    title: "Uncertainty can change the shortlist",
    body: "A planet is better represented by a distribution than a point. Propagating published error bars exposes fragile ranks and prevents false precision.",
  },
  {
    number: "05",
    title: "A good control can break a beautiful metric",
    body: "Venus looks deceptively Earth-like to a bulk-property score. Running the Solar System through the same machinery reveals what the score cannot know.",
  },
  {
    number: "06",
    title: "The next observation is part of the answer",
    body: "A useful search should identify the measurement that would reduce uncertainty most, rather than ending with a static ranking.",
  },
] as const;

const terms = [
  ["Observed", "A value directly tied to an observation or published fit."],
  ["Derived", "A quantity calculated from observed inputs with a stated equation."],
  ["Model-inferred", "A value estimated through a model, prior or population relation."],
  ["Scenario", "A conditional result under deliberately chosen assumptions."],
  ["Forecast", "A prediction about what a future observation or mission could measure."],
  ["Simulated", "Artificial data used to test a pipeline or inference procedure."],
  ["Completeness", "The chance a real signal in a defined survey domain would be recovered and selected."],
  ["Reliability", "The fraction of selected candidates expected to be genuine rather than false alarms."],
  ["Habitable zone", "A model-dependent irradiation range where surface liquid water may be possible under specified atmospheric assumptions."],
  ["Occurrence rate", "The inferred average number of planets per star in an explicitly defined population domain."],
  ["Evidence graph", "The project’s map from a claim back through quantities, models, measurements and sources."],
  ["Earth 2.0 index", "A transparent prioritisation score. It is not a probability of habitability or life."],
] as const;

export function LearningJourney() {
  const reduced = useReducedMotion();
  const reveal = reduced
    ? { initial: false as const, whileInView: undefined }
    : { initial: { opacity: 0, y: 18 }, whileInView: { opacity: 1, y: 0 } };

  return (
    <>
      <section aria-labelledby="lessons-title" className="border-y border-[var(--color-line)] bg-[var(--color-deep)]">
        <div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
          <div className="max-w-3xl">
            <p className="eyebrow text-[var(--color-cyan)]">Learning log</p>
            <h2 id="lessons-title" className="mt-3 text-[length:var(--text-display)] font-light leading-tight">
              Six ideas that changed how I read exoplanet data
            </h2>
          </div>
          <div className="mt-12 grid gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-line)] md:grid-cols-2 xl:grid-cols-3">
            {lessons.map((lesson, index) => (
              <motion.article
                key={lesson.number}
                {...reveal}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.38, delay: reduced ? 0 : (index % 3) * 0.05 }}
                className="group min-h-64 bg-[var(--color-panel)] p-7 transition-colors hover:bg-[var(--color-raised)]"
              >
                <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--color-gold)]">{lesson.number}</p>
                <h3 className="mt-12 max-w-[18ch] font-[family-name:var(--font-display)] text-xl font-medium leading-tight text-[var(--color-ivory)]">
                  {lesson.title}
                </h3>
                <p className="mt-4 max-w-[40ch] text-[13px] leading-relaxed text-[var(--color-muted)]">{lesson.body}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="dictionary-title" className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="lg:sticky lg:top-24 lg:self-start">
            <p className="eyebrow text-[var(--color-gold)]">Research dictionary</p>
            <h2 id="dictionary-title" className="mt-3 text-[length:var(--text-title)] font-light">
              The words I needed to keep straight
            </h2>
            <p className="mt-5 max-w-[46ch] text-sm leading-relaxed text-[var(--color-dim)]">
              This dictionary is part of the method. Each label limits what a number is allowed to claim, from a direct observation to a conditional forecast.
            </p>
          </div>
          <dl className="divide-y divide-[var(--color-line)] border-y border-[var(--color-line)]">
            {terms.map(([term, definition], index) => (
              <motion.div
                key={term}
                {...reveal}
                viewport={{ once: true, amount: 0.45 }}
                transition={{ duration: 0.3, delay: reduced ? 0 : Math.min(index * 0.015, 0.12) }}
                className="grid gap-2 py-5 sm:grid-cols-[11rem_1fr] sm:gap-6"
              >
                <dt className="font-[family-name:var(--font-mono)] text-[12px] uppercase tracking-[0.12em] text-[var(--color-ivory)]">{term}</dt>
                <dd className="max-w-[68ch] text-sm leading-relaxed text-[var(--color-muted)]">{definition}</dd>
              </motion.div>
            ))}
          </dl>
        </div>
      </section>
    </>
  );
}
