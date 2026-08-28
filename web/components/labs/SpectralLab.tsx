"use client";

/**
 * Spectral Lab.
 *
 * Renders published transmission spectra with expected molecular band
 * positions overlaid. The overlay is explicitly labelled as band POSITIONS,
 * never as detections: a dashed line at 1.4 microns says "water absorbs here",
 * not "water was found here".
 */

import { useEffect, useMemo, useState } from "react";

import { assetPath } from "@/lib/assets";
import type { SpectraIndexRow } from "@/lib/types";
import { num, slugify } from "@/lib/format";

const BAND_COLOURS: Record<string, string> = {
  primary: "var(--color-gold)",
  biosignature_context: "var(--color-rose)",
  secondary: "var(--color-muted)",
};

interface SpecPoint {
  wavelength_um: number;
  depth_ppm: number;
  depth_ppm_err: number | null;
}

export function SpectralLab({ index }: { index: SpectraIndexRow[] }) {
  const transmission = useMemo(
    () => index.filter((r) => r.kind === "transmission").sort((a, b) => b.n_points - a.n_points),
    [index],
  );

  const [planet, setPlanet] = useState<string>(transmission[0]?.pl_name ?? "");
  const [points, setPoints] = useState<SpecPoint[] | null>(null);
  const [bands, setBands] = useState<
    { species: string; label: string; bands_um: number[]; colour_role: string; biosignature_relevance?: string }[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [caveat, setCaveat] = useState<string>("");
  // null = fully zoomed out (shows the whole spectrum). Reset on every planet
  // switch so the zoom from one spectrum never carries over to the next.
  const [zoom, setZoom] = useState<[number, number] | null>(null);

  const load = async (name: string) => {
    setPlanet(name);
    setLoading(true);
    setPoints(null);
    setZoom(null);
    try {
      const slug = slugify(name);
      const res = await fetch(
        assetPath("/data/spectra/" + slug + ".json"),
      );
      if (!res.ok) return;
      const spec = await res.json();
      if (spec?.points) {
        setPoints(spec.points);
        setBands(spec.expected_bands ?? []);
        setCaveat(spec.caveat ?? "");
      }
    } finally {
      setLoading(false);
    }
  };

  // useEffect, not useMemo: this must run only after the client mounts. A
  // static export still does a server render pass for this "use client"
  // component, and Node's fetch rejects a relative URL like "/data/...", so
  // running the load during that pass throws on every build.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (planet) void load(planet);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fullWlRange: [number, number] = points && points.length
    ? [Math.min(...points.map((p) => p.wavelength_um)), Math.max(...points.map((p) => p.wavelength_um))]
    : [0.3, 5];
  const wlRange = zoom ?? fullWlRange;

  const visiblePoints = (points ?? []).filter(
    (p) => p.wavelength_um >= wlRange[0] && p.wavelength_um <= wlRange[1],
  );
  const depthSource = visiblePoints.length ? visiblePoints : points ?? [];
  const depthRange = depthSource.length
    ? [Math.min(...depthSource.map((p) => p.depth_ppm)), Math.max(...depthSource.map((p) => p.depth_ppm))]
    : [0, 1];

  // Flatten every (species, wavelength) band instance visible in the current
  // zoom window, then greedily pack their labels into as few stacked rows
  // ("lanes") as needed so that no two labels ever overlap horizontally --
  // dense clusters (several species absorbing within a few tenths of a
  // micron of each other) get more rows instead of garbled overlapping text.
  const visibleBandInstances = bands.flatMap((b) =>
    b.bands_um
      .filter((wl) => wl >= wlRange[0] && wl <= wlRange[1])
      .map((wl) => ({ ...b, wl })),
  );

  const W = 760;
  const H = 380;
  const padL = 56;
  const padB = 40;
  const padR = 16;
  const LANE_HEIGHT = 11;
  const BASE_PAD_T = 16;

  const bandXScale = (wl: number) =>
    padL + ((wl - wlRange[0]) / (wlRange[1] - wlRange[0] || 1)) * (W - padL - padR);

  const estCharWidth = 5.2; // px per character at the 9px mono label font
  const labelGap = 6;
  const laneRightEdge: number[] = [];
  const laidOutBands = visibleBandInstances
    .slice()
    .sort((a, b) => bandXScale(a.wl) - bandXScale(b.wl))
    .map((b) => {
      const x = bandXScale(b.wl);
      const halfWidth = (b.species.length * estCharWidth) / 2;
      let lane = 0;
      while (lane < laneRightEdge.length && x - halfWidth < laneRightEdge[lane]! + labelGap) {
        lane++;
      }
      laneRightEdge[lane] = x + halfWidth;
      return { ...b, x, lane };
    });
  const numLanes = laneRightEdge.length;
  const padT = BASE_PAD_T + numLanes * LANE_HEIGHT;

  const xScale = bandXScale;
  const yScale = (d: number) => {
    const span = depthRange[1]! - depthRange[0]! || 1;
    const pad = span * 0.12;
    return H - padB - ((d - (depthRange[0]! - pad)) / (span + 2 * pad)) * (H - padT - padB);
  };

  const zoomBy = (factor: number) => {
    const [lo, hi] = zoom ?? fullWlRange;
    const center = (lo + hi) / 2;
    const fullSpan = fullWlRange[1] - fullWlRange[0];
    const halfSpan = Math.max(((hi - lo) * factor) / 2, fullSpan * 0.01);
    let newLo = center - halfSpan;
    let newHi = center + halfSpan;
    if (newLo < fullWlRange[0]) {
      newHi += fullWlRange[0] - newLo;
      newLo = fullWlRange[0];
    }
    if (newHi > fullWlRange[1]) {
      newLo -= newHi - fullWlRange[1];
      newHi = fullWlRange[1];
    }
    newLo = Math.max(newLo, fullWlRange[0]);
    newHi = Math.min(newHi, fullWlRange[1]);
    setZoom(newHi - newLo >= fullSpan * 0.999 ? null : [newLo, newHi]);
  };
  const isZoomed = zoom !== null;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      <div className="grid gap-8 lg:grid-cols-[300px_1fr]">
        <div className="panel h-fit p-4 lg:sticky lg:top-20">
          <p className="eyebrow mb-3">
            Planets with published spectra ({transmission.length})
          </p>
          <ul className="max-h-[70vh] space-y-0.5 overflow-y-auto">
            {transmission.map((r) => (
              <li key={r.pl_name}>
                <button
                  type="button"
                  onClick={() => load(r.pl_name)}
                  aria-current={planet === r.pl_name}
                  className={`flex w-full cursor-pointer items-center justify-between rounded-[var(--radius-sm)] px-2.5 py-1.5 text-left text-[12.5px] transition-colors ${
                    planet === r.pl_name
                      ? "bg-[var(--color-panel)] text-[var(--color-cyan)]"
                      : "text-[var(--color-dim)] hover:bg-[var(--color-panel)]"
                  }`}
                >
                  <span>{r.pl_name}</span>
                  <span className="font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-muted)]">
                    {r.n_points}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div>
          {loading && <p className="text-[13px] text-[var(--color-muted)]">Loading spectrum…</p>}
          {!loading && points && (
            <div className="panel p-5">
              <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-[family-name:var(--font-display)] text-xl font-medium">
                  {planet}
                </h2>
                <div className="flex items-center gap-3">
                  <p className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
                    {visiblePoints.length} points · {num(wlRange[0], 2)}–{num(wlRange[1], 2)} μm
                  </p>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => zoomBy(1 / 1.6)}
                      aria-label="Zoom in"
                      title="Zoom in"
                      className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[12px] text-[var(--color-dim)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                    >
                      +
                    </button>
                    <button
                      type="button"
                      onClick={() => zoomBy(1.6)}
                      aria-label="Zoom out"
                      title="Zoom out"
                      className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[12px] text-[var(--color-dim)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                    >
                      −
                    </button>
                    {isZoomed && (
                      <button
                        type="button"
                        onClick={() => setZoom(null)}
                        className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-2 py-0.5 text-[11px] text-[var(--color-dim)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={"Transmission spectrum of " + planet} className="w-full">
                {/* axes */}
                <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="var(--color-line-strong)" />
                <line x1={padL} y1={padT} x2={padL} y2={H - padB} stroke="var(--color-line-strong)" />

                {/* band overlays: each label is packed into the first lane
                    (stacked row) where it doesn't collide with a label
                    already placed there, so dense clusters spread upward
                    instead of overlapping into unreadable text. */}
                {laidOutBands.map((b, i) => {
                  const labelY = padT - 4 - b.lane * LANE_HEIGHT;
                  const colour = BAND_COLOURS[b.colour_role] ?? "var(--color-muted)";
                  return (
                    <g key={b.species + i}>
                      <title>
                        {b.label} ({b.species}) — absorption feature near {num(b.wl, 3)} μm.
                        {b.biosignature_relevance ? " " + b.biosignature_relevance : ""}
                      </title>
                      <line
                        x1={b.x} x2={b.x} y1={labelY + 6} y2={H - padB}
                        stroke={colour}
                        strokeDasharray="3 3" strokeOpacity={0.55} strokeWidth={1}
                      />
                      <text
                        x={b.x} y={labelY} fontSize={9}
                        fill={colour}
                        textAnchor="middle" fontFamily="var(--font-mono)"
                      >
                        {b.species}
                      </text>
                    </g>
                  );
                })}

                {/* data */}
                {visiblePoints.map((p, i) => (
                  <g key={i}>
                    {p.depth_ppm_err !== null && (
                      <line
                        x1={xScale(p.wavelength_um)} x2={xScale(p.wavelength_um)}
                        y1={yScale(p.depth_ppm - p.depth_ppm_err)}
                        y2={yScale(p.depth_ppm + p.depth_ppm_err)}
                        stroke="var(--color-sci)" strokeOpacity={0.4} strokeWidth={1}
                      />
                    )}
                    <circle cx={xScale(p.wavelength_um)} cy={yScale(p.depth_ppm)} r={2} fill="var(--color-sci)" fillOpacity={0.85} />
                  </g>
                ))}

                <text x={W / 2} y={H - 6} fontSize={11} fill="var(--color-muted)" textAnchor="middle">
                  Wavelength (μm)
                </text>
                <text x={14} y={H / 2} fontSize={11} fill="var(--color-muted)" textAnchor="middle" transform={`rotate(-90 14 ${H / 2})`}>
                  Transit depth (ppm)
                </text>
              </svg>

              <p className="mt-3 text-[11px] text-[var(--color-muted)]">
                Hover a dashed line for the chemical&apos;s full name, its exact wavelength in
                microns, and why it matters as biosignature evidence (or doesn&apos;t).
              </p>
              <p className="mt-2 border-t border-[var(--color-line)] pt-3 text-[12px] leading-relaxed text-[var(--color-rose)]">
                {caveat || "Dashed lines mark where a species absorbs. They are expected band positions, not detections."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
