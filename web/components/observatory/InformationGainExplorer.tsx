"use client";

import { motion, useReducedMotion } from "motion/react";
import { useMemo, useState } from "react";

import { EvidenceLabel } from "@/components/observatory/EvidenceLabel";
import type { InformationGainRow } from "@/lib/observatory-types";

function fmt(value: number | null, digits = 3): string {
  return value === null ? "unsupported" : value.toLocaleString("en-GB", { maximumSignificantDigits: digits });
}

export function InformationGainExplorer({ rows }: { rows: InformationGainRow[] }) {
  const planets = [...new Set(rows.map((row) => row.pl_name))];
  const [planet, setPlanet] = useState(planets[0]);
  const targetRows = useMemo(() => rows.filter((row) => row.pl_name === planet), [planet, rows]);
  const [action, setAction] = useState(targetRows[0]?.action_id ?? "");
  const selected = targetRows.find((row) => row.action_id === action) ?? targetRows[0];
  const reduced = useReducedMotion();

  if (!selected) return null;

  return (
    <section className="mx-auto max-w-[1400px] px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="eig-explorer-title">
      <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr]">
        <div>
          <p className="eyebrow text-[var(--color-rose)]">Decision laboratory</p>
          <h2 id="eig-explorer-title" className="mt-3 text-[length:var(--text-title)] font-light">Choose a world and a measurement</h2>
          <p className="mt-4 max-w-[54ch] text-sm leading-relaxed text-[var(--color-muted)]">
            The calculator compares a declared current uncertainty with a synthetic future precision. It reports expected posterior shrinkage and expected KL information in bits.
          </p>
          <div className="mt-8 grid gap-5">
            <label className="text-xs text-[var(--color-dim)]">
              Candidate
              <select
                value={planet}
                onChange={(event) => {
                  const nextPlanet = event.target.value;
                  setPlanet(nextPlanet);
                  setAction(rows.find((row) => row.pl_name === nextPlanet)?.action_id ?? "");
                }}
                className="mt-2 min-h-11 w-full rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-panel)] px-3 text-sm text-[var(--color-ivory)]"
              >
                {planets.map((name) => <option key={name}>{name}</option>)}
              </select>
            </label>
            <label className="text-xs text-[var(--color-dim)]">
              Measurement action
              <select value={selected.action_id} onChange={(event) => setAction(event.target.value)} className="mt-2 min-h-11 w-full rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-panel)] px-3 text-sm text-[var(--color-ivory)]">
                {targetRows.map((row) => <option key={row.action_id} value={row.action_id}>{row.parameter}</option>)}
              </select>
            </label>
          </div>
        </div>

        <motion.article key={`${planet}-${selected.action_id}`} initial={reduced ? false : { opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.28 }} className="panel-raised p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="eyebrow">Expected update</p>
            <EvidenceLabel label={selected.label} />
          </div>
          <h3 className="mt-5 font-[family-name:var(--font-display)] text-2xl text-[var(--color-ivory)]">{selected.pl_name}</h3>
          <p className="mt-1 text-sm text-[var(--color-muted)]">{selected.parameter}</p>
          {selected.expected_information_gain_bits === null ? (
            <div className="mt-10 border-l-2 border-[var(--color-rose)] pl-4">
              <p className="text-lg text-[var(--color-ivory)]">No defensible calculation</p>
              <p className="mt-2 text-sm leading-relaxed text-[var(--color-muted)]">The catalogue lacks a finite two-sided value and uncertainty for this action. Missing support remains visible rather than becoming a zero.</p>
            </div>
          ) : (
            <>
              <div className="mt-8 grid gap-6 sm:grid-cols-3">
                <div><p className="eyebrow">Prior σ</p><p className="mt-2 font-[family-name:var(--font-mono)] text-xl text-[var(--color-ivory)]">{fmt(selected.prior_sigma)} <span className="text-xs text-[var(--color-muted)]">{selected.unit}</span></p></div>
                <div><p className="eyebrow">Synthetic σ</p><p className="mt-2 font-[family-name:var(--font-mono)] text-xl text-[var(--color-ivory)]">{fmt(selected.observation_sigma)} <span className="text-xs text-[var(--color-muted)]">{selected.unit}</span></p></div>
                <div><p className="eyebrow">Expected posterior σ</p><p className="mt-2 font-[family-name:var(--font-mono)] text-xl text-[var(--color-cyan)]">{fmt(selected.expected_posterior_sigma)} <span className="text-xs text-[var(--color-muted)]">{selected.unit}</span></p></div>
              </div>
              <div className="mt-8 border-t border-[var(--color-line)] pt-6">
                <p className="font-[family-name:var(--font-mono)] text-4xl font-light tabular-nums text-[var(--color-gold)]">{fmt(selected.expected_information_gain_bits, 4)} bits</p>
                <p className="mt-2 text-xs text-[var(--color-muted)]">Expected KL information · target-local action rank {fmt(selected.within_target_information_rank, 2)}</p>
              </div>
            </>
          )}
          <p className="mt-8 text-xs leading-relaxed text-[var(--color-muted)]">Observing time and cost: {selected.cost_or_time.replaceAll("_", " ")}. This is a precision requirement, not an observing proposal or instrument guarantee.</p>
        </motion.article>
      </div>
    </section>
  );
}

