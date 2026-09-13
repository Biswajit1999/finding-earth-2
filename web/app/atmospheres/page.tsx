import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { Reveal } from "@/components/observatory/Reveal";
import { assetPath } from "@/lib/assets";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Atmospheres", description: "Published transmission and eclipse measurements, separate reductions, and explicitly hypothetical scale-height scenarios." };

export default function AtmospheresPage() {
  const data = getObservatory().atmosphere;
  const evidence = data.spectrum_evidence;
  const screen = data.earth_analogue_screen;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · atmospheres" title="A spectrum is a reduction, not an atmosphere" lede="Published wavelength-dependent measurements remain attached to their facility, instrument, reference and reduction path. Clear-atmosphere scale heights are shown as scenarios and never mistaken for molecular detections." meta="Transmission + eclipse archives · reduction-preserving architecture · scenario calculator" label="OBSERVED" stats={[
    { value: Number(evidence.measurement_count).toLocaleString("en-GB"), label: "spectral points", sub: "published archive measurements" },
    { value: Number(evidence.transmission_measurements).toLocaleString("en-GB"), label: "transmission", sub: "measurement rows" },
    { value: Number(evidence.eclipse_measurements).toLocaleString("en-GB"), label: "eclipse", sub: "measurement rows" },
    { value: Number(evidence.reduction_count).toLocaleString("en-GB"), label: "separate reductions", sub: "never silently merged" },
  ]} findingTitle="Different reductions are evidence about uncertainty" finding={<div className="space-y-4"><p>When two teams reduce the same target differently, the disagreement is scientifically useful. The pipeline stores each reduction independently and computes overlap diagnostics without selecting a winner or averaging incompatible products.</p><Link href="/spectral-lab" className="link inline-block">Open the real spectral measurements →</Link></div>} interpretation={String(evidence.claim_boundary)} figure="/figures/v2/atmosphere-observability.png" figureAlt="Atmospheric transmission signal scenarios across candidate planets" figureCaption="Scale-height amplitudes are clear, isothermal atmosphere scenarios. They do not establish that an atmosphere exists or identify molecules.">
    <section className="border-b border-[var(--color-line)] bg-[var(--color-ink)]">
      <div className="mx-auto grid max-w-[1400px] gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.72fr_1.28fr] lg:py-24">
        <Reveal>
          <p className="eyebrow text-[var(--color-gold)]">Earth 2.0 spectrum screen</p>
          <h2 className="mt-3 text-[length:var(--text-title)] font-light leading-tight">The strongest result is an evidence gap.</h2>
          <p className="mt-6 max-w-[56ch] text-[15px] leading-relaxed text-[var(--color-dim)]">{screen.finding}</p>
          <div className="mt-8 grid grid-cols-3 gap-3">
            {[
              [screen.strict_small_temperate_candidates, "strict candidates"],
              [screen.strict_candidates_with_indexed_reductions, "indexed spectra"],
              [screen.strict_candidates_with_tabulated_measurements, "measured spectra"],
            ].map(([value, label]) => <div key={String(label)} className="rounded-xl border border-[var(--color-line)] p-4"><p className="font-mono text-2xl text-white">{String(value)}</p><p className="mt-1 text-[10px] uppercase tracking-widest text-[var(--color-muted)]">{String(label)}</p></div>)}
          </div>
          <p className="mt-8 text-sm leading-relaxed text-[var(--color-muted)]">{screen.next_observation}</p>
        </Reveal>
        <Reveal>
          <Image src={assetPath("/figures/v2/earth-analogue-spectrum-screen.png")} width={1944} height={1116} sizes="(min-width: 1024px) 760px, calc(100vw - 2rem)" alt="Coverage funnel showing that none of the fifteen strict small temperate candidates has an archived spectrum in the ingested data" className="w-full rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-white" />
          <p className="mt-3 text-[12px] leading-relaxed text-[var(--color-muted)]">{screen.claim_boundary}</p>
        </Reveal>
      </div>
    </section>
  </ObservatoryChapter>;
}
