import type { EvidenceLabel as EvidenceLabelType } from "@/lib/observatory-types";

const TONES: Record<string, string> = {
  OBSERVED: "var(--color-cyan)",
  DERIVED: "var(--color-sci)",
  "MODEL-INFERRED": "var(--color-gold)",
  SCENARIO: "var(--color-rose)",
  FORECAST: "var(--color-violet)",
  SIMULATED: "var(--color-rose)",
  "MODEL-SENSITIVITY": "var(--color-gold)",
  OBSERVED_CONTROL_WITH_DERIVED_MODEL_OUTPUTS: "var(--color-cyan)",
};

export function EvidenceLabel({ label }: { label: EvidenceLabelType }) {
  const tone = TONES[label] ?? "var(--color-muted)";
  return (
    <span
      className="inline-flex min-h-6 items-center rounded-full border px-2 py-0.5 font-[family-name:var(--font-mono)] text-[9px] uppercase tracking-[0.12em]"
      style={{ color: tone, borderColor: `color-mix(in srgb, ${tone} 42%, transparent)` }}
    >
      {label.replaceAll("_", " ")}
    </span>
  );
}
