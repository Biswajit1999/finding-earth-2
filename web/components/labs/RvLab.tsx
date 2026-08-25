"use client";

/**
 * RV Lab.
 *
 * Radial-velocity time series from DACE with the periodogram and the mandatory
 * stellar-activity cross-check surfaced explicitly. A rotating, spotted star
 * imitates a planet; this lab shows the check that rules that out (or does
 * not) for each candidate with public RV data.
 */

import { useEffect, useMemo, useState } from "react";
import type { DeepDiveIndexEntry } from "@/lib/types";
import { num } from "@/lib/format";

interface RvDataset {
  status: string;
  dataset?: {
    n_measurements_used: number;
    baseline_years: number;
    instruments: Record<string, number>;
    median_uncertainty_ms: number | null;
    rv_rms_ms: number | null;
  };
  rv_periodogram?: {
    peaks: { period_days: number; power: number; fap: number }[];
    curve?: { period_days: number[]; power: number[] };
  };
  activity_periodograms?: Record<
    string,
    { label: string; peaks: { period_days: number; power: number }[] }
  >;
  n_activity_coincidences?: number;
  activity_coincidences?: { rv_period_days: number; indicator_label: string; indicator_period_days: number }[];
  keplerian_fit?: {
    ok: boolean;
    period_days: number;
    semi_amplitude_ms: number;
    semi_amplitude_err_ms: number;
    semi_amplitude_snr: number | null;
    reliable: boolean;
    unreliable_because: string[];
    msini_earth: number | null;
    folded?: { phase: number[]; rv_ms: number[]; rv_err_ms: number[] };
  };
}

export function RvLab({ entries }: { entries: DeepDiveIndexEntry[] }) {
  const withRv = useMemo(() => entries.filter((e) => e.has_rv_analysis), [entries]);
  const [active, setActive] = useState(0);
  const [rv, setRv] = useState<RvDataset | null>(null);
  const planetName = withRv[active]?.planet ?? "";

  useEffect(() => {
    const e = withRv[active];
    if (!e) return;
    // Clears the previous planet's data before the fetch below resolves, so it
    // can't render for a moment under the newly-selected planet's name.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRv(null);
    fetch((process.env.NEXT_PUBLIC_BASE_PATH ?? "") + "/data/deepdive/" + e.slug + ".json")
      .then((r) => r.json())
      .then((dd) => setRv(dd.rv_analysis))
      .catch(() => setRv(null));
  }, [active, withRv]);

  if (withRv.length === 0) {
    return (
      <div className="mx-auto max-w-[1400px] px-4 py-8 text-[13px] text-[var(--color-muted)] sm:px-6">
        No radial-velocity analyses are available in this build.
      </div>
    );
  }

  const fit = rv?.keplerian_fit;
  const folded = fit?.folded;

  const W = 700;
  const H = 300;
  const padL = 52;
  const padB = 36;
  const padT = 14;
  const padR = 14;
  const yMin = folded ? Math.min(...folded.rv_ms) - 1 : -1;
  const yMax = folded ? Math.max(...folded.rv_ms) + 1 : 1;
  const xScale = (x: number) => padL + x * (W - padL - padR);
  const yScale = (y: number) =>
    H - padB - ((y - yMin) / (yMax - yMin || 1)) * (H - padT - padB);

  // Periodogram: power vs. period on a log period axis (peaks span from
  // ~1 day to thousands of days, so a linear axis would crush the short
  // -period end where the planet signal actually lives).
  const curve = rv?.rv_periodogram?.curve;
  const pgPeaks = rv?.rv_periodogram?.peaks.slice(0, 5) ?? [];
  const coincidentPeriods = new Set(
    (rv?.activity_coincidences ?? []).map((c) => c.rv_period_days),
  );
  const PG_H = 190;
  const pgPadL = 52;
  const pgPadB = 30;
  const pgPadT = 12;
  const pgPadR = 14;
  let pgPathD = "";
  let pgX = (_p: number) => 0;
  let pgY = (_pw: number) => 0;
  let pgTicks: { period: number; label: string }[] = [];
  if (curve && curve.period_days.length > 0) {
    const periods = curve.period_days;
    const powers = curve.power;
    const pMin = Math.min(...periods);
    const pMax = Math.max(...periods);
    const logPMin = Math.log10(pMin);
    const logPMax = Math.log10(pMax);
    const maxPower = Math.max(...powers, ...pgPeaks.map((p) => p.power)) * 1.12;
    pgX = (p: number) =>
      pgPadL + ((Math.log10(p) - logPMin) / (logPMax - logPMin || 1)) * (W - pgPadL - pgPadR);
    pgY = (pw: number) => PG_H - pgPadB - (pw / (maxPower || 1)) * (PG_H - pgPadT - pgPadB);
    pgPathD = periods.map((p, i) => (i === 0 ? "M" : "L") + pgX(p) + " " + pgY(powers[i]!)).join(" ");
    pgTicks = [1, 10, 100, 1000, 10000]
      .filter((t) => t >= pMin && t <= pMax)
      .map((t) => ({ period: t, label: t >= 1000 ? t / 1000 + "k" : String(t) }));
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      <div className="mb-5 flex flex-wrap gap-2">
        {withRv.map((e, i) => (
          <button
            key={e.slug}
            type="button"
            onClick={() => setActive(i)}
            aria-pressed={active === i}
            className={`cursor-pointer rounded-[var(--radius-sm)] border px-3 py-1.5 text-[12.5px] transition-colors ${
              active === i
                ? "border-[var(--color-cyan)] text-[var(--color-cyan)]"
                : "border-[var(--color-line-strong)] text-[var(--color-dim)] hover:border-[var(--color-cyan)]"
            }`}
          >
            {e.planet}
          </button>
        ))}
      </div>

      {!rv ? (
        <p className="text-[13px] text-[var(--color-muted)]">Loading…</p>
      ) : (
        <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
          <div className="space-y-6">
            {folded && (
              <div className="panel p-5">
                <h2 className="mb-4 font-[family-name:var(--font-display)] text-xl font-medium">
                  {planetName} — phase-folded radial velocity
                </h2>
                <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={"Phase-folded RV curve of " + planetName} className="w-full">
                  <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="var(--color-line-strong)" />
                  <line x1={padL} y1={padT} x2={padL} y2={H - padB} stroke="var(--color-line-strong)" />
                  <line x1={padL} y1={yScale(0)} x2={W - padR} y2={yScale(0)} stroke="var(--color-line)" strokeDasharray="2 3" />
                  {folded.phase.map((x, i) => (
                    <g key={i}>
                      <line
                        x1={xScale(x)} x2={xScale(x)}
                        y1={yScale(folded.rv_ms[i]! - folded.rv_err_ms[i]!)}
                        y2={yScale(folded.rv_ms[i]! + folded.rv_err_ms[i]!)}
                        stroke="var(--color-gold)" strokeOpacity={0.35} strokeWidth={1}
                      />
                      <circle cx={xScale(x)} cy={yScale(folded.rv_ms[i]!)} r={2} fill="var(--color-gold)" fillOpacity={0.85} />
                    </g>
                  ))}
                  <text x={W / 2} y={H - 6} fontSize={11} fill="var(--color-muted)" textAnchor="middle">
                    Orbital phase
                  </text>
                  <text x={12} y={H / 2} fontSize={11} fill="var(--color-muted)" textAnchor="middle" transform={`rotate(-90 12 ${H / 2})`}>
                    RV (m/s)
                  </text>
                </svg>
              </div>
            )}

            {rv.rv_periodogram && curve && (
              <div className="panel p-5">
                <p className="eyebrow mb-3">
                  RV periodogram — Lomb-Scargle power vs. period
                </p>
                <svg
                  viewBox={`0 0 ${W} ${PG_H}`}
                  role="img"
                  aria-label={"Radial-velocity periodogram of " + planetName}
                  className="w-full"
                >
                  <line x1={pgPadL} y1={PG_H - pgPadB} x2={W - pgPadR} y2={PG_H - pgPadB} stroke="var(--color-line-strong)" />
                  <line x1={pgPadL} y1={pgPadT} x2={pgPadL} y2={PG_H - pgPadB} stroke="var(--color-line-strong)" />

                  {pgTicks.map((t) => (
                    <g key={t.period}>
                      <line
                        x1={pgX(t.period)} x2={pgX(t.period)} y1={pgPadT} y2={PG_H - pgPadB}
                        stroke="var(--color-line)" strokeDasharray="2 4" strokeOpacity={0.5}
                      />
                      <text x={pgX(t.period)} y={PG_H - pgPadB + 13} fontSize={9} fill="var(--color-muted)" textAnchor="middle" fontFamily="var(--font-mono)">
                        {t.label}d
                      </text>
                    </g>
                  ))}

                  <path d={pgPathD} fill="none" stroke="var(--color-sci)" strokeWidth={1} />

                  {pgPeaks.map((p, i) => {
                    const flagged = coincidentPeriods.has(p.period_days);
                    const colour = flagged ? "var(--color-rose)" : "var(--color-gold)";
                    return (
                      <g key={i}>
                        <title>
                          Peak at {num(p.period_days, 3)} d, power {num(p.power, 4)}, FAP{" "}
                          {p.fap.toExponential(2)}
                          {flagged ? " — coincides with a stellar-activity indicator period" : ""}
                        </title>
                        <line
                          x1={pgX(p.period_days)} x2={pgX(p.period_days)}
                          y1={pgY(p.power)} y2={PG_H - pgPadB}
                          stroke={colour} strokeOpacity={i === 0 ? 0.9 : 0.55} strokeWidth={i === 0 ? 1.5 : 1}
                        />
                        <circle cx={pgX(p.period_days)} cy={pgY(p.power)} r={i === 0 ? 3 : 2} fill={colour} />
                        {i < 3 && (
                          <text
                            x={pgX(p.period_days)} y={pgY(p.power) - 6} fontSize={9}
                            fill={colour} textAnchor="middle" fontFamily="var(--font-mono)"
                          >
                            {num(p.period_days, 2)}d
                          </text>
                        )}
                      </g>
                    );
                  })}

                  <text x={W / 2} y={PG_H - 3} fontSize={11} fill="var(--color-muted)" textAnchor="middle">
                    Period (days, log scale)
                  </text>
                  <text x={12} y={PG_H / 2} fontSize={11} fill="var(--color-muted)" textAnchor="middle" transform={`rotate(-90 12 ${PG_H / 2})`}>
                    Power
                  </text>
                </svg>
                <p className="mt-2 text-[11px] text-[var(--color-muted)]">
                  Gold peaks are candidate orbital periods.{" "}
                  {coincidentPeriods.size > 0
                    ? "A peak marked in rose coincides with a stellar-activity indicator period and should not be read as a planet on its own."
                    : "None of the top peaks coincide with a stellar-activity indicator period."}
                </p>
              </div>
            )}

            {rv.rv_periodogram && (
              <div className="panel p-5">
                <p className="eyebrow mb-3">RV periodogram — top peaks</p>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Period (days)</th>
                      <th scope="col">Power</th>
                      <th scope="col">False-alarm probability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rv.rv_periodogram.peaks.slice(0, 5).map((p, i) => (
                      <tr key={i}>
                        <td className="font-[family-name:var(--font-mono)] tabular-nums">{num(p.period_days, 3)}</td>
                        <td className="font-[family-name:var(--font-mono)] tabular-nums">{num(p.power, 4)}</td>
                        <td className="font-[family-name:var(--font-mono)] tabular-nums">{p.fap.toExponential(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="space-y-4">
            {rv.dataset && (
              <div className="panel p-4">
                <p className="eyebrow mb-2">Dataset</p>
                <SidebarRow label="Measurements" value={String(rv.dataset.n_measurements_used)} />
                <SidebarRow label="Baseline" value={num(rv.dataset.baseline_years, 1) + " yr"} />
                <SidebarRow label="Instruments" value={Object.keys(rv.dataset.instruments).join(", ")} />
                <SidebarRow label="Median uncertainty" value={num(rv.dataset.median_uncertainty_ms, 2) + " m/s"} />
              </div>
            )}

            <div
              className="panel border-l-2 p-4"
              style={{
                borderColor:
                  (rv.n_activity_coincidences ?? 0) > 0 ? "var(--color-rose)" : "var(--color-verdant)",
              }}
            >
              <p className="eyebrow mb-2">Stellar-activity cross-check</p>
              <p className="text-[13px] leading-relaxed text-[var(--color-dim)]">
                {(rv.n_activity_coincidences ?? 0) > 0
                  ? rv.n_activity_coincidences + " RV periodogram peak(s) coincide with a stellar-activity indicator period. Any such period must not be treated as a planet without further argument."
                  : "No RV periodogram peak coincides with a stellar-activity indicator period at this tolerance."}
              </p>
            </div>

            {fit && (
              <div
                className="panel border-l-2 p-4"
                style={{ borderColor: fit.reliable ? "var(--color-verdant)" : "var(--color-rose)" }}
              >
                <p className="eyebrow mb-2">Circular-orbit fit</p>
                <SidebarRow label="Period" value={num(fit.period_days, 4) + " d"} />
                <SidebarRow
                  label="Semi-amplitude"
                  value={num(fit.semi_amplitude_ms, 3) + " ± " + num(fit.semi_amplitude_err_ms, 3) + " m/s"}
                />
                <SidebarRow label="S/N" value={fit.semi_amplitude_snr !== null ? num(fit.semi_amplitude_snr, 1) : "—"} />
                {fit.reliable ? (
                  <p className="mt-2 text-[12px] text-[var(--color-verdant)]">
                    Reliable fit
                    {fit.msini_earth !== null ? ": M sin i = " + num(fit.msini_earth, 3) + " M⊕" : ""}
                  </p>
                ) : (
                  <p className="mt-2 text-[12px] leading-relaxed text-[var(--color-rose)]">
                    NOT reliable: {fit.unreliable_because.join("; ")}. No mass is
                    reported.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SidebarRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-[var(--color-line)]/60 py-1.5 text-[12px]">
      <span className="text-[var(--color-muted)]">{label}</span>
      <span className="font-[family-name:var(--font-mono)] text-right tabular-nums text-[var(--color-ivory)]">
        {value}
      </span>
    </div>
  );
}
