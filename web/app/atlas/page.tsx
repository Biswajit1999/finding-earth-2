import type { Metadata } from "next";
import { AtlasTable } from "@/components/atlas/AtlasTable";
import { PageHeader } from "@/components/PageHeader";
import { getCatalogueFile, getSummary } from "@/lib/data";
import { compactInt } from "@/lib/format";

export const metadata: Metadata = {
  title: "Candidate Atlas",
  description:
    "Filter, sort and search the full analysed catalogue of confirmed exoplanets with computed Earth-2.0 scores.",
};

export default function AtlasPage() {
  const file = getCatalogueFile();
  const summary = getSummary();

  return (
    <>
      <PageHeader
        eyebrow="Full catalogue"
        title="Candidate Atlas"
        lede={`Every one of the ${compactInt(summary.population.n_confirmed_planets)} confirmed planets in this analysis, filterable and sortable in the browser. Nothing here is recomputed in JavaScript — every score, interval and flag was produced by the Python pipeline and shipped as data.`}
        meta={`Catalogue generated ${new Date(file.generated_utc).toISOString().slice(0, 16).replace("T", " ")} UTC · earth2 v${file.earth2_version}`}
      />
      <AtlasTable file={file} />
    </>
  );
}
