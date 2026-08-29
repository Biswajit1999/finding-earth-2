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
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

import type { UniverseFile } from "@/lib/types";

export type ColourMode = "index" | "teff" | "method" | "distance";

export const METHOD_COLOURS: Record<string, [number, number, number]> = {
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
export function indexColour(v: number | null): [number, number, number] {
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

export function distanceColour(d: number): [number, number, number] {
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
  rotationSpeed = 0.05,
  twinkle = true,
  visibleMask,
  onSelect,
  showDistanceLines = false,
  radialScale = "log",
  flagLowConfidenceAstrometry = false,
}: {
  data: UniverseFile;
  colourMode?: ColourMode;
  scale?: number;
  pointScale?: number;
  highlightIndices?: Set<number>;
  rotate?: boolean;
  rotationSpeed?: number;
  /**
   * Distinct from `rotate`: `rotate` also turns off the moment a viewer
   * manually drags to orbit (nothing to do with motion preference), so
   * gating the twinkle off that would kill it for anyone who ever touches
   * the camera. This should be wired straight to prefers-reduced-motion.
   */
  twinkle?: boolean;
  /** When present, index i is hidden (size forced to 0) unless visibleMask[i] is truthy. */
  visibleMask?: Uint8Array;
  /** Fires with the vertex index of the star the viewer clicked. */
  onSelect?: (index: number) => void;
  /** Faint radial spokes from the Sun to every currently-visible system. */
  showDistanceLines?: boolean;
  /**
   * "log" (default) compresses distance so nearby and far systems are both
   * visible in the same view. "linear" plots true parsecs -- offered so a
   * reader can see for themselves why compression is used (almost every
   * point collapses near the origin), not as an equally-informative
   * alternative projection.
   */
  radialScale?: "log" | "linear";
  /**
   * Dim points with Gaia RUWE > 1.4 (the archive's own threshold for "the
   * single-star astrometric fit is poor, often an unresolved binary").
   * Deliberately just dims the point rather than drawing a 3D uncertainty
   * sphere: the underlying distance posterior is asymmetric, and a sphere
   * would misrepresent it as a symmetric, precisely-bounded volume.
   */
  flagLowConfidenceAstrometry?: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const { positions, colours, sizes, phases, confidences, selections } = useMemo(() => {
    const n = data.n_points;
    const positions = new Float32Array(n * 3);
    const colours = new Float32Array(n * 3);
    const sizes = new Float32Array(n);
    const phases = new Float32Array(n);
    const confidences = new Float32Array(n);
    const selections = new Float32Array(n);

    for (let i = 0; i < n; i++) {
      // Log-compress radial distance by default: real positions span 1 pc to
      // >8 kpc, and a linear map puts 99% of systems in an invisible speck at
      // the origin. The compression is monotonic, so relative ordering and
      // direction stay true, and the interface states that the radial axis
      // is non-linear -- radialScale="linear" is the escape hatch that lets a
      // reader see that collapse for themselves rather than take it on faith.
      const x = data.x[i] ?? 0;
      const y = data.y[i] ?? 0;
      const z = data.z[i] ?? 0;
      const r = Math.sqrt(x * x + y * y + z * z) || 1;
      const rc = radialScale === "linear" ? r : Math.log10(1 + r) * 120;
      positions[i * 3] = (x / r) * rc * scale;
      positions[i * 3 + 1] = (y / r) * rc * scale;
      positions[i * 3 + 2] = (z / r) * rc * scale;

      const ruwe = data.gaia_ruwe[i];
      confidences[i] =
        flagLowConfidenceAstrometry && ruwe !== null && ruwe > 1.4 ? 0.32 : 1.0;

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
      selections[i] = hot ? 1 : 0;
      const idx = data.earth2_index[i] ?? 0;
      colours[i * 3] = hot ? 1 : c[0];
      colours[i * 3 + 1] = hot ? 0.85 : c[1];
      colours[i * 3 + 2] = hot ? 0.35 : c[2];

      // Size encodes the index so good candidates are findable, with a floor so
      // nothing disappears entirely. A point excluded by the active filters is
      // sized to zero rather than removed from the buffer, so filtering never
      // triggers a geometry rebuild.
      const visible = !visibleMask || visibleMask[i];
      // Keep the catalogue as a field of precise marks rather than bubbles.
      // The selected system gets its emphasis from a shader-drawn reticle,
      // not an oversized point that hides its neighbours.
      sizes[i] = visible ? (1.8 + idx * 2.4) * pointScale : 0;
      phases[i] = (i * 12.9898) % (Math.PI * 2);
    }
    return { positions, colours, sizes, phases, confidences, selections };
  }, [data, colourMode, scale, pointScale, highlightIndices, visibleMask, radialScale, flagLowConfidenceAstrometry]);

  useFrame(({ clock }, delta) => {
    if (rotate && group.current) {
      group.current.rotation.y += delta * rotationSpeed;
    }
    if (twinkle && materialRef.current) {
      materialRef.current.uniforms.uTime.value = clock.elapsedTime;
    }
  });

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    g.setAttribute("color", new THREE.BufferAttribute(colours, 3));
    g.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
    g.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
    g.setAttribute("aConf", new THREE.BufferAttribute(confidences, 1));
    g.setAttribute("aSelected", new THREE.BufferAttribute(selections, 1));
    return g;
  }, [positions, colours, sizes, phases, confidences, selections]);

  const uniforms = useMemo(() => ({ uTime: { value: 0 } }), []);

  // One segment (Sun -> system) per currently-visible point, in a single
  // LineSegments draw call. Kept very faint: at full n=6,327 this reads as a
  // soft radial texture around the origin, not a legible line to any one
  // star, which is the point -- it communicates "everything we have a
  // distance for radiates from here" without competing with the points.
  const linePositions = useMemo(() => {
    if (!showDistanceLines) return null;
    const n = data.n_points;
    let nVisible = 0;
    for (let i = 0; i < n; i++) if (sizes[i]! > 0) nVisible++;
    const arr = new Float32Array(nVisible * 6);
    let o = 0;
    for (let i = 0; i < n; i++) {
      if (sizes[i]! <= 0) continue;
      arr[o++] = 0;
      arr[o++] = 0;
      arr[o++] = 0;
      arr[o++] = positions[i * 3]!;
      arr[o++] = positions[i * 3 + 1]!;
      arr[o++] = positions[i * 3 + 2]!;
    }
    return arr;
  }, [showDistanceLines, data.n_points, positions, sizes]);

  // A star is "selected" on pointer up only if the pointer never travelled
  // far from where it went down -- i.e. our own click-vs-drag test, done on
  // raw raycasted pointer events rather than R3F's synthesized onClick.
  // OrbitControls shares this same canvas for orbit-dragging, and R3F's
  // built-in click/drag heuristic was unreliable in combination with it.
  const downPos = useRef<{ x: number; y: number } | null>(null);
  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    downPos.current = { x: e.clientX, y: e.clientY };
  };
  const handlePointerUp = (e: ThreeEvent<PointerEvent>) => {
    const down = downPos.current;
    downPos.current = null;
    if (!down || !onSelect || e.index === undefined) return;
    // Allow a little natural hand movement without confusing an intentional
    // click with an orbit drag. The raycaster still decides which real point
    // was targeted; this does not fabricate or snap to a different system.
    if (Math.hypot(e.clientX - down.x, e.clientY - down.y) < 10) {
      onSelect(e.index);
    }
  };

  return (
    <group ref={group}>
      <points
        geometry={geometry}
        onPointerDown={onSelect ? handlePointerDown : undefined}
        onPointerUp={onSelect ? handlePointerUp : undefined}
      >
        <shaderMaterial
          ref={materialRef}
          transparent
          depthWrite={false}
          depthTest
          blending={THREE.NormalBlending}
          uniforms={uniforms}
          vertexShader={`
            attribute float aSize;
            attribute float aPhase;
            attribute float aConf;
            attribute float aSelected;
            uniform float uTime;
            varying vec3 vColor;
            varying float vConf;
            varying float vSelected;
            varying float vDepthFade;
            varying float vPulse;
            void main() {
              vColor = color;
              vConf = aConf;
              vSelected = aSelected;
              // Ordinary catalogue points remain stable. Motion is reserved
              // for the selected-system reticle, where it communicates state
              // instead of making thousands of marks shimmer at once.
              vPulse = 0.88 + 0.12 * sin(uTime * 2.2 + aPhase);
              vec4 mv = modelViewMatrix * vec4(position, 1.0);
              float cameraDistance = max(-mv.z, 0.1);
              float perspective = clamp(5.5 / cameraDistance, 0.72, 1.45);
              vDepthFade = clamp(8.5 / cameraDistance, 0.68, 1.0);
              float catalogueSize = clamp(aSize * perspective, 1.75, 5.5);
              gl_PointSize = mix(catalogueSize, 17.0, aSelected);
              gl_Position = projectionMatrix * mv;
            }
          `}
          fragmentShader={`
            varying vec3 vColor;
            varying float vConf;
            varying float vSelected;
            varying float vDepthFade;
            varying float vPulse;
            void main() {
              vec2 d = gl_PointCoord - vec2(0.5);
              float r = length(d);
              if (r > 0.5) discard;
              float edge = max(fwidth(r), 0.018);
              float point = 1.0 - smoothstep(0.38, 0.5, r);
              float ring = 1.0 - smoothstep(
                0.035 + edge,
                0.075 + edge,
                abs(r - 0.38)
              );
              float selectedCore = 1.0 - smoothstep(0.055, 0.12, r);
              float selectedMark = max(selectedCore, ring * vPulse);
              float alpha = mix(point * 0.94 * vDepthFade, selectedMark * 0.94, vSelected);
              // Dimmed, not replaced by a fabricated uncertainty volume: a
              // planet flagged for possibly-unresolved-binary astrometry is
              // still a real point at its best-estimate position, just a
              // less certain one -- lower alpha says that plainly.
              gl_FragColor = vec4(vColor, alpha * vConf);
            }
          `}
          vertexColors
        />
      </points>
      {showDistanceLines && linePositions && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
          </bufferGeometry>
          <lineBasicMaterial
            color="#7fa8d9"
            transparent
            opacity={0.05}
            depthWrite={false}
          />
        </lineSegments>
      )}

      {/* The Sun at the origin — our own vantage point. */}
      <mesh>
        <sphereGeometry args={[0.055, 20, 20]} />
        <meshBasicMaterial color="#ffd77a" />
      </mesh>
      {/* A circular glow, not the stock square point sprite -- THREE.PointsMaterial
          with no sprite texture renders a literal square, which read as a stray
          box sitting behind the Sun. */}
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array([0, 0, 0]), 3]}
          />
        </bufferGeometry>
        <shaderMaterial
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          vertexShader={`
            void main() {
              vec4 mv = modelViewMatrix * vec4(position, 1.0);
              gl_PointSize = 46.0;
              gl_Position = projectionMatrix * mv;
            }
          `}
          fragmentShader={`
            void main() {
              vec2 d = gl_PointCoord - vec2(0.5);
              float r = length(d) * 2.0;
              float a = (1.0 - smoothstep(0.0, 1.0, r)) * 0.4;
              gl_FragColor = vec4(1.0, 0.85, 0.55, a);
            }
          `}
        />
      </points>
      <Html position={[0, 0.09, 0]} center distanceFactor={2.2} occlude={false}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            letterSpacing: "0.06em",
            color: "#e9e7e2",
            background: "rgba(7,9,14,0.72)",
            border: "1px solid rgba(255,215,122,0.4)",
            borderRadius: "3px",
            padding: "3px 6px",
            whiteSpace: "nowrap",
            pointerEvents: "none",
            userSelect: "none",
          }}
        >
          ☉ Sol — you are here
        </div>
      </Html>
    </group>
  );
}
