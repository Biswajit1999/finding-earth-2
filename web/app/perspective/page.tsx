import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/PageHeader";
import { LearningJourney } from "@/components/perspective/LearningJourney";
import { LiveDataPulse } from "@/components/perspective/LiveDataPulse";
import { getSummary } from "@/lib/data";

export const metadata: Metadata = {
  title: "Beyond Earth 2.0 — An Author’s Perspective",
  description: "Biswajit Jana’s learning log, research dictionary, author conclusion and forward-looking questions from building Finding Earth 2.0.",
};

export default function PerspectivePage() {
  const summary = getSummary();
  return (
    <>
      <PageHeader
        eyebrow="Author perspective · hypotheses and questions, not observational conclusions · Biswajit Jana"
        title="Beyond Earth 2.0 — An Author’s Perspective"
        lede="I began with a simple question and built a reproducible research system around it. The deeper lesson was that finding another Earth is less about sorting a catalogue and more about learning exactly what each observation can—and cannot—tell us."
        meta={`${summary.scale.total_source_records.toLocaleString("en-GB")} source records · ${summary.population.n_confirmed_planets.toLocaleString("en-GB")} confirmed planets · every claim labelled by evidence type`}
      />

      <main>
        <section className="mx-auto grid max-w-[1400px] gap-10 px-4 py-20 sm:px-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="eyebrow text-[var(--color-gold)]">Why I built it</p>
            <h2 className="mt-3 max-w-[18ch] text-[length:var(--text-display)] font-light leading-tight">A question became a way of thinking</h2>
          </div>
          <div className="space-y-5 text-[15px] leading-relaxed text-[var(--color-dim)]">
            <p>I wanted to know which known world comes closest to Earth. At first that sounded like a ranking problem. Building the pipeline showed me that it is really an evidence problem: the catalogue mixes observations, derived quantities, model estimates and missing uncertainty.</p>
            <p>So I built more than a score. I built a source trail, uncertainty propagation, Solar-System controls, observable-specific laboratories and a growing dictionary that forces me to name what kind of claim I am making.</p>
            <p>The project now asks a better question: given how our surveys select what we see, what does the evidence imply about the population beyond the visible catalogue—and which observation would teach us the most next? Reconstructing the Kepler DR25 selection function made that lesson quantitative.</p>
          </div>
        </section>

        <LearningJourney />

        <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]">
          <div className="mx-auto grid max-w-[1400px] gap-10 px-4 py-20 sm:px-6 lg:grid-cols-[.8fr_1.2fr]">
            <div><p className="eyebrow text-[var(--color-gold)]">Author perspective</p><h2 className="mt-3 text-[length:var(--text-display)] font-light">Questions I carry forward</h2><p className="mt-5 text-xs leading-relaxed text-[var(--color-muted)]">These are my hypotheses, values and open questions. They are not NASA or ESA conclusions and they are not outputs of the candidate model.</p></div>
            <div className="grid gap-3 sm:grid-cols-2">{[
              "Is finding a physically compatible world enough—or only the start?",
              "Should humanity transmit, listen, or decide through a wider public process?",
              "What message could remain intelligible after a century of delay?",
              "Could autonomous probes make exploration more realistic than human travel?",
              "How would relativistic time change the human meaning of a journey?",
              "What would evidence of another civilisation ask humanity to become?",
            ].map((question) => <article key={question} className="panel-raised p-5 text-sm leading-relaxed text-[var(--color-dim)]">{question}</article>)}</div>
          </div>
        </section>

        <section className="mx-auto max-w-[1400px] px-4 pb-20 sm:px-6">
          <LiveDataPulse records={summary.scale.total_source_records} planets={summary.population.n_confirmed_planets} generated={summary.generated_utc} />
        </section>

        <section className="border-t border-[var(--color-line)] bg-[var(--color-deep)]">
          <div className="mx-auto max-w-[1400px] px-4 py-24 sm:px-6">
            <p className="eyebrow text-[var(--color-gold)]">Author conclusion</p>
            <blockquote className="mt-6 max-w-5xl font-[family-name:var(--font-display)] text-3xl font-light leading-[1.25] text-[var(--color-ivory)] sm:text-4xl">
              “I did not find a second Earth. I learned how difficult it is to earn that conclusion—and built a system that makes every step of the search inspectable.”
            </blockquote>
            <p className="mt-8 max-w-[70ch] text-sm leading-relaxed text-[var(--color-muted)]">The most honest result is not a winner. It is a map of what humanity has measured, what the models add, where the selection effects hide, and what evidence is still missing. That map can improve as the archives grow.</p>
            <div className="mt-8 flex flex-wrap gap-5 text-sm">
              <Link href="/research" className="link">Read the research article →</Link>
              <Link href="/methods" className="link">Inspect the methods →</Link>
              <Link href="/occurrence" className="link">See observed become intrinsic →</Link>
              <Link href="/universe" className="link">Explore the discovery universe →</Link>
              <Link href="/beyond" className="link">Calculate distance and contact →</Link>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
