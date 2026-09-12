"use client";

import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { EvidenceLabel } from "@/components/observatory/EvidenceLabel";
import type { MissionDetail, MissionRecord } from "@/lib/observatory-types";

export function MissionObservatory({ missions, details }: { missions: MissionRecord[]; details: Record<string, MissionDetail> }) {
  const [active, setActive] = useState(missions[0]?.mission_id ?? "jwst");
  const reduced = useReducedMotion();
  const detail = details[active];
  if (!detail) return null;

  return (
    <section className="mx-auto max-w-[1400px] px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="mission-observatory-title">
      <div className="grid gap-8 lg:grid-cols-[16rem_1fr]">
        <div>
          <p className="eyebrow text-[var(--color-violet)]">Six separate instruments</p>
          <h2 id="mission-observatory-title" className="mt-3 text-[length:var(--text-title)] font-light">Mission desk</h2>
          <div className="mt-7 grid grid-cols-2 gap-2 lg:grid-cols-1" role="tablist" aria-label="Missions">
            {missions.map((mission) => (
              <button key={mission.mission_id} type="button" role="tab" aria-selected={active === mission.mission_id} onClick={() => setActive(mission.mission_id)} className={`min-h-11 cursor-pointer rounded-[var(--radius-sm)] border px-3 py-2 text-left text-xs transition-colors ${active === mission.mission_id ? "border-[var(--color-violet)] bg-[var(--color-violet)]/10 text-[var(--color-ivory)]" : "border-[var(--color-line)] text-[var(--color-muted)] hover:border-[var(--color-line-strong)] hover:text-[var(--color-ivory)]"}`}>{mission.name}</button>
            ))}
          </div>
        </div>
        <motion.article key={active} role="tabpanel" initial={reduced ? false : { opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }} className="panel-raised p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">{detail.mission.agency}</p><h3 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-light text-[var(--color-ivory)]">{detail.mission.name}</h3><p className="mt-2 text-sm text-[var(--color-muted)]">{detail.mission.status}</p></div><div className="flex flex-wrap gap-2">{[...new Set(detail.evidence_records.map((record) => record.label))].map((label) => <EvidenceLabel key={label} label={label} />)}</div></div>
          <p className="mt-7 max-w-[70ch] text-[15px] leading-relaxed text-[var(--color-dim)]">{detail.mission.scientific_role}</p>
          <div className="mt-8 grid gap-8 md:grid-cols-2">
            <div><p className="eyebrow text-[var(--color-cyan)]">Can measure</p><ul className="mt-3 space-y-2 text-sm leading-relaxed text-[var(--color-muted)]">{detail.mission.measures.map((item) => <li key={item} className="border-l border-[var(--color-line-strong)] pl-3">{item}</li>)}</ul></div>
            <div><p className="eyebrow text-[var(--color-rose)]">Cannot establish alone</p><ul className="mt-3 space-y-2 text-sm leading-relaxed text-[var(--color-muted)]">{detail.mission.cannot_measure.map((item) => <li key={item} className="border-l border-[var(--color-line-strong)] pl-3">{item}</li>)}</ul></div>
          </div>
          {detail.evidence_records.length > 0 && <div className="mt-8 grid gap-px overflow-hidden rounded-[var(--radius-md)] bg-[var(--color-line)] sm:grid-cols-2">{detail.evidence_records.map((record) => <div key={record.evidence_id} className="bg-[var(--color-panel)] p-5"><EvidenceLabel label={record.label} /><p className="mt-5 font-[family-name:var(--font-mono)] text-2xl text-[var(--color-ivory)]">{record.value.toLocaleString("en-GB")}</p><p className="mt-1 text-xs text-[var(--color-muted)]">{record.unit}</p><p className="mt-4 text-xs leading-relaxed text-[var(--color-muted)]">{record.interpretation}</p></div>)}</div>}
          <p className="mt-8 border-l-2 border-[var(--color-gold)] pl-4 text-xs leading-relaxed text-[var(--color-muted)]">{detail.mission.forecast_boundary}</p>
        </motion.article>
      </div>
    </section>
  );
}

