import type { Metadata } from "next";

import { ObservatoryChapter } from "@/components/observatory/Chapter";
import { SelectionSurfaceExplorer } from "@/components/observatory/SelectionSurfaceExplorer";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Kepler Selection Function", description: "Interactive Kepler DR25 transit geometry, observing-window, pipeline recovery and vetting selection surface." };

export default function SelectionPage() {
  const data = getObservatory().selection;
  return <ObservatoryChapter eyebrow="Exoearth evidence observatory · selection" title="What Kepler was capable of detecting" lede="A planet can exist and still never enter the catalogue. This surface combines transit geometry, the observed phase window, injection-calibrated pipeline recovery and vetting across a declared target sample." meta={`${data.surface_grid.period_points.length} periods × ${data.surface_grid.radius_points.length} radii · ${data.surface_grid.cells} evaluated cells`} label={data.label} stats={[
    { value: Number(data.stellar_denominator.selected_unique_targets).toLocaleString("en-GB"), label: "selected GK targets", sub: "unique DR25 stars" },
    { value: Number(data.calibration_sample.domain_inj1_rows).toLocaleString("en-GB"), label: "injection trials", sub: "inside model domain" },
    { value: String(data.surface_grid.cells), label: "surface cells", sub: "50–500 d · 0.5–2.0 R⊕" },
    { value: "4 factors", label: "selection chain", sub: "geometry · window · recovery · vetting" },
  ]} findingTitle="Survey sensitivity is a physical part of the answer" finding={<p>Longer-period, smaller planets are harder to see for several independent reasons. The selected cell view exposes those factors separately, preventing a low catalogue count from being read as direct evidence that such planets are intrinsically rare.</p>} interpretation={data.interpretation} figure="/figures/v2/selection-surface.png" figureAlt="Kepler DR25 selection probability over orbital period and planet radius" figureCaption="The colour field is target-averaged total selection probability. It is detection exposure, not occurrence or habitability.">
    <SelectionSurfaceExplorer cells={data.cells} periods={data.surface_grid.period_points} radii={data.surface_grid.radius_points} />
  </ObservatoryChapter>;
}

