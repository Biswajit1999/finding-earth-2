"use client";

/**
 * The Candidate Atlas.
 *
 * Filters and sorts the entire analysed catalogue in the browser. Two decisions
 * make that viable at 6,000+ rows:
 *
 * 1. The data stays **columnar**. Filtering walks typed arrays and produces an
 *    array of row indices; it never materialises objects. Materialisation
 *    happens only for the ~40 rows actually on screen.
 *
 * 2. The body is **windowed**. Only the visible slice is in the DOM. Rendering
 *    6,000 rows of nine cells each would put 54,000 nodes in the document and
 *    make every keystroke janky.
 *
 * Filter state is mirrored into the URL so a filtered view is a shareable
 * citation — "the 15 planets in the conservative HZ below 1.6 R⊕" should be a
 * link, not a set of instructions.
 */

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { HzChip, MassClassChip, ControlChip } from "@/components/Chips";
import { ScoreMeter, UncertaintyBar } from "@/components/UncertaintyBar";
import type { CatalogueFile } from "@/lib/types";
import { distanceLabel, num, slugify } from "@/lib/format";

type SortKey =
  | "earth2_index"
  | "esi_global_p50"
  | "hz_conservative_prob"
  | "score_observational_confidence"
  | "pl_rade"
  | "pl_bmasse"
  | "insol_used"
  | "teq_used"
  | "sy_dist"
  | "pl_orbper"
  | "disc_year"
  | "tsm";

const COLUMNS: { key: SortKey; label: string; unit?: string; width?: string }[] = [
  { key: "earth2_index", label: "Earth-2.0 index" },
  { key: "esi_global_p50", label: "ESI", unit: "16th–84th pct" },
  { key: "hz_conservative_prob", label: "Habitable zone" },
  { key: "score_observational_confidence", label: "Confidence" },
  { key: "pl_rade", label: "Radius", unit: "R⊕" },
  { key: "pl_bmasse", label: "Mass", unit: "M⊕" },
  { key: "insol_used", label: "Flux", unit: "S⊕" },
  { key: "teq_used", label: "T_eq", unit: "K" },
  { key: "sy_dist", label: "Distance", unit: "pc" },
];

const ROW_HEIGHT = 41;
const OVERSCAN = 8;

export interface AtlasFilters {
  q: string;
  radeMax: number | null;
  radeMin: number | null;
  hzOnly: boolean;
  rockyOnly: boolean;
  measuredMassOnly: boolean;
  transitingOnly: boolean;
  hasSpectrum: boolean;
  hasRv: boolean;
  method: string;
  maxDist: number | null;
  showControls: boolean;
}

const DEFAULT_FILTERS: AtlasFilters = {
  q: "",
  radeMax: null,
  radeMin: null,
  hzOnly: false,
  rockyOnly: false,
  measuredMassOnly: false,
  transitingOnly: false,
  hasSpectrum: false,
  hasRv: false,
  method: "",
  maxDist: null,
  showControls: true,
};

export function AtlasTable({ file }: { file: CatalogueFile }) {
  const c = file.columns;
  const n = file.n_rows;

  const [filters, setFilters] = useState<AtlasFilters>(DEFAULT_FILTERS);
  const [sortKey, setSortKey] = useState<SortKey>("earth2_index");
  const [sortDesc, setSortDesc] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [hydrated, setHydrated] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportH, setViewportH] = useState(720);

  /* ---------------- URL state ---------------- */
  // window.location.search is a browser-only external source unavailable
  // during the static export's server render pass, so it can only be read
  // here, on mount, not computed as render-time derived state.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const next: AtlasFilters = { ...DEFAULT_FILTERS };
    if (p.get("q")) next.q = p.get("q") ?? "";
    if (p.get("rmax")) next.radeMax = Number(p.get("rmax"));
    if (p.get("rmin")) next.radeMin = Number(p.get("rmin"));
    next.hzOnly = p.get("hz") === "1";
    next.rockyOnly = p.get("rocky") === "1";
    next.measuredMassOnly = p.get("mass") === "1";
    next.transitingOnly = p.get("tran") === "1";
    next.hasSpectrum = p.get("spec") === "1";
    next.hasRv = p.get("rv") === "1";
    next.method = p.get("method") ?? "";
    if (p.get("dist")) next.maxDist = Number(p.get("dist"));
    if (p.get("ctrl") === "0") next.showControls = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFilters(next);
    if (p.get("sort")) setSortKey(p.get("sort") as SortKey);
    if (p.get("dir") === "asc") setSortDesc(false);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const p = new URLSearchParams();
    if (filters.q) p.set("q", filters.q);
    if (filters.radeMax !== null) p.set("rmax", String(filters.radeMax));
    if (filters.radeMin !== null) p.set("rmin", String(filters.radeMin));
    if (filters.hzOnly) p.set("hz", "1");
    if (filters.rockyOnly) p.set("rocky", "1");
    if (filters.measuredMassOnly) p.set("mass", "1");
    if (filters.transitingOnly) p.set("tran", "1");
    if (filters.hasSpectrum) p.set("spec", "1");
    if (filters.hasRv) p.set("rv", "1");
    if (filters.method) p.set("method", filters.method);
    if (filters.maxDist !== null) p.set("dist", String(filters.maxDist));
    if (!filters.showControls) p.set("ctrl", "0");
    if (sortKey !== "earth2_index") p.set("sort", sortKey);
    if (!sortDesc) p.set("dir", "asc");
    const qs = p.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [filters, sortKey, sortDesc, hydrated]);

  /* ---------------- filter + sort over columnar arrays ---------------- */
  const rows = useMemo(() => {
    const q = filters.q.trim().toLowerCase();
    const idx: number[] = [];

    for (let i = 0; i < n; i++) {
      if (!filters.showControls && c.is_control[i]) continue;

      if (q) {
        const name = (c.pl_name[i] ?? "").toLowerCase();
        const host = (c.hostname[i] ?? "").toLowerCase();
        if (!name.includes(q) && !host.includes(q)) continue;
      }
      const rade = c.pl_rade[i];
      if (filters.radeMax !== null && (rade === null || rade > filters.radeMax)) continue;
      if (filters.radeMin !== null && (rade === null || rade < filters.radeMin)) continue;
      if (filters.hzOnly && !((c.hz_conservative_prob[i] ?? 0) > 0.5)) continue;
      if (filters.rockyOnly && !((c.rocky_plausibility[i] ?? 0) > 0.5)) continue;
      if (
        filters.measuredMassOnly &&
        !(c.mass_class[i] === "measured" || c.mass_class[i] === "msini_deprojected")
      )
        continue;
      if (filters.transitingOnly && c.tran_flag[i] !== 1) continue;
      if (filters.hasSpectrum && !((c.n_transmission_points[i] ?? 0) > 0)) continue;
      if (filters.hasRv && c.rv_flag[i] !== 1) continue;
      if (filters.method && c.discoverymethod[i] !== filters.method) continue;
      if (filters.maxDist !== null) {
        const d = c.sy_dist[i];
        if (d === null || d > filters.maxDist) continue;
      }
      idx.push(i);
    }

    const key = sortKey as keyof typeof c;
    const arr = c[key] as (number | null)[];
    idx.sort((a, b) => {
      const va = arr[a];
      const vb = arr[b];
      // Missing values always sort last, in both directions. A planet with no
      // measured radius is not "the smallest planet".
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      return sortDesc ? vb - va : va - vb;
    });
    return idx;
  }, [filters, sortKey, sortDesc, c, n]);

  /* ---------------- windowing ---------------- */
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => setScrollTop(el.scrollTop);
    const measure = () => setViewportH(el.clientHeight || 720);
    el.addEventListener("scroll", onScroll, { passive: true });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, []);

  useEffect(() => {
    // Synchronizing to the scroll container (an external DOM API) after a
    // filter/sort change, not deriving state from those props directly.
    scrollRef.current?.scrollTo({ top: 0 });
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setScrollTop(0);
  }, [filters, sortKey, sortDesc]);

  const first = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const visibleCount = Math.ceil(viewportH / ROW_HEIGHT) + OVERSCAN * 2;
  const last = Math.min(rows.length, first + visibleCount);
  const window_ = rows.slice(first, last);

  const toggleSort = useCallback(
    (k: SortKey) => {
      if (k === sortKey) setSortDesc((d) => !d);
      else {
        setSortKey(k);
        setSortDesc(true);
      }
    },
    [sortKey],
  );

  const toggleSelect = (i: number) => {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(i)) next.delete(i);
      else if (next.size < 5) next.add(i);
      return next;
    });
  };

  const set = <K extends keyof AtlasFilters>(k: K, v: AtlasFilters[K]) =>
    setFilters((f) => ({ ...f, [k]: v }));

  const methods = useMemo(() => {
    const s = new Set<string>();
    for (let i = 0; i < n; i++) {
      const m = c.discoverymethod[i];
      if (m) s.add(m);
    }
    return [...s].sort();
  }, [c, n]);

  const compareHref =
    selected.size > 0
      ? `/compare?p=${[...selected].map((i) => encodeURIComponent(c.pl_name[i] ?? "")).join(",")}`
      : null;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">
      {/* ---------------- filters ---------------- */}
      <div className="panel mb-4 p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[220px] flex-1">
            <label htmlFor="atlas-q" className="eyebrow mb-1.5 block">
              Search planet or host
            </label>
            <input
              id="atlas-q"
              type="search"
              value={filters.q}
              onChange={(e) => set("q", e.target.value)}
              placeholder="TRAPPIST, Proxima, Kepler-442…"
              className="w-full rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-3 py-2 text-[13px] text-[var(--color-ivory)] placeholder:text-[var(--color-muted)]"
            />
          </div>

          <div>
            <label htmlFor="atlas-method" className="eyebrow mb-1.5 block">
              Discovery method
            </label>
            <select
              id="atlas-method"
              value={filters.method}
              onChange={(e) => set("method", e.target.value)}
              className="cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-3 py-2 text-[13px] text-[var(--color-ivory)]"
            >
              <option value="">All methods</option>
              {methods.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="atlas-rmax" className="eyebrow mb-1.5 block">
              Max radius (R⊕)
            </label>
            <input
              id="atlas-rmax"
              type="number"
              step="0.1"
              min="0"
              value={filters.radeMax ?? ""}
              onChange={(e) =>
                set("radeMax", e.target.value === "" ? null : Number(e.target.value))
              }
              placeholder="any"
              className="w-24 rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-3 py-2 text-[13px] text-[var(--color-ivory)]"
            />
          </div>

          <div>
            <label htmlFor="atlas-dist" className="eyebrow mb-1.5 block">
              Max distance (pc)
            </label>
            <input
              id="atlas-dist"
              type="number"
              step="1"
              min="0"
              value={filters.maxDist ?? ""}
              onChange={(e) =>
                set("maxDist", e.target.value === "" ? null : Number(e.target.value))
              }
              placeholder="any"
              className="w-24 rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-3 py-2 text-[13px] text-[var(--color-ivory)]"
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-[var(--color-line)] pt-3">
          {(
            [
              ["hzOnly", "In conservative HZ (P > 0.5)"],
              ["rockyOnly", "Rocky plausibility > 0.5"],
              ["measuredMassOnly", "Measured mass only"],
              ["transitingOnly", "Transiting"],
              ["hasSpectrum", "Has published spectrum"],
              ["hasRv", "RV detected"],
              ["showControls", "Show Solar System controls"],
            ] as [keyof AtlasFilters, string][]
          ).map(([k, label]) => (
            <label
              key={k as string}
              className="flex cursor-pointer items-center gap-2 text-[12.5px] text-[var(--color-dim)]"
            >
              <input
                type="checkbox"
                checked={Boolean(filters[k])}
                onChange={(e) => set(k, e.target.checked as never)}
                className="size-3.5 cursor-pointer accent-[var(--color-cyan)]"
              />
              {label}
            </label>
          ))}

          <button
            type="button"
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className="ml-auto cursor-pointer text-[12px] text-[var(--color-muted)] underline underline-offset-4 hover:text-[var(--color-cyan)]"
          >
            Reset filters
          </button>
        </div>
      </div>

      {/* ---------------- status bar ---------------- */}
      <div className="mb-3 flex flex-wrap items-center gap-x-6 gap-y-2">
        <p
          className="font-[family-name:var(--font-mono)] text-[12px] tabular-nums text-[var(--color-dim)]"
          role="status"
          aria-live="polite"
        >
          {rows.length.toLocaleString("en-GB")} of {n.toLocaleString("en-GB")} rows
        </p>
        {selected.size > 0 && compareHref && (
          <Link href={compareHref} className="link text-[12.5px]">
            Compare {selected.size} selected →
          </Link>
        )}
        {selected.size >= 5 && (
          <span className="text-[11.5px] text-[var(--color-gold)]">
            Five is the comparison maximum
          </span>
        )}
      </div>

      {/* ---------------- table ---------------- */}
      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <div className="min-w-[1120px]">
            {/* header */}
            <div
              role="row"
              className="flex border-b border-[var(--color-line-strong)] bg-[var(--color-panel)]"
            >
              <HeaderCell className="w-[40px]" label="" />
              <HeaderCell className="w-[210px]" label="Planet" />
              {COLUMNS.map((col) => (
                <div
                  key={col.key}
                  role="columnheader"
                  aria-sort={
                    sortKey === col.key ? (sortDesc ? "descending" : "ascending") : "none"
                  }
                  className="flex flex-1"
                >
                  <button
                    type="button"
                    onClick={() => toggleSort(col.key)}
                    className={`flex min-h-11 w-full cursor-pointer flex-col items-start justify-center px-2.5 py-2 text-left font-[family-name:var(--font-mono)] text-[10.5px] uppercase tracking-[0.07em] transition-colors hover:text-[var(--color-cyan)] ${
                      sortKey === col.key
                        ? "text-[var(--color-cyan)]"
                        : "text-[var(--color-muted)]"
                    }`}
                  >
                    <span>
                      {col.label}
                      {sortKey === col.key && (
                        <span aria-hidden className="ml-1">
                          {sortDesc ? "↓" : "↑"}
                        </span>
                      )}
                    </span>
                    {col.unit && (
                      <span className="text-[9.5px] normal-case tracking-normal text-[var(--color-faint)]">
                        {col.unit}
                      </span>
                    )}
                  </button>
                </div>
              ))}
              <HeaderCell className="w-[130px]" label="Mass provenance" />
            </div>

            {/* windowed body */}
            <div
              ref={scrollRef}
              className="max-h-[68vh] overflow-y-auto"
              tabIndex={0}
              role="region"
              aria-label="Catalogue rows, scrollable"
            >
              <div style={{ height: rows.length * ROW_HEIGHT, position: "relative" }}>
                <div
                  style={{
                    transform: `translateY(${first * ROW_HEIGHT}px)`,
                    position: "absolute",
                    left: 0,
                    right: 0,
                  }}
                >
                  {window_.map((i) => {
                    const isControl = c.is_control[i];
                    return (
                      <div
                        key={i}
                        className="flex items-center border-b border-[var(--color-line)]/55 transition-colors hover:bg-[var(--color-cyan)]/[0.04]"
                        style={{ height: ROW_HEIGHT }}
                      >
                        <div className="w-[40px] px-2.5">
                          <input
                            type="checkbox"
                            checked={selected.has(i)}
                            onChange={() => toggleSelect(i)}
                            aria-label={`Select ${c.pl_name[i]} for comparison`}
                            className="size-3.5 cursor-pointer accent-[var(--color-cyan)]"
                          />
                        </div>

                        <div className="w-[210px] truncate px-2.5">
                          {isControl ? (
                            <span className="text-[13px] text-[var(--color-gold)]">
                              {c.pl_name[i]}
                            </span>
                          ) : (
                            <Link
                              href={`/candidate/${slugify(c.pl_name[i] ?? "")}`}
                              className="text-[13px] text-[var(--color-ivory)] transition-colors hover:text-[var(--color-cyan)]"
                            >
                              {c.pl_name[i]}
                            </Link>
                          )}
                          <span className="ml-1.5 font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]">
                            {c.st_spectype[i] ?? ""}
                          </span>
                        </div>

                        <Cell>
                          <ScoreMeter
                            value={c.earth2_index[i]}
                            tone="var(--color-gold)"
                            width={62}
                            label={`${c.pl_name[i]} index`}
                          />
                        </Cell>

                        <Cell>
                          <UncertaintyBar
                            lo={c.esi_global_p16[i]}
                            mid={c.esi_global_p50[i]}
                            hi={c.esi_global_p84[i]}
                            min={0.4}
                            max={1}
                            width={88}
                            height={12}
                            label={`${c.pl_name[i]} ESI`}
                          />
                        </Cell>

                        <Cell>
                          {isControl ? (
                            <ControlChip />
                          ) : (
                            <HzChip
                              prob={c.hz_conservative_prob[i]}
                              extrapolated={c.hz_model_extrapolated[i]}
                            />
                          )}
                        </Cell>

                        <Cell>
                          <ScoreMeter
                            value={c.score_observational_confidence[i]}
                            tone="var(--color-sci)"
                            width={62}
                            label={`${c.pl_name[i]} confidence`}
                          />
                        </Cell>

                        <NumCell v={c.pl_rade[i]} d={2} />
                        <NumCell v={c.pl_bmasse[i]} d={2} />
                        <NumCell v={c.insol_used[i]} d={2} />
                        <NumCell v={c.teq_used[i]} d={0} />
                        <Cell>
                          <span className="font-[family-name:var(--font-mono)] text-[11px] tabular-nums text-[var(--color-dim)]">
                            {c.sy_dist[i] === null ? "—" : num(c.sy_dist[i], 1)}
                          </span>
                        </Cell>

                        <div className="w-[130px] px-2.5">
                          <MassClassChip massClass={c.mass_class[i]} showGlyph={false} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-muted)]">
        Rows are windowed: only the visible slice is in the document. Missing
        values sort last in both directions — a planet with no measured radius is
        not the smallest planet. Solar System bodies appear in gold and are
        comparison controls, not exoplanet observations.
      </p>
    </div>
  );
}

function HeaderCell({ label, className }: { label: string; className?: string }) {
  return (
    <div
      className={`px-2.5 py-2 font-[family-name:var(--font-mono)] text-[10.5px] uppercase tracking-[0.07em] text-[var(--color-muted)] ${className ?? ""}`}
    >
      {label}
    </div>
  );
}

function Cell({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-1 items-center px-2.5">{children}</div>;
}

function NumCell({ v, d }: { v: number | null; d: number }) {
  return (
    <div className="flex flex-1 items-center px-2.5">
      <span className="font-[family-name:var(--font-mono)] text-[11.5px] tabular-nums text-[var(--color-dim)]">
        {v === null ? <span className="text-[var(--color-muted)]">—</span> : num(v, d)}
      </span>
    </div>
  );
}
