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
import { Suspense, useMemo, useState } from "react";

import { StarField, type ColourMode } from "@/components/three/StarField";
import type { UniverseFile } from "@/lib/types";
import { compactInt, num, slugify } from "@/lib/format";

const COLOUR_MODES: { key: ColourMode; label: string }[] = [
  { key: "index", label: "Earth-2.0 index" },
  { key: "teff", label: "Host temperature" },
  { key: "method", label: "Discovery method" },
  { key: "distance", label: "Distance" },
];

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

export function UniverseExplorer({ data }: { data: UniverseFile }) {
  const reduced = useReducedMotion();
  const [mode, setMode] = useState<ColourMode>("index");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [webglFailed, setWebglFailed] = useState(false);
  const [rotate, setRotate] = useState(!reduced);

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

  const info = selected !== null ? selected : null;

  if (webglFailed) {
    return (
      <div className="panel mx-auto max-w-2xl p-8 text-center">
        <p className="text-[14px] text-[var(--color-ivory)]">
          WebGL is unavailable in this browser.
        </p>
        <p className="mt-2 text-[13px] text-[var(--color-muted)]">
          The 3D universe requires WebGL. Try the{" "}
          <a href="/atlas" className="link">
            Candidate Atlas
          </a>{" "}
          for the same data as a searchable table instead.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="relative h-[74vh] min-h-[520px] w-full overflow-hidden border-y border-[var(--color-line)] bg-[var(--color-void)]">
        <Canvas
          camera={{ position: [0, 1.1, 5.2], fov: 55 }}
          dpr={[1, 1.75]}
          gl={{ antialias: true, powerPreference: "high-performance" }}
          onCreated={({ gl }) => gl.setClearColor("#07090e", 1)}
          onError={() => setWebglFailed(true)}
        >
          <Suspense fallback={null}>
            <StarField data={data} colourMode={mode} rotate={rotate} highlightIndices={highlight} />
          </Suspense>
          <OrbitControls
            enablePan
            enableZoom
            enableRotate
            minDistance={0.6}
            maxDistance={14}
            autoRotate={false}
            onStart={() => setRotate(false)}
          />
        </Canvas>

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
                          {num(data.dist_pc[i], 1)} pc
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
                <dd className="text-[var(--color-dim)]">{num(data.dist_pc[info], 2)} pc</dd>
                <dt className="text-[var(--color-muted)]">Radius</dt>
                <dd className="text-[var(--color-dim)]">{num(data.rade[info], 2)} R⊕</dd>
                <dt className="text-[var(--color-muted)]">T_eq</dt>
                <dd className="text-[var(--color-dim)]">{num(data.teq[info], 0)} K</dd>
                <dt className="text-[var(--color-muted)]">HZ probability</dt>
                <dd className="text-[var(--color-dim)]">{num(data.hz_prob[info], 2)}</dd>
                <dt className="text-[var(--color-muted)]">Method</dt>
                <dd className="text-[var(--color-dim)]">{data.method[info] ?? "—"}</dd>
                <dt className="text-[var(--color-muted)]">Earth-2.0 index</dt>
                <dd className="text-[var(--color-gold)]">{num(data.earth2_index[info], 3)}</dd>
              </dl>
              <Link
                href={"/candidate/" + slugify(data.name[info])}
                className="link mt-3 inline-block text-[12px]"
              >
                Open deep dive →
              </Link>
            </div>
          )}

          <div className="pointer-events-none self-end font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-faint)]">
            {compactInt(data.n_points)} systems · {compactInt(data.n_excluded_no_distance)}{" "}
            excluded (no measured distance) · drag to orbit, scroll to zoom
          </div>
        </div>
      </div>
    </div>
  );
}
