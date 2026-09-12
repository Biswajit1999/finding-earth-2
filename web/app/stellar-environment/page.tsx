import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Stellar Environment", description: "MUSCLES-derived ultraviolet environments and declared XUV and atmospheric-escape scenarios for high-value candidates." };

export default function StellarEnvironmentPage() {
  const data = getObservatory().environment;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · stellar environment" title="The star is part of the planet" lede="Bolometric irradiation can place a world inside a habitable-zone boundary while ultraviolet and X-ray histories reshape its atmosphere. The observatory keeps present SED-derived fluxes apart from evolutionary and escape scenarios." meta="MUSCLES SEDs where matched · generic histories elsewhere · energy-limited escape ensemble" label="SCENARIO" stats={[
    { value: data.population.targets.toLocaleString("en-GB"), label: "high-value targets", sub: "rank-selected evaluation set" },
    { value: data.population.with_muscles_current_sed.toLocaleString("en-GB"), label: "MUSCLES matches", sub: "current stitched SED evidence" },
    { value: data.population.with_age_activity_histories.toLocaleString("en-GB"), label: "XUV histories", sub: "scenario-supported targets" },
    { value: data.population.with_escape_ensemble.toLocaleString("en-GB"), label: "escape ensembles", sub: "declared parameter grid" },
  ]} findingTitle="The bolometric twin can have a different high-energy history" finding={<p>A similar equilibrium temperature does not imply a similar atmospheric environment. For matched MUSCLES hosts, the current SED constrains the derived ultraviolet dose. For the wider sample, saturation time, decay slope, heating efficiency and XUV radius remain explicit scenario choices.</p>} interpretation={data.claim_boundary} figure="/figures/v2/bolometric-xuv.png" figureAlt="Bolometric irradiation compared with XUV environment scenarios" figureCaption="Current archive-derived SED quantities and generic evolutionary scenarios use different evidence labels." />;
}

