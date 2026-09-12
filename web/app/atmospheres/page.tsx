import type { Metadata } from "next";
import Link from "next/link";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Atmospheres", description: "Published transmission and eclipse measurements, separate reductions, and explicitly hypothetical scale-height scenarios." };

export default function AtmospheresPage() {
  const data = getObservatory().atmosphere;
  const evidence = data.spectrum_evidence;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · atmospheres" title="A spectrum is a reduction, not an atmosphere" lede="Published wavelength-dependent measurements remain attached to their facility, instrument, reference and reduction path. Clear-atmosphere scale heights are shown as scenarios and never mistaken for molecular detections." meta="Transmission + eclipse archives · reduction-preserving architecture · scenario calculator" label="OBSERVED" stats={[
    { value: Number(evidence.measurement_count).toLocaleString("en-GB"), label: "spectral points", sub: "published archive measurements" },
    { value: Number(evidence.transmission_measurements).toLocaleString("en-GB"), label: "transmission", sub: "measurement rows" },
    { value: Number(evidence.eclipse_measurements).toLocaleString("en-GB"), label: "eclipse", sub: "measurement rows" },
    { value: Number(evidence.reduction_count).toLocaleString("en-GB"), label: "separate reductions", sub: "never silently merged" },
  ]} findingTitle="Different reductions are evidence about uncertainty" finding={<div className="space-y-4"><p>When two teams reduce the same target differently, the disagreement is scientifically useful. The pipeline stores each reduction independently and computes overlap diagnostics without selecting a winner or averaging incompatible products.</p><Link href="/spectral-lab" className="link inline-block">Open the real spectral measurements →</Link></div>} interpretation={String(evidence.claim_boundary)} figure="/figures/v2/atmosphere-observability.png" figureAlt="Atmospheric transmission signal scenarios across candidate planets" figureCaption="Scale-height amplitudes are clear, isothermal atmosphere scenarios. They do not establish that an atmosphere exists or identify molecules." />;
}

