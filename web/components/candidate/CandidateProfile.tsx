import Link from "next/link";

import { Caveat, StatBlock } from "@/components/PageHeader";
import { HzChip, MassClassChip, StatusChip } from "@/components/Chips";
import { ScoreMeter, UncertaintyBar } from "@/components/UncertaintyBar";
import { SystemView } from "@/components/three/SystemView";
import type { DeepDive, Planet } from "@/lib/types";
import { distanceLabel, num, pct, slugify, spectralClass } from "@/lib/format";

/** Rich view when a full deep-dive JSON exists for this planet. */
export function DeepDiveProfile({ dd }: { dd: DeepDive }) {
  const pp = dd.planet_parameters;
  const hz = dd.habitable_zone;
  const esi = dd.earth_similarity;
  const host = dd.host_star;
  const ev = dd.evidence;
  const obs = dd.observability;
  const rv = dd.rv_analysis;
  const transit = dd.transit_analysis;
  const spec = dd.transmission_spectrum;

  return (
    <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
      {/* ---------------- headline stats ---------------- */}
      <div className="mb-10 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-4">
        <StatBlock
          value={num(dd.ranking.earth2_index, 3)}
          label="Earth-2.0 index"
          sub={dd.ranking.earth2_rank ? "rank #" + dd.ranking.earth2_rank : undefined}
          tone="var(--color-gold)"
        />
        <StatBlock
          value={num(esi.esi_p50, 3)}
          label="Earth Similarity Index"
          sub={
            esi.esi_p16 !== null && esi.esi_p84 !== null
              ? num(esi.esi_p16, 3) + "–" + num(esi.esi_p84, 3) + " (68% CI)"
              : undefined
          }
          tone="var(--color-cyan)"
        />
        <StatBlock
          value={pct(hz.conservative_probability)}
          label="Conservative HZ probability"
          sub={hz.model_extrapolated ? "host outside model validity range" : undefined}
          tone={hz.model_extrapolated ? "var(--color-rose)" : "var(--color-verdant)"}
        />
        <StatBlock
          value={num(pp.radius_earth.value, 2) + " R⊕"}
          label="Radius"
          sub={pp.mass_earth.class ? "mass: " + pp.mass_earth.class : undefined}
        />
      </div>

      {/* ---------------- plain-language summary ---------------- */}
      {(dd.narrative.location || dd.narrative.host_star || dd.narrative.planet) && (
        <div className="mb-10">
          <p className="eyebrow mb-2">At a glance</p>
          <p className="max-w-[70ch] text-[15px] leading-relaxed text-[var(--color-dim)]">
            {[
              dd.narrative.location,
              dd.narrative.host_star,
              dd.narrative.system,
              dd.narrative.planet,
              dd.narrative.climate,
            ]
              .filter(Boolean)
              .join(" ")}
          </p>
        </div>
      )}

      {/* ---------------- orbit and habitable-zone view ---------------- */}
      <div className="mb-10">
        <SystemView
          hostTeffK={host.teff_k}
          hostRadiusSun={host.radius_sun}
          planetRadiusEarth={pp.radius_earth.value}
          planetTeqK={pp.equilibrium_temperature_k?.value ?? null}
          semiMajorAxisAu={pp.semi_major_axis_au}
          eccentricity={pp.eccentricity}
          hzBoundariesAu={hz.boundaries_au ?? null}
        />
      </div>

      {hz.model_extrapolated && (
        <Caveat tone="warn" title="Habitable-zone model extrapolated">
          This host&rsquo;s effective temperature is{" "}
          {num(Math.abs(hz.teff_offset_from_validity_k), 0)} K outside the Kopparapu et al.
          (2013) fit&rsquo;s stated 2600–7200 K validity range. The habitable-zone
          probability above uses a temperature clamped to the boundary and is an
          extrapolation, not a supported model evaluation. Only{" "}
          {pct(hz.teff_valid_fraction_of_draws)} of Monte Carlo draws for this host
          actually fell inside the valid range.
        </Caveat>
      )}

      <div className="mt-10 grid gap-10 lg:grid-cols-3">
        {/* ---------------- left: parameters ---------------- */}
        <div className="space-y-8 lg:col-span-2">
          <Section title="Planet parameters">
            <Row label="Radius" value={num(pp.radius_earth.value, 3) + " R⊕"}
                 sub={pp.radius_earth.err_upper ? "+" + num(pp.radius_earth.err_upper, 3) + " / " + num(pp.radius_earth.err_lower, 3) : undefined} />
            <Row label="Mass" value={pp.mass_earth.value !== null ? num(pp.mass_earth.value, 3) + " M⊕" : "—"}
                 sub={pp.mass_earth.class_meaning} chip={<MassClassChip massClass={pp.mass_earth.class} />} />
            <Row label="Bulk density" value={pp.density_g_cm3.value !== null ? num(pp.density_g_cm3.value, 3) + " g/cm³" : "—"}
                 sub={pp.density_g_cm3.source ? "source: " + pp.density_g_cm3.source : undefined} />
            <Row label="Escape velocity" value={pp.escape_velocity_kms !== null ? num(pp.escape_velocity_kms, 2) + " km/s" : "—"} />
            <Row label="Orbital period" value={num(pp.orbital_period_days, 4) + " days"} />
            <Row label="Semi-major axis" value={num(pp.semi_major_axis_au, 5) + " au"} />
            <Row label="Eccentricity" value={num(pp.eccentricity, 3)} />
            <Row label="Incident flux" value={num(pp.insolation_earth.value, 3) + " S⊕"}
                 sub={"source: " + (pp.insolation_earth.source ?? "—")} />
            <Row label="Equilibrium temperature" value={num(pp.equilibrium_temperature_k.value, 1) + " K"}
                 sub={"Bond albedo assumed: " + num(pp.equilibrium_temperature_k.albedo_assumed, 3) + ". " + pp.equilibrium_temperature_k.note} />
          </Section>

          <Section title="Host star">
            <Row label="Name" value={dd.hostname} />
            <Row label="Spectral type" value={host.spectral_type ?? spectralClass(host.teff_k)} />
            <Row label="Effective temperature" value={num(host.teff_k, 0) + " K"} />
            <Row label="Radius" value={num(host.radius_sun, 3) + " R☉"} />
            <Row label="Mass" value={num(host.mass_sun, 3) + " M☉"} />
            <Row label="Luminosity" value={"10^" + num(host.luminosity_log_sun, 3) + " L☉"} />
            <Row label="Metallicity [Fe/H]" value={num(host.metallicity_dex, 3)} />
            <Row label="Age" value={host.age_gyr !== null ? num(host.age_gyr, 2) + " Gyr" : "—"} />
            <Row label="Distance" value={distanceLabel(host.distance_pc)} />
            <Row label="Multiplicity" value={host.n_stars_in_system + " star(s), " + host.n_planets_in_system + " known planet(s)"} />
          </Section>

          {dd.gaia_crossmatch && (
            <Section title="Gaia DR3 cross-check">
              <Row
                label="Parallax distance"
                value={num(dd.gaia_crossmatch.distance_pc, 2) + " pc"}
                sub={
                  dd.gaia_crossmatch.distance_disagreement_vs_archive_pct !== null
                    ? num(dd.gaia_crossmatch.distance_disagreement_vs_archive_pct, 2) +
                      "% vs. archive-adopted distance"
                    : undefined
                }
              />
              <Row
                label="RUWE"
                value={num(dd.gaia_crossmatch.ruwe, 3)}
                sub={dd.gaia_crossmatch.ruwe_note ?? undefined}
              />
              {dd.gaia_crossmatch.non_single_star_flag && (
                <Row label="Multiplicity flag" value="Gaia non_single_star" />
              )}
              {dd.gaia_crossmatch.ruwe_note && (
                <Caveat tone="warn" title="Elevated RUWE">
                  This host&rsquo;s Gaia astrometric solution has RUWE{" "}
                  {num(dd.gaia_crossmatch.ruwe, 2)}, above the conventional 1.4 threshold for a
                  well-fit single star. An unresolved binary companion, if present, could bias
                  the stellar (and hence planetary) radius this candidate&rsquo;s scores depend
                  on.
                </Caveat>
              )}
            </Section>
          )}

          <Section title="Habitable zone">
            <Row label="Boundary model" value={hz.model} />
            {hz.boundaries_seff && Object.keys(hz.boundaries_seff).length > 0 && (
              <div className="mt-2 overflow-x-auto">
                <table className="data-table min-w-[520px]">
                  <thead>
                    <tr>
                      <th scope="col">Boundary</th>
                      <th scope="col" className="text-right">S_eff (Earth units)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(hz.boundaries_seff).map(([k, v]) => (
                      <tr key={k}>
                        <td className="capitalize">{k.replace(/_/g, " ")}</td>
                        <td className="text-right font-[family-name:var(--font-mono)] tabular-nums">
                          {num(v as number, 4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <Section title="Atmospheric spectroscopy">
            {spec.available === false ? (
              <p className="text-[13px] text-[var(--color-muted)]">{spec.message}</p>
            ) : (
              <>
                <p className="text-[13px] text-[var(--color-dim)]">
                  {spec.n_points} published transmission-spectrum points across{" "}
                  {spec.wavelength_range_um?.[0].toFixed(2)}–
                  {spec.wavelength_range_um?.[1].toFixed(2)} μm from{" "}
                  {spec.facilities?.join(", ")}.
                </p>
                <Link href="/spectral-lab" className="link mt-2 inline-block text-[12.5px]">
                  Open in Spectral Lab →
                </Link>
              </>
            )}
          </Section>

          <Section title="Transit analysis">
            {transit.attempted === false ? (
              <p className="text-[13px] text-[var(--color-muted)]">{transit.reason}</p>
            ) : transit.status === "ok" ? (
              <>
                <StatusChip ok labelOk="fit validated" labelNo="fit not validated" />
                <p className="mt-2 text-[13px] text-[var(--color-dim)]">
                  Depth {num(transit.fit?.depth_ppm, 0)} ppm from a trapezoid fit to a
                  public TESS light curve.
                </p>
              </>
            ) : transit.status === "fit_not_validated" ? (
              <>
                <StatusChip ok={false} labelOk="" labelNo="fit not validated" />
                <p className="mt-2 text-[13px] text-[var(--color-dim)]">
                  {transit.catalogue_check?.interpretation}
                </p>
              </>
            ) : (
              <p className="text-[13px] text-[var(--color-muted)]">
                {transit.message ?? "No usable transit fit was produced."}
              </p>
            )}
          </Section>

          <Section title="Radial-velocity analysis">
            {rv.attempted === false ? (
              <p className="text-[13px] text-[var(--color-muted)]">{rv.reason}</p>
            ) : rv.status === "ok" ? (
              <>
                <Row label="Measurements" value={String(rv.dataset?.n_measurements_used)}
                     sub={"baseline " + num(rv.dataset?.baseline_years, 1) + " yr across " + Object.keys(rv.dataset?.instruments ?? {}).length + " instrument(s)"} />
                <Row label="Activity coincidences" value={String(rv.n_activity_coincidences)}
                     sub="RV periodogram peaks matching a stellar-activity indicator period" />
                {rv.keplerian_fit?.ok && (
                  <Row
                    label="Fitted semi-amplitude"
                    value={num(rv.keplerian_fit.semi_amplitude_ms, 2) + " ± " + num(rv.keplerian_fit.semi_amplitude_err_ms, 2) + " m/s"}
                    sub={rv.keplerian_fit.reliable
                      ? (rv.keplerian_fit.msini_earth !== null ? "M sin i = " + num(rv.keplerian_fit.msini_earth, 2) + " M⊕" : undefined)
                      : "NOT RELIABLE: " + (rv.keplerian_fit.unreliable_because ?? []).join("; ")}
                  />
                )}
              </>
            ) : (
              <p className="text-[13px] text-[var(--color-muted)]">{rv.message}</p>
            )}
          </Section>

          {dd.measurement_provenance && dd.measurement_provenance.length > 0 && (
            <Section title="Measurement provenance">
              <div className="overflow-x-auto">
                <table className="data-table min-w-[560px]">
                  <thead>
                    <tr>
                      <th scope="col">Parameter</th>
                      <th scope="col">Value</th>
                      <th scope="col">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dd.measurement_provenance.map((p, i) => (
                      <tr key={i}>
                        <td>{p.parameter_label}</td>
                        <td className="font-[family-name:var(--font-mono)] tabular-nums">
                          {p.value !== null ? num(p.value, 4) : "—"}
                        </td>
                        <td>
                          {p.source_kind === "archive_calculated" ? (
                            <span className="text-[var(--color-rose)]">
                              archive-calculated (not a publication)
                            </span>
                          ) : p.reference_url ? (
                            <a href={p.reference_url} target="_blank" rel="noreferrer" className="link">
                              {p.reference_label}
                            </a>
                          ) : (
                            p.reference_label ?? "—"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          )}
        </div>

        {/* ---------------- right: sidebar ---------------- */}
        <div className="space-y-6">
          <div className="panel p-5">
            <p className="eyebrow mb-3">Component scores</p>
            <div className="space-y-3">
              <ScoreRow label="Earth similarity" value={dd.ranking.scores.earth_similarity ?? null} tone="var(--color-cyan)" />
              <ScoreRow label="Conservative habitability" value={dd.ranking.scores.conservative_habitability ?? null} tone="var(--color-verdant)" />
              <ScoreRow label="Observational confidence" value={dd.ranking.scores.observational_confidence ?? null} tone="var(--color-sci)" />
              <ScoreRow label="Characterisation potential" value={dd.ranking.scores.characterisation_potential ?? null} tone="var(--color-violet)" />
            </div>
          </div>

          <div className="panel p-5">
            <p className="eyebrow mb-3">Evidence</p>
            <dl className="space-y-2 text-[12.5px]">
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">Independent references</dt>
                <dd className="font-[family-name:var(--font-mono)] tabular-nums">{ev.n_independent_references ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">Published parameter sets</dt>
                <dd className="font-[family-name:var(--font-mono)] tabular-nums">{ev.n_published_parameter_sets ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">Uncertainty coverage</dt>
                <dd className="font-[family-name:var(--font-mono)] tabular-nums">{pct(ev.uncertainty_coverage)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">Discovery method</dt>
                <dd>{ev.discovery_method}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">Discovery year</dt>
                <dd className="font-[family-name:var(--font-mono)]">{ev.discovery_year}</dd>
              </div>
              {ev.controversial_flag && (
                <p className="mt-2 text-[11.5px] text-[var(--color-rose)]">
                  Flagged as controversial by the archive.
                </p>
              )}
            </dl>
          </div>

          <div className="panel p-5">
            <p className="eyebrow mb-3">Observability</p>
            <dl className="space-y-2 text-[12.5px]">
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">TSM</dt>
                <dd className="font-[family-name:var(--font-mono)] tabular-nums">
                  {obs.tsm !== null ? num(obs.tsm, 2) : "n/a (non-transiting)"}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-[var(--color-muted)]">RV semi-amplitude (expected)</dt>
                <dd className="font-[family-name:var(--font-mono)] tabular-nums">
                  {obs.rv_semi_amplitude_ms !== null ? num(obs.rv_semi_amplitude_ms, 3) + " m/s" : "—"}
                </dd>
              </div>
            </dl>
          </div>

          {dd.identifiers && Object.keys(dd.identifiers).length > 0 && (
            <div className="panel p-5">
              <p className="eyebrow mb-3">Identifiers</p>
              <dl className="space-y-1.5 font-[family-name:var(--font-mono)] text-[11.5px]">
                {Object.entries(dd.identifiers).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <dt className="text-[var(--color-muted)]">{k}</dt>
                    <dd className="text-[var(--color-dim)]">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {dd.system.siblings.length > 0 && (
            <div className="panel p-5">
              <p className="eyebrow mb-3">Other planets in this system</p>
              <ul className="space-y-2">
                {dd.system.siblings.map((s) => (
                  <li key={s.pl_name}>
                    <Link
                      href={"/candidate/" + slugify(s.pl_name)}
                      className="text-[12.5px] text-[var(--color-dim)] hover:text-[var(--color-cyan)]"
                    >
                      {s.pl_name}
                    </Link>
                    <span className="ml-1.5 font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-muted)]">
                      {s.pl_orbper !== null ? num(s.pl_orbper, 2) + " d" : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Link
            href={"/compare?p=" + encodeURIComponent(dd.planet)}
            className="block cursor-pointer rounded-[var(--radius-md)] border border-[var(--color-line-strong)] px-4 py-2.5 text-center text-[12.5px] text-[var(--color-ivory)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
          >
            Add to comparison →
          </Link>
        </div>
      </div>

      <p className="mt-10 border-t border-[var(--color-line)] pt-4 text-[11px] leading-relaxed text-[var(--color-faint)]">
        {dd.visualisation_disclaimer}
      </p>
    </div>
  );
}

/** Basic fallback view built directly from the catalogue for planets without a deep-dive JSON. */
export function BasicProfile({ p }: { p: Planet }) {
  return (
    <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
      <Caveat tone="info" title="Standard profile">
        This planet is outside the top-ranked systems selected for a full
        deep-dive analysis (transit and radial-velocity retrieval). The
        parameters below are the complete pipeline output for this planet from
        the analysed catalogue.
      </Caveat>

      <div className="mt-8 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-4">
        <StatBlock value={num(p.index_value, 3)} label="Earth-2.0 index" tone="var(--color-gold)" />
        <StatBlock value={num(p.esi, 3)} label="Earth Similarity Index" tone="var(--color-cyan)" />
        <StatBlock value={pct(p.hzProb)} label="Habitable-zone probability" tone="var(--color-verdant)" />
        <StatBlock value={num(p.rade, 2) + " R⊕"} label="Radius" />
      </div>

      <div className="mt-10 grid gap-8 lg:grid-cols-2">
        <div className="panel p-5">
          <p className="eyebrow mb-3">Planet</p>
          <Row label="Mass" value={p.mass !== null ? num(p.mass, 3) + " M⊕" : "—"} chip={<MassClassChip massClass={p.massClass} />} />
          <Row label="Bulk density" value={p.density !== null ? num(p.density, 3) + " g/cm³" : "—"} />
          <Row label="Orbital period" value={num(p.period, 4) + " days"} />
          <Row label="Semi-major axis" value={num(p.smax, 5) + " au"} />
          <Row label="Eccentricity" value={num(p.ecc, 3)} />
          <Row label="Incident flux" value={num(p.insol, 3) + " S⊕"} />
          <Row label="Equilibrium temperature" value={num(p.teq, 1) + " K"} />
        </div>
        <div className="panel p-5">
          <p className="eyebrow mb-3">Host star &amp; system</p>
          <Row label="Host" value={p.host} />
          <Row label="Spectral type" value={p.spectype ?? spectralClass(p.teff)} />
          <Row label="Effective temperature" value={num(p.teff, 0) + " K"} />
          <Row label="Radius" value={num(p.srad, 3) + " R☉"} />
          <Row label="Mass" value={num(p.smass, 3) + " M☉"} />
          <Row label="Distance" value={distanceLabel(p.dist)} />
          <Row label="Discovery" value={(p.method ?? "—") + (p.discYear ? ", " + p.discYear : "")} />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          href={"/compare?p=" + encodeURIComponent(p.name)}
          className="cursor-pointer rounded-[var(--radius-md)] border border-[var(--color-line-strong)] px-4 py-2.5 text-[12.5px] text-[var(--color-ivory)] transition-colors hover:border-[var(--color-cyan)] hover:text-[var(--color-cyan)]"
        >
          Add to comparison →
        </Link>
        <Link href="/atlas" className="link px-2 py-2.5 text-[12.5px]">
          Back to the Candidate Atlas →
        </Link>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="rule-label mb-3">
        <span className="eyebrow">{title}</span>
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Row({
  label,
  value,
  sub,
  chip,
}: {
  label: string;
  value: string;
  sub?: string;
  chip?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-[var(--color-line)]/60 py-2">
      <span className="text-[12.5px] text-[var(--color-dim)]">{label}</span>
      <span className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-mono)] text-[12.5px] tabular-nums text-[var(--color-ivory)]">
          {value}
        </span>
        {chip}
      </span>
      {sub && <span className="w-full text-[11px] leading-snug text-[var(--color-muted)]">{sub}</span>}
    </div>
  );
}

function ScoreRow({ label, value, tone }: { label: string; value: number | null; tone: string }) {
  return (
    <div>
      <p className="mb-1 text-[12px] text-[var(--color-dim)]">{label}</p>
      <ScoreMeter value={value} tone={tone} width={160} label={label} />
    </div>
  );
}
