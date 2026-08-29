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

function SpiralArm({ armIndex, colour }: { armIndex: number; colour: string }) {
  // A logarithmic spiral, r = a * e^(b*theta) -- the standard idealised model
  // for a galaxy's spiral arms. This is a schematic shape, not a fit to any
  // measured arm pitch angle.
  const a = 6;
  const b = 0.19;
  const offset = (armIndex * Math.PI * 2) / 2;
  const points: string[] = [];
  for (let t = 0; t <= 620; t += 4) {
    const theta = (t / 100) * Math.PI + offset;
    const r = a * Math.exp(b * theta * 0.62);
    if (r > 175) break;
    const x = 250 + r * Math.cos(theta);
    const y = 250 + r * Math.sin(theta);
    points.push((points.length === 0 ? "M" : "L") + x.toFixed(1) + " " + y.toFixed(1));
  }
  return (
    <path
      d={points.join(" ")}
      fill="none"
      stroke={colour}
      strokeWidth={10}
      strokeLinecap="round"
      opacity={0.14}
    />
  );
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
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-medium">
              Where we are in the Milky Way
            </h2>
            <span className="eyebrow">illustrative background</span>
          </div>
          <svg viewBox={`0 0 ${G_W} ${G_W}`} role="img" aria-label="Schematic top-down map of the Milky Way showing the Sun's real position" className="w-full">
            <circle cx={G_W / 2} cy={G_W / 2} r={G_R} fill="none" stroke="var(--color-line)" strokeDasharray="2 4" />
            <circle cx={G_W / 2} cy={G_W / 2} r={70} fill="var(--color-gold)" opacity={0.1} />
            <circle cx={G_W / 2} cy={G_W / 2} r={38} fill="var(--color-gold)" opacity={0.14} />
            {[0, 1].map((i) => (
              <SpiralArm key={i} armIndex={i} colour="var(--color-sci)" />
            ))}
            {/* Galactic Centre */}
            <circle cx={G_W / 2} cy={G_W / 2} r={2.5} fill="var(--color-ivory)" />
            <text x={G_W / 2} y={G_W / 2 - 10} fontSize={9} fill="var(--color-muted)" textAnchor="middle" fontFamily="var(--font-mono)">
              Galactic Centre
            </text>

            {/* The ring showing panel 2's extent, for scale */}
            <circle
              cx={gx(data.sun_x_kpc)} cy={gy(data.sun_y_kpc)}
              r={round2((localExtentPc / 1000) * gScale)}
              fill="none" stroke="var(--color-cyan)" strokeOpacity={0.4} strokeDasharray="2 3"
            />

            {/* The Sun -- real position */}
            <circle cx={gx(data.sun_x_kpc)} cy={gy(data.sun_y_kpc)} r={4} fill="#ffd77a" />
            <text
              x={gx(data.sun_x_kpc)} y={gy(data.sun_y_kpc) - 9}
              fontSize={10} fill="var(--color-ivory)" textAnchor="middle" fontFamily="var(--font-mono)" fontWeight={600}
            >
              ☉ you are here
            </text>

            <text x={G_W / 2} y={G_W - 8} fontSize={9} fill="var(--color-faint)" textAnchor="middle" fontFamily="var(--font-mono)">
              ~{G_KPC * 2} kpc across · linear scale
            </text>
          </svg>
          <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-muted)]">
            The spiral structure is a schematic illustration, not measured data — nobody has
            photographed the Milky Way from outside it. The Sun&apos;s position is real:{" "}
            {num(data.galcen_distance_kpc, 2)} kpc from the Galactic Centre (
            {data.galcen_distance_citation}), {num(data.sun_height_pc, 1)} pc above the midplane (
            {data.sun_height_citation}). The dashed cyan ring marks the extent of the panel on the
            right — everything we&apos;ve found so far is that small a fraction of the galaxy.
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
