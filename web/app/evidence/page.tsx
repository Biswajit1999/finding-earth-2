import type { Metadata } from "next";

import { EvidenceExplorer } from "@/components/observatory/EvidenceExplorer";
import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Evidence Graph", description: "Trace scientific claims through quantities, transformations, measurements, stars, planets and publication sources." };

export default function EvidencePage() {
  const data = getObservatory().evidence;
  const nodes = Object.values(data.nodes_by_kind).reduce((total, count) => total + count, 0);
  const labels = Object.keys(data.quantity_labels);
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · provenance" title="Every number should have a way home" lede="The evidence graph connects a reported quantity to the planet and host, its evidence class, the archive record or transformation that produced it, and the publication source where available." meta="Directed provenance graph · measurement-level source links · explicit gaps" label="OBSERVED" stats={[
    { value: nodes.toLocaleString("en-GB"), label: "graph nodes", sub: "measurements · planets · stars · sources" },
    { value: data.edges.toLocaleString("en-GB"), label: "directed edges", sub: "machine-readable relationships" },
    { value: String(labels.length), label: "evidence classes", sub: labels.join(" · ") },
    { value: data.records_with_provenance_gaps.toLocaleString("en-GB"), label: "provenance gaps", sub: "visible, never silently filled" },
  ]} findingTitle="Provenance gaps are findings too" finding={<p>A composite archive row is not automatically an independent observation. The graph makes source depth visible and records where the current public tables cannot connect a value to a publication-level measurement. Those gaps prevent false confidence and identify the next data-engineering task.</p>} interpretation={data.scope}>
    <EvidenceExplorer examples={data.mass_examples} />
  </ObservatoryChapter>;
}
