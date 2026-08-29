"use client";

/**
 * 2D sky-projection view -- a genuine fallback, not a miniature of the 3D map.
 *
 * The Cartesian view answers "where is this system in space, relative to the
 * Sun". This one answers a different, older question: "where do we look to
 * see it" -- each system's real Galactic longitude/latitude (l, b), exactly
 * as computed by the Python export (`export_universe`'s `gal_l_deg`/
 * `gal_b_deg`, via astropy) and never re-derived here. It needs no WebGL, so
 * it works everywhere the 3D map cannot, and it uses the identical colour
 * encoding as StarField so switching views never looks like switching data.
 */

import { useMemo, useState } from "react";

import type { UniverseFile } from "@/lib/types";
import {
  METHOD_COLOURS,
  distanceColour,
  indexColour,
  teffColour,
  type ColourMode,
} from "@/components/three/StarField";

const W = 740;
const H = 400;
const PAD = 12;
const PLOT_W = W - PAD * 2;
const PLOT_H = H - PAD * 2;

// Longitude increases to the LEFT and the Galactic Centre sits at the centre
// of the plot -- the convention used by most published all-sky Galactic
// maps, since we are looking outward from inside the disk.
function lx(lDeg: number): number {
  const wrapped = lDeg > 180 ? lDeg - 360 : lDeg;
  return PAD + ((180 - wrapped) / 360) * PLOT_W;
}
function by(bDeg: number): number {
  return PAD + ((90 - bDeg) / 180) * PLOT_H;
}

function rgbToCss([r, g, b]: [number, number, number]): string {
  const lift = (channel: number) => Math.min(1, channel * 1.25 + 0.035);
  return `rgb(${Math.round(lift(r) * 255)}, ${Math.round(lift(g) * 255)}, ${Math.round(lift(b) * 255)})`;
}

const L_TICKS = [-180, -90, 0, 90, 180];
const B_TICKS = [-90, -45, 0, 45, 90];

export function SkyProjection({
  data,
  colourMode = "index",
  visibleMask,
  highlightIndices,
  onSelect,
  flagLowConfidenceAstrometry = false,
}: {
  data: UniverseFile;
  colourMode?: ColourMode;
  /** When present, index i is hidden unless visibleMask[i] is truthy. */
  visibleMask?: Uint8Array;
  highlightIndices?: Set<number>;
  onSelect?: (index: number) => void;
  flagLowConfidenceAstrometry?: boolean;
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  const points = useMemo(() => {
    const out: {
      i: number;
      x: number;
      y: number;
      colour: string;
      opacity: number;
    }[] = [];
    for (let i = 0; i < data.n_points; i++) {
      if (visibleMask && !visibleMask[i]) continue;
      const l = data.gal_l_deg[i];
      const b = data.gal_b_deg[i];
      if (l === null || l === undefined || b === null || b === undefined) continue;

      let c: [number, number, number];
      switch (colourMode) {
        case "teff":
          c = teffColour(data.st_teff[i] ?? null);
          break;
        case "method":
          c = METHOD_COLOURS[data.method[i] ?? ""] ?? [0.42, 0.46, 0.54];
          break;
        case "distance":
          c = distanceColour(data.dist_pc[i] ?? 1);
          break;
        default:
          c = indexColour(data.earth2_index[i] ?? null);
      }

      const ruwe = data.gaia_ruwe[i];
      const dimmed = flagLowConfidenceAstrometry && ruwe !== null && ruwe > 1.4;

      out.push({
        i,
        x: Math.round(lx(l) * 100) / 100,
        y: Math.round(by(b) * 100) / 100,
        colour: rgbToCss(c),
        opacity: dimmed ? 0.22 : 0.75,
      });
    }
    return out;
  }, [data, colourMode, visibleMask, flagLowConfidenceAstrometry]);

  const info = hovered !== null ? hovered : null;

  return (
    <div className="relative h-full w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="All-sky map of every system's real Galactic longitude and latitude"
        className="h-full w-full"
      >
        <defs>
          <radialGradient id="sky-bulge-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--color-gold)" stopOpacity={0.14} />
            <stop offset="100%" stopColor="var(--color-gold)" stopOpacity={0} />
          </radialGradient>
        </defs>

        <rect x={PAD} y={PAD} width={PLOT_W} height={PLOT_H} fill="none" stroke="var(--color-line)" />

        {/* A faint glow around the Galactic Centre direction -- an orientation
            cue, not a claim about planet density; the caption below states
            plainly why detections cluster there. */}
        <circle cx={lx(0)} cy={by(0)} r={70} fill="url(#sky-bulge-glow)" />

        {L_TICKS.map((t) => (
          <line
            key={"l" + t}
            x1={lx(t)} x2={lx(t)}
            y1={PAD} y2={PAD + PLOT_H}
            stroke="var(--color-line)"
            strokeDasharray="1 4"
          />
        ))}
        {B_TICKS.map((t) => (
          <line
            key={"b" + t}
            x1={PAD} x2={PAD + PLOT_W}
            y1={by(t)} y2={by(t)}
            stroke="var(--color-line)"
            strokeDasharray="1 4"
          />
        ))}

        {L_TICKS.map((t) => (
          <text
            key={"lt" + t}
            x={lx(t)}
            y={PAD + PLOT_H + 11}
            fontSize={8.5}
            fill="var(--color-faint)"
            textAnchor="middle"
            fontFamily="var(--font-mono)"
          >
            {t === 0 ? "0° (GC)" : t === 180 || t === -180 ? "180°" : `${t}°`}
          </text>
        ))}
        {B_TICKS.map((t) => (
          <text
            key={"bt" + t}
            x={PAD - 4}
            y={by(t) + 3}
            fontSize={8.5}
            fill="var(--color-faint)"
            textAnchor="end"
            fontFamily="var(--font-mono)"
          >
            {t}°
          </text>
        ))}

        <text
          x={lx(0)} y={PAD - 3}
          fontSize={9} fill="var(--color-muted)" textAnchor="middle" fontFamily="var(--font-mono)"
        >
          Galactic Centre
        </text>

        {points.map((p) => {
          const hot = highlightIndices?.has(p.i) ?? false;
          return (
            <circle
              key={p.i}
              cx={p.x}
              cy={p.y}
              r={hot ? 4.5 : 1.4}
              fill={hot ? "#ffd977" : p.colour}
              fillOpacity={hot ? 1 : p.opacity}
              onClick={onSelect ? () => onSelect(p.i) : undefined}
              onMouseEnter={() => setHovered(p.i)}
              onMouseLeave={() => setHovered((h) => (h === p.i ? null : h))}
              className={onSelect ? "cursor-pointer" : undefined}
            />
          );
        })}
      </svg>

      {info !== null && (
        <div
          className="pointer-events-none absolute left-1/2 top-2 -translate-x-1/2 rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)]/90 px-2 py-1 text-[11px] text-[var(--color-ivory)]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {data.name[info]}
        </div>
      )}
    </div>
  );
}
