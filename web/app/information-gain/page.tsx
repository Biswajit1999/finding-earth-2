import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { InformationGainExplorer } from "@/components/observatory/InformationGainExplorer";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Expected Information Gain", description: "Choose a candidate and measurement action to inspect expected posterior shrinkage under declared synthetic Gaussian likelihoods." };

export default function InformationGainPage() {
  const data = getObservatory().information_gain;
  const audit = data.objective_conditioned_audit;
  const kepler296f = audit.rows.find((row) => row.pl_name === "Kepler-296 f");
  return (
    <ObservatoryChapter
      eyebrow="Exoearth evidence observatory · decisions"
      title="What should we measure next?"
      lede="Expected information gain is only comparable after the scientific objective is fixed. This lab separates information about each measured parameter from information transferred to planet radius."
      meta={`${data.candidate_count} candidates × ${data.action_count} actions · ${data.supported_rows} supported calculations`}
      label={audit.label}
      stats={[
        { value: String(audit.eligible_target_count), label: "jointly testable worlds", sub: "both radius actions supported" },
        { value: String(audit.scalar_stellar_action_wins), label: "scalar stellar wins", sub: "different own-parameter objectives" },
        { value: String(audit.indirect_wins_at_or_below_ceiling), label: "objective-conditioned wins", sub: "stellar → planet radius at |ρ| ≤ 0.90" },
        { value: `${kepler296f?.stellar_to_planet_radius_information_bits_at_abs_correlation_0p90.toFixed(2) ?? "—"} bits`, label: "Kepler-296 f transfer", sub: "planet-radius EIG at |ρ| = 0.90" },
      ]}
      findingTitle="A high score can answer the wrong question"
      finding={
        <p>
          Stellar-radius precision has the larger own-parameter score for 10 of 13 eligible worlds. Once the objective is fixed to planet-radius uncertainty, none beats a direct radius measurement at |ρ| ≤ 0.90. Kepler-296 f needs |ρ| = 0.9952 merely to break even under this synthetic model.
        </p>
      }
      interpretation={`${audit.claim_boundary} ${data.claim_boundary}`}
      figure="/figures/v2/objective-conditioned-information.png"
      figureAlt="Direct planet-radius information compared with information transferred from a stellar-radius measurement under an absolute correlation of 0.90"
      figureCaption="Cyan and gold bars answer the same planet-radius objective. Rose bars show the original stellar-radius own-parameter score and are displayed only to expose why cross-objective rankings can mislead."
    >
      <InformationGainExplorer rows={data.rows} />
    </ObservatoryChapter>
  );
}
