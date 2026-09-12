import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "HWO Precursor Atlas", description: "HPIC and TSS25 precursor targets with direct-imaging accessibility under explicit analytic trade cases." };

export default function HwoPage() {
  const data = getObservatory().hwo;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · HWO" title="A precursor atlas for direct imaging" lede="The Habitable Worlds Observatory is still a developing mission concept. This atlas joins public precursor catalogues and computes orbit-conditioned accessibility only under three declared analytic telescope trade cases." meta="HPIC v1.1 + TSS25 · Gaia multiplicity · Monte Carlo orbital geometry" label="FORECAST" stats={[
    { value: Number(data.catalogue.hpic_rows).toLocaleString("en-GB"), label: "HPIC stars", sub: "complete precursor catalogue" },
    { value: Number(data.catalogue.known_planet_host_rows).toLocaleString("en-GB"), label: "known hosts", sub: "catalogue exact matches" },
    { value: data.known_planet_forecast.supported_planets.toLocaleString("en-GB"), label: "supported planets", sub: "generic accessibility forecast" },
    { value: String(data.instrument_scenarios.length), label: "trade cases", sub: "aperture · wavelength · IWA" },
  ]} findingTitle="Accessibility changes with the assumed observatory" finding={<p>Angular separation, reflected-light contrast and unknown orbital phase interact. A target accessible in a 500 nm, 8 m trade case may fail at 750 nm or with a smaller aperture. The atlas exposes those dependencies instead of publishing a mission-independent target score.</p>} interpretation={data.claim_boundary} figure="/figures/v2/hwo-atlas.png" figureAlt="HWO precursor star atlas and direct imaging accessibility forecasts" figureCaption="All accessibility values are forecasts under generic analytic cases. No case is presented as a final HWO flight specification or yield." />;
}

