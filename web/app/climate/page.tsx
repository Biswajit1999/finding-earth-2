import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Climate Sensitivity", description: "Time-dependent habitable-zone inference and climate-boundary sensitivity using MIST stellar evolution tracks." };

export default function ClimatePage() {
  const data = getObservatory().climate;
  const robust = data.population.classification_robustness;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · climate" title="A habitable zone moves with its star" lede="The present-day orbit is only one frame. MIST stellar tracks and three named Kopparapu boundary prescriptions test whether a planet stays inside a modelled irradiation range through time." meta="Stellar evolution × climate boundary × measurement uncertainty" label={data.label} stats={[
    { value: data.population.confirmed_planets_evaluated.toLocaleString("en-GB"), label: "planets evaluated", sub: "full confirmed catalogue" },
    { value: data.population.inferred.toLocaleString("en-GB"), label: "supported histories", sub: "measurement and grid gates passed" },
    { value: Number(robust.robustly_inside_across_prescriptions).toLocaleString("en-GB"), label: "robustly inside", sub: "all implemented prescriptions" },
    { value: Number(robust.boundary_or_model_sensitive).toLocaleString("en-GB"), label: "boundary sensitive", sub: "classification changes" },
  ]} findingTitle="Most planets cannot support a time-resolved claim" finding={<p>The dominant climate result is missing support. Only a subset has the stellar age, mass, metallicity, luminosity and uncertainties needed for a continuous history. Among supported systems, model agreement and disagreement remain explicit rather than being averaged away.</p>} interpretation={data.claim_boundary} figure="/figures/v2/climate-sensitivity.png" figureAlt="Continuous habitable-zone classifications and sensitivity across climate prescriptions" figureCaption="Climate classifications are conditional on stellar tracks and named one-dimensional boundary prescriptions; they are not observed climates." />;
}

