import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { UniverseExplorer } from "@/components/universe/UniverseExplorer";
import { getUniverse } from "@/lib/data";

export const metadata: Metadata = {
  title: "Universe",
  description:
    "An interactive 3D map of every analysed exoplanet system with a measured distance, positioned by real coordinates.",
};

export default function UniversePage() {
  const data = getUniverse();
  return (
    <>
      <PageHeader
        eyebrow="3D map"
        title="The universe, as measured"
        lede="Every point is a real system with a measured parallax distance, placed at its true right ascension, declination and distance from the Sun. The radial axis is log-compressed so nearby and distant systems are both visible; that compression is stated, not hidden. Systems without a measured distance are excluded and counted, never placed at an invented position."
      />
      <UniverseExplorer data={data} />
    </>
  );
}
