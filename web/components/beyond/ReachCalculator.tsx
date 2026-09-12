"use client";

import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";

const LY_PER_PC = 3.261563777;
const PC_KM = 3.085677581491367e13;
const C_KM_S = 299_792.458;
const SPEEDS = [
  ["Voyager-like", 17 / C_KM_S],
  ["Parker reference", 191 / C_KM_S],
  ["0.01c", 0.01], ["0.1c", 0.1], ["0.2c", 0.2], ["0.5c", 0.5],
  ["0.9c", 0.9], ["0.99c", 0.99],
] as const;
const PRESETS = [
  ["Proxima b", 1.301], ["10 pc", 10], ["Milky Way", 1_000],
  ["Andromeda", 780_000], ["M51", 8_600_000],
] as const;

function number(value: number, digits = 2) {
  if (value >= 1e6 || value < 0.01) return value.toExponential(digits);
  return value.toLocaleString("en-GB", { maximumFractionDigits: digits });
}

export function ReachCalculator() {
  const [distance, setDistance] = useState(1.301);
  const values = useMemo(() => {
    const pc = Math.max(0.000001, Number.isFinite(distance) ? distance : 1.301);
    const ly = pc * LY_PER_PC;
    return {
      pc, ly, km: pc * PC_KM,
      separationMicroarcsec: 1e6 / pc,
      resolveOrbitMetres: 1.22 * 550e-9 / (1 / (pc * 206265)),
      fluxVs10pc: (10 / pc) ** 2,
    };
  }, [distance]);

  return (
    <section aria-labelledby="reach-title" className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
      <div className="grid gap-10 lg:grid-cols-[.7fr_1.3fr]">
        <div>
          <p className="eyebrow text-[var(--color-cyan)]">Interactive physics</p>
          <h2 id="reach-title" className="mt-3 text-[length:var(--text-display)] font-light leading-tight">Could we ever reach it?</h2>
          <p className="mt-5 max-w-[55ch] text-sm leading-relaxed text-[var(--color-dim)]">Choose any distance. Earth-frame travel is d/v. Traveller time uses special-relativistic time dilation. Light marks the causal limit; a massive spacecraft cannot reach c.</p>
          <label className="mt-7 block text-xs text-[var(--color-muted)]" htmlFor="distance-pc">Distance in parsecs</label>
          <input id="distance-pc" type="number" min="0.000001" step="0.1" value={distance} onChange={(event) => setDistance(Number(event.target.value))} className="mt-2 w-full rounded border border-[var(--color-line-strong)] bg-[var(--color-panel)] px-4 py-3 font-[family-name:var(--font-mono)] text-[var(--color-ivory)] outline-none focus:border-[var(--color-cyan)]" />
          <div className="mt-3 flex flex-wrap gap-2">
            {PRESETS.map(([label, pc]) => <button key={label} type="button" onClick={() => setDistance(pc)} className="rounded border border-[var(--color-line)] px-3 py-1.5 text-xs text-[var(--color-dim)] transition hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]">{label}</button>)}
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div key={values.pc} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: .25 }} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              {[["parsecs", values.pc], ["light-years", values.ly], ["kilometres", values.km]].map(([label, value]) => <div key={String(label)} className="panel-raised p-5"><p className="font-[family-name:var(--font-mono)] text-xl text-[var(--color-ivory)]">{number(Number(value), 3)}</p><p className="mt-2 text-xs uppercase tracking-wider text-[var(--color-muted)]">{label}</p></div>)}
            </div>
            <div className="overflow-x-auto rounded border border-[var(--color-line)]">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-[var(--color-panel)] text-xs uppercase tracking-wider text-[var(--color-muted)]"><tr><th className="p-3">Reference speed</th><th className="p-3">Earth-frame years</th><th className="p-3">Traveller years</th><th className="p-3">Lorentz γ</th></tr></thead>
                <tbody>{SPEEDS.map(([label, beta]) => { const earth = values.ly / beta; const gamma = 1 / Math.sqrt(1 - beta ** 2); return <tr key={label} className="border-t border-[var(--color-line)]"><td className="p-3 text-[var(--color-ivory)]">{label}</td><td className="p-3 font-[family-name:var(--font-mono)]">{number(earth)}</td><td className="p-3 font-[family-name:var(--font-mono)]">{number(earth / gamma)}</td><td className="p-3 font-[family-name:var(--font-mono)]">{number(gamma, 4)}</td></tr>; })}</tbody>
              </table>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="mt-16 rounded-[var(--radius-lg)] border border-[var(--color-line-strong)] bg-[var(--color-deep)] p-6 sm:p-9">
        <p className="eyebrow text-[var(--color-gold)]">Cosmic conversation</p>
        <div className="mt-8 grid grid-cols-[auto_1fr_auto_1fr_auto] items-center gap-2 text-center text-xs sm:gap-5 sm:text-sm">
          <span>Earth sends</span><motion.span className="h-px bg-[var(--color-cyan)]" initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} transition={{ duration: 1.2 }} /><span>Target receives<br/><strong>{number(values.ly)} years</strong></span><motion.span className="h-px bg-[var(--color-gold)]" initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} transition={{ duration: 1.2, delay: .3 }} /><span>Reply reaches Earth<br/><strong>{number(values.ly * 2)} years</strong></span>
        </div>
        <p className="mt-7 text-xs leading-relaxed text-[var(--color-muted)]">This is the minimum round trip, assuming an immediate reply. It says nothing about whether anyone is there, listening, able to decode the signal, or willing to answer.</p>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="panel-raised p-6"><p className="eyebrow">Flux</p><p className="mt-3 text-2xl">{number(values.fluxVs10pc, 3)}×</p><p className="mt-2 text-xs text-[var(--color-muted)]">relative to the same source at 10 pc; flux follows 1/d².</p></div>
        <div className="panel-raised p-6"><p className="eyebrow">Earth–Sun separation</p><p className="mt-3 text-2xl">{number(values.separationMicroarcsec, 3)} µas</p><p className="mt-2 text-xs text-[var(--color-muted)]">one astronomical unit projected on the sky.</p></div>
        <div className="panel-raised p-6"><p className="eyebrow">Ideal diffraction aperture</p><p className="mt-3 text-2xl">{number(values.resolveOrbitMetres, 3)} m</p><p className="mt-2 text-xs text-[var(--color-muted)]">Rayleigh separation at 550 nm, before contrast, wavefront, crowding, and photon limits.</p></div>
      </div>
    </section>
  );
}
