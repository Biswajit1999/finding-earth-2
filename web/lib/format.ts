/**
 * Formatting helpers.
 *
 * One rule governs this file: **a missing measurement renders as an em dash,
 * never as zero.** Formatting `null` as `0.00` would turn "we do not know this
 * planet's mass" into "this planet has no mass", which is the single easiest way
 * for an interface to lie about data.
 */

export const EMDASH = "—";

export function num(
  v: number | null | undefined,
  digits = 2,
  fallback: string = EMDASH,
): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return fallback;
  return v.toFixed(digits);
}

export function int(v: number | null | undefined, fallback: string = EMDASH): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return fallback;
  return Math.round(v).toLocaleString("en-GB");
}

export function compactInt(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return EMDASH;
  return v.toLocaleString("en-GB");
}

export function pct(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return EMDASH;
  return `${(v * 100).toFixed(digits)}%`;
}

/** Significant-figure formatting for values spanning many orders of magnitude. */
export function sig(v: number | null | undefined, figures = 3): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return EMDASH;
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1e5 || abs < 1e-3) return v.toExponential(figures - 1);
  return Number(v.toPrecision(figures)).toString();
}

/** Parsecs to light years, for readers who think in light years. */
export function pcToLy(pc: number | null | undefined): number | null {
  if (pc === null || pc === undefined || !Number.isFinite(pc)) return null;
  return pc * 3.26156;
}

export function distanceLabel(pc: number | null | undefined): string {
  const ly = pcToLy(pc);
  if (ly === null) return EMDASH;
  return `${num(pc, 1)} pc / ${num(ly, 1)} ly`;
}

/* -------------------------------------------------------------------------
   Domain vocabulary
   ------------------------------------------------------------------------- */

export const MASS_CLASS_LABEL: Record<string, string> = {
  measured: "measured",
  msini_deprojected: "M sin i / sin i",
  msini_lower_limit: "M sin i",
  upper_limit: "upper limit",
  inferred_mass_radius: "inferred",
  missing: "no mass",
};

export const MASS_CLASS_MEANING: Record<string, string> = {
  measured: "A directly measured dynamical mass.",
  msini_deprojected:
    "A radial-velocity minimum mass, de-projected using an inclination measured elsewhere.",
  msini_lower_limit:
    "A radial-velocity minimum mass. The true mass is M/sin(i), so this is a LOWER limit.",
  upper_limit: "Reported only as an upper limit, not a measurement.",
  inferred_mass_radius:
    "NOT measured. Predicted from the planet's radius by a mass-radius relation, so it adds no information beyond the radius.",
  missing: "No mass is available for this planet.",
};

/** Colour token per mass class. Always paired with the text label, never alone. */
export const MASS_CLASS_TONE: Record<string, string> = {
  measured: "text-[var(--color-sci)]",
  msini_deprojected: "text-[var(--color-cyan)]",
  msini_lower_limit: "text-[var(--color-gold)]",
  upper_limit: "text-[var(--color-muted)]",
  inferred_mass_radius: "text-[var(--color-rose)]",
  missing: "text-[var(--color-muted)]",
};

export const METHOD_TONE: Record<string, string> = {
  Transit: "var(--color-sci)",
  "Radial Velocity": "var(--color-gold)",
  Microlensing: "var(--color-verdant)",
  Imaging: "var(--color-violet)",
  "Transit Timing Variations": "var(--color-rose)",
  "Solar System reference": "var(--color-cyan)",
};

export function methodColour(m: string | null): string {
  return (m && METHOD_TONE[m]) || "var(--color-muted)";
}

/**
 * Spectral class from effective temperature.
 * Boundaries follow the conventional Morgan-Keenan main-sequence divisions.
 */
export function spectralClass(teff: number | null | undefined): string {
  if (teff === null || teff === undefined || !Number.isFinite(teff)) return EMDASH;
  if (teff >= 30000) return "O";
  if (teff >= 10000) return "B";
  if (teff >= 7500) return "A";
  if (teff >= 6000) return "F";
  if (teff >= 5200) return "G";
  if (teff >= 3700) return "K";
  if (teff >= 2400) return "M";
  return "L";
}

/**
 * Approximate blackbody colour for a stellar effective temperature.
 * Used for the 3D map and star glyphs. Perceptual approximation, not photometry.
 */
export function starColour(teff: number | null | undefined): string {
  const t = teff ?? 5000;
  if (t >= 10000) return "#a7c0ff";
  if (t >= 7500) return "#cbd8ff";
  if (t >= 6000) return "#f4f2ea";
  if (t >= 5200) return "#ffe9b8";
  if (t >= 3700) return "#ffc478";
  if (t >= 2400) return "#ff8f5e";
  return "#ff6b4a";
}

/** UTC ISO string to a readable UTC label. */
export function utcLabel(iso: string | null | undefined): string {
  if (!iso) return EMDASH;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export function slugify(name: string): string {
  return name.replace(/\s+/g, "_").replace(/\//g, "-");
}
