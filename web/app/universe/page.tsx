import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { UniverseExplorer } from "@/components/universe/UniverseExplorer";
import { getUniverse, getDeepDiveIndex, getDiscoveryTimeline } from "@/lib/data";

export const metadata: Metadata = {
  title: "Discovery Universe",
  description:
    "A selection-aware 3D history of confirmed exoplanet discoveries, positioned from measured coordinates and filterable by year and method.",
};

export default function UniversePage() {
  const data = getUniverse();
  const deepDiveSlugs = new Set(getDeepDiveIndex().map((e) => e.slug));
  const timeline = getDiscoveryTimeline();
  return (
    <>
      <PageHeader
        eyebrow="Selection-aware 3D history"
        title="How exoplanet discovery filled our sky"
        lede="Each point is a confirmed-planet record placed at its host star’s measured right ascension, declination and distance from the Sun. Multiple planets orbiting one star share that host position; switch between planets and unique hosts for an unduplicated star map. Move the year control to watch the observed catalogue accumulate, then separate detection methods to expose their different survey footprints. This is a history of what instruments found—not a map of where planets are intrinsically most common. The radial axis is log-compressed, and planet records without a measured host distance are excluded and counted."
      />
      <UniverseExplorer data={data} deepDiveSlugs={deepDiveSlugs} timeline={timeline} />
    </>
  );
}
