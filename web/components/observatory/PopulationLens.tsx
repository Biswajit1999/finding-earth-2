"use client";

import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { EvidenceLabel } from "@/components/observatory/EvidenceLabel";

interface PopulationProps {
  funnel: Array<{ stage: string; value: number; unit: string; label: string }>;
  posterior: { p16: number; p50: number; p84: number };
}

export function PopulationLens({ funnel, posterior }: PopulationProps) {
  const [view, setView] = useState<"observed" | "intrinsic">("observed");
  const reduced = useReducedMotion();
  const observed = funnel.filter((item) => item.label === "OBSERVED" || item.label === "DERIVED");

  return (
    <section className="mx-auto max-w-[1100px] px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="population-lens-title">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="eyebrow text-[var(--color-cyan)]">Observed / corrected lens</p>
          <h2 id="population-lens-title" className="mt-3 text-[length:var(--text-title)] font-light">One survey, two different questions</h2>
        </div>
        <div className="flex rounded-[var(--radius-md)] border border-[var(--color-line-strong)] p-1" role="group" aria-label="Population view">
          {(["observed", "intrinsic"] as const).map((item) => (
            <button key={item} type="button" aria-pressed={view === item} onClick={() => setView(item)} className={`min-h-10 cursor-pointer rounded-[var(--radius-sm)] px-4 text-xs capitalize transition-colors ${view === item ? "bg-[var(--color-cyan)]/15 text-[var(--color-cyan)]" : "text-[var(--color-muted)] hover:text-[var(--color-ivory)]"}`}>{item}</button>
          ))}
        </div>
      </div>
      <motion.div key={view} initial={reduced ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="mt-10 panel-raised p-6 sm:p-8">
        {view === "observed" ? (
          <>
            <div className="flex items-center justify-between"><h3 className="text-xl text-[var(--color-ivory)]">What entered the catalogue</h3><EvidenceLabel label="OBSERVED" /></div>
            <div className="mt-8 grid gap-px overflow-hidden rounded-[var(--radius-md)] bg-[var(--color-line)] sm:grid-cols-3">
              {observed.slice(0, 3).map((item) => (
                <div key={item.stage} className="bg-[var(--color-panel)] p-5"><p className="font-[family-name:var(--font-mono)] text-2xl text-[var(--color-ivory)]">{item.value.toLocaleString("en-GB", { maximumFractionDigits: 1 })}</p><p className="mt-2 text-xs text-[var(--color-muted)]">{item.stage.replaceAll("_", " ")} · {item.unit}</p></div>
              ))}
            </div>
            <p className="mt-6 text-sm leading-relaxed text-[var(--color-muted)]">These counts describe detected and reliability-adjusted signals in the declared DR25 sample. They retain the imprint of transit geometry, observing windows, pipeline recovery and vetting.</p>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between"><h3 className="text-xl text-[var(--color-ivory)]">What the selected sample implies</h3><EvidenceLabel label="MODEL-INFERRED" /></div>
            <p className="mt-8 font-[family-name:var(--font-mono)] text-5xl font-light tabular-nums text-[var(--color-gold)]">{posterior.p50.toFixed(3)}</p>
            <p className="mt-2 text-sm text-[var(--color-muted)]">planets per star · 16th–84th percentile {posterior.p16.toFixed(3)}–{posterior.p84.toFixed(3)}</p>
            <p className="mt-6 text-sm leading-relaxed text-[var(--color-muted)]">This posterior reverses the survey selection inside one fixed period–radius box. It is conditional on the target sample and model and is not a probability of habitability or life.</p>
          </>
        )}
      </motion.div>
    </section>
  );
}

