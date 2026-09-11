"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useMemo, useState } from "react";

import type { OccurrenceStory as OccurrenceStoryData } from "@/lib/types";

const LATEST =
  "https://raw.githubusercontent.com/Biswajit1999/finding-earth-2/main/web/public/data/occurrence.json";

const stageTone = ["var(--color-ivory)", "var(--color-gold)", "var(--color-cyan)", "#9ee493"];

function readable(value: number, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("en-GB", { maximumFractionDigits }).format(value);
}

export function OccurrenceStory({ bundled }: { bundled: OccurrenceStoryData }) {
  const reduced = useReducedMotion();
  const [story, setStory] = useState(bundled);
  const [active, setActive] = useState(0);
  const [pulse, setPulse] = useState<"checking" | "current" | "updated" | "offline">("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${LATEST}?opened=${Date.now()}`, { cache: "no-store", signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Latest occurrence snapshot unavailable");
        return response.json() as Promise<OccurrenceStoryData>;
      })
      .then((latest) => {
        if (
          latest.schema_version !== "1.0" ||
          latest.label !== "OBSERVED + MODEL-INFERRED" ||
          !latest.source_hashes?.occurrence_posterior
        ) {
          throw new Error("Latest occurrence snapshot failed its browser schema gate");
        }
        const changed =
          latest.source_hashes.occurrence_posterior !==
          bundled.source_hashes.occurrence_posterior;
        if (changed) setStory(latest);
        setPulse(changed ? "updated" : "current");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setPulse("offline");
      });
    return () => controller.abort();
  }, [bundled]);

  const rate = story.intrinsic_posterior.full_fixed_box;
  const stages = story.story_steps;
  const activeStep = stages[active];
  const posteriorCards = [
    {
      value: story.intrinsic_posterior.gamma_earth_per_dlnp_dlnr.p50,
      title: "Gamma Earth",
      note: "per selected star per d ln P d ln R at the Earth pivot",
    },
    {
      value: story.intrinsic_posterior.hsu_box_projection.p50,
      title: "Hsu fixed-box projection",
      note: "237–500 days · 0.75–1.5 Earth radii",
    },
    {
      value: story.intrinsic_posterior.earth_20_percent_box_projection.p50,
      title: "Earth ±20% projection",
      note: "fixed period and radius · not a habitable-zone rate",
    },
  ];
  const pulseLabel =
    pulse === "checking"
      ? "Checking the newest verified posterior…"
      : pulse === "updated"
        ? "Loaded a newer committed posterior"
        : pulse === "current"
          ? "Bundled posterior matches GitHub main"
          : "Live check unavailable · bundled verified posterior shown";

  const scaleCards = useMemo(
    () => [
      {
        value: readable(story.funnel[1].value, 0),
        title: "catalogue candidates",
        note: "what passed the observed KOI contract",
        label: "OBSERVED",
      },
      {
        value: readable(story.funnel[2].value, 1),
        title: "latent valid candidates",
        note: "mean after reliability + FPP imputation",
        label: "MODEL-INFERRED",
      },
      {
        value: readable(story.funnel[3].value, 1),
        title: "effective stars",
        note: "median exposure for the inferred shape",
        label: "MODEL-INFERRED",
      },
      {
        value: readable(rate.p50, 3),
        title: "planets per selected star",
        note: `${readable(rate.p025, 3)}–${readable(rate.p975, 3)} · 95% interval`,
        label: "MODEL-INFERRED",
      },
    ],
    [rate, story.funnel],
  );

  return (
    <>
      <section className="mx-auto max-w-[1400px] px-4 py-16 sm:px-6 sm:py-20">
        <div className="grid gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-line)] sm:grid-cols-2 xl:grid-cols-4">
          {scaleCards.map((card, index) => (
            <motion.article
              key={card.title}
              initial={reduced ? false : { opacity: 0, y: 16 }}
              whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.35, delay: reduced ? 0 : index * 0.05 }}
              className="min-h-52 bg-[var(--color-panel)] p-6"
            >
              <p className="eyebrow" style={{ color: stageTone[index] }}>{card.label}</p>
              <p className="mt-9 font-[family-name:var(--font-mono)] text-4xl font-light tabular-nums text-[var(--color-ivory)]">
                {card.value}
              </p>
              <h2 className="mt-3 text-sm font-semibold text-[var(--color-ivory)]">{card.title}</h2>
              <p className="mt-2 max-w-[28ch] text-xs leading-relaxed text-[var(--color-muted)]">{card.note}</p>
            </motion.article>
          ))}
        </div>
        <p className="mt-4 font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]" role="status" aria-live="polite">
          <span className={`mr-2 inline-block size-1.5 rounded-full ${pulse === "offline" ? "bg-[var(--color-gold)]" : "bg-[var(--color-cyan)]"}`} />
          {pulseLabel}
        </p>
      </section>

      <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]">
        <div className="mx-auto grid max-w-[1400px] gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[0.78fr_1.22fr]">
          <div>
            <p className="eyebrow text-[var(--color-gold)]">Selection lens</p>
            <h2 className="mt-3 max-w-[14ch] text-[length:var(--text-title)] font-light leading-tight">Four readings of the same survey</h2>
            <p className="mt-5 max-w-[46ch] text-sm leading-relaxed text-[var(--color-dim)]">
              Step through the reasoning. Each transition changes the question being asked, so every number keeps its evidence label and unit.
            </p>
            <div className="mt-8 grid gap-2" role="tablist" aria-label="Observed to intrinsic story">
              {stages.map((step, index) => (
                <button
                  key={step.number}
                  type="button"
                  role="tab"
                  id={`occurrence-tab-${index}`}
                  aria-controls="occurrence-story-panel"
                  aria-selected={active === index}
                  onClick={() => setActive(index)}
                  className={`grid cursor-pointer grid-cols-[2.5rem_1fr] items-center rounded-[var(--radius-sm)] border px-3 py-3 text-left transition-colors ${active === index ? "border-[var(--color-cyan)] bg-[var(--color-cyan)]/6" : "border-[var(--color-line)] hover:border-[var(--color-line-strong)]"}`}
                >
                  <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--color-cyan)]">{step.number}</span>
                  <span className="text-sm text-[var(--color-ivory)]">{step.title}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="relative min-h-[30rem] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line-strong)] bg-[var(--color-panel)] p-7 sm:p-10">
            <div aria-hidden className="absolute inset-0 opacity-40" style={{ background: "radial-gradient(circle at 75% 20%, color-mix(in srgb, var(--color-cyan) 18%, transparent), transparent 42%)" }} />
            <motion.div
              key={activeStep.number}
              initial={reduced ? false : { opacity: 0, x: 18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="relative flex h-full flex-col"
              role="tabpanel"
              id="occurrence-story-panel"
              aria-labelledby={`occurrence-tab-${active}`}
            >
              <p className="font-[family-name:var(--font-mono)] text-7xl font-light text-[var(--color-line-strong)] sm:text-8xl">{activeStep.number}</p>
              <div className="mt-auto pt-16">
                <p className="eyebrow text-[var(--color-cyan)]">Evidence changes meaning here</p>
                <h3 className="mt-3 max-w-[20ch] text-3xl font-light leading-tight text-[var(--color-ivory)]">{activeStep.title}</h3>
                <p className="mt-5 max-w-[58ch] text-[15px] leading-relaxed text-[var(--color-dim)]">{activeStep.body}</p>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="grid gap-8 lg:grid-cols-[1.35fr_0.65fr]">
          <figure className="panel overflow-hidden">
            {/* A pipeline-generated scientific figure; static export cannot use the image optimizer. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/figures/observed_vs_intrinsic.png`} alt="Three-panel Kepler DR25 figure showing catalogue candidates, the total selection surface, and the inferred intrinsic period-radius density" className="h-auto w-full" />
            <figcaption className="border-t border-[var(--color-line)] p-5 text-xs leading-relaxed text-[var(--color-muted)]">
              Candidate colour is reliability. The middle panel is total selection probability, including geometry and target-wise pipeline plus vetting response. The final panel shows relative intrinsic density at the median fitted slopes.
            </figcaption>
          </figure>
          <aside className="panel-raised p-6 sm:p-8">
            <p className="eyebrow text-[var(--color-gold)]">Earth-pivot visibility</p>
            <p className="mt-5 font-[family-name:var(--font-mono)] text-4xl tabular-nums text-[var(--color-ivory)]">
              1 / {readable(story.earth_pivot_visibility.one_selected_signal_per_stars, 0)}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-[var(--color-dim)]">
              Approximate selected-signal probability per searched star at 365.25 days and one Earth radius under this DR25 model.
            </p>
            <dl className="mt-8 divide-y divide-[var(--color-line)] border-y border-[var(--color-line)] text-xs">
              <div className="flex justify-between gap-5 py-3"><dt className="text-[var(--color-muted)]">Transit geometry</dt><dd className="font-[family-name:var(--font-mono)]">{(100 * story.earth_pivot_visibility.mean_transit_geometry).toFixed(3)}%</dd></div>
              <div className="flex justify-between gap-5 py-3"><dt className="text-[var(--color-muted)]">Phase window</dt><dd className="font-[family-name:var(--font-mono)]">{(100 * story.earth_pivot_visibility.mean_phase_window).toFixed(1)}%</dd></div>
              <div className="flex justify-between gap-5 py-3"><dt className="text-[var(--color-muted)]">Total selection</dt><dd className="font-[family-name:var(--font-mono)]">{(100 * story.earth_pivot_visibility.mean_total_selection).toFixed(4)}%</dd></div>
              <div className="flex justify-between gap-5 py-3"><dt className="text-[var(--color-muted)]">Effective stars</dt><dd className="font-[family-name:var(--font-mono)]">{story.earth_pivot_visibility.effective_stars.toFixed(2)}</dd></div>
            </dl>
            <p className="mt-5 text-[11px] leading-relaxed text-[var(--color-muted)]">The pipeline term already includes the observing window. The displayed average factors are diagnostics and are not multiplied together.</p>
          </aside>
        </div>
      </section>

      <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]">
        <div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
          <p className="eyebrow text-[var(--color-cyan)]">What the posterior can say</p>
          <div className="mt-8 grid gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-line)] md:grid-cols-3">
            {posteriorCards.map(({ value, title, note }, index) => (
              <motion.article
                key={title}
                initial={reduced ? false : { opacity: 0, scale: 0.98 }}
                whileInView={reduced ? undefined : { opacity: 1, scale: 1 }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ delay: reduced ? 0 : index * 0.06 }}
                className="bg-[var(--color-panel)] p-7"
              >
                <p className="font-[family-name:var(--font-mono)] text-3xl text-[var(--color-ivory)]">
                  {readable(value, 3)}
                </p>
                <h3 className="mt-4 text-sm font-semibold text-[var(--color-ivory)]">{title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-[var(--color-muted)]">{note}</p>
              </motion.article>
            ))}
          </div>
          <div className="mt-8 border-l-2 border-[var(--color-rose)] py-2 pl-5">
            <p className="eyebrow text-[var(--color-rose)]">Claim boundary</p>
            <p className="mt-2 max-w-[78ch] text-sm leading-relaxed text-[var(--color-dim)]">{story.claim_boundary}</p>
          </div>
        </div>
      </section>
    </>
  );
}
