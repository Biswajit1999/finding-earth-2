"use client";

import { motion, useReducedMotion } from "motion/react";
import { useMemo, useState } from "react";

import { EvidenceLabel } from "@/components/observatory/EvidenceLabel";
import type { SelectionCell } from "@/lib/observatory-types";

function nearestIndex(values: number[], target: number): number {
  return values.reduce(
    (best, value, index) =>
      Math.abs(value - target) < Math.abs(values[best] - target) ? index : best,
    0,
  );
}

function pct(value: number): string {
  return `${(value * 100).toFixed(value < 0.01 ? 3 : 1)}%`;
}

export function SelectionSurfaceExplorer({
  cells,
  periods,
  radii,
}: {
  cells: SelectionCell[];
  periods: number[];
  radii: number[];
}) {
  const [periodIndex, setPeriodIndex] = useState(nearestIndex(periods, 365.25));
  const [radiusIndex, setRadiusIndex] = useState(nearestIndex(radii, 1));
  const reduced = useReducedMotion();
  const selected = useMemo(() => {
    const period = periods[periodIndex];
    const radius = radii[radiusIndex];
    return cells.reduce((best, cell) => {
      const distance = Math.abs(Math.log(cell.period_days / period)) + Math.abs(Math.log(cell.planet_radius_earth / radius));
      const bestDistance = Math.abs(Math.log(best.period_days / period)) + Math.abs(Math.log(best.planet_radius_earth / radius));
      return distance < bestDistance ? cell : best;
    });
  }, [cells, periodIndex, periods, radii, radiusIndex]);

  const maxSelection = Math.max(...cells.map((cell) => cell.mean_total_selection));

  return (
    <section className="mx-auto max-w-[1400px] px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="selection-explorer-title">
      <div className="grid gap-10 xl:grid-cols-[1fr_0.8fr]">
        <div>
          <p className="eyebrow text-[var(--color-cyan)]">Interactive selection surface</p>
          <h2 id="selection-explorer-title" className="mt-3 text-[length:var(--text-title)] font-light">
            Move through period–radius space
          </h2>
          <p className="mt-4 max-w-[70ch] text-sm leading-relaxed text-[var(--color-muted)]">
            Each cell asks how often a planet signal at this period and radius would transit, land in an observed phase window, pass the DR25 pipeline and survive vetting across the selected GK-dwarf targets.
          </p>

          <div className="mt-8 overflow-x-auto pb-2">
            <div
              className="grid w-max gap-1"
              style={{ gridTemplateColumns: `repeat(${periods.length}, 24px)` }}
              role="grid"
              aria-label="Kepler DR25 total selection probability by period and radius"
            >
              {[...radii].reverse().flatMap((radius) =>
                periods.map((period) => {
                  const cell = cells.find((item) => item.period_days === period && item.planet_radius_earth === radius);
                  if (!cell) return null;
                  const active = cell.period_days === selected.period_days && cell.planet_radius_earth === selected.planet_radius_earth;
                  const opacity = 0.08 + 0.92 * Math.sqrt(cell.mean_total_selection / maxSelection);
                  return (
                    <button
                      key={`${period}-${radius}`}
                      type="button"
                      role="gridcell"
                      aria-label={`${period.toFixed(1)} days, ${radius.toFixed(2)} Earth radii, ${pct(cell.mean_total_selection)} total selection probability`}
                      aria-selected={active}
                      title={`${period.toFixed(1)} d · ${radius.toFixed(2)} R⊕ · ${pct(cell.mean_total_selection)}`}
                      onClick={() => {
                        setPeriodIndex(periods.indexOf(period));
                        setRadiusIndex(radii.indexOf(radius));
                      }}
                      className={`size-6 cursor-pointer rounded-[1px] border transition-transform hover:scale-110 focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-cyan)] ${active ? "border-[var(--color-ivory)]" : "border-transparent"}`}
                      style={{ background: `color-mix(in srgb, var(--color-cyan) ${Math.round(opacity * 100)}%, var(--color-panel))` }}
                    />
                  );
                }),
              )}
            </div>
            <div className="mt-3 flex max-w-[520px] justify-between font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]">
              <span>{periods[0].toFixed(0)} d</span>
              <span>orbital period →</span>
              <span>{periods.at(-1)?.toFixed(0)} d</span>
            </div>
          </div>
        </div>

        <div className="panel-raised self-start p-6">
          <div className="flex items-center justify-between gap-3">
            <p className="eyebrow">Selected survey cell</p>
            <EvidenceLabel label={selected.label} />
          </div>
          <motion.div
            key={`${periodIndex}-${radiusIndex}`}
            initial={reduced ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24 }}
          >
            <p className="mt-6 font-[family-name:var(--font-mono)] text-2xl tabular-nums text-[var(--color-ivory)]">
              {selected.period_days.toFixed(1)} d · {selected.planet_radius_earth.toFixed(2)} R⊕
            </p>
            <dl className="mt-6 space-y-3 text-sm">
              {[
                ["Transit geometry", selected.mean_transit_geometry],
                ["Observed phase window", selected.mean_phase_window],
                ["Pipeline incl. window", selected.mean_pipeline_including_window],
                ["Vetting | recovered", selected.mean_vetting_given_recovered],
                ["Total selection", selected.mean_total_selection],
              ].map(([label, value]) => (
                <div key={String(label)} className="grid grid-cols-[1fr_auto] gap-4 border-b border-[var(--color-line)] pb-2">
                  <dt className="text-[var(--color-muted)]">{label}</dt>
                  <dd className="font-[family-name:var(--font-mono)] tabular-nums text-[var(--color-ivory)]">{pct(Number(value))}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-5 text-xs leading-relaxed text-[var(--color-muted)]">
              Equivalent exposure: <span className="font-[family-name:var(--font-mono)] text-[var(--color-gold)]">{selected.effective_stars.toFixed(1)} stars</span>. This is detection exposure, not an inferred planet count.
            </p>
          </motion.div>
          <div className="mt-7 space-y-5">
            <label className="block text-xs text-[var(--color-dim)]">
              Orbital period · {periods[periodIndex].toFixed(1)} days
              <input className="mt-2 w-full accent-[var(--color-cyan)]" type="range" min={0} max={periods.length - 1} value={periodIndex} onChange={(event) => setPeriodIndex(Number(event.target.value))} />
            </label>
            <label className="block text-xs text-[var(--color-dim)]">
              Planet radius · {radii[radiusIndex].toFixed(2)} R⊕
              <input className="mt-2 w-full accent-[var(--color-cyan)]" type="range" min={0} max={radii.length - 1} value={radiusIndex} onChange={(event) => setRadiusIndex(Number(event.target.value))} />
            </label>
          </div>
        </div>
      </div>
    </section>
  );
}

