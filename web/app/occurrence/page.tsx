import type { Metadata } from "next";
import Link from "next/link";

import { OccurrenceStory } from "@/components/occurrence/OccurrenceStory";
import { PageHeader } from "@/components/PageHeader";
import { getOccurrenceStory } from "@/lib/data";

export const metadata: Metadata = {
  title: "Observed to Intrinsic",
  description:
    "An interactive, evidence-labelled account of how the Kepler DR25 catalogue becomes a conditional intrinsic occurrence posterior.",
};

export default function OccurrencePage() {
  const story = getOccurrenceStory();
  const domain = story.domain;

  return (
    <>
      <PageHeader
        eyebrow="Kepler DR25 · observed to intrinsic"
        title={story.title}
        lede="A catalogue records what a telescope could see. To ask how common small, long-period planets may be, I had to reconstruct the selection process, account for unreliable candidates and carry those uncertainties into a population model."
        meta={`${domain.period_min_days}–${domain.period_max_days} days · ${domain.radius_min_earth}–${domain.radius_max_earth} Earth radii · conditional on the selected GK-dwarf sample`}
      >
        <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <Link href="/methods" className="link">
            Inspect the equations →
          </Link>
          <Link href="/limitations" className="link">
            Read the claim limits →
          </Link>
          <a
            href="https://github.com/Biswajit1999/finding-earth-2/tree/main/results/population"
            className="link"
            target="_blank"
            rel="noreferrer noopener"
          >
            Download the research products ↗
          </a>
        </div>
      </PageHeader>

      <OccurrenceStory bundled={story} />

      <section className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="grid gap-10 border-l border-[var(--color-line-strong)] pl-6 lg:grid-cols-[0.7fr_1.3fr] lg:pl-10">
          <div>
            <p className="eyebrow text-[var(--color-gold)]">What I learned</p>
            <h2 className="mt-3 text-[length:var(--text-title)] font-light leading-tight">
              The missing planets are part of the result
            </h2>
          </div>
          <div className="space-y-4 text-[15px] leading-relaxed text-[var(--color-dim)]">
            <p>
              I used to read a planet catalogue as if it were a map of what exists.
              This analysis taught me to read it as the output of an instrument,
              an observing schedule, a detection pipeline and a human-designed
              vetting process.
            </p>
            <p>
              The posterior is broad because the data are genuinely weak near an
              Earth-like period and radius. Keeping that width visible is part of
              the finding. It tells me where a future survey can add the most
              knowledge.
            </p>
            <Link href="/perspective" className="link inline-block text-sm">
              Continue to my research dictionary and conclusion →
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
