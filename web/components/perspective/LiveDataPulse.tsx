"use client";

import { useEffect, useState } from "react";

type LatestSummary = {
  generated_utc?: string;
  scale?: { total_source_records?: number };
  population?: { n_confirmed_planets?: number };
};

type Pulse = { status: "checking" | "current" | "newer" | "unavailable"; records: number; planets: number; generated: string };

const LATEST_SUMMARY = "https://raw.githubusercontent.com/Biswajit1999/finding-earth-2/main/web/public/data/summary.json";

export function LiveDataPulse({ records, planets, generated }: { records: number; planets: number; generated: string }) {
  const [pulse, setPulse] = useState<Pulse>({ status: "checking", records, planets, generated });

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${LATEST_SUMMARY}?opened=${Date.now()}`, { cache: "no-store", signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Latest snapshot unavailable");
        return response.json() as Promise<LatestSummary>;
      })
      .then((latest) => {
        const latestRecords = latest.scale?.total_source_records;
        const latestPlanets = latest.population?.n_confirmed_planets;
        if (!Number.isFinite(latestRecords) || !Number.isFinite(latestPlanets) || !latest.generated_utc) {
          throw new Error("Latest snapshot has an invalid schema");
        }
        const isNewer = new Date(latest.generated_utc).getTime() > new Date(generated).getTime();
        setPulse({ status: isNewer ? "newer" : "current", records: latestRecords!, planets: latestPlanets!, generated: latest.generated_utc });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setPulse({ status: "unavailable", records, planets, generated });
      });
    return () => controller.abort();
  }, [generated, planets, records]);

  const formatter = new Intl.NumberFormat("en-GB");
  const label = pulse.status === "checking" ? "Checking the latest research snapshot…"
    : pulse.status === "newer" ? "A newer processed snapshot is available"
      : pulse.status === "current" ? "This page matches the latest processed snapshot"
        : "Live check unavailable; showing the bundled verified snapshot";

  return (
    <section aria-labelledby="data-pulse-title" className="panel-raised relative overflow-hidden p-7 sm:p-9">
      <div aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-[var(--color-cyan)]" />
      <div className="grid items-end gap-8 lg:grid-cols-[1fr_auto]">
        <div>
          <p className="eyebrow text-[var(--color-cyan)]">Automatic data pulse</p>
          <h2 id="data-pulse-title" className="mt-3 text-2xl font-light text-[var(--color-ivory)]">The site checks for a fresher processed snapshot whenever this page opens</h2>
          <p className="mt-4 max-w-[70ch] text-sm leading-relaxed text-[var(--color-muted)]">
            The full archive pipeline downloads, validates, hashes and processes data in an automated workflow. Scientific changes remain review-gated before publication; this browser check can surface the newest committed result without pretending that an unchecked archive row is analysis-ready.
          </p>
          <p className="mt-4 font-[family-name:var(--font-mono)] text-xs text-[var(--color-dim)]" role="status" aria-live="polite">{label}</p>
        </div>
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-line)] bg-[var(--color-line)] text-center">
          <div className="bg-[var(--color-deep)] px-5 py-4">
            <dt className="eyebrow">Source records</dt>
            <dd className="mt-2 font-[family-name:var(--font-mono)] text-xl tabular-nums text-[var(--color-ivory)]">{formatter.format(pulse.records)}</dd>
          </div>
          <div className="bg-[var(--color-deep)] px-5 py-4">
            <dt className="eyebrow">Confirmed planets</dt>
            <dd className="mt-2 font-[family-name:var(--font-mono)] text-xl tabular-nums text-[var(--color-ivory)]">{formatter.format(pulse.planets)}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
