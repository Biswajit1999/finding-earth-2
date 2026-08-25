"use client";

/**
 * Interactive re-weighting of the composite Earth-2.0 index.
 *
 * This is the ONE computation this site performs client-side, and it is
 * deliberately narrow: the four component scores were computed in Python from
 * the Monte Carlo posteriors and the archive data. All this component does is
 * recombine four already-computed numbers with a different weighted geometric
 * mean -- the same formula and the same epsilon floor as
 * earth2.ranking.scores.rank_catalogue, just with reader-chosen weights instead
 * of the pipeline's defaults.
 */

import Link from "next/link";
import { useMemo, useState } from "react";

import { HzChip, MassClassChip } from "@/components/Chips";
import { ScoreMeter } from "@/components/UncertaintyBar";
import type { CatalogueFile } from "@/lib/types";
import { num, slugify } from "@/lib/format";

const EPS = 0.01;

interface Weights {
  similarity: number;
  habitability: number;
  confidence: number;
  characterisation: number;
}

const DEFAULT_WEIGHTS: Weights = {
  similarity: 0.35,
  habitability: 0.4,
  confidence: 0.25,
  characterisation: 0.0,
};

const PRESETS: { label: string; weights: Weights; blurb: string }[] = [
  {
    label: "Pipeline default",
    weights: DEFAULT_WEIGHTS,
    blurb: "35% similarity, 40% habitability, 25% confidence, 0% characterisation",
  },
  {
    label: "Evidence-first",
    weights: { similarity: 0.2, habitability: 0.25, confidence: 0.55, characterisation: 0 },
    blurb: "Prioritise how well a planet is actually measured over how Earth-like it looks",
  },
  {
    label: "Similarity-first",
    weights: { similarity: 0.7, habitability: 0.2, confidence: 0.1, characterisation: 0 },
    blurb: "Prioritise bulk-property resemblance to Earth above all else",
  },
  {
    label: "Follow-up target",
    weights: { similarity: 0.15, habitability: 0.15, confidence: 0.2, characterisation: 0.5 },
    blurb: "Prioritise atmospheric observability with current instruments",
  },
];

function geometricMean(scores: (number | null)[], weights: number[]): number | null {
  const total = weights.reduce((a, b) => a + Math.max(b, 0), 0);
  if (total <= 0) return null;
  let logSum = 0;
  let usable = true;
  for (let i = 0; i < scores.length; i++) {
    const w = weights[i]! / total;
    if (w <= 0) continue;
    const s = scores[i];
    if (s === null) usable = false;
    const floored = Math.max(Math.min(s ?? EPS, 1), EPS);
    logSum += w * Math.log(floored);
  }
  return usable ? Math.exp(logSum) : null;
}

export function WeightedRanking({ file }: { file: CatalogueFile }) {
  const c = file.columns;
  const [w, setW] = useState<Weights>(DEFAULT_WEIGHTS);

  const ranked = useMemo(() => {
    const weights = [w.similarity, w.habitability, w.confidence, w.characterisation];
    const rows: { i: number; score: number | null }[] = [];
    for (let i = 0; i < file.n_rows; i++) {
      if (c.is_control[i]) continue;
      if (!c.rankable[i]) continue;
      const scores = [
        c.score_earth_similarity[i],
        c.score_conservative_habitability[i],
        c.score_observational_confidence[i],
        c.score_characterisation_potential[i],
      ];
      rows.push({ i, score: geometricMean(scores, weights) });
    }
    rows.sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
    return rows.slice(0, 30);
  }, [w, c, file.n_rows]);

  const setSlider = (k: keyof Weights) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setW((prev) => ({ ...prev, [k]: Number(e.target.value) / 100 }));

  const total = w.similarity + w.habitability + w.confidence + w.characterisation || 1;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      <div className="grid gap-8 lg:grid-cols-[340px_1fr]">
        {/* ---------------- controls ---------------- */}
        <div className="panel h-fit p-5 lg:sticky lg:top-20">
          <p className="eyebrow mb-4">Composite weights</p>

          {(
            [
              ["similarity", "Earth similarity", "var(--color-cyan)"],
              ["habitability", "Conservative habitability", "var(--color-verdant)"],
              ["confidence", "Observational confidence", "var(--color-sci)"],
              ["characterisation", "Characterisation potential", "var(--color-violet)"],
            ] as [keyof Weights, string, string][]
          ).map(([key, label, colour]) => (
            <div key={key} className="mb-5">
              <div className="mb-1.5 flex items-baseline justify-between">
                <label htmlFor={`w-${key}`} className="text-[12.5px] text-[var(--color-ivory)]">
                  {label}
                </label>
                <span className="font-[family-name:var(--font-mono)] text-[11px] tabular-nums text-[var(--color-dim)]">
                  {((w[key] / total) * 100).toFixed(0)}%
                </span>
              </div>
              <input
                id={`w-${key}`}
                type="range"
                min={0}
                max={100}
                value={Math.round(w[key] * 100)}
                onChange={setSlider(key)}
                className="w-full cursor-pointer accent-[var(--color-cyan)]"
                style={{ accentColor: colour }}
                aria-valuetext={String(Math.round(w[key] * 100)) + " percent"}
              />
            </div>
          ))}

          <p className="mb-3 mt-1 text-[11px] leading-relaxed text-[var(--color-muted)]">
            Weights are normalised to sum to 100%. Recombination uses the same
            weighted geometric mean as the pipeline default: a near-zero
            component still drags the whole index toward zero, so a strong
            similarity score cannot compensate for a disqualifying habitability
            score.
          </p>

          <div className="border-t border-[var(--color-line)] pt-3">
            <p className="eyebrow mb-2">Presets</p>
            <ul className="space-y-1.5">
              {PRESETS.map((p) => (
                <li key={p.label}>
                  <button
                    type="button"
                    onClick={() => setW(p.weights)}
                    className="w-full cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line)] px-2.5 py-1.5 text-left transition-colors hover:border-[var(--color-cyan)]"
                  >
                    <span className="block text-[12px] text-[var(--color-ivory)]">
                      {p.label}
                    </span>
                    <span className="block text-[10.5px] text-[var(--color-muted)]">
                      {p.blurb}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* ---------------- ranked list ---------------- */}
        <div>
          <p
            className="mb-3 font-[family-name:var(--font-mono)] text-[12px] text-[var(--color-dim)]"
            role="status"
            aria-live="polite"
          >
            Top 30 under this weighting, recomputed live from the pipeline&rsquo;s
            component scores
          </p>
          <ol className="space-y-1.5">
            {ranked.map(({ i, score }, rank) => (
              <li
                key={i}
                className="panel flex items-center gap-4 px-4 py-3 transition-colors hover:border-[var(--color-cyan)]"
              >
                <span className="w-6 shrink-0 text-right font-[family-name:var(--font-mono)] text-[12px] text-[var(--color-muted)]">
                  {rank + 1}
                </span>
                <div className="w-48 shrink-0">
                  <Link
                    href={"/candidate/" + slugify(c.pl_name[i] ?? "")}
                    className="text-[13.5px] font-medium text-[var(--color-ivory)] transition-colors hover:text-[var(--color-cyan)]"
                  >
                    {c.pl_name[i]}
                  </Link>
                  <span className="ml-1.5 text-[10.5px] text-[var(--color-muted)]">
                    {c.st_spectype[i] ?? ""}
                  </span>
                </div>
                <div className="w-28 shrink-0">
                  <ScoreMeter
                    value={score}
                    tone="var(--color-gold)"
                    width={70}
                    label={(c.pl_name[i] ?? "") + " re-weighted index"}
                  />
                </div>
                <div className="hidden shrink-0 sm:block">
                  <HzChip
                    prob={c.hz_conservative_prob[i]}
                    extrapolated={c.hz_model_extrapolated[i]}
                  />
                </div>
                <div className="hidden shrink-0 md:block">
                  <MassClassChip massClass={c.mass_class[i]} />
                </div>
                <span className="ml-auto shrink-0 font-[family-name:var(--font-mono)] text-[11px] tabular-nums text-[var(--color-muted)]">
                  {num(c.pl_rade[i], 2)} R⊕
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
