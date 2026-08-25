"use client";

/**
 * Per-world orbit and habitable-zone view.
 *
 * Every distance plotted here -- the semi-major axis, the eccentricity, and
 * the five Kopparapu et al. (2013) habitable-zone boundaries -- is computed
 * in Python (earth2.habitability.hz) and read from the deep-dive JSON,
 * exactly like every other number on this page. Nothing here recomputes the
 * habitable-zone flux model in JavaScript.
 *
 * What IS a visualisation choice, stated here rather than left implicit:
 * star and planet radii are shown on a compressed, non-linear scale so a
 * planet is visible at all next to its star, and the whole system is
 * rescaled so its outermost habitable-zone boundary fits the view regardless
 * of whether the real orbit is a few stellar radii (most M-dwarf candidates
 * here) or a fraction of an au. Distances *relative to the HZ boundaries*
 * are preserved; the star-to-planet size ratio and the absolute AU scale are
 * not literal. Surface colour is a physically-motivated illustration from
 * equilibrium temperature, not an observation -- see the disclaimer on this
 * page for why that distinction matters.
 */

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useReducedMotion } from "motion/react";
import * as THREE from "three";

import { teffColour } from "@/components/three/StarField";

export interface SystemViewProps {
  hostTeffK: number | null;
  hostRadiusSun: number | null;
  planetRadiusEarth: number | null;
  planetTeqK: number | null;
  semiMajorAxisAu: number | null;
  eccentricity: number | null;
  hzBoundariesAu: {
    recent_venus: number | null;
    runaway_greenhouse: number | null;
    moist_greenhouse: number | null;
    maximum_greenhouse: number | null;
    early_mars: number | null;
  } | null;
}

/** Cold (blue) to hot (red) illustrative colour for a planet's equilibrium
 * temperature. Deliberately distinct from teffColour (stellar temperatures
 * run 2,000-40,000 K; equilibrium temperatures of interest here run
 * 150-1,500 K) so the two are never visually confused. */
function eqTempColour(k: number | null): [number, number, number] {
  const t = k ?? 255;
  if (t < 200) return [0.55, 0.72, 0.98]; // frigid, blue-white
  if (t < 260) return [0.62, 0.83, 0.86]; // cold, pale cyan
  if (t < 320) return [0.42, 0.75, 0.55]; // temperate, Earth-like green
  if (t < 450) return [0.85, 0.72, 0.35]; // warm, tan
  if (t < 700) return [0.87, 0.5, 0.28]; // hot, orange
  return [0.82, 0.32, 0.24]; // scorched, red
}

function Star({ teffK, radius }: { teffK: number | null; radius: number }) {
  const [r, g, b] = teffColour(teffK);
  return (
    <mesh>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial color={new THREE.Color(r, g, b)} toneMapped={false} />
    </mesh>
  );
}

function OrbitingPlanet({
  semiMajorAxis,
  eccentricity,
  radius,
  colour,
  periodSeconds,
  animate,
}: {
  semiMajorAxis: number;
  eccentricity: number;
  radius: number;
  colour: [number, number, number];
  periodSeconds: number;
  animate: boolean;
}) {
  const ref = useRef<THREE.Group>(null);
  const b = semiMajorAxis * Math.sqrt(Math.max(1 - eccentricity * eccentricity, 0));

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = animate ? clock.getElapsedTime() : 0;
    const theta = (t / periodSeconds) * Math.PI * 2;
    // Star sits at a focus of the ellipse, not its centre.
    const focusOffset = semiMajorAxis * eccentricity;
    ref.current.position.set(
      Math.cos(theta) * semiMajorAxis - focusOffset,
      0,
      Math.sin(theta) * b,
    );
  });

  return (
    <group ref={ref}>
      <mesh>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial color={new THREE.Color(...colour)} roughness={0.85} />
      </mesh>
    </group>
  );
}

function OrbitPath({ semiMajorAxis, eccentricity }: { semiMajorAxis: number; eccentricity: number }) {
  const points = useMemo(() => {
    const b = semiMajorAxis * Math.sqrt(Math.max(1 - eccentricity * eccentricity, 0));
    const focusOffset = semiMajorAxis * eccentricity;
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 128; i++) {
      const theta = (i / 128) * Math.PI * 2;
      pts.push(new THREE.Vector3(
        Math.cos(theta) * semiMajorAxis - focusOffset, 0, Math.sin(theta) * b,
      ));
    }
    return pts;
  }, [semiMajorAxis, eccentricity]);
  const geom = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);
  return (
    <primitive object={new THREE.Line(geom, new THREE.LineBasicMaterial({ color: "#5b6472", transparent: true, opacity: 0.55 }))} />
  );
}

function HzAnnulus({ inner, outer, colour, opacity }: { inner: number; outer: number; colour: string; opacity: number }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[inner, outer, 96]} />
      <meshBasicMaterial color={colour} transparent opacity={opacity} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  );
}

export function SystemView({
  hostTeffK, hostRadiusSun, planetRadiusEarth, planetTeqK,
  semiMajorAxisAu, eccentricity, hzBoundariesAu,
}: SystemViewProps) {
  const reduced = useReducedMotion();

  const hz = hzBoundariesAu;
  const a = semiMajorAxisAu ?? 1.0;
  const e = Math.min(Math.max(eccentricity ?? 0, 0), 0.9);

  // Scale the whole scene so the outermost feature (widest HZ boundary, or
  // the orbit's own aphelion if it lies further out) fits a fixed display
  // radius -- this is the one deliberate "not to scale" choice, stated in
  // the module docstring above and in the caption this component is always
  // rendered with.
  const outerAu = Math.max(
    hz?.early_mars ?? 0, hz?.maximum_greenhouse ?? 0, a * (1 + e), 0.05,
  );
  const scale = 5.2 / outerAu;

  const starRadius = Math.min(1.15, Math.max(0.28, 0.28 + 0.55 * Math.cbrt(hostRadiusSun ?? 1)));
  const planetRadius = Math.min(0.42, Math.max(0.09, 0.09 + 0.11 * Math.cbrt(planetRadiusEarth ?? 1)));
  const planetColour = eqTempColour(planetTeqK);

  return (
    <div className="relative h-[320px] w-full overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-line)] bg-[var(--color-void)] sm:h-[380px]">
      <Canvas
        camera={{ position: [0, 3.4, 5.6], fov: 45 }}
        dpr={[1, 1.75]}
        gl={{ antialias: true, powerPreference: "high-performance" }}
        onCreated={({ gl }) => gl.setClearColor("#07090e", 1)}
      >
        <ambientLight intensity={0.35} />
        <pointLight position={[0, 0, 0]} intensity={40} decay={2} />

        <Star teffK={hostTeffK} radius={starRadius} />

        {hz?.runaway_greenhouse != null && hz?.maximum_greenhouse != null && (
          <HzAnnulus
            inner={hz.runaway_greenhouse * scale}
            outer={hz.maximum_greenhouse * scale}
            colour="#2f7d32"
            opacity={0.22}
          />
        )}
        {hz?.recent_venus != null && hz?.early_mars != null && (
          <HzAnnulus
            inner={hz.recent_venus * scale}
            outer={hz.early_mars * scale}
            colour="#c9a13b"
            opacity={0.1}
          />
        )}

        <OrbitPath semiMajorAxis={a * scale} eccentricity={e} />
        <OrbitingPlanet
          semiMajorAxis={a * scale}
          eccentricity={e}
          radius={planetRadius}
          colour={planetColour}
          periodSeconds={14}
          animate={!reduced}
        />
      </Canvas>

      <p className="pointer-events-none absolute bottom-2 left-2.5 right-2.5 text-[10px] leading-snug text-[var(--color-faint)]">
        Orbit and habitable-zone boundaries computed in Python from this system&rsquo;s
        actual parameters. Sizes and the overall scale are compressed for visibility, not
        literal; green = conservative HZ, gold = optimistic HZ.
      </p>
    </div>
  );
}
