import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { UniverseExplorer } from "@/components/universe/UniverseExplorer";
import { getUniverse, getDeepDiveIndex } from "@/lib/data";

export const metadata: Metadata = {
  title: "Discovery Universe",
  description:
    "A selection-aware 3D history of confirmed exoplanet discoveries, positioned from measured coordinates and filterable by year and method.",
};

export default function UniversePage() {
  const data = getUniverse();
  const deepDiveSlugs = new Set(getDeepDiveIndex().map((e) => e.slug));
  return (
    <>
      <PageHeader
        eyebrow="Selection-aware 3D history"
        title="How exoplanet discovery filled our sky"
        lede="Every point is a real system with a measured distance, placed from its right ascension, declination and distance from the Sun. Move the year control to watch the observed catalogue accumulate, then separate detection methods to expose their different survey footprints. This is a history of what instruments found—not a map of where planets are intrinsically most common. The radial axis is log-compressed, and systems without distance are excluded and counted."
      />
      <UniverseExplorer data={data} deepDiveSlugs={deepDiveSlugs} />
    </>
  );
}
