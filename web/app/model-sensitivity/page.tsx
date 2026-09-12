import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { SensitivityExplorer } from "@/components/observatory/SensitivityExplorer";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Model Sensitivity", description: "Candidate rank, climate, bulk-composition, atmosphere and HWO accessibility sensitivity across implemented model choices." };

export default function ModelSensitivityPage() {
  const data = getObservatory().falsification;
  const spans = data.candidate_sensitivity.map((row) => row.legacy_rank_span);
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · sensitivity" title="How much does the conclusion depend on the model?" lede="The observatory recomputes the leading candidate set across declared ranking weights, climate boundaries, composition relations, atmospheric assumptions and direct-imaging trade cases." meta={`${data.candidate_count} candidates · five legacy weight menus · three climate prescriptions`} label="MODEL-SENSITIVITY" stats={[
    { value: String(data.candidate_count), label: "candidates tested", sub: "same evidence, varied assumptions" },
    { value: String(Math.max(...spans)), label: "largest rank span", sub: "places across weight menus" },
    { value: "3", label: "climate prescriptions", sub: "agreement remains visible" },
    { value: "3+", label: "composition models", sub: "only where domains support them" },
  ]} findingTitle="Some leaders are stable; some are choices in disguise" finding={<p>A ranking can look precise while depending strongly on its weights. The candidate-level view exposes the full rank interval and the ranges produced by supported physical models. Missing model support is shown as unsupported rather than converted into agreement.</p>} interpretation={data.claim_boundary} figure="/figures/v2/falsification.png" figureAlt="Solar-System falsification results and candidate model rank sensitivity" figureCaption="Rank spans cover five declared legacy weight menus. Climate, composition and HWO ranges cover only the implemented supported model sets.">
    <SensitivityExplorer rows={data.candidate_sensitivity} />
  </ObservatoryChapter>;
}

