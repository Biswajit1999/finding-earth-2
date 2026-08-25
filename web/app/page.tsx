import Link from "next/link";

import { Hero } from "@/components/Hero";
import { MassClassChip, HzChip } from "@/components/Chips";
import { ScoreMeter, UncertaintyBar } from "@/components/UncertaintyBar";
import { getSummary, getTopCandidates, getUniverse, getCoverage } from "@/lib/data";
import { compactInt, distanceLabel, num, pct, slugify } from "@/lib/format";

export default function HomePage() {
  const summary = getSummary();
  const universe = getUniverse();
  const top = getTopCandidates(8);
  const coverage = getCoverage();

  const cov = summary.measurement_coverage as Record<string, number>;
  const nPlanets = summary.population.n_confirmed_planets;
  const prov = summary.measurement_provenance;

  return (
    <>
      <Hero summary={summary} universe={universe} />

      {/* ================= what this asks ================= */}
      <section className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="rule-label mb-8">
          <span className="eyebrow">The question</span>
        </div>

        <div className="grid gap-12 lg:grid-cols-[1.15fr_1fr]">
          <div>
            <h2 className="text-[length:var(--text-display)] font-light leading-[1.05]">
              Five things that get conflated, kept apart
            </h2>
            <p className="mt-6 max-w-[58ch] text-[15px] leading-relaxed text-[var(--color-dim)]">
              Headlines collapse &ldquo;Earth-sized&rdquo;,
              &ldquo;habitable-zone&rdquo;, &ldquo;potentially habitable&rdquo; and
              &ldquo;could host life&rdquo; into one claim. They are different
              claims, supported by different evidence, and this project reports
              them separately at every stage.
            </p>
          </div>

          <dl className="space-y-0 self-end">
            {[
              [
                "Earth similarity",
                "Bulk radius, density, escape velocity and equilibrium temperature resemble Earth's.",
              ],
              [
                "Habitable-zone position",
                "Incident flux is compatible with surface liquid water under a stated climate model.",
              ],
              [
                "Rocky plausibility",
                "Radius sits below the regime where planets are predominantly volatile-rich.",
              ],
              [
                "Atmospheric observability",
                "Whether an atmosphere could be characterised with current instruments.",
              ],
              [
                "Evidence for life",
                "Not established for any planet. No metric here estimates it.",
              ],
            ].map(([term, def], i, arr) => (
              <div
                key={term}
                className={`flex gap-5 py-3.5 ${
                  i < arr.length - 1 ? "border-b border-[var(--color-line)]" : ""
                }`}
              >
                <dt
                  className={`w-[11.5rem] shrink-0 text-[13px] font-medium ${
                    i === arr.length - 1
                      ? "text-[var(--color-rose)]"
                      : "text-[var(--color-ivory)]"
                  }`}
                >
                  {term}
                </dt>
                <dd className="text-[13px] leading-relaxed text-[var(--color-muted)]">
                  {def}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ================= top candidates ================= */}
      <section className="border-y border-[var(--color-line)] bg-[var(--color-deep)]">
        <div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
          <div className="rule-label mb-3">
            <span className="eyebrow">Computed ranking</span>
          </div>
          <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
            <h2 className="text-[length:var(--text-display)] font-light">
              Leading candidates
            </h2>
            <p className="max-w-[46ch] text-[13px] leading-relaxed text-[var(--color-muted)]">
              Produced by the pipeline, not selected by hand. The intervals are
              16th–84th percentiles from{" "}
              {compactInt(summary.monte_carlo.n_samples)} Monte Carlo draws per
              planet.
            </p>
          </div>

          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="data-table min-w-[860px]">
              <caption className="sr-only">
                Top eight Earth-2.0 candidates with component scores, Earth
                Similarity Index posteriors, mass provenance and distance
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="w-10">#</th>
                  <th scope="col">Planet</th>
                  <th scope="col">Earth-2.0 index</th>
                  <th scope="col">Earth Similarity Index</th>
                  <th scope="col">Habitable zone</th>
                  <th scope="col">Mass</th>
                  <th scope="col" className="text-right">Radius</th>
                  <th scope="col" className="text-right">Distance</th>
                </tr>
              </thead>
              <tbody>
                {top.map((p) => (
                  <tr key={p.name}>
                    <td className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
                      {p.rank ?? "—"}
                    </td>
                    <td>
                      <Link
                        href={`/candidate/${slugify(p.name)}`}
                        className="font-medium text-[var(--color-ivory)] transition-colors hover:text-[var(--color-cyan)]"
                      >
                        {p.name}
                      </Link>
                      <span className="ml-2 text-[11px] text-[var(--color-muted)]">
                        {p.spectype ?? ""}
                      </span>
                    </td>
                    <td>
                      <ScoreMeter
                        value={p.index_value}
                        tone="var(--color-gold)"
                        label={`${p.name} Earth-2.0 index`}
                      />
                    </td>
                    <td>
                      <UncertaintyBar
                        lo={p.esiLo}
                        mid={p.esi}
                        hi={p.esiHi}
                        min={0.7}
                        max={1}
                        width={104}
                        tone="var(--color-cyan)"
                        label={`${p.name} Earth Similarity Index`}
                      />
                    </td>
                    <td>
                      <HzChip prob={p.hzProb} extrapolated={p.hzExtrapolated} />
                    </td>
                    <td>
                      <MassClassChip massClass={p.massClass} />
                    </td>
                    <td className="text-right font-[family-name:var(--font-mono)] text-[12px] tabular-nums">
                      {num(p.rade, 2)} R⊕
                    </td>
                    <td className="text-right font-[family-name:var(--font-mono)] text-[11px] tabular-nums text-[var(--color-dim)]">
                      {distanceLabel(p.dist)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link href="/atlas" className="link text-[13px]">
              All {compactInt(nPlanets)} analysed planets →
            </Link>
            <Link href="/ranking" className="link text-[13px]">
              Change the weighting yourself →
            </Link>
          </div>
        </div>
      </section>

      {/* ================= the evidence problem ================= */}
      <section className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="rule-label mb-8">
          <span className="eyebrow">Why the ranking looks like this</span>
        </div>

        <div className="grid gap-10 lg:grid-cols-3">
          <article className="panel p-6">
            <p className="font-[family-name:var(--font-mono)] text-[2rem] leading-none text-[var(--color-rose)]">
              {pct(cov.n_with_mass_inferred_from_radius / nPlanets, 0)}
            </p>
            <h3 className="mt-3 text-[15px] font-semibold text-[var(--color-ivory)]">
              of catalogue masses were never measured
            </h3>
            <p className="mt-2 text-[13px] leading-relaxed text-[var(--color-muted)]">
              {compactInt(cov.n_with_mass_inferred_from_radius)} planets carry a
              mass predicted from their radius by a mass–radius relation. Density
              and escape velocity computed from such a mass re-encode the radius
              rather than adding information, so the Earth Similarity Index would
              appear to combine four independent properties while being driven by
              one.
            </p>
          </article>

          <article className="panel p-6">
            <p className="font-[family-name:var(--font-mono)] text-[2rem] leading-none text-[var(--color-gold)]">
              0.92
            </p>
            <h3 className="mt-3 text-[15px] font-semibold text-[var(--color-ivory)]">
              Venus scores 0.92 on the Earth Similarity Index
            </h3>
            <p className="mt-2 text-[13px] leading-relaxed text-[var(--color-muted)]">
              Venus&rsquo;s high albedo makes its equilibrium temperature{" "}
              <em>cooler</em> than Earth&rsquo;s, and equilibrium temperature is
              the only temperature exoplanet catalogues provide. An ESI built on
              data that exists for real exoplanets cannot separate an Earth from a
              Venus. Venus runs through the whole pipeline as a control so this is
              visible rather than asserted.
            </p>
          </article>

          <article className="panel p-6">
            <p className="font-[family-name:var(--font-mono)] text-[2rem] leading-none text-[var(--color-cyan)]">
              ~1 ppm
            </p>
            <h3 className="mt-3 text-[15px] font-semibold text-[var(--color-ivory)]">
              is an Earth twin&rsquo;s atmospheric signal
            </h3>
            <p className="mt-2 text-[13px] leading-relaxed text-[var(--color-muted)]">
              For a real nitrogen–oxygen atmosphere around a Sun-like star, the
              transmission signal is about one part per million — against a
              current best precision of tens of ppm. Finding an Earth twin and
              characterising its atmosphere are separated by a generation of
              instruments.
            </p>
          </article>
        </div>

        {/* provenance strip */}
        {prov && (
          <div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-[var(--color-line)] pt-6">
            <p className="text-[13px] text-[var(--color-dim)]">
              Every number on this site traces back to a source.
            </p>
            <p className="font-[family-name:var(--font-mono)] text-[12px] tabular-nums text-[var(--color-muted)]">
              {compactInt(prov.n_links)} measurement links ·{" "}
              {compactInt(prov.n_distinct_publications)} publications ·{" "}
              {compactInt(prov.n_with_ads_bibcode)} with ADS bibcodes ·{" "}
              {compactInt(prov.by_kind?.archive_calculated ?? 0)} values calculated
              by the archive rather than measured
            </p>
            <Link href="/data" className="link text-[13px]">
              Data provenance →
            </Link>
          </div>
        )}
      </section>

      {/* ================= laboratories ================= */}
      <section className="border-t border-[var(--color-line)] bg-[var(--color-deep)]">
        <div className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
          <div className="rule-label mb-8">
            <span className="eyebrow">Inspect the observations</span>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                href: "/spectral-lab",
                title: "Spectral Lab",
                stat: `${summary.atmosphere["planets_with_transmission_spectra"]} planets`,
                body: "Published transmission and emission spectra with expected molecular band positions — marked as band positions, never as detections.",
              },
              {
                href: "/transit-lab",
                title: "Transit Lab",
                stat: "4 of 4 validated",
                body: "Light curves retrieved from MAST, detrended, folded and fitted, with every fit checked against the published depth before it is reported.",
              },
              {
                href: "/rv-lab",
                title: "RV Lab",
                stat: "Proxima recovered",
                body: "Radial velocities from DACE with a mandatory stellar-activity cross-check, because a rotating spotted star imitates a planet.",
              },
            ].map((c) => (
              <Link
                key={c.href}
                href={c.href}
                className="group panel flex flex-col p-6 transition-colors hover:border-[var(--color-cyan)]"
              >
                <p className="eyebrow text-[var(--color-cyan)]">{c.stat}</p>
                <h3 className="mt-2.5 font-[family-name:var(--font-display)] text-xl font-medium">
                  {c.title}
                </h3>
                <p className="mt-2.5 flex-1 text-[13px] leading-relaxed text-[var(--color-muted)]">
                  {c.body}
                </p>
                <p className="mt-5 text-[12px] text-[var(--color-dim)] transition-colors group-hover:text-[var(--color-cyan)]">
                  Open →
                </p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ================= coverage ================= */}
      <section className="mx-auto max-w-[1400px] px-4 py-20 sm:px-6">
        <div className="rule-label mb-8">
          <span className="eyebrow">Data coverage</span>
        </div>
        <div className="grid gap-10 lg:grid-cols-[1fr_1.3fr]">
          <div>
            <h2 className="text-[length:var(--text-title)] font-light">
              What looks measured, and what is actually quantified
            </h2>
            <p className="mt-5 max-w-[52ch] text-[14px] leading-relaxed text-[var(--color-dim)]">
              The pale bar is how many planets have a value at all. The solid bar
              is how many have that value{" "}
              <strong className="text-[var(--color-ivory)]">
                with a published uncertainty
              </strong>
              . The gap between them is the part of the catalogue that looks
              measured but cannot be propagated — and it is large.
            </p>
            <Link href="/limitations" className="link mt-5 inline-block text-[13px]">
              What this analysis cannot establish →
            </Link>
          </div>

          <ul className="space-y-2.5">
            {coverage
              .slice()
              .sort((a, b) => b.pct_with_value - a.pct_with_value)
              .slice(0, 10)
              .map((c) => (
                <li key={c.column} className="flex items-center gap-4">
                  <span className="w-[13.5rem] shrink-0 text-[12px] text-[var(--color-dim)]">
                    {c.quantity}
                  </span>
                  <span className="relative h-3 flex-1 overflow-hidden rounded-[2px] bg-[var(--color-panel)]">
                    <span
                      className="absolute inset-y-0 left-0 bg-[var(--color-line-strong)]"
                      style={{ width: `${c.pct_with_value}%` }}
                    />
                    {c.pct_with_uncertainty !== null && (
                      <span
                        className="absolute inset-y-[3px] left-0 bg-[var(--color-sci)]"
                        style={{ width: `${c.pct_with_uncertainty}%` }}
                      />
                    )}
                  </span>
                  <span className="w-24 shrink-0 text-right font-[family-name:var(--font-mono)] text-[11px] tabular-nums text-[var(--color-muted)]">
                    {c.pct_with_value.toFixed(0)}%
                    {c.pct_with_uncertainty !== null && (
                      <span className="text-[var(--color-sci)]">
                        {" "}
                        / {c.pct_with_uncertainty.toFixed(0)}%
                      </span>
                    )}
                  </span>
                </li>
              ))}
          </ul>
        </div>
      </section>
    </>
  );
}
