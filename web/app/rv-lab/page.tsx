import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { RvLab } from "@/components/labs/RvLab";
import { getDeepDiveIndex } from "@/lib/data";

export const metadata: Metadata = {
  title: "RV Lab",
  description:
    "Radial-velocity time series from DACE, periodograms, and the mandatory stellar-activity cross-check.",
};

export default function RvLabPage() {
  const entries = getDeepDiveIndex();
  return (
    <>
      <PageHeader
        eyebrow="Spectroscopy"
        title="RV Lab"
        lede="Public radial-velocity time series from the Data & Analysis Center for Exoplanets (DACE), with a mandatory cross-check against stellar activity indicators measured from the same spectra. A rotating, spotted star can imitate a planet; this check is what rules that out."
      />
      <RvLab entries={entries} />
    </>
  );
}
