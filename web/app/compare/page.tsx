import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { CompareWorlds } from "@/components/compare/CompareWorlds";
import { getCatalogueFile } from "@/lib/data";

export const metadata: Metadata = {
  title: "Compare Worlds",
  description: "Compare two to five exoplanets side by side, with Earth as a reference.",
};

// Static export cannot read searchParams at build time. CompareWorlds reads the
// `?p=` query string itself, client-side, on mount.
export default function ComparePage() {
  const file = getCatalogueFile();

  return (
    <>
      <PageHeader
        eyebrow="Side by side"
        title="Compare worlds"
        lede="Select up to five planets to compare directly. Earth is included automatically as a reference unless you have already added it."
      />
      <CompareWorlds file={file} initialNames={[]} />
    </>
  );
}
