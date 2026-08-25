"use client";

/**
 * GPU point cloud of real planetary systems.
 *
 * Every point is a system with a MEASURED distance, placed at its true
 * equatorial Cartesian position in parsecs with the Sun at the origin. Nothing
 * here is a decorative particle: if a planet has no parallax-derived distance,
 * the Python export excluded it rather than inventing a position, and the count
 * of exclusions is reported to the reader.
 *
 * Rendering uses a single THREE.Points with per-vertex colour and size, so
 * thousands of systems cost one draw call.
 */

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

import type { UniverseFile } from "@/lib/types";

export type ColourMode = "index" | "teff" | "method" | "distance";

const METHOD_COLOURS: Record<string, [number, number, number]> = {
  Transit: [0.357, 0.553, 0.937],
  "Radial Velocity": [0.878, 0.639, 0.243],
  Microlensing: [0.31, 0.69, 0.478],
  Imaging: [0.604, 0.498, 0.878],
  "Transit Timing Variations": [0.878, 0.376, 0.494],
};

export function teffColour(t: number | null): [number, number, number] {
  const k = t ?? 5000;
  if (k >= 10000) return [0.655, 0.753, 1.0];
  if (k >= 7500) return [0.796, 0.847, 1.0];
  if (k >= 6000) return [0.957, 0.949, 0.918];
  if (k >= 5200) return [1.0, 0.914, 0.722];
  if (k >= 3700) return [1.0, 0.769, 0.471];
  if (k >= 2400) return [1.0, 0.561, 0.369];
  return [1.0, 0.42, 0.29];
}

/** Viridis-like ramp for the Earth-2.0 index. Perceptually ordered. */
function indexColour(v: number | null): [number, number, number] {
  if (v === null || !Number.isFinite(v)) return [0.26, 0.29, 0.35];
  const stops: [number, [number, number, number]][] = [
    [0.0, [0.267, 0.005, 0.329]],
    [0.25, [0.229, 0.322, 0.545]],
    [0.5, [0.128, 0.567, 0.551]],
    [0.75, [0.369, 0.789, 0.383]],
    [1.0, [0.993, 0.906, 0.144]],
  ];
  const t = Math.max(0, Math.min(1, v));
  for (let i = 0; i < stops.length - 1; i++) {
    const [a, ca] = stops[i]!;
    const [b, cb] = stops[i + 1]!;
    if (t >= a && t <= b) {
      const f = (t - a) / (b - a || 1);
      return [
        ca[0] + (cb[0] - ca[0]) * f,
        ca[1] + (cb[1] - ca[1]) * f,
        ca[2] + (cb[2] - ca[2]) * f,
      ];
    }
  }
  return [0.993, 0.906, 0.144];
}

function distanceColour(d: number): [number, number, number] {
  const t = Math.max(0, Math.min(1, Math.log10(Math.max(d, 1)) / 3.5));
  return [0.31 + 0.6 * (1 - t), 0.82 - 0.35 * t, 0.88 - 0.1 * t];
}

export function StarField({
  data,
  colourMode = "index",
  scale = 0.012,
  pointScale = 1,
  highlightIndices,
  rotate = true,
  rotationSpeed = 0.012,
}: {
  data: UniverseFile;
  colourMode?: ColourMode;
  scale?: number;
  pointScale?: number;
  highlightIndices?: Set<number>;
  rotate?: boolean;
  rotationSpeed?: number;
}) {
  const group = useRef<THREE.Group>(null);

  const { positions, colours, sizes } = useMemo(() => {
    const n = data.n_points;
    const positions = new Float32Array(n * 3);
    const colours = new Float32Array(n * 3);
    const sizes = new Float32Array(n);

    for (let i = 0; i < n; i++) {
      // Log-compress radial distance: real positions span 1 pc to >8 kpc, and a
      // linear map puts 99% of systems in an invisible speck at the origin. The
      // compression is monotonic, so relative ordering and direction stay true,
      // and the interface states that the radial axis is non-linear.
      const x = data.x[i] ?? 0;
      const y = data.y[i] ?? 0;
      const z = data.z[i] ?? 0;
      const r = Math.sqrt(x * x + y * y + z * z) || 1;
      const rc = Math.log10(1 + r) * 120;
      positions[i * 3] = (x / r) * rc * scale;
      positions[i * 3 + 1] = (y / r) * rc * scale;
      positions[i * 3 + 2] = (z / r) * rc * scale;

      let c: [number, number, number];
      switch (colourMode) {
        case "teff":
          c = teffColour(data.st_teff[i] ?? null);
          break;
        case "method":
          c = METHOD_COLOURS[data.method[i] ?? ""] ?? [0.42, 0.46, 0.54];
          break;
        case "distance":
          c = distanceColour(data.dist_pc[i] ?? 1);
          break;
        default:
          c = indexColour(data.earth2_index[i] ?? null);
      }

      const hot = highlightIndices?.has(i) ?? false;
      const idx = data.earth2_index[i] ?? 0;
      colours[i * 3] = hot ? 1 : c[0];
      colours[i * 3 + 1] = hot ? 0.85 : c[1];
      colours[i * 3 + 2] = hot ? 0.35 : c[2];

      // Size encodes the index so good candidates are findable, with a floor so
      // nothing disappears entirely.
      sizes[i] = (hot ? 7 : 1.6 + idx * 4.2) * pointScale;
    }
    return { positions, colours, sizes };
  }, [data, colourMode, scale, pointScale, highlightIndices]);

  useFrame((_, delta) => {
    if (rotate && group.current) {
      group.current.rotation.y += delta * rotationSpeed;
    }
  });

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    g.setAttribute("color", new THREE.BufferAttribute(colours, 3));
    g.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
    return g;
  }, [positions, colours, sizes]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexShader: `
          attribute float aSize;
          varying vec3 vColor;
          void main() {
            vColor = color;
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = aSize * (140.0 / -mv.z);
            gl_Position = projectionMatrix * mv;
          }
        `,
        fragmentShader: `
          varying vec3 vColor;
          void main() {
            vec2 d = gl_PointCoord - vec2(0.5);
            float r = length(d);
            if (r > 0.5) discard;
            float a = smoothstep(0.5, 0.06, r);
            gl_FragColor = vec4(vColor, a);
          }
        `,
        vertexColors: true,
      }),
    [],
  );

  return (
    <group ref={group}>
      <points geometry={geometry} material={material} />
      {/* The Sun at the origin — our own vantage point. */}
      <mesh>
        <sphereGeometry args={[0.055, 20, 20]} />
        <meshBasicMaterial color="#ffd77a" />
      </mesh>
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array([0, 0, 0]), 3]}
          />
        </bufferGeometry>
        <pointsMaterial size={0.3} color="#ffd77a" transparent opacity={0.35} sizeAttenuation />
      </points>
    </group>
  );
}
