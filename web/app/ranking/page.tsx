import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { WeightedRanking } from "@/components/ranking/WeightedRanking";
import { getCatalogueFile } from "@/lib/data";

export const metadata: Metadata = {
  title: "Ranking",
  description:
    "Re-weight the four Earth-2.0 component scores yourself and see the composite ranking update live.",
};

export default function RankingPage() {
  const file = getCatalogueFile();
  return (
    <>
      <PageHeader
        eyebrow="Interactive"
        title="Change the weighting yourself"
        lede="The composite Earth-2.0 index is a weighted geometric mean of four component scores. Every reader can choose different weights: there is no single correct answer to how much habitability should matter relative to how well something is measured. Every value below is already computed; the browser only recombines four numbers."
      />
      <WeightedRanking file={file} />
    </>
  );
}
