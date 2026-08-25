import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/PageHeader";
import { HzChip, MassClassChip } from "@/components/Chips";
import { BasicProfile, DeepDiveProfile } from "@/components/candidate/CandidateProfile";
import { getAllPlanetSlugs, getDeepDive, getPlanetBySlug } from "@/lib/data";
import { num } from "@/lib/format";

type Params = Promise<{ slug: string }>;

export function generateStaticParams() {
  return getAllPlanetSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const p = getPlanetBySlug(slug);
  if (!p) return { title: "Candidate not found" };
  return {
    title: p.name,
    description:
      `${p.name}: Earth-2.0 index ${num(p.index_value, 3)}, ` +
      `Earth Similarity Index ${num(p.esi, 3)}, radius ${num(p.rade, 2)} R⊕, ` +
      `orbiting ${p.host}.`,
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
