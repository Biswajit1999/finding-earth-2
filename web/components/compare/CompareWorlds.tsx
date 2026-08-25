"use client";

/**
 * Side-by-side comparison of 2-5 worlds, Earth optionally included as a
 * reference row. Every metric is drawn straight from the exported catalogue;
 * nothing is recomputed.
 */

import { useEffect, useMemo, useState } from "react";
import type { CatalogueFile } from "@/lib/types";
import { MassClassChip, HzChip } from "@/components/Chips";
import { num, distanceLabel } from "@/lib/format";

const METRICS: { key: keyof CatalogueFile["columns"]; label: string; unit?: string; digits: number }[] = [
  { key: "pl_rade", label: "Radius", unit: "R⊕", digits: 3 },
  { key: "pl_bmasse", label: "Mass", unit: "M⊕", digits: 3 },
  { key: "pl_dens_used", label: "Bulk density", unit: "g/cm³", digits: 2 },
  { key: "pl_orbper", label: "Orbital period", unit: "days", digits: 2 },
  { key: "pl_orbsmax", label: "Semi-major axis", unit: "au", digits: 4 },
  { key: "pl_orbeccen", label: "Eccentricity", digits: 3 },
  { key: "insol_used", label: "Incident flux", unit: "S⊕", digits: 3 },
  { key: "teq_used", label: "Equilibrium temperature", unit: "K", digits: 1 },
  { key: "st_teff", label: "Host effective temperature", unit: "K", digits: 0 },
  { key: "st_rad", label: "Host radius", unit: "R☉", digits: 3 },
  { key: "st_mass", label: "Host mass", unit: "M☉", digits: 3 },
  { key: "sy_dist", label: "Distance", unit: "pc", digits: 2 },
  { key: "esi_global_p50", label: "Earth Similarity Index (median)", digits: 3 },
  { key: "hz_conservative_prob", label: "Habitable-zone probability", digits: 3 },
  { key: "score_observational_confidence", label: "Observational confidence", digits: 3 },
  { key: "earth2_index", label: "Earth-2.0 index", digits: 3 },
];

export function CompareWorlds({
  file,
  initialNames,
}: {
  file: CatalogueFile;
  initialNames: string[];
}) {
  const c = file.columns;
  const nameToIdx = useMemo(() => {
    const m = new Map<string, number>();
    c.pl_name.forEach((n, i) => m.set(n, i));
    return m;
  }, [c]);

  const [selected, setSelected] = useState<number[]>(() =>
    initialNames.map((n) => nameToIdx.get(n)).filter((v): v is number => v !== undefined).slice(0, 5),
  );
  const [query, setQuery] = useState("");

  // Static export cannot read the query string at build time, so it is read
  // here on mount instead. Only runs when the caller did not already supply
  // names (e.g. from an in-app Link with a resolved href).
  useEffect(() => {
    if (initialNames.length > 0) return;
    const p = new URLSearchParams(window.location.search);
    const names = (p.get("p") ?? "").split(",").filter(Boolean);
    if (names.length === 0) return;
    const idx = names
      .map((n) => nameToIdx.get(decodeURIComponent(n)))
      .filter((v): v is number => v !== undefined)
      .slice(0, 5);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (idx.length > 0) setSelected(idx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const out: number[] = [];
    for (let i = 0; i < file.n_rows && out.length < 8; i++) {
      if (selected.includes(i)) continue;
      if ((c.pl_name[i] ?? "").toLowerCase().includes(q)) out.push(i);
    }
    return out;
  }, [query, c, file.n_rows, selected]);

  const add = (i: number) => {
    if (selected.length >= 5) return;
    setSelected((s) => [...s, i]);
    setQuery("");
  };
  const remove = (i: number) => setSelected((s) => s.filter((x) => x !== i));

  const earthIdx = useMemo(
    () => c.pl_name.findIndex((n, i) => n === "Earth" && c.is_control[i]),
    [c],
  );

  const cols = earthIdx >= 0 && !selected.includes(earthIdx) ? [earthIdx, ...selected] : selected;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      <div className="panel mb-6 p-4">
        <label htmlFor="cmp-q" className="eyebrow mb-1.5 block">
          Add a world ({selected.length}/5 selected)
        </label>
        <input
          id="cmp-q"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={selected.length >= 5}
          placeholder="Search planets…"
          className="w-full max-w-sm rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-3 py-2 text-[13px] text-[var(--color-ivory)] placeholder:text-[var(--color-muted)] disabled:opacity-50"
        />
        {matches.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {matches.map((i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => add(i)}
                  className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-2.5 py-1 text-[12px] text-[var(--color-dim)] hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                >
                  + {c.pl_name[i]}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {cols.length === 0 ? (
        <div className="panel p-10 text-center text-[13px] text-[var(--color-muted)]">
          Search above to add worlds to the comparison.
        </div>
      ) : (
        <div className="panel overflow-x-auto">
          <table className="data-table min-w-[640px]">
            <caption className="sr-only">
              Side-by-side comparison of selected exoplanets and Earth
            </caption>
            <thead>
              <tr>
                <th scope="col" className="sticky left-0 z-10 bg-[var(--color-panel)]">
                  Metric
                </th>
                {cols.map((i) => (
                  <th key={i} scope="col" className="min-w-[150px]">
                    <div className="flex items-center justify-between gap-2">
                      <span className={c.is_control[i] ? "text-[var(--color-gold)]" : ""}>
                        {c.pl_name[i]}
                      </span>
                      {!c.is_control[i] && (
                        <button
                          type="button"
                          onClick={() => remove(i)}
                          aria-label={"Remove " + c.pl_name[i]}
                          className="cursor-pointer text-[var(--color-muted)] hover:text-[var(--color-rose)]"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row" className="sticky left-0 z-10 bg-[var(--color-panel)] font-normal text-[var(--color-dim)]">
                  Host star
                </th>
                {cols.map((i) => (
                  <td key={i} className="font-[family-name:var(--font-mono)] text-[12px]">
                    {c.hostname[i]}
                  </td>
                ))}
              </tr>
              <tr>
                <th scope="row" className="sticky left-0 z-10 bg-[var(--color-panel)] font-normal text-[var(--color-dim)]">
                  Mass provenance
                </th>
                {cols.map((i) => (
                  <td key={i}>
                    {c.is_control[i] ? (
                      <span className="text-[11px] text-[var(--color-muted)]">reference body</span>
                    ) : (
                      <MassClassChip massClass={c.mass_class[i]} />
                    )}
                  </td>
                ))}
              </tr>
              <tr>
                <th scope="row" className="sticky left-0 z-10 bg-[var(--color-panel)] font-normal text-[var(--color-dim)]">
                  Habitable zone
                </th>
                {cols.map((i) => (
                  <td key={i}>
                    <HzChip prob={c.hz_conservative_prob[i]} extrapolated={c.hz_model_extrapolated[i]} />
                  </td>
                ))}
              </tr>
              {METRICS.map((m) => (
                <tr key={m.key as string}>
                  <th scope="row" className="sticky left-0 z-10 bg-[var(--color-panel)] font-normal text-[var(--color-dim)]">
                    {m.label}
                    {m.unit && <span className="ml-1 text-[var(--color-muted)]">({m.unit})</span>}
                  </th>
                  {cols.map((i) => {
                    const arr = c[m.key] as (number | null)[];
                    const v = arr[i];
                    return (
                      <td key={i} className="font-[family-name:var(--font-mono)] text-[12px] tabular-nums">
                        {v === null ? (
                          <span className="text-[var(--color-muted)]">—</span>
                        ) : (
                          num(v, m.digits)
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr>
                <th scope="row" className="sticky left-0 z-10 bg-[var(--color-panel)] font-normal text-[var(--color-dim)]">
                  Distance
                </th>
                {cols.map((i) => (
                  <td key={i} className="font-[family-name:var(--font-mono)] text-[11.5px] tabular-nums text-[var(--color-dim)]">
                    {c.is_control[i] ? "—" : distanceLabel(c.sy_dist[i])}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 max-w-[70ch] text-[11.5px] leading-relaxed text-[var(--color-muted)]">
        Earth is included automatically as a reference row when not already
        selected. Solar System bodies are comparison controls, not exoplanet
        observations, and their mass and habitable-zone entries reflect that.
      </p>
    </div>
  );
}
