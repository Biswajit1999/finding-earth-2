import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/PageHeader";
import { ReachCalculator } from "@/components/beyond/ReachCalculator";

export const metadata: Metadata = {
  title: "Beyond Earth 2.0",
  description: "Physics-based distance, extragalactic detection, communication delay and technosignature research futures, separated from the core exoplanet evidence.",
  alternates: { canonical: "https://biswajit1999.github.io/finding-earth-2/beyond/" },
};

const signals = [
  ["Narrow-band radio", "frequency drift, repeatability, sky localisation", "radio interference"],
  ["Optical / near-IR pulse", "time-coincident photons and repeat events", "instrumental and atmospheric transients"],
  ["Industrial atmosphere", "retrieved abundance inconsistent with tested natural pathways", "photochemistry and retrieval degeneracy"],
  ["Artificial illumination", "phase-locked night-side excess", "thermal emission, clouds, albedo maps"],
  ["Waste heat", "spectral energy imbalance", "dust and natural infrared excess"],
  ["Transit anomaly", "repeatable geometry inconsistent with tested bodies", "rings, dust, activity, processing artifacts"],
] as const;

export default function BeyondPage() {
  return <>
    <PageHeader eyebrow="Research futures · explicitly separated" title="Beyond Earth 2.0" lede="From detection to distance, civilisation and contact. Here the project asks what physics permits, what future missions might test, and what remains speculation—without leaking those ideas into the candidate evidence." meta="OBSERVED FACT · PHYSICS-BASED CALCULATION · MISSION FORECAST · RESEARCH HYPOTHESIS · AUTHOR PERSPECTIVE" />
    <main>
      <section className="mx-auto grid max-w-[1400px] gap-8 px-4 py-20 sm:px-6 lg:grid-cols-2">
        <div><p className="eyebrow text-[var(--color-gold)]">The data universe</p><h2 className="mt-3 text-[length:var(--text-display)] font-light">Scale only matters when it answers a question</h2></div>
        <div className="space-y-4 text-sm leading-relaxed text-[var(--color-dim)]"><p>Gaia DR3 holds about 1.8 billion sources, while time-domain surveys can create trillions of measurements. Those numbers are not exoplanet counts. A scalable evidence system should push filters toward archives, partition by stable identity and time, preserve manifests, and materialise only question-specific products.</p><p>The priority is information: stellar parameters that change planet radii, injection experiments that identify selection, spectra that test atmospheres, and time series that can falsify a signal.</p></div>
      </section>

      <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]"><div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6"><p className="eyebrow text-[var(--color-cyan)]">Negative feasibility is a result</p><h2 className="mt-3 max-w-[20ch] text-[length:var(--text-display)] font-light">An Earth in another galaxy is not a scaled-up nearby observation</h2><div className="mt-8 grid gap-5 md:grid-cols-3"><article className="panel-raised p-6"><h3>Photons disappear</h3><p className="mt-3 text-sm text-[var(--color-dim)]">Flux falls as 1/d². From 10 pc to M51, the same source becomes about 7.4×10¹¹ times fainter.</p></article><article className="panel-raised p-6"><h3>Angles collapse</h3><p className="mt-3 text-sm text-[var(--color-dim)]">At 8.6 Mpc, one AU spans about 0.116 microarcseconds. Ideal 550 nm diffraction alone asks for a kilometre-scale baseline before contrast and crowding.</p></article><article className="panel-raised p-6"><h3>Confusion dominates</h3><p className="mt-3 text-sm text-[var(--color-dim)]">Ordinary stellar transits remain unresolved inside crowded galaxy pixels. Microlensing, pixel lensing and X-ray eclipses can reveal candidates without characterising an Earth twin.</p></article></div><div className="mt-8 rounded border border-[var(--color-gold)]/40 p-6"><p className="eyebrow text-[var(--color-gold)]">Case study · unconfirmed candidate</p><h3 className="mt-2 text-xl">M51-ULS-1b</h3><p className="mt-3 max-w-4xl text-sm leading-relaxed text-[var(--color-dim)]">A single Chandra X-ray eclipse motivated a Saturn-size planet interpretation around an X-ray binary roughly 8.6 Mpc away. It is an unconfirmed extragalactic candidate, not an Earth analogue; its long proposed orbit makes a repeat transit a decades-long wait.</p><a className="link mt-4 inline-block" href="https://doi.org/10.1038/s41550-021-01495-w" target="_blank" rel="noreferrer">Read the primary study →</a></div></div></section>

      <ReachCalculator />

      <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]"><div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6"><p className="eyebrow text-[var(--color-gold)]">If someone is there, can we know?</p><h2 className="mt-3 text-[length:var(--text-display)] font-light">A technosignature needs an evidence graph too</h2><p className="mt-5 max-w-3xl text-sm leading-relaxed text-[var(--color-dim)]">An anomaly begins a chain of natural-hypothesis tests; it does not end with an intelligence claim. Non-detections constrain only the frequencies, powers, directions, times, and signal classes actually searched.</p><div className="mt-8 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b border-[var(--color-line-strong)] text-xs uppercase tracking-wider text-[var(--color-muted)]"><th className="p-3">Channel</th><th className="p-3">Evidence needed</th><th className="p-3">Natural / instrumental alternatives</th></tr></thead><tbody>{signals.map(([channel, evidence, alternatives]) => <tr key={channel} className="border-b border-[var(--color-line)]"><td className="p-3 text-[var(--color-ivory)]">{channel}</td><td className="p-3 text-[var(--color-dim)]">{evidence}</td><td className="p-3 text-[var(--color-muted)]">{alternatives}</td></tr>)}</tbody></table></div></div></section>

      <section className="mx-auto max-w-[1400px] px-4 py-24 sm:px-6"><p className="eyebrow">Staged research programme</p><div className="mt-8 flex flex-wrap items-center gap-3 font-[family-name:var(--font-mono)] text-xs text-[var(--color-dim)]">{["FIND A WORLD","DETERMINE WHAT IT IS","TEST LIFE-COMPATIBLE CONDITIONS","SEARCH BIOSIGNATURES","SEARCH TECHNOSIGNATURES","CALCULATE SIGNAL DELAY","CALCULATE TRAVEL LIMITS","CHOOSE THE NEXT TEST"].map((item, index) => <span key={item} className="contents"><span className="rounded border border-[var(--color-line-strong)] px-3 py-2">{item}</span>{index < 7 && <span aria-hidden>→</span>}</span>)}</div><p className="mt-8 max-w-3xl text-sm text-[var(--color-dim)]">The boundary is the product: what we know, what we can infer, what we could test, and what we can only imagine.</p><div className="mt-7 flex gap-5 text-sm"><Link className="link" href="/perspective">Read Biswajit Jana’s perspective →</Link><a className="link" href="https://github.com/Biswajit1999/finding-earth-2/blob/main/docs/EXTRAGALACTIC_EARTH.md">Open the quantitative chapter →</a></div></section>
    </main>
  </>;
}
