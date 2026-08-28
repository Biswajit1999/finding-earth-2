"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { num, sig, slugify } from "@/lib/format";
import type { CatalogueFile, Maybe } from "@/lib/types";

type Lane = "timing" | "atmosphere" | "rv" | "imaging";

const LANES: Array<{
  key: Lane;
  label: string;
  eyebrow: string;
  description: string;
}> = [
  {
    key: "timing",
    label: "Transit timing",
    eyebrow: "Can we recover the event?",
    description:
      "One-sigma transit-time uncertainty propagated to 2030-01-01 from published midpoint and period errors. TTV systems need a non-linear timing model.",
  },
  {
    key: "atmosphere",
    label: "Atmospheres",
    eyebrow: "Relative screening metrics",
    description:
      "Kempton et al. TSM and ESM compare relative signal-to-noise potential. They are not exposure-time calculators and are defined only for transiting systems.",
  },
  {
    key: "rv",
    label: "Radial velocity",
    eyebrow: "Expected dynamical signal",
    description:
      "Expected Keplerian semi-amplitude from the adopted mass and orbit. Stellar activity, cadence, and instrument noise are separate requirements.",
  },
  {
    key: "imaging",
    label: "Reflected light",
    eyebrow: "Geometry and contrast scenario",
    description:
      "Maximum angular-separation scale plus Lambertian quadrature contrast at geometric albedo 0.30. These are not instrument detectability claims.",
  },
];

function valueAt(values: Maybe[] | undefined, index: number): number | null {
  return values?.[index] ?? null;
}

export function FollowUpLab({ file }: { file: CatalogueFile }) {
  const [lane, setLane] = useState<Lane>("timing");
  const [query, setQuery] = useState("");
  const [topCandidatesOnly, setTopCandidatesOnly] = useState(true);
  const columns = file.columns;
  const laneInfo = LANES.find((item) => item.key === lane) ?? LANES[0];

  const rows = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    const indices = Array.from({ length: file.n_rows }, (_, index) => index);
    const metric = (index: number): number | null => {
      if (lane === "timing") {
        return valueAt(columns.ephemeris_uncertainty_2030_minutes, index);
      }
      if (lane === "atmosphere") {
        return valueAt(columns.tsm, index) ?? valueAt(columns.esm, index);
      }
      if (lane === "rv") return valueAt(columns.rv_semi_amplitude_ms, index);
      return valueAt(columns.max_angular_separation_mas, index);
    };

    return indices
      .filter((index) => !columns.is_control[index])
      .filter((index) => metric(index) !== null)
      .filter((index) => {
        if (!topCandidatesOnly) return true;
        const rank = columns.earth2_rank[index];
        return rank !== null && rank <= 250;
      })
      .filter((index) => {
        if (!needle) return true;
        return `${columns.pl_name[index]} ${columns.hostname[index]}`
          .toLocaleLowerCase()
          .includes(needle);
      })
      .sort((a, b) => {
        const av = metric(a) ?? Number.POSITIVE_INFINITY;
        const bv = metric(b) ?? Number.POSITIVE_INFINITY;
        return lane === "timing" ? av - bv : bv - av;
      })
      .slice(0, 200);
  }, [columns, file.n_rows, lane, query, topCandidatesOnly]);

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div>
          <div
            className="grid grid-cols-2 gap-2 sm:grid-cols-4"
            role="group"
            aria-label="Follow-up pathway"
          >
            {LANES.map((item) => (
              <button
                key={item.key}
                type="button"
                aria-pressed={lane === item.key}
                onClick={() => setLane(item.key)}
                className={`min-h-11 cursor-pointer rounded-[var(--radius-md)] border px-3 py-2 text-[12.5px] transition-colors ${
                  lane === item.key
                    ? "border-[var(--color-cyan)] bg-[var(--color-panel)] text-[var(--color-ivory)]"
                    : "border-[var(--color-line)] text-[var(--color-dim)] hover:border-[var(--color-line-strong)] hover:text-[var(--color-ivory)]"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="sr-only" htmlFor="follow-up-search">
              Search planets or host stars
            </label>
            <input
              id="follow-up-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search planet or host…"
              className="min-h-11 flex-1 rounded-[var(--radius-md)] border border-[var(--color-line)] bg-[var(--color-deep)] px-3 text-[13px] text-[var(--color-ivory)] outline-none placeholder:text-[var(--color-muted)] focus:border-[var(--color-cyan)]"
            />
            <label className="flex min-h-11 cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-line)] px-3 text-[12px] text-[var(--color-dim)]">
              <input
                type="checkbox"
                checked={topCandidatesOnly}
                onChange={(event) => setTopCandidatesOnly(event.target.checked)}
                className="accent-[var(--color-cyan)]"
              />
              Top 250 Earth-2.0 candidates
            </label>
          </div>
        </div>

        <aside className="panel p-4" aria-live="polite">
          <p className="eyebrow">{laneInfo.eyebrow}</p>
          <p className="mt-2 text-[12.5px] leading-relaxed text-[var(--color-dim)]">
            {laneInfo.description}
          </p>
          <p className="mt-3 font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-muted)]">
            {rows.length} rows shown · maximum 200
          </p>
        </aside>
      </div>

      <div className="mt-7 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-line)]">
        <table className="data-table min-w-[760px]">
          <thead>
            <tr>
              <th scope="col">Planet</th>
              <th scope="col">Earth-2.0</th>
              {lane === "timing" && <th scope="col">2030 timing σ</th>}
              {lane === "atmosphere" && <th scope="col">TSM</th>}
              {lane === "atmosphere" && <th scope="col">ESM</th>}
              {lane === "rv" && <th scope="col">Expected K</th>}
              {lane === "rv" && <th scope="col">Mass basis</th>}
              {lane === "imaging" && <th scope="col">Max separation</th>}
              {lane === "imaging" && <th scope="col">Contrast scenario</th>}
              <th scope="col">Evidence note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((index) => {
              const ttv = columns.ttv_flag?.[index] === 1;
              const massClass = columns.mass_class[index] ?? "—";
              return (
                <tr key={`${columns.pl_name[index]}-${index}`}>
                  <td>
                    <Link
                      className="font-medium text-[var(--color-ivory)] hover:text-[var(--color-cyan)]"
                      href={`/candidate/${slugify(columns.pl_name[index])}`}
                    >
                      {columns.pl_name[index]}
                    </Link>
                    <span className="mt-0.5 block text-[10.5px] text-[var(--color-muted)]">
                      {columns.hostname[index]}
                    </span>
                  </td>
                  <td className="font-[family-name:var(--font-mono)] tabular-nums">
                    {num(columns.earth2_index[index], 3)}
                  </td>
                  {lane === "timing" && (
                    <td className="font-[family-name:var(--font-mono)] tabular-nums">
                      {num(valueAt(columns.ephemeris_uncertainty_2030_minutes, index), 1)} min
                    </td>
                  )}
                  {lane === "atmosphere" && (
                    <td className="font-[family-name:var(--font-mono)] tabular-nums">
                      {num(valueAt(columns.tsm, index), 2)}
                    </td>
                  )}
                  {lane === "atmosphere" && (
                    <td className="font-[family-name:var(--font-mono)] tabular-nums">
                      {num(valueAt(columns.esm, index), 2)}
                    </td>
                  )}
                  {lane === "rv" && (
                    <td className="font-[family-name:var(--font-mono)] tabular-nums">
                      {num(valueAt(columns.rv_semi_amplitude_ms, index), 3)} m/s
                    </td>
                  )}
                  {lane === "rv" && <td>{massClass.replaceAll("_", " ")}</td>}
                  {lane === "imaging" && (
                    <td className="font-[family-name:var(--font-mono)] tabular-nums">
                      {num(valueAt(columns.max_angular_separation_mas, index), 2)} mas
                    </td>
                  )}
                  {lane === "imaging" && (
                    <td className="font-[family-name:var(--font-mono)] tabular-nums">
                      {sig(valueAt(columns.reflected_light_contrast_ag0p3, index), 3)}
                    </td>
                  )}
                  <td className="text-[var(--color-muted)]">
                    {lane === "timing" && (ttv ? "TTV flag: linear forecast incomplete" : "Linear ephemeris")}
                    {lane === "atmosphere" && "Screening proxy, not exposure time"}
                    {lane === "rv" && "Activity/noise not included"}
                    {lane === "imaging" && "Aᵍ=0.30 · Lambert quadrature"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && (
        <div className="panel mt-4 p-5 text-[13px] text-[var(--color-dim)]">
          No planets match this pathway and filter. Remove the top-250 filter or
          clear the search term.
        </div>
      )}

      <p className="mt-5 max-w-4xl text-[11.5px] leading-relaxed text-[var(--color-muted)]">
        This table prioritises inspection, not proposals. Scheduling requires a
        current ephemeris, observatory visibility, instrument simulators,
        saturation and noise checks, and—for RV work—a target-specific stellar
        activity model. See the <Link href="/methods#follow-up" className="link">methods and assumptions</Link>.
      </p>
    </div>
  );
}
