"use client";

/**
 * Transit Lab.
 *
 * Shows the transit pipeline's validation run: real MAST light curves,
 * detrended, folded on the published ephemeris and fitted with a trapezoid,
 * compared against the published depth. These five targets are validation
 * instruments (bright hot Jupiters and sub-Neptunes chosen for signal
 * strength), not Earth-2.0 candidates -- a distinction stated on the page and
 * never blurred.
 */

import { useState } from "react";
import type { TransitValidationFile } from "@/lib/types";
import { num } from "@/lib/format";

export function TransitLab({ data }: { data: TransitValidationFile }) {
  const attempted = data.targets.filter((t) => t.folded_binned);
  const [active, setActive] = useState(0);
  const t = attempted[active];

  if (!t) {
    return (
      <div className="mx-auto max-w-[1400px] px-4 py-8 text-[13px] text-[var(--color-muted)] sm:px-6">
        No validated transit fits are available in this build.
      </div>
    );
  }

  const folded = t.folded_binned!;
  const W = 760;
  const H = 340;
  const padL = 52;
  const padB = 40;
  const padT = 16;
  const padR = 16;

  const xMin = Math.min(...folded.phase_hours);
  const xMax = Math.max(...folded.phase_hours);
  const yMin = Math.min(...folded.flux) - 0.0008;
  const yMax = Math.max(...folded.flux) + 0.0008;

  const xScale = (x: number) => padL + ((x - xMin) / (xMax - xMin || 1)) * (W - padL - padR);
  const yScale = (y: number) => H - padB - ((y - yMin) / (yMax - yMin || 1)) * (H - padT - padB);

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      <div className="mb-5 flex flex-wrap gap-2">
        {attempted.map((target, i) => (
          <button
            key={target.planet}
            type="button"
            onClick={() => setActive(i)}
            aria-pressed={active === i}
            className={`cursor-pointer rounded-[var(--radius-sm)] border px-3 py-1.5 text-[12.5px] transition-colors ${
              active === i
                ? "border-[var(--color-cyan)] text-[var(--color-cyan)]"
                : "border-[var(--color-line-strong)] text-[var(--color-dim)] hover:border-[var(--color-cyan)]"
            }`}
          >
            {target.planet}
            {target.validated ? (
              <span className="ml-1.5 text-[var(--color-verdant)]">✓</span>
            ) : (
              <span className="ml-1.5 text-[var(--color-rose)]">✕</span>
            )}
          </button>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div className="panel p-5">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-[family-name:var(--font-display)] text-xl font-medium">
              {t.planet}
            </h2>
            <p className="text-[12px] text-[var(--color-muted)]">{t.why}</p>
          </div>

          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={"Phase-folded transit light curve of " + t.planet} className="w-full">
            <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="var(--color-line-strong)" />
            <line x1={padL} y1={padT} x2={padL} y2={H - padB} stroke="var(--color-line-strong)" />
            <line x1={xScale(0)} y1={padT} x2={xScale(0)} y2={H - padB} stroke="var(--color-line)" strokeDasharray="2 3" />

            {folded.phase_hours.map((x, i) => (
              <g key={i}>
                <line
                  x1={xScale(x)} x2={xScale(x)}
                  y1={yScale(folded.flux[i]! - folded.flux_err[i]!)}
                  y2={yScale(folded.flux[i]! + folded.flux_err[i]!)}
                  stroke="var(--color-sci)" strokeOpacity={0.35} strokeWidth={1}
                />
                <circle cx={xScale(x)} cy={yScale(folded.flux[i]!)} r={2} fill="var(--color-sci)" fillOpacity={0.85} />
              </g>
            ))}

            <text x={W / 2} y={H - 6} fontSize={11} fill="var(--color-muted)" textAnchor="middle">
              Hours from mid-transit
            </text>
            <text x={12} y={H / 2} fontSize={11} fill="var(--color-muted)" textAnchor="middle" transform={`rotate(-90 12 ${H / 2})`}>
              Relative flux
            </text>
          </svg>
        </div>

        <div className="space-y-4">
          <div className="panel p-4">
            <p className="eyebrow mb-2">Fit vs. published</p>
            <Row label="Published depth" value={num(t.published_depth_ppm, 0) + " ppm"} />
            <Row label="Fitted depth" value={num(t.fitted_depth_ppm, 0) + " ppm"} />
            <Row
              label="Ratio"
              value={num(t.ratio_fitted_to_published, 3)}
              tone={t.validated ? "var(--color-verdant)" : "var(--color-rose)"}
            />
            <Row label="Depth S/N" value={num(t.depth_snr, 1)} />
            <Row label="Cadence precision" value={num(t.cadence_precision_ppm, 0) + " ppm"} />
          </div>
          <div
            className="panel border-l-2 p-4"
            style={{ borderColor: t.validated ? "var(--color-verdant)" : "var(--color-rose)" }}
          >
            <p className="text-[12.5px] leading-relaxed text-[var(--color-dim)]">
              {t.validated
                ? "This fit is consistent with the published depth within a factor of 1.6 and is treated as validated."
                : "This fit disagrees with the published depth by more than a factor of 1.6 and is NOT treated as a measurement."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-8 panel p-5">
        <p className="eyebrow mb-2">Why these targets, not the top candidates</p>
        <p className="text-[13px] leading-relaxed text-[var(--color-dim)]">{data.purpose}</p>
        <p className="mt-3 text-[13px] leading-relaxed text-[var(--color-dim)]">{data.systematic_note}</p>
        <p className="mt-3 font-[family-name:var(--font-mono)] text-[12px] text-[var(--color-muted)]">
          {data.n_validated} of {data.n_attempted} attempted targets validated · median ratio{" "}
          {num(data.median_ratio_fitted_to_published, 3)}
        </p>
      </div>
    </div>
  );
}

function Row({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--color-line)]/60 py-1.5 text-[12.5px]">
      <span className="text-[var(--color-muted)]">{label}</span>
      <span
        className="font-[family-name:var(--font-mono)] tabular-nums"
        style={{ color: tone ?? "var(--color-ivory)" }}
      >
        {value}
      </span>
    </div>
  );
}
