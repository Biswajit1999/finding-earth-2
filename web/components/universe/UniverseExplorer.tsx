"use client";

/**
 * The full interactive 3D universe.
 *
 * Every point is a real system with a measured distance, at its true
 * equatorial position (Sun at the origin, radial axis log-compressed so the
 * view is not 99% empty space around a single visible cluster). Colour
 * encoding is switchable and always paired with a legend; nothing here uses
 * colour as the sole carrier of meaning.
 */

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useReducedMotion } from "motion/react";
import Link from "next/link";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";

import { StarField, type ColourMode } from "@/components/three/StarField";
import type { UniverseFile } from "@/lib/types";
import { compactInt, EMDASH, int, num, slugify, utcLabel } from "@/lib/format";

/** The subset of three-stdlib's OrbitControls this component actually drives. */
interface OrbitControlsHandle {
  object: { position: { x: number; y: number; z: number; set: (x: number, y: number, z: number) => void } };
  target: { x: number; y: number; z: number };
  update: () => void;
  minDistance: number;
  maxDistance: number;
}

const COLOUR_MODES: { key: ColourMode; label: string }[] = [
  { key: "index", label: "Earth-2.0 index" },
  { key: "teff", label: "Host temperature" },
  { key: "method", label: "Discovery method" },
  { key: "distance", label: "Distance" },
];

// The same five methods StarField.tsx colour-codes explicitly; every other
// discovery method (disk kinematics, pulsar timing, astrometry, ...) groups
// into "Other" for filtering, matching how the legend already presents them.
const NAMED_METHODS = [
  "Transit",
  "Radial Velocity",
  "Microlensing",
  "Imaging",
  "Transit Timing Variations",
] as const;
const ALL_METHOD_GROUPS = [...NAMED_METHODS, "Other"];

function methodGroup(m: string | null): string {
  return m && (NAMED_METHODS as readonly string[]).includes(m) ? m : "Other";
}

const LY_PER_PC = 3.26156;

function toPc(value: number, unit: "pc" | "ly"): number {
  return unit === "ly" ? value / LY_PER_PC : value;
}
function fromPc(pc: number, unit: "pc" | "ly"): number {
  return unit === "ly" ? pc * LY_PER_PC : pc;
}

function Legend({ mode }: { mode: ColourMode }) {
  if (mode === "index") {
    return (
      <div className="flex items-center gap-2">
        <span className="text-[10.5px] text-[var(--color-muted)]">0</span>
        <span
          className="h-2 w-32 rounded-full"
          style={{
            background:
              "linear-gradient(to right, #440154, #3a558c, #218e8d, #5ec962, #fde725)",
          }}
        />
        <span className="text-[10.5px] text-[var(--color-muted)]">1</span>
      </div>
    );
  }
  if (mode === "teff") {
    return (
      <div className="flex items-center gap-2">
        <span className="text-[10.5px] text-[var(--color-muted)]">2400 K</span>
        <span
          className="h-2 w-32 rounded-full"
          style={{
            background:
              "linear-gradient(to right, #ff6b4a, #ffc478, #ffe9b8, #f4f2ea, #cbd8ff, #a7c0ff)",
          }}
        />
        <span className="text-[10.5px] text-[var(--color-muted)]">10,000+ K</span>
      </div>
    );
  }
  if (mode === "distance") {
    return (
      <div className="flex items-center gap-2">
        <span className="text-[10.5px] text-[var(--color-muted)]">near</span>
        <span
          className="h-2 w-32 rounded-full"
          style={{ background: "linear-gradient(to right, #4fd1e0, #e0a33e)" }}
        />
        <span className="text-[10.5px] text-[var(--color-muted)]">far (log)</span>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      {[
        ["Transit", "#5b8def"],
        ["Radial Velocity", "#e0a33e"],
        ["Microlensing", "#4fb07a"],
        ["Imaging", "#9a7fe0"],
        ["Other", "#6c7689"],
      ].map(([label, colour]) => (
        <span key={label} className="flex items-center gap-1.5 text-[10.5px] text-[var(--color-dim)]">
          <span
            className="inline-block size-2 rounded-full"
            style={{ background: colour as string }}
          />
          {label}
        </span>
      ))}
    </div>
  );
}

export function UniverseExplorer({
  data,
  deepDiveSlugs,
}: {
  data: UniverseFile;
  /** Slugs with a full deep-dive page; most of the 6,300+ systems here don't have one. */
  deepDiveSlugs?: Set<string>;
}) {
  const reduced = useReducedMotion();
  const [mode, setMode] = useState<ColourMode>("index");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [webglFailed, setWebglFailed] = useState(false);
  const [rotate, setRotate] = useState(!reduced);
  const [unit, setUnit] = useState<"pc" | "ly">("pc");
  const [activeMethods, setActiveMethods] = useState<Set<string>>(
    () => new Set(ALL_METHOD_GROUPS),
  );
  const [showLines, setShowLines] = useState(false);
  const [ready, setReady] = useState(false);
  const controlsRef = useRef<OrbitControlsHandle | null>(null);

  const zoomBy = (factor: number) => {
    const controls = controlsRef.current;
    if (!controls) return;
    const cam = controls.object;
    const t = controls.target;
    const dx = cam.position.x - t.x;
    const dy = cam.position.y - t.y;
    const dz = cam.position.z - t.z;
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
    const newDist = Math.min(Math.max(dist * factor, controls.minDistance), controls.maxDistance);
    const s = newDist / dist;
    cam.position.set(t.x + dx * s, t.y + dy * s, t.z + dz * s);
    controls.update();
  };

  const maxDistPc = useMemo(
    () => data.dist_pc.reduce((m, d) => (Number.isFinite(d) && d > m ? d : m), 1),
    [data],
  );
  const [distRange, setDistRange] = useState<[number, number]>(() => [0, maxDistPc]);

  const discoveryYears = useMemo(
    () => data.disc_year.filter((year): year is number => Number.isFinite(year)),
    [data.disc_year],
  );
  const minDiscoveryYear = discoveryYears.length ? Math.min(...discoveryYears) : 1992;
  const maxDiscoveryYear = discoveryYears.length ? Math.max(...discoveryYears) : minDiscoveryYear;
  const unknownDiscoveryYears = data.n_points - discoveryYears.length;
  const [discoveryYear, setDiscoveryYear] = useState(maxDiscoveryYear);
  const [playingHistory, setPlayingHistory] = useState(false);

  useEffect(() => {
    if (!playingHistory) return;
    const timer = window.setInterval(() => {
      setDiscoveryYear((year) => {
        if (year >= maxDiscoveryYear) {
          setPlayingHistory(false);
          return maxDiscoveryYear;
        }
        return year + 1;
      });
    }, reduced ? 900 : 420);
    return () => window.clearInterval(timer);
  }, [playingHistory, maxDiscoveryYear, reduced]);

  const methodCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const g of ALL_METHOD_GROUPS) counts[g] = 0;
    for (let i = 0; i < data.n_points; i++) {
      const g = methodGroup(data.method[i]);
      counts[g] = (counts[g] ?? 0) + 1;
    }
    return counts;
  }, [data]);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const out: number[] = [];
    for (let i = 0; i < data.n_points && out.length < 8; i++) {
      if (data.name[i].toLowerCase().includes(q) || data.host[i].toLowerCase().includes(q)) {
        out.push(i);
      }
    }
    return out;
  }, [query, data]);

  const highlight = useMemo(() => {
    if (selected === null) return undefined;
    return new Set([selected]);
  }, [selected]);

  const filterMask = useMemo(() => {
    const mask = new Uint8Array(data.n_points);
    const [lo, hi] = distRange;
    const allMethods = activeMethods.size === ALL_METHOD_GROUPS.length;
    let nVisible = 0;
    for (let i = 0; i < data.n_points; i++) {
      const d = data.dist_pc[i];
      const distOk = d >= lo && d <= hi;
      const methodOk = allMethods || activeMethods.has(methodGroup(data.method[i]));
      const year = data.disc_year[i];
      const yearOk = Number.isFinite(year)
        ? (year as number) <= discoveryYear
        : discoveryYear === maxDiscoveryYear;
      if (distOk && methodOk && yearOk) {
        mask[i] = 1;
        nVisible++;
      }
    }
    return { mask, nVisible };
  }, [data, distRange, activeMethods, discoveryYear, maxDiscoveryYear]);

  const filtersActive = distRange[0] > 0 || distRange[1] < maxDistPc || activeMethods.size < ALL_METHOD_GROUPS.length || discoveryYear < maxDiscoveryYear;

  const info = selected !== null ? selected : null;

  if (webglFailed) {
    return (
      <div className="panel mx-auto max-w-2xl p-8 text-center">
        <p className="text-[14px] text-[var(--color-ivory)]">
          WebGL is unavailable in this browser.
        </p>
        <p className="mt-2 text-[13px] text-[var(--color-muted)]">
          The 3D universe requires WebGL. Try the{" "}
          <Link href="/atlas" className="link">
            Candidate Atlas
          </Link>{" "}
          for the same data as a searchable table instead.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        className="relative h-[74vh] min-h-[520px] w-full overflow-hidden border-y border-[var(--color-line)]"
        style={{
          background:
            "radial-gradient(ellipse at 50% 45%, #10152a 0%, #090b16 45%, #05060b 100%)",
        }}
      >
        <Canvas
          camera={{ position: [0, 1.1, 5.2], fov: 55 }}
          dpr={[1, 1.75]}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
          onCreated={({ gl, raycaster }) => {
            // Transparent so the container's own radial gradient (a soft
            // haze, not flat black) shows behind the points instead of being
            // painted over every frame.
            gl.setClearColor("#000000", 0);
            // The default threshold is tuned for typical scene scales, not
            // this compressed log-distance layout -- too small and clicks on
            // a visibly-there point miss every time, too large and dense
            // clusters can't be told apart.
            raycaster.params.Points.threshold = 0.16;
            setReady(true);
          }}
          onError={() => setWebglFailed(true)}
        >
          <Suspense fallback={null}>
            <StarField
              data={data}
              colourMode={mode}
              rotate={rotate}
              twinkle={!reduced}
              highlightIndices={highlight}
              visibleMask={filterMask.mask}
              onSelect={setSelected}
              showDistanceLines={showLines}
            />
          </Suspense>
          <OrbitControls
            ref={controlsRef as never}
            enablePan
            enableZoom
            enableRotate
            minDistance={0.6}
            maxDistance={14}
            autoRotate={false}
            onStart={() => setRotate(false)}
          />
        </Canvas>

        {/* ---------------- branded loading veil ---------------- */}
        <div
          aria-hidden={ready}
          className={`absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[var(--color-void)] transition-opacity duration-700 ${
            ready ? "pointer-events-none opacity-0" : "opacity-100"
          }`}
        >
          <p className="font-[family-name:var(--font-display)] text-lg font-medium text-[var(--color-ivory)]">
            Finding Earth 2.0
          </p>
          <p className="eyebrow">Biswajit Jana</p>
          <div className="flex gap-1.5" aria-hidden>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="size-1.5 animate-pulse rounded-full bg-[var(--color-gold)]"
                style={{ animationDelay: i * 0.15 + "s" }}
              />
            ))}
          </div>
          <p className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
            {compactInt(data.n_points)} real systems · NASA Exoplanet Archive + Gaia DR3
          </p>
          <p className="font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-faint)]">
            Static snapshot, last synced {utcLabel(data.generated_utc)} — not fetched live
          </p>
        </div>

        {/* ---------------- controls overlay ---------------- */}
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-4 sm:p-5">
          <div className="pointer-events-auto flex flex-wrap items-start justify-between gap-3">
            <div className="panel-raised max-w-xs p-3">
              <label htmlFor="uni-search" className="eyebrow mb-1.5 block">
                Find a system
              </label>
              <input
                id="uni-search"
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="TRAPPIST-1, Kepler…"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-2.5 py-1.5 text-[12.5px] text-[var(--color-ivory)] placeholder:text-[var(--color-muted)]"
              />
              {matches.length > 0 && (
                <ul className="mt-2 max-h-48 overflow-y-auto">
                  {matches.map((i) => (
                    <li key={i}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelected(i);
                          setQuery("");
                        }}
                        className="w-full cursor-pointer rounded px-1.5 py-1 text-left text-[12px] text-[var(--color-dim)] hover:bg-[var(--color-panel)] hover:text-[var(--color-cyan)]"
                      >
                        {data.name[i]}{" "}
                        <span className="text-[10px] text-[var(--color-muted)]">
                          {num(fromPc(data.dist_pc[i], unit), 1)} {unit}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="panel-raised p-3">
              <p className="eyebrow mb-1.5">Colour by</p>
              <div className="flex flex-wrap gap-1.5">
                {COLOUR_MODES.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    onClick={() => setMode(m.key)}
                    aria-pressed={mode === m.key}
                    className={`cursor-pointer rounded-[var(--radius-sm)] border px-2 py-1 text-[11px] transition-colors ${
                      mode === m.key
                        ? "border-[var(--color-cyan)] text-[var(--color-cyan)]"
                        : "border-[var(--color-line-strong)] text-[var(--color-dim)] hover:border-[var(--color-cyan)]"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <div className="mt-2.5 border-t border-[var(--color-line)] pt-2">
                <Legend mode={mode} />
              </div>
            </div>

            <div className="panel-raised w-[230px] p-3">
              <div className="mb-1.5 flex items-center justify-between">
                <p className="eyebrow">Filters</p>
                {filtersActive && (
                  <button
                    type="button"
                    onClick={() => {
                      setDistRange([0, maxDistPc]);
                      setActiveMethods(new Set(ALL_METHOD_GROUPS));
                      setDiscoveryYear(maxDiscoveryYear);
                      setPlayingHistory(false);
                    }}
                    className="cursor-pointer text-[10.5px] text-[var(--color-cyan)] hover:underline"
                  >
                    Reset
                  </button>
                )}
              </div>

              <div className="flex items-center justify-between">
                <label htmlFor="uni-dist-lo" className="text-[10.5px] text-[var(--color-muted)]">
                  Distance
                </label>
                <div className="flex overflow-hidden rounded-[var(--radius-sm)] border border-[var(--color-line-strong)]">
                  {(["pc", "ly"] as const).map((u) => (
                    <button
                      key={u}
                      type="button"
                      onClick={() => setUnit(u)}
                      aria-pressed={unit === u}
                      className={`cursor-pointer px-1.5 py-0.5 text-[10px] ${
                        unit === u
                          ? "bg-[var(--color-cyan)]/15 text-[var(--color-cyan)]"
                          : "text-[var(--color-muted)]"
                      }`}
                    >
                      {u}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-1.5 flex items-center gap-1.5">
                <input
                  id="uni-dist-lo"
                  type="number"
                  min={0}
                  value={Math.round(fromPc(distRange[0], unit) * 100) / 100}
                  onChange={(e) => {
                    const v = toPc(Number(e.target.value) || 0, unit);
                    setDistRange(([, hi]) => [Math.min(Math.max(v, 0), hi), hi]);
                  }}
                  aria-label={"Minimum distance in " + unit}
                  className="w-full min-w-0 rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-1.5 py-1 text-[11px] text-[var(--color-ivory)]"
                />
                <span className="text-[10px] text-[var(--color-muted)]">–</span>
                <input
                  type="number"
                  min={0}
                  value={Math.round(fromPc(distRange[1], unit) * 100) / 100}
                  onChange={(e) => {
                    const v = toPc(Number(e.target.value) || 0, unit);
                    setDistRange(([lo]) => [lo, Math.max(v, lo)]);
                  }}
                  aria-label={"Maximum distance in " + unit}
                  className="w-full min-w-0 rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-void)] px-1.5 py-1 text-[11px] text-[var(--color-ivory)]"
                />
              </div>

              <label className="mt-2 flex cursor-pointer items-center justify-between gap-2 text-[11px] text-[var(--color-dim)]">
                <span className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={showLines}
                    onChange={() => setShowLines((v) => !v)}
                  />
                  Distance lines from Sun
                </span>
              </label>

              <p className="mb-1 mt-2.5 border-t border-[var(--color-line)] pt-2 text-[10.5px] text-[var(--color-muted)]">
                Discovery method
              </p>
              <div className="flex flex-col gap-0.5">
                {ALL_METHOD_GROUPS.map((g) => (
                  <label
                    key={g}
                    className="flex cursor-pointer items-center justify-between gap-2 rounded px-1 py-0.5 text-[11px] text-[var(--color-dim)] hover:bg-[var(--color-panel)]"
                  >
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={activeMethods.has(g)}
                        onChange={() =>
                          setActiveMethods((prev) => {
                            const next = new Set(prev);
                            if (next.has(g)) next.delete(g);
                            else next.add(g);
                            return next;
                          })
                        }
                      />
                      {g}
                    </span>
                    <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]">
                      {int(methodCounts[g])}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* ---------------- selected system panel ---------------- */}
          {info !== null && (
            <div className="pointer-events-auto panel-raised max-w-sm self-start p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-[14px] font-medium text-[var(--color-ivory)]">
                    {data.name[info]}
                  </p>
                  <p className="text-[11.5px] text-[var(--color-muted)]">{data.host[info]}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="cursor-pointer text-[11px] text-[var(--color-muted)] hover:text-[var(--color-ivory)]"
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>
              <dl className="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-1.5 font-[family-name:var(--font-mono)] text-[11px]">
                <dt className="text-[var(--color-muted)]">Distance</dt>
                <dd className="text-[var(--color-dim)]">
                  {num(data.dist_pc[info], 2)} pc
                  <span className="text-[var(--color-muted)]">
                    {" "}
                    ({num(data.dist_pc[info] * LY_PER_PC, 1)} ly)
                  </span>
                </dd>
                <dt className="text-[var(--color-muted)]">Radius</dt>
                <dd className="text-[var(--color-dim)]">{num(data.rade[info], 2)} R⊕</dd>
                <dt className="text-[var(--color-muted)]">T_eq</dt>
                <dd className="text-[var(--color-dim)]">{num(data.teq[info], 0)} K</dd>
                <dt className="text-[var(--color-muted)]">HZ probability</dt>
                <dd className="text-[var(--color-dim)]">{num(data.hz_prob[info], 2)}</dd>
                <dt className="text-[var(--color-muted)]">Method</dt>
                <dd className="text-[var(--color-dim)]">{data.method[info] ?? "—"}</dd>
                <dt className="text-[var(--color-muted)]">Discovered</dt>
                <dd className="text-[var(--color-dim)]">
                  {Number.isFinite(data.disc_year[info]) ? data.disc_year[info] : EMDASH}
                </dd>
                <dt className="text-[var(--color-muted)]">Earth-2.0 index</dt>
                <dd className="text-[var(--color-gold)]">{num(data.earth2_index[info], 3)}</dd>
              </dl>
              {deepDiveSlugs?.has(slugify(data.name[info])) ? (
                <Link
                  href={"/candidate/" + slugify(data.name[info])}
                  className="link mt-3 inline-block text-[12px]"
                >
                  Open deep dive →
                </Link>
              ) : (
                <p className="mt-3 text-[11px] text-[var(--color-muted)]">
                  Not one of the ranked candidates with a full deep-dive page.
                </p>
              )}
            </div>
          )}

          <div className="flex w-full items-end justify-between gap-3">
            <div className="pointer-events-auto panel-raised w-full max-w-xl p-3" aria-label="Discovery history controls">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="eyebrow">Discovery history · through {discoveryYear}</p>
                  <p className="mt-0.5 text-[10.5px] text-[var(--color-muted)]">
                    Archive chronology—not stellar motion. The map grows as discoveries enter the record.
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      if (discoveryYear >= maxDiscoveryYear) setDiscoveryYear(minDiscoveryYear);
                      setPlayingHistory((value) => !value);
                    }}
                    aria-pressed={playingHistory}
                    className="min-h-9 cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-3 py-1 text-[11px] text-[var(--color-ivory)] hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                  >
                    {playingHistory ? "Pause" : "Play"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPlayingHistory(false);
                      setDiscoveryYear(maxDiscoveryYear);
                    }}
                    className="min-h-9 cursor-pointer rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] px-3 py-1 text-[11px] text-[var(--color-dim)] hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
                  >
                    Show all
                  </button>
                </div>
              </div>
              <input
                type="range"
                min={minDiscoveryYear}
                max={maxDiscoveryYear}
                step={1}
                value={discoveryYear}
                onChange={(event) => {
                  setPlayingHistory(false);
                  setDiscoveryYear(Number(event.target.value));
                }}
                aria-label="Latest discovery year shown"
                aria-valuetext={`Discoveries through ${discoveryYear}`}
                className="w-full accent-[var(--color-cyan)]"
              />
              <div className="mt-0.5 flex justify-between font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]">
                <span>{minDiscoveryYear}</span>
                <span aria-live="polite">{compactInt(filterMask.nVisible)} systems visible</span>
                <span>{maxDiscoveryYear}</span>
              </div>
              {unknownDiscoveryYears > 0 && discoveryYear === maxDiscoveryYear && (
                <p className="mt-1 text-[10px] text-[var(--color-faint)]">
                  “Show all” also includes {compactInt(unknownDiscoveryYears)} records without a discovery year.
                </p>
              )}
            </div>
            <div className="pointer-events-none hidden max-w-md text-right font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-faint)] xl:block">
              {compactInt(filterMask.nVisible)} of {compactInt(data.n_points)} systems shown ·{" "}
              {compactInt(data.n_excluded_no_distance)} excluded (no measured distance) · drag to
              orbit, right-click or two-finger drag to pan, scroll or use the buttons to zoom, click
              a star
            </div>
          </div>
        </div>

        {/* ---------------- zoom controls ---------------- */}
        <div className="pointer-events-auto absolute bottom-4 right-4 z-10 flex flex-col gap-1">
          <button
            type="button"
            onClick={() => zoomBy(1 / 1.35)}
            aria-label="Zoom in"
            title="Zoom in"
            className="panel-raised cursor-pointer px-2.5 py-1.5 text-[13px] text-[var(--color-dim)] hover:text-[var(--color-cyan)]"
          >
            +
          </button>
          <button
            type="button"
            onClick={() => zoomBy(1.35)}
            aria-label="Zoom out"
            title="Zoom out"
            className="panel-raised cursor-pointer px-2.5 py-1.5 text-[13px] text-[var(--color-dim)] hover:text-[var(--color-cyan)]"
          >
            −
          </button>
        </div>
      </div>
    </div>
  );
}
