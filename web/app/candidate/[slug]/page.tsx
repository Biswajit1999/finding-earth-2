import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/PageHeader";
import { HzChip, MassClassChip } from "@/components/Chips";
import { BasicProfile, DeepDiveProfile } from "@/components/candidate/CandidateProfile";
import { getAllPlanetSlugs, getDeepDive, getPlanetBySlug } from "@/lib/data";
import { num } from "@/lib/format";

const SITE_ROOT = "https://biswajit1999.github.io/finding-earth-2";

type Params = Promise<{ slug: string }>;

export function generateStaticParams() {
  return getAllPlanetSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const p = getPlanetBySlug(slug);
  if (!p) return { title: "Candidate not found" };

  const description =
    `Finding Earth 2.0 analysis of ${p.name}, orbiting ${p.host}: ` +
    `Earth-2.0 index ${num(p.index_value, 3)}, Earth Similarity Index ${num(p.esi, 3)}, ` +
    `radius ${num(p.rade, 2)} R⊕, habitable-zone probability ${num(p.hzProb, 3)}, ` +
    `mass provenance ${p.massClass ?? "unavailable"}.`;

  const canonical = `${SITE_ROOT}/candidate/${slug}/`;

  return {
    title: `${p.name} Exoplanet Analysis`,
    description,
    alternates: { canonical },
    openGraph: {
      type: "article",
      url: canonical,
      title: `${p.name} — Finding Earth 2.0`,
      description,
    },
  };
}

export default async function CandidatePage({ params }: { params: Params }) {
  const { slug } = await params;
  const p = getPlanetBySlug(slug);
  if (!p) notFound();

  const dd = getDeepDive(slug);

  return (
    <>
      <PageHeader
        eyebrow={p.host + (p.spectype ? " · " + p.spectype : "")}
        title={p.name}
        meta={
          (p.rank ? "Rank #" + p.rank + " of the ranked catalogue · " : "") +
          (p.method ? "Discovered by " + p.method : "") +
          (p.discYear ? " in " + p.discYear : "")
        }
      >
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <HzChip prob={p.hzProb} extrapolated={p.hzExtrapolated} />
          <MassClassChip massClass={p.massClass} />
        </div>
      </PageHeader>

      {dd ? <DeepDiveProfile dd={dd} /> : <BasicProfile p={p} />}
    </>
  );
}
