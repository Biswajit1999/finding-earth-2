import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { PopulationLens } from "@/components/observatory/PopulationLens";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Population Inference", description: "Observed Kepler DR25 candidates and the conditional intrinsic planet occurrence posterior, kept visibly separate." };

export default function PopulationPage() {
  const data = getObservatory().population;
  const rate = data.intrinsic_posterior.full_fixed_box;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · population" title="The catalogue is the visible tip" lede="Finding Earth 2.0 reconstructs the selection that shaped Kepler DR25, then asks which intrinsic population is consistent with the signals that survived." meta="Fixed domain · selected GK dwarfs · reliability and completeness propagated" label="MODEL-INFERRED" stats={[
    { value: data.funnel[0].value.toLocaleString("en-GB"), label: "selected target stars", sub: "survey denominator" },
    { value: data.funnel[1].value.toLocaleString("en-GB"), label: "catalogue candidates", sub: "observed entries" },
    { value: data.funnel[3].value.toFixed(1), label: "effective stars", sub: "selection-corrected exposure" },
    { value: rate.p50.toFixed(3), label: "planets per star", sub: `${rate.p16.toFixed(3)}–${rate.p84.toFixed(3)} (16–84%)` },
  ]} findingTitle="Detection losses dominate near an Earth-like orbit" finding={<p>The difference between a catalogue count and a population estimate is the missing part of the survey: geometric transits that never occur, phases that were not observed, signals the pipeline misses, candidates rejected by vetting, and remaining false-alarm uncertainty. Reversing that chain produces a broad posterior rather than a single corrected count.</p>} interpretation={data.claim_boundary} figure="/figures/v2/observed-intrinsic.png" figureAlt="Observed Kepler DR25 candidate funnel compared with the inferred intrinsic occurrence posterior" figureCaption="OBSERVED and DERIVED survey counts lead to a MODEL-INFERRED fixed-box occurrence posterior. The labels are part of the result." methodsHref="/occurrence">
    <PopulationLens funnel={data.funnel} posterior={rate} />
  </ObservatoryChapter>;
}

