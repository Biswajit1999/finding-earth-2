"use client";

/**
 * Yearly method-share and distance-quantile plots, linked to the 3D/2D
 * discovery-history playback above.
 *
 * Every number here is read straight from `export_discovery_timeline`'s
 * Python output -- cumulative counts and cumulative median/90th-percentile
 * distance, by method, through each calendar year -- using the identical
 * row filter the 3D and 2D views use. Nothing is recomputed from the raw
 * per-planet arrays in this component; it only lays the pipeline's own
 * numbers out on two shared axes and marks the year the reader has
 * currently scrubbed to.
 */

import { useMemo } from "react";

import type { DiscoveryTimelineFile } from "@/lib/types";
import { methodColour } from "@/lib/format";

const GROUPS = [
  "Transit",
  "Radial Velocity",
  "Microlensing",
  "Imaging",
  "Transit Timing Variations",
  "Other",
] as const;

const W = 680;
const PAD_L = 34;
const PAD_R = 10;
const SHARE_H = 90;
const DIST_H = 130;
const GAP = 26;
const TOP = 8;

const PLOT_W = W - PAD_L - PAD_R;

const DIST_MIN_PC = 1;
const DIST_MAX_PC = 10000;
const DIST_TICKS = [1, 10, 100, 1000, 10000];

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}

export function DiscoveryTimelineCharts({
  data,
  currentYear,
}: {
  data: DiscoveryTimelineFile;
  /** The year currently scrubbed in the 3D/2D discovery-history playback above. */
  currentYear: number;
}) {
  const years = data.years;
  const minYear = years[0] ?? currentYear;
  const maxYear = years[years.length - 1] ?? currentYear;

  const xAt = (year: number) =>
    round2(PAD_L + ((year - minYear) / Math.max(maxYear - minYear, 1)) * PLOT_W);

  const shareTop = TOP;
  const distTop = shareTop + SHARE_H + GAP;
  const H = distTop + DIST_H + 24;

  const yShare = (pct: number) => round2(shareTop + SHARE_H - (pct / 100) * SHARE_H);
  const yDist = (pc: number) => {
    const clamped = Math.max(Math.min(pc, DIST_MAX_PC), DIST_MIN_PC);
    const t =
      (Math.log10(clamped) - Math.log10(DIST_MIN_PC)) /
      (Math.log10(DIST_MAX_PC) - Math.log10(DIST_MIN_PC));
    return round2(distTop + DIST_H - t * DIST_H);
  };

  const stackedAreas = useMemo(() => {
    const bottom = new Array(years.length).fill(0);
    const areas: { group: string; d: string }[] = [];
    for (const g of GROUPS) {
      const counts = data.method_share_counts_by_year[g];
      if (!counts) continue;
      const top = years.map((_, i) => {
        const total = data.total_count_by_year[i] || 1;
        const pct = (counts[i]! / total) * 100;
        return bottom[i] + pct;
      });
      const topPts = years.map((year, i) => [xAt(year), yShare(top[i]!)] as const);
      const bottomPts = years.map((year, i) => [xAt(year), yShare(bottom[i]!)] as const).reverse();
      const d =
        "M " +
        [...topPts, ...bottomPts].map(([x, y]) => `${x} ${y}`).join(" L ");
      areas.push({ group: g, d });
      for (let i = 0; i < years.length; i++) bottom[i] = top[i]!;
    }
    return areas;
    // xAt/yShare are pure functions of years/minYear/maxYear, recomputed each render deliberately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, years]);

  const distanceLines = useMemo(() => {
    return GROUPS.map((g) => {
      const q = data.distance_quantiles_pc_by_year[g];
      if (!q) return null;
      const firstIdx = q.median_pc.findIndex((v) => v !== null && v !== undefined);
      if (firstIdx === -1) return null;
      const medianPts = years
        .slice(firstIdx)
        .map((year, i) => [xAt(year), yDist(q.median_pc[firstIdx + i]!)] as const);
      const p90Pts = years
        .slice(firstIdx)
        .map((year, i) => [xAt(year), yDist(q.p90_pc[firstIdx + i] ?? q.median_pc[firstIdx + i]!)] as const);
      const medianD = "M " + medianPts.map(([x, y]) => `${x} ${y}`).join(" L ");
      const p90D = "M " + p90Pts.map(([x, y]) => `${x} ${y}`).join(" L ");
      return { group: g, medianD, p90D };
    }).filter(
      (v): v is { group: (typeof GROUPS)[number]; medianD: string; p90D: string } => v !== null,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, years]);

  const markerX = xAt(Math.max(minYear, Math.min(maxYear, currentYear)));
  const yearTicks = years.filter((y) => y % 5 === 0 || y === minYear || y === maxYear);

  return (
    <div className="panel p-4">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="font-[family-name:var(--font-display)] text-[15px] font-medium text-[var(--color-ivory)]">
          How the record grew, method by method
        </h3>
        <span className="eyebrow">through {currentYear}</span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Yearly method share and distance reach of the discovery record" className="w-full">
        {/* ---------------- chart 1: cumulative method share ---------------- */}
        <text x={PAD_L} y={shareTop - 2} fontSize={9} fill="var(--color-muted)" fontFamily="var(--font-mono)">
          Share of cumulative record
        </text>
        <rect x={PAD_L} y={shareTop} width={PLOT_W} height={SHARE_H} fill="none" stroke="var(--color-line)" />
        {[0, 50, 100].map((p) => (
          <g key={p}>
            <line x1={PAD_L} x2={PAD_L + PLOT_W} y1={yShare(p)} y2={yShare(p)} stroke="var(--color-line)" strokeDasharray="1 3" />
            <text x={PAD_L - 4} y={yShare(p) + 3} fontSize={8} textAnchor="end" fill="var(--color-faint)" fontFamily="var(--font-mono)">
              {p}%
            </text>
          </g>
        ))}
        <clipPath id="timeline-share-clip">
          <rect x={PAD_L} y={shareTop} width={PLOT_W} height={SHARE_H} />
        </clipPath>
        <g clipPath="url(#timeline-share-clip)">
          {stackedAreas.map(({ group, d }) => (
            <path key={group} d={d} fill={methodColour(group)} fillOpacity={0.55} stroke={methodColour(group)} strokeOpacity={0.8} strokeWidth={0.6} />
          ))}
        </g>

        {/* ---------------- chart 2: cumulative distance reach ---------------- */}
        <text x={PAD_L} y={distTop - 2} fontSize={9} fill="var(--color-muted)" fontFamily="var(--font-mono)">
          Median (solid) / 90th-percentile (dashed) distance reached, pc
        </text>
        <rect x={PAD_L} y={distTop} width={PLOT_W} height={DIST_H} fill="none" stroke="var(--color-line)" />
        {DIST_TICKS.map((pc) => (
          <g key={pc}>
            <line x1={PAD_L} x2={PAD_L + PLOT_W} y1={yDist(pc)} y2={yDist(pc)} stroke="var(--color-line)" strokeDasharray="1 3" />
            <text x={PAD_L - 4} y={yDist(pc) + 3} fontSize={8} textAnchor="end" fill="var(--color-faint)" fontFamily="var(--font-mono)">
              {pc >= 1000 ? `${pc / 1000}k` : pc}
            </text>
          </g>
        ))}
        <clipPath id="timeline-dist-clip">
          <rect x={PAD_L} y={distTop} width={PLOT_W} height={DIST_H} />
        </clipPath>
        <g clipPath="url(#timeline-dist-clip)">
          {distanceLines.map(({ group, medianD, p90D }) => (
            <g key={group}>
              <path d={p90D} fill="none" stroke={methodColour(group)} strokeOpacity={0.45} strokeDasharray="2 2" strokeWidth={1} />
              <path d={medianD} fill="none" stroke={methodColour(group)} strokeOpacity={0.95} strokeWidth={1.4} />
            </g>
          ))}
        </g>

        {/* ---------------- shared year axis + playback marker ---------------- */}
        {yearTicks.map((year) => (
          <text key={year} x={xAt(year)} y={distTop + DIST_H + 12} fontSize={8} textAnchor="middle" fill="var(--color-faint)" fontFamily="var(--font-mono)">
            {year}
          </text>
        ))}
        <line x1={markerX} x2={markerX} y1={shareTop} y2={distTop + DIST_H} stroke="var(--color-cyan)" strokeOpacity={0.8} strokeWidth={1} vectorEffect="non-scaling-stroke" />
      </svg>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
        {GROUPS.map((g) => (
          <span key={g} className="flex items-center gap-1.5 text-[10.5px] text-[var(--color-dim)]">
            <span className="inline-block size-2 rounded-full" style={{ background: methodColour(g) }} />
            {g}
          </span>
        ))}
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-[var(--color-muted)]">{data.note}</p>
    </div>
  );
}
