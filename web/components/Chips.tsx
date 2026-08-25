/**
 * Evidence chips.
 *
 * Each chip states an evidential fact in words. Colour reinforces the word; it
 * never carries the meaning alone, so the interface stays readable in greyscale
 * and for colour-blind readers.
 */

import { MASS_CLASS_LABEL, MASS_CLASS_MEANING } from "@/lib/format";

const TONES: Record<string, string> = {
  measured: "var(--color-sci)",
  msini_deprojected: "var(--color-cyan)",
  msini_lower_limit: "var(--color-gold)",
  upper_limit: "var(--color-muted)",
  inferred_mass_radius: "var(--color-rose)",
  missing: "var(--color-muted)",
};

export function MassClassChip({
  massClass,
  showGlyph = true,
}: {
  massClass: string | null;
  showGlyph?: boolean;
}) {
  const key = massClass ?? "missing";
  const tone = TONES[key] ?? "var(--color-muted)";
  const label = MASS_CLASS_LABEL[key] ?? key;

  // A distinct glyph per class so the chips remain distinguishable without colour.
  const glyph =
    key === "measured"
      ? "●"
      : key === "msini_deprojected"
        ? "◐"
        : key === "msini_lower_limit"
          ? "≥"
          : key === "upper_limit"
            ? "≤"
            : key === "inferred_mass_radius"
              ? "≈"
              : "○";

  return (
    <span className="chip" style={{ color: tone }} title={MASS_CLASS_MEANING[key]}>
      {showGlyph && <span aria-hidden>{glyph}</span>}
      <span>{label}</span>
    </span>
  );
}

export function HzChip({
  prob,
  extrapolated = false,
}: {
  prob: number | null;
  extrapolated?: boolean;
}) {
  if (prob === null || !Number.isFinite(prob)) {
    return (
      <span className="chip" style={{ color: "var(--color-muted)" }} title="Insufficient data to evaluate habitable-zone membership">
        <span aria-hidden>?</span>
        <span>unknown</span>
      </span>
    );
  }
  const tone =
    prob >= 0.9
      ? "var(--color-verdant)"
      : prob >= 0.5
        ? "var(--color-gold)"
        : "var(--color-muted)";
  const glyph = prob >= 0.9 ? "◆" : prob >= 0.5 ? "◈" : "◇";

  return (
    <span
      className="chip"
      style={{ color: tone }}
      title={
        extrapolated
          ? "Habitable-zone probability, conditional on draws inside the model's 2600–7200 K validity range. This host lies outside that range, so the evaluation is an extrapolation."
          : "Fraction of Monte Carlo draws placing this planet inside the conservative habitable zone"
      }
    >
      <span aria-hidden>{glyph}</span>
      <span>
        HZ {(prob * 100).toFixed(0)}%{extrapolated ? " ⚠" : ""}
      </span>
    </span>
  );
}

export function ControlChip() {
  return (
    <span
      className="chip"
      style={{ color: "var(--color-gold)" }}
      title="A Solar System body included as a comparison control. Not an exoplanet observation, and excluded from the ranking."
    >
      <span aria-hidden>★</span>
      <span>control</span>
    </span>
  );
}

export function StatusChip({
  ok,
  labelOk,
  labelNo,
  hint,
}: {
  ok: boolean;
  labelOk: string;
  labelNo: string;
  hint?: string;
}) {
  return (
    <span
      className="chip"
      style={{ color: ok ? "var(--color-verdant)" : "var(--color-rose)" }}
      title={hint}
    >
      <span aria-hidden>{ok ? "✓" : "✕"}</span>
      <span>{ok ? labelOk : labelNo}</span>
    </span>
  );
}
