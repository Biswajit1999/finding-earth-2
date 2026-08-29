"use client";

/**
 * Two honest panels, not one dishonest one.
 *
 * A single linear scale cannot show both "where is the Sun in the Milky Way"
 * (a ~30 kpc galaxy) and "how far has each detection method actually reached"
 * (hundreds to a few thousand parsecs) without either panel being unreadable.
 * So: a full-galaxy overview at a real linear kpc scale, and a separate
 * Sun-centred local panel at a log-radial scale (same direction-preserving,
 * radius-compressing technique StarField.tsx already uses) for the shells.
 *
 * The Milky Way's own spiral structure drawn behind panel one is an
 * illustrative schematic -- we are inside the galaxy and cannot photograph
 * its shape from outside it -- and is labelled as such. Every point position,
 * the Sun's position, and every shell radius are real, computed from this
 * catalogue's actual measured coordinates.
 */

import { useMemo, useState } from "react";
import Link from "next/link";

import type { GalaxyFile } from "@/lib/types";
import { compactInt, methodColour, num, slugify } from "@/lib/format";

const NAMED_METHODS = [
  "Transit",
  "Radial Velocity",
  "Microlensing",
  "Imaging",
  "Transit Timing Variations",
] as const;

// Deterministic pseudo-random in [0,1) -- NOT Math.random(). The star-dust
// texture must render identically on the server and the client; a real RNG
// would reroll on every render and re-trigger the exact float-mismatch
// hydration bug already fixed once on this page (see gx/gy/lRadius above).
function hash(i: number): number {
  const s = Math.sin(i * 12.9898 + 78.233) * 43758.5453;
  return s - Math.floor(s);
}

/**
 * One arm of a logarithmic spiral, r = a * e^(b*theta) -- the standard
 * idealised model for a spiral galaxy's arms. The Milky Way is currently
 * modelled as two major stellar arms (Perseus, Scutum-Centaurus) attached to
 * a central bar, plus two more minor gas-dominated arms (Sagittarius,
 * Norma/Outer) -- real structure, established from infrared star-count
 * surveys (Benjamin et al. 2005, ApJ 630, L149), but this drawing is a
 * schematic shape, not a fit to any measured pitch angle or arm width.
 */
function SpiralArm({
  armIndex,
  colour,
  width,
  opacity,
  label,
}: {
  armIndex: number;
  colour: string;
  width: number;
  opacity: number;
  label: string;
}) {
  const a = 6;
  const b = 0.19;
  const offset = (armIndex * Math.PI) / 2;
  const points: { x: number; y: number }[] = [];
  for (let t = 0; t <= 620; t += 4) {
    const theta = (t / 100) * Math.PI + offset;
    const r = a * Math.exp(b * theta * 0.62);
    if (r > 178) break;
    points.push({ x: 250 + r * Math.cos(theta), y: 250 + r * Math.sin(theta) });
  }
  const d = points
    .map((p, i) => (i === 0 ? "M" : "L") + p.x.toFixed(1) + " " + p.y.toFixed(1))
    .join(" ");
  const end = points[points.length - 1];
  return (
    <>
      <path d={d} fill="none" stroke={colour} strokeWidth={width} strokeLinecap="round" opacity={opacity} />
      {end && (
        <text
          x={end.x.toFixed(1)} y={end.y.toFixed(1)}
          fontSize={7.5} fill={colour} opacity={0.75}
          textAnchor={end.x > 250 ? "start" : "end"}
          dx={end.x > 250 ? 4 : -4}
          fontFamily="var(--font-mono)"
        >
          {label}
        </text>
      )}
    </>
  );
}

const ARMS = [
  { colour: "var(--color-sci)", width: 13, opacity: 0.22, label: "Perseus Arm" },
  { colour: "var(--color-violet)", width: 9, opacity: 0.16, label: "Norma Arm" },
  { colour: "var(--color-sci)", width: 13, opacity: 0.22, label: "Scutum–Centaurus Arm" },
  { colour: "var(--color-violet)", width: 9, opacity: 0.16, label: "Sagittarius Arm" },
];

/** Fixed, deterministic star-dust scatter -- texture, not data. */
function StarDust({ count, seedOffset }: { count: number; seedOffset: number }) {
  const dots = [];
  for (let i = 0; i < count; i++) {
    const angle = hash(i + seedOffset) * Math.PI * 2;
    const r = 22 + Math.sqrt(hash(i + seedOffset + 900)) * 185;
    const x = (250 + r * Math.cos(angle)).toFixed(1);
    const y = (250 + r * Math.sin(angle)).toFixed(1);
    const rad = (0.4 + hash(i + seedOffset + 1800) * 0.7).toFixed(2);
    const op = (0.15 + hash(i + seedOffset + 2700) * 0.35).toFixed(2);
    dots.push(<circle key={i} cx={x} cy={y} r={rad} fill="var(--color-ivory)" opacity={op} />);
  }
  return <>{dots}</>;
}

export function GalaxyExplorer({
  data,
  deepDiveSlugs,
}: {
  data: GalaxyFile;
  /** Slugs with a full deep-dive page; most systems here don't have one. */
  deepDiveSlugs?: Set<string>;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const [g1Zoom, setG1Zoom] = useState(1);

  const shells = useMemo(
    () =>
      Object.entries(data.method_shells_pc).sort((a, b) => a[1] - b[1]),
    [data],
  );
  const maxShellPc = shells.length ? Math.max(...shells.map(([, v]) => v)) : 1000;

  /* ---------------- panel 1: full galaxy, real linear kpc scale ---------------- */
  const G_W = 500;
  const G_R = 210; // px for ~18 kpc, a generous Milky Way disk radius
  const G_KPC = 18;
  const gScale = G_R / G_KPC;
  // Rounded at the source: an unrounded float can stringify with a different
  // last digit between the server's Node/V8 build and the browser's, which
  // React's hydration check treats as a real mismatch.
  const round2 = (v: number) => Math.round(v * 100) / 100;
  const gx = (kpc: number) => round2(G_W / 2 + kpc * gScale);
  const gy = (kpc: number) => round2(G_W / 2 - kpc * gScale);
  const localExtentPc = maxShellPc * 1.15;

  // Every system, plotted at its real linear Galactocentric position -- the
  // same frame the Sun's own marker uses, not a separate compressed scale.
  // At full zoom-out this is a small, dense smear right on top of the Sun
  // (everything we've found so far really is that close to us); zooming in
  // resolves it into the actual cluster.
  // Zoom scales distance-from-the-Sun in kpc-space, then reprojects to
  // pixels -- not a naive SVG group scale(), which would also balloon
  // stroke widths and label text at high zoom. The Sun's own position
  // (kpc == sun_x/y_kpc) is the fixed point every zoom level pivots on.
  const gxZoomed = (kpc: number) =>
    round2(gx(data.sun_x_kpc) + (kpc - data.sun_x_kpc) * gScale * g1Zoom);
  const gyZoomed = (kpc: number) =>
    round2(gy(data.sun_y_kpc) - (kpc - data.sun_y_kpc) * gScale * g1Zoom);

  const galaxyPoints = useMemo(
    () => data.name.map((_, i) => ({ i, kx: data.x_kpc[i]!, ky: data.y_kpc[i]! })),
    [data],
  );
  const zoomG1 = (factor: number) =>
    setG1Zoom((z) => Math.min(Math.max(z * factor, 1), 40));

  /* ---------------- panel 2: local, log-radial, centred on the Sun ---------------- */
  const L_W = 560;
  const L_R = 250;
  const logMax = Math.log10(1 + localExtentPc);
  const lRadius = (pc: number) => round2((Math.log10(1 + Math.max(pc, 0)) / logMax) * L_R);

  const points = useMemo(() => {
    return data.name.map((name, i) => {
      const dxKpc = data.x_kpc[i]! - data.sun_x_kpc;
      const dyKpc = data.y_kpc[i]! - data.sun_y_kpc;
      const angle = Math.atan2(dyKpc, dxKpc);
      const r = lRadius(data.dist_pc[i]!);
      return {
        i,
        name,
        px: round2(L_W / 2 + r * Math.cos(angle)),
        py: round2(L_W / 2 + r * Math.sin(angle)),
        method: data.method[i],
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const info = selected !== null ? selected : null;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      <div className="grid gap-8 lg:grid-cols-2">
        {/* ---------------- panel 1 ---------------- */}
        <div className="panel p-5">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-medium">
              Where we are in the Milky Way
            </h2>
            <div className="flex items-center gap-2">
              <span className="eyebrow">illustrative background</span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => zoomG1(1.6)}
                  aria-label="Zoom in on the local cluster"
                  title="Zoom in on the local cluster"
                  className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-1.5 py-0.5 text-[11px] text-[var(--color-dim)] hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                >
                  +
                </button>
                <button
                  type="button"
                  onClick={() => zoomG1(1 / 1.6)}
                  aria-label="Zoom out"
                  title="Zoom out"
                  className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-1.5 py-0.5 text-[11px] text-[var(--color-dim)] hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                >
                  −
                </button>
                {g1Zoom !== 1 && (
                  <button
                    type="button"
                    onClick={() => setG1Zoom(1)}
                    className="cursor-pointer text-[10.5px] text-[var(--color-cyan)] hover:underline"
                  >
                    Reset
                  </button>
                )}
              </div>
            </div>
          </div>
          <svg viewBox={`0 0 ${G_W} ${G_W}`} role="img" aria-label="Schematic top-down map of the Milky Way showing the Sun's real position" className="w-full">
            <defs>
              <radialGradient id="galaxy-disk-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--color-sci)" stopOpacity={0.1} />
                <stop offset="70%" stopColor="var(--color-sci)" stopOpacity={0.03} />
                <stop offset="100%" stopColor="var(--color-sci)" stopOpacity={0} />
              </radialGradient>
              <radialGradient id="galaxy-bulge-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#ffe0a3" stopOpacity={0.55} />
                <stop offset="45%" stopColor="var(--color-gold)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--color-gold)" stopOpacity={0} />
              </radialGradient>
            </defs>

            <circle cx={G_W / 2} cy={G_W / 2} r={G_R} fill="url(#galaxy-disk-glow)" />
            <circle cx={G_W / 2} cy={G_W / 2} r={G_R} fill="none" stroke="var(--color-line)" strokeDasharray="2 4" />

            <StarDust count={170} seedOffset={0} />

            {ARMS.map((arm, i) => (
              <SpiralArm key={i} armIndex={i} colour={arm.colour} width={arm.width} opacity={arm.opacity} label={arm.label} />
            ))}

            {/* The central bar -- the Milky Way is now known to be a barred
                spiral (Benjamin et al. 2005), not a plain circular bulge. */}
            <ellipse
              cx={G_W / 2} cy={G_W / 2} rx={62} ry={20}
              transform={`rotate(25 ${G_W / 2} ${G_W / 2})`}
              fill="url(#galaxy-bulge-glow)"
            />
            <circle cx={G_W / 2} cy={G_W / 2} r={58} fill="url(#galaxy-bulge-glow)" />

            {/* Galactic Centre */}
            <circle cx={G_W / 2} cy={G_W / 2} r={2.5} fill="var(--color-ivory)" />
            <text x={G_W / 2} y={G_W / 2 - 10} fontSize={9} fill="var(--color-muted)" textAnchor="middle" fontFamily="var(--font-mono)">
              Galactic Centre
            </text>

            {/* The ring showing panel 2's extent, for scale */}
            <circle
              cx={gx(data.sun_x_kpc)} cy={gy(data.sun_y_kpc)}
              r={round2((localExtentPc / 1000) * gScale * g1Zoom)}
              fill="none" stroke="var(--color-cyan)" strokeOpacity={0.4} strokeDasharray="2 3"
            />

            {/* Every system we've actually found, at its real position --
                clipped to the panel so a high zoom doesn't paint outside it. */}
            <clipPath id="galaxy-panel-clip">
              <rect x={0} y={0} width={G_W} height={G_W} rx={4} />
            </clipPath>
            <g clipPath="url(#galaxy-panel-clip)">
              {galaxyPoints.map((p) => (
                <circle
                  key={p.i}
                  cx={gxZoomed(p.kx)} cy={gyZoomed(p.ky)}
                  r={1.1}
                  fill="var(--color-cyan)"
                  fillOpacity={0.55}
                />
              ))}
            </g>

            {/* The Sun -- real position, in its real home arm */}
            <circle cx={gx(data.sun_x_kpc)} cy={gy(data.sun_y_kpc)} r={7} fill="#ffd77a" opacity={0.18} />
            <circle cx={gx(data.sun_x_kpc)} cy={gy(data.sun_y_kpc)} r={4} fill="#ffd77a" />
            <text
              x={gx(data.sun_x_kpc)} y={gy(data.sun_y_kpc) - 9}
              fontSize={10} fill="var(--color-ivory)" textAnchor="middle" fontFamily="var(--font-mono)" fontWeight={600}
            >
              ☉ you are here
            </text>
            <text
              x={gx(data.sun_x_kpc)} y={gy(data.sun_y_kpc) + 16}
              fontSize={8} fill="var(--color-muted)" textAnchor="middle" fontFamily="var(--font-mono)"
            >
              Orion Spur (Local Arm)
            </text>

            <text x={G_W / 2} y={G_W - 8} fontSize={9} fill="var(--color-faint)" textAnchor="middle" fontFamily="var(--font-mono)">
              ~{G_KPC * 2} kpc across · linear scale
            </text>
          </svg>
          <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-muted)]">
            The spiral arms, central bar, and Orion Spur are drawn schematically — nobody has
            photographed the Milky Way from outside it — but the arm names and the barred
            structure are real, established from infrared star-count surveys (Benjamin et al.
            2005, ApJ 630, L149), not invented for this illustration. The Sun&apos;s position is
            real: {num(data.galcen_distance_kpc, 2)} kpc from the Galactic Centre (
            {data.galcen_distance_citation}), {num(data.sun_height_pc, 1)} pc above the midplane (
            {data.sun_height_citation}). The dashed cyan ring marks the extent of the panel on the
            right — everything we&apos;ve found so far is that small a fraction of the galaxy. The
            faint cyan dots are every one of the {compactInt(data.n_points)} systems in this
            catalogue, plotted at their real position — at this scale they sit almost on top of
            the Sun, which is itself the finding; use the{" "}
            <span className="font-[family-name:var(--font-mono)]">+</span> control above to zoom
            into the cluster and see it resolve. Zoomed in, one thin streak reaches toward the
            Galactic Centre — that is not planets being more common there. {data.galactic_centre_bulge_note}{" "}
            In this catalogue,{" "}
            {num(data.pct_within_10deg_of_galactic_centre_by_method["Microlensing"] ?? null, 1)}%
            of Microlensing detections fall within 10° of Sagittarius A* on the real sky, against{" "}
            {num(data.pct_within_10deg_of_galactic_centre_by_method["Transit"] ?? null, 1)}% for
            Transit and{" "}
            {num(data.pct_within_10deg_of_galactic_centre_by_method["Radial Velocity"] ?? null, 1)}%
            for Radial Velocity — computed straight from each system&apos;s archive right
            ascension and declination, independent of the Galactocentric coordinates plotted
            above.
          </p>
        </div>

        {/* ---------------- panel 2 ---------------- */}
        <div className="panel p-5">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-medium">
              How far each method has actually reached
            </h2>
            <span className="eyebrow">{compactInt(data.n_points)} systems</span>
          </div>
          <svg viewBox={`0 0 ${L_W} ${L_W}`} role="img" aria-label="Systems plotted around the Sun, with detection-distance shells per method" className="w-full">
            {shells.map(([method, pc]) => (
              <g key={method}>
                <circle
                  cx={L_W / 2} cy={L_W / 2} r={lRadius(pc)}
                  fill="none"
                  stroke={methodColour(method)}
                  strokeOpacity={0.35}
                  strokeDasharray="2 3"
                />
                <text
                  x={round2(L_W / 2 + lRadius(pc) * Math.cos(-0.35 - NAMED_METHODS.indexOf(method as (typeof NAMED_METHODS)[number]) * 0.5))}
                  y={round2(L_W / 2 + lRadius(pc) * Math.sin(-0.35 - NAMED_METHODS.indexOf(method as (typeof NAMED_METHODS)[number]) * 0.5))}
                  fontSize={9}
                  fill={methodColour(method)}
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                >
                  {method} · {compactInt(Math.round(pc))} pc
                </text>
              </g>
            ))}

            {points.map((p) => (
              <circle
                key={p.i}
                cx={p.px} cy={p.py} r={p.i === info ? 4 : 1.6}
                fill={methodColour(p.method)}
                fillOpacity={p.i === info ? 1 : 0.55}
                onClick={() => setSelected(p.i)}
                className="cursor-pointer"
              />
            ))}

            <circle cx={L_W / 2} cy={L_W / 2} r={5} fill="#ffd77a" />
            <text x={L_W / 2} y={L_W / 2 + 18} fontSize={9} fill="var(--color-ivory)" textAnchor="middle" fontFamily="var(--font-mono)">
              ☉ Sun
            </text>
          </svg>
          <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-muted)]">
            {data.method_shells_note} Radius is log-scaled (true 3-D distance from the Sun, same
            compression the 3-D map uses) so every shell stays legible at once; angle is each
            system&apos;s real projected direction.
          </p>

          {info !== null && (
            <div className="mt-3 border-t border-[var(--color-line)] pt-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-[13px] font-medium text-[var(--color-ivory)]">{data.name[info]}</p>
                  <p className="text-[11px] text-[var(--color-muted)]">{data.host[info]}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  aria-label="Close"
                  className="cursor-pointer text-[11px] text-[var(--color-muted)] hover:text-[var(--color-ivory)]"
                >
                  ✕
                </button>
              </div>
              <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 font-[family-name:var(--font-mono)] text-[11px]">
                <dt className="text-[var(--color-muted)]">Distance</dt>
                <dd className="text-[var(--color-dim)]">{num(data.dist_pc[info], 1)} pc</dd>
                <dt className="text-[var(--color-muted)]">Method</dt>
                <dd className="text-[var(--color-dim)]">{data.method[info] ?? "—"}</dd>
              </dl>
              {deepDiveSlugs?.has(slugify(data.name[info])) ? (
                <Link href={"/candidate/" + slugify(data.name[info])} className="link mt-2 inline-block text-[11.5px]">
                  Open deep dive →
                </Link>
              ) : (
                <p className="mt-2 text-[11px] text-[var(--color-muted)]">
                  Not one of the ranked candidates with a full deep-dive page.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
