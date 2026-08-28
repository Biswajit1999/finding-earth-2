import type { Metadata } from "next";

import { FollowUpLab } from "@/components/follow-up/FollowUpLab";
import { PageHeader } from "@/components/PageHeader";
import { getCatalogueFile } from "@/lib/data";

export const metadata: Metadata = {
  title: "Follow-up Lab",
  description:
    "Compare transit-timing, atmospheric, radial-velocity, and reflected-light follow-up diagnostics without mixing them into the Earth-2.0 ranking.",
};

export default function FollowUpPage() {
  const file = getCatalogueFile();

  return (
    <>
      <PageHeader
        eyebrow="Observation planning"
        title="Follow-up Lab"
        lede="Four observing pathways, kept deliberately separate. Compare transit-clock freshness, atmospheric screening metrics, expected radial-velocity amplitude, and reflected-light geometry without pretending they are interchangeable—or probabilities of detection."
        meta="Scenario diagnostics from the reproducible pipeline · default view limits the table to the top 250 Earth-2.0 candidates"
      />
      <FollowUpLab file={file} />
    </>
  );
}
