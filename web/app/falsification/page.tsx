import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { EvidenceLabel } from "@/components/observatory/EvidenceLabel";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Falsification", description: "Solar-System controls used to expose where similarity, habitable-zone and bulk-composition metrics fail." };

export default function FalsificationPage() {
  const data = getObservatory().falsification;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · falsification" title="A model must be allowed to fail" lede="Earth, Venus, Mars, Mercury and Jupiter pass through the same scoring machinery as the exoplanets. Their known outcomes reveal what the metrics cannot infer." meta="Five unranked Solar-System controls · same equations · known physical counterexamples" label="OBSERVED_CONTROL_WITH_DERIVED_MODEL_OUTPUTS" stats={[
    { value: String(data.control_count), label: "control worlds", sub: "kept outside exoplanet ranks" },
    { value: data.venus_esi.toFixed(3), label: "Venus ESI", sub: "high bulk similarity" },
    { value: data.venus_conservative_hz_probability.toFixed(1), label: "Venus HZ probability", sub: "conservative boundary" },
    { value: "0", label: "life probabilities", sub: "no metric estimates biology" },
  ]} findingTitle="Venus breaks the easy interpretation" finding={<p>Venus receives a high Earth Similarity Index even though its observed surface is hostile. Mars can satisfy a nominal habitable-zone test while remaining cold, arid and low-pressure. These controls falsify the reading of similarity or orbital irradiation as a habitability detector.</p>} interpretation={data.claim_boundary} figure="/figures/v2/falsification.png" figureAlt="Solar-System controls showing high similarity and habitable-zone scores alongside known hostile outcomes" figureCaption="The controls are observed Solar-System worlds with derived model outputs. They diagnose model scope and remain unranked.">
    <section className="mx-auto max-w-[1200px] px-4 py-16 sm:px-6 sm:py-20"><div className="grid gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-line)] md:grid-cols-2 xl:grid-cols-5">{data.controls.map((control) => <article key={String(control.pl_name)} className="bg-[var(--color-panel)] p-5"><EvidenceLabel label={String(control.label)} /><h2 className="mt-6 font-[family-name:var(--font-display)] text-2xl text-[var(--color-ivory)]">{String(control.pl_name)}</h2><dl className="mt-5 space-y-2 text-xs"><div className="flex justify-between"><dt className="text-[var(--color-muted)]">ESI</dt><dd className="font-[family-name:var(--font-mono)]">{Number(control.esi_global).toFixed(3)}</dd></div><div className="flex justify-between"><dt className="text-[var(--color-muted)]">Conservative HZ</dt><dd className="font-[family-name:var(--font-mono)]">{Number(control.hz_conservative_prob).toFixed(2)}</dd></div></dl><p className="mt-5 text-xs leading-relaxed text-[var(--color-muted)]">{String(control.known_surface_outcome)}</p></article>)}</div></section>
  </ObservatoryChapter>;
}

