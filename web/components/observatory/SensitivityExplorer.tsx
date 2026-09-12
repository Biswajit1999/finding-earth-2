"use client";

import { useMemo, useState } from "react";

import type { SensitivityRow } from "@/lib/observatory-types";

function probabilityRange(lo: number | null, hi: number | null): string {
  if (lo === null || hi === null) return "unsupported";
  return `${(lo * 100).toFixed(1)}–${(hi * 100).toFixed(1)}%`;
}

export function SensitivityExplorer({ rows }: { rows: SensitivityRow[] }) {
  const [selectedName, setSelectedName] = useState(rows[0]?.pl_name ?? "");
  const selected = useMemo(() => rows.find((row) => row.pl_name === selectedName) ?? rows[0], [rows, selectedName]);
  if (!selected) return null;

  const metrics = [
    ["Legacy composite rank", `${selected.legacy_rank_min}–${selected.legacy_rank_max}`, Math.min(100, selected.legacy_rank_span * 8)],
    ["HZ probability across climate prescriptions", probabilityRange(selected.hz_model_probability_min, selected.hz_model_probability_max), (selected.hz_model_probability_range ?? 0) * 100],
    ["Rocky probability across supported models", probabilityRange(selected.p_rocky_model_min, selected.p_rocky_model_max), (selected.p_rocky_model_range ?? 0) * 100],
    ["HWO accessibility across trade cases", probabilityRange(selected.hwo_accessibility_min, selected.hwo_accessibility_max), ((selected.hwo_accessibility_max ?? 0) - (selected.hwo_accessibility_min ?? 0)) * 100],
  ] as const;

  return (
    <section className="mx-auto max-w-[1100px] px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="sensitivity-explorer-title">
      <div className="panel-raised p-6 sm:p-8">
        <div className="grid gap-6 sm:grid-cols-[1fr_18rem] sm:items-end">
          <div>
            <p className="eyebrow text-[var(--color-gold)]">Interactive robustness view</p>
            <h2 id="sensitivity-explorer-title" className="mt-3 text-[length:var(--text-title)] font-light">How much does the answer move?</h2>
          </div>
          <label className="text-xs text-[var(--color-dim)]">Candidate
            <select value={selectedName} onChange={(event) => setSelectedName(event.target.value)} className="mt-2 min-h-11 w-full rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-panel)] px-3 text-sm text-[var(--color-ivory)]">
              {rows.map((row) => <option key={row.pl_name}>{row.pl_name}</option>)}
            </select>
          </label>
        </div>
        <div className="mt-10 space-y-6">
          {metrics.map(([label, value, width]) => (
            <div key={label}>
              <div className="flex items-baseline justify-between gap-4 text-sm"><span className="text-[var(--color-muted)]">{label}</span><span className="font-[family-name:var(--font-mono)] text-[var(--color-ivory)]">{value}</span></div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-line)]"><div className="h-full rounded-full bg-[var(--color-gold)] transition-[width] duration-300" style={{ width: `${Math.max(2, width)}%` }} /></div>
            </div>
          ))}
        </div>
        <p className="mt-8 text-xs leading-relaxed text-[var(--color-muted)]">A short bar can also mean the relevant model is unsupported; the text value carries that distinction. The ranges cover the implemented model menu, not every plausible model.</p>
      </div>
    </section>
  );
}

