import Image from "next/image";
import Link from "next/link";

import { Caveat, PageHeader, StatBlock } from "@/components/PageHeader";
import { EvidenceLabel } from "@/components/observatory/EvidenceLabel";
import { Reveal } from "@/components/observatory/Reveal";
import { assetPath } from "@/lib/assets";
import type { EvidenceLabel as EvidenceLabelType } from "@/lib/observatory-types";

export interface ChapterStat {
  value: string;
  label: string;
  sub?: string;
}

export function ObservatoryChapter({
  eyebrow,
  title,
  lede,
  meta,
  label,
  stats,
  findingTitle,
  finding,
  interpretation,
  figure,
  figureAlt,
  figureCaption,
  methodsHref,
  children,
}: {
  eyebrow: string;
  title: string;
  lede: string;
  meta?: string;
  label: EvidenceLabelType;
  stats: ChapterStat[];
  findingTitle: string;
  finding: React.ReactNode;
  interpretation: string;
  figure?: string;
  figureAlt?: string;
  figureCaption?: string;
  methodsHref?: string;
  children?: React.ReactNode;
}) {
  return (
    <>
      <PageHeader eyebrow={eyebrow} title={title} lede={lede} meta={meta}>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <EvidenceLabel label={label} />
          <Link href={methodsHref ?? "/methods"} className="link text-sm">
            Inspect methods →
          </Link>
          <Link href="/evidence" className="link text-sm">
            Trace evidence →
          </Link>
        </div>
      </PageHeader>

      <section className="mx-auto max-w-[1400px] px-4 py-14 sm:px-6 sm:py-20">
        <Reveal className="grid gap-8 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => (
            <StatBlock key={stat.label} {...stat} />
          ))}
        </Reveal>
      </section>

      <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]">
        <div className="mx-auto grid max-w-[1400px] gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.75fr_1.25fr] lg:py-20">
          <Reveal>
            <p className="eyebrow text-[var(--color-gold)]">What the analysis found</p>
            <h2 className="mt-3 max-w-[18ch] text-[length:var(--text-title)] font-light leading-tight">
              {findingTitle}
            </h2>
          </Reveal>
          <Reveal className="space-y-6">
            <div className="max-w-[72ch] text-[15px] leading-relaxed text-[var(--color-dim)]">
              {finding}
            </div>
            <Caveat title="Claim boundary">{interpretation}</Caveat>
          </Reveal>
        </div>
      </section>

      {children}

      {figure && (
        <section className="mx-auto max-w-[1200px] px-4 py-16 sm:px-6 sm:py-20">
          <Reveal>
            <figure>
              <Image
                src={assetPath(figure)}
                width={1800}
                height={1100}
                sizes="(min-width: 1200px) 1100px, calc(100vw - 2rem)"
                alt={figureAlt ?? "Generated scientific result figure"}
                className="w-full rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-white"
              />
              {figureCaption && (
                <figcaption className="mt-3 max-w-[90ch] text-[12px] leading-relaxed text-[var(--color-muted)]">
                  {figureCaption}
                </figcaption>
              )}
            </figure>
          </Reveal>
        </section>
      )}
    </>
  );
}

