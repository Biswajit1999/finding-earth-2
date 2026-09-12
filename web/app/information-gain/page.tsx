import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { InformationGainExplorer } from "@/components/observatory/InformationGainExplorer";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Expected Information Gain", description: "Choose a candidate and measurement action to inspect expected posterior shrinkage under declared synthetic Gaussian likelihoods." };

export default function InformationGainPage() {
  const data = getObservatory().information_gain;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · decisions" title="What should we measure next?" lede="Candidate ranking identifies interesting worlds. Expected information gain asks a different question: which supported measurement would reduce a declared uncertainty the most?" meta={`${data.candidate_count} candidates × ${data.action_count} actions · ${data.supported_rows} supported calculations`} label={data.label} stats={[
    { value: String(data.candidate_count), label: "candidate worlds", sub: "leading ranked sample" },
    { value: String(data.action_count), label: "measurement actions", sub: "explicit synthetic likelihoods" },
    { value: String(data.supported_rows), label: "supported actions", sub: `${data.row_count - data.supported_rows} remain undetermined` },
    { value: "bits", label: "information unit", sub: "expected KL divergence" },
  ]} findingTitle="The highest score is not always the most useful next target" finding={<p>A precise parameter offers little information if it is already known well. A weaker parameter can dominate the decision if a plausible measurement sharply contracts its posterior. Unsupported actions remain withheld because information gain requires both a calibrated prior and a defensible observation model.</p>} interpretation={data.claim_boundary} figure="/figures/v2/information-gain.png" figureAlt="Expected information gain for measurement actions across leading candidates" figureCaption="The heatmap reports synthetic linear-Gaussian information in bits. Cost, observing time and instrument feasibility are not modelled.">
    <InformationGainExplorer rows={data.rows} />
  </ObservatoryChapter>;
}

