import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { GalaxyExplorer } from "@/components/galaxy/GalaxyExplorer";
import { getGalaxy, getDeepDiveIndex } from "@/lib/data";

export const metadata: Metadata = {
  title: "Galaxy",
  description:
    "Where the Sun actually sits in the Milky Way, and how far each detection method has really reached, computed from every system's measured coordinates.",
};

export default function GalaxyPage() {
  const data = getGalaxy();
  const deepDiveSlugs = new Set(getDeepDiveIndex().map((e) => e.slug));
  return (
    <>
      <PageHeader
        eyebrow="Galactic context"
        title="Our place in the galaxy"
        lede="The Sun's position here is real, computed from a standard equatorial-to-Galactocentric transform, not assumed. The Milky Way's own spiral shape behind it is a labelled illustration -- we are inside the galaxy and cannot photograph its structure from outside. Every system plotted, and every detection-distance shell, comes from this catalogue's actual measured coordinates."
      />
      <GalaxyExplorer data={data} deepDiveSlugs={deepDiveSlugs} />
    </>
  );
}
