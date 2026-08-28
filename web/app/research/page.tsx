import type { Metadata } from "next";
import Link from "next/link";

import { getSummary } from "@/lib/data";
import { compactInt, num, pct } from "@/lib/format";
import { ArticleFigure } from "@/components/ArticleFigure";
import { SideNote } from "@/components/SideNote";

export const metadata: Metadata = {
  title: "Research Article",
  description:
    "The full long-form research article: methods, results, limitations and conclusions of the Earth-2.0 search.",
};

const researchSections = [
  { href: "#abstract", label: "Overview", detail: "01–03" },
  { href: "#datasets", label: "Evidence base", detail: "04–07" },
  { href: "#hz-model", label: "Physical models", detail: "08–10" },
  { href: "#transit", label: "Observations", detail: "11–14" },
  { href: "#ranking", label: "Ranking", detail: "15–17" },
  { href: "#biases", label: "Interpretation", detail: "18–22" },
] as const;

export default function ResearchPage() {
  const s = getSummary();
  const hz = s.habitable_zone;
  const cov = s.measurement_coverage as Record<string, number>;
  const prov = s.measurement_provenance;
  const shortFacilityName = (name: string) =>
    name.match(/\(([^)]+)\)/)?.[1] ?? name.split(" ").slice(0, 3).join(" ");
  const mcPlanets = s.monte_carlo.n_planets ?? s.population.n_confirmed_planets;
  const topFacilities = Object.entries(
    s.atmosphere.transmission_facilities as Record<string, number>,
  ).sort((a, b) => b[1] - a[1]);
  const nPlanets = s.population.n_confirmed_planets;

  return (
    <article className="research-page mx-auto max-w-[1480px] px-4 py-12 sm:px-6">
      <header className="research-masthead mx-auto max-w-[var(--measure)] border-b border-[var(--color-line)] pb-10">
        <p className="eyebrow">Research article</p>
        <h1 className="mt-4 text-[length:var(--text-display)] font-light leading-[1.05]">
          Finding Earth 2.0 in Distant Worlds
        </h1>
        <p className="mt-5 text-[15px] leading-relaxed text-[var(--color-dim)]">
          A reproducible, data-driven search for potentially Earth-like worlds
          across the public astronomical archives.
        </p>
        <p className="mt-4 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
          Author: Biswajit Jana · Generated{" "}
          {new Date(s.generated_utc).toISOString().slice(0, 10)} from the analysis
          pipeline (earth2 v{s.earth2_version})
        </p>
      </header>

      <div className="research-layout mt-10">
        <nav className="research-toc" aria-label="Research article sections">
          <p className="eyebrow">On this page</p>
          <ol className="mt-4">
            {researchSections.map((section) => (
              <li key={section.href}>
                <a href={section.href}>
                  <span>{section.label}</span>
                  <span aria-hidden="true">{section.detail}</span>
                </a>
              </li>
            ))}
          </ol>
          <Link className="research-rail-link" href="/methods">
            Methods &amp; equations <span aria-hidden="true">↗</span>
          </Link>
        </nav>

        <div className="prose-sci research-body">
        <h2 id="abstract">1. Abstract</h2>
        <p>
          Among the {compactInt(nPlanets)} planets confirmed by the NASA Exoplanet
          Archive as of this analysis, we ask a narrowly scoped question: which
          known planets most closely satisfy physically motivated conditions
          associated with an Earth-like, potentially habitable world, how strong
          is the observational evidence behind each, and where does that evidence
          run out? We ingest {compactInt(s.scale.total_source_records)}{" "}
          provenance-tracked records from {s.scale.n_datasets_retrieved} NASA
          Exoplanet Archive tables, cross-reference public radial-velocity
          holdings from DACE and light curves from MAST, propagate every
          published measurement uncertainty through {compactInt(
            s.monte_carlo.n_samples,
          )}{" "}
          Monte Carlo draws per planet, and rank candidates on four independent,
          interpretable axes. The central finding is a scarcity result: only{" "}
          {hz["n_conservative_hz_and_below_1p6_re"]} planets are simultaneously
          inside the conservative habitable zone and small enough to be plausibly
          rocky, and only{" "}
          {hz["n_conservative_hz_and_below_1p6_re_with_measured_mass"]} of those
          has an actually measured mass. We do not claim evidence of life,
          habitability, or a confirmed second Earth for any object in this
          catalogue.
        </p>

        <h2 id="the-search">2. The search for another Earth</h2>
        <p>
          The public framing of exoplanet discovery habitually collapses several
          distinct claims into one headline: &ldquo;Earth-sized&rdquo;,
          &ldquo;in the habitable zone&rdquo;, &ldquo;potentially
          habitable&rdquo;, and occasionally &ldquo;could host life&rdquo;. These
          are not synonyms. A planet can be Earth-sized and molten. A planet can
          sit in the habitable zone and be a mini-Neptune with no solid surface
          at all. This project treats the conflation itself as a problem worth
          engineering around: every metric it computes answers one and only one
          of these questions, and every result surfaces which question it is
          answering.
        </p>

        <h2 id="what-earth-like-means">3. What does &ldquo;Earth-like&rdquo; actually mean?</h2>
        <p>
          We decompose &ldquo;Earth-like&rdquo; into five components that are
          measured, or fail to be measured, independently:{" "}
          <strong>Earth similarity</strong> (bulk radius, density, escape
          velocity, and equilibrium temperature resemble Earth&rsquo;s);{" "}
          <strong>habitable-zone position</strong> (incident stellar flux is
          compatible with surface liquid water under a stated climate model);{" "}
          <strong>rocky plausibility</strong> (radius sits below the regime where
          planets are predominantly volatile-rich); <strong>atmospheric
          observability</strong> (whether a real atmospheric measurement is
          feasible with current instruments); and <strong>evidence for
          life</strong>, which this project does not attempt to quantify for any
          planet. Conflating the first four with the fifth is, in our view, the
          single most common error in public communication about exoplanets.
        </p>

        <h2 id="datasets">4. Public datasets</h2>
        <p>
          The analysis spine is the NASA Exoplanet Archive&rsquo;s{" "}
          <code>pscomppars</code> table (one row per confirmed planet, columns
          drawn from the best available publication per parameter) cross-checked
          against <code>ps</code> (one row per published parameter set, used to
          count independent references and measure inter-publication
          disagreement). Atmospheric measurements come from the archive&rsquo;s{" "}
          <code>transitspec</code> and <code>emissionspec</code> tables:{" "}
          {compactInt(Number(s.atmosphere["transmission_measurement_rows"]))}{" "}
          genuine transmission-spectroscopy measurements across{" "}
          {String(s.atmosphere["planets_with_transmission_spectra"])} planets. Transit
          photometry is retrieved live from MAST via <code>lightkurve</code>.
          Radial velocities are retrieved live from the public holdings of the
          Data &amp; Analysis Center for Exoplanets (DACE), University of Geneva.
          Full per-dataset provenance — the literal query, retrieval timestamp,
          and a SHA-256 of the payload as received — is in{" "}
          <Link href="/data" className="link">
            Data sources
          </Link>
          . Host-star distances are additionally cross-checked against Gaia
          DR3 by exact <code>source_id</code> — never coordinate matching,
          which risks silently pairing the wrong star in crowded fields — for
          every host the archive itself links to a Gaia identifier.
        </p>

        <ArticleFigure
          src="/figures/data_coverage.png"
          width={1644}
          height={1018}
          alt="Horizontal bars comparing the number of catalogue planets with a value against the number with a published uncertainty for each physical quantity"
          caption={
            <>
              Measurement coverage across the confirmed-planet catalogue.
              Dark bars count planets with a reported value; bright overlays
              show the subset that also has a published uncertainty. The gap
              is scientifically consequential: a value without an error bar
              cannot contribute honest width to a propagated posterior.
            </>
          }
        />

        <SideNote eyebrow="Independent distance check" side="right">
          {compactInt(s.gaia_crossmatch.n_hosts_matched)} host stars matched
          to Gaia DR3 by exact source_id. Archive distance vs. Gaia parallax
          agree to a median of {num(s.gaia_crossmatch.median_distance_disagreement_pct, 2)}%.
        </SideNote>

        <ArticleFigure
          src="/figures/gaia_parallax_check.png"
          width={1252}
          height={1052}
          alt="Scatter plot comparing NASA Exoplanet Archive distances against Gaia DR3 parallax-derived distances for 4,408 host stars"
          caption={
            <>
              Independent distance cross-check for the{" "}
              {compactInt(s.gaia_crossmatch.n_hosts_matched)} confirmed-planet
              host stars matched to Gaia DR3 by exact <code>source_id</code>:
              the archive&rsquo;s adopted distance against 1000/parallax
              computed directly from this project&rsquo;s own Gaia crossmatch.
              Points are coloured by Gaia&rsquo;s RUWE statistic; outlined
              points exceed RUWE &gt; 1.4, the conventional threshold for a
              poorly-fit or unresolved-binary astrometric solution. The two
              distances agree to a median of{" "}
              {num(s.gaia_crossmatch.median_distance_disagreement_pct, 2)}%
              across all matched hosts.
            </>
          }
        />

        <h2 id="architecture">5. Data architecture</h2>
        <p>
          The pipeline is a five-stage, deterministic Python package: ingestion
          (with per-retrieval manifests), catalogue construction (mass-provenance
          classification, self-consistent flux and temperature derivation),
          uncertainty propagation (Monte Carlo), ranking (four interpretable
          scores combined by a non-compensatory geometric mean), and reporting
          (figures, deep dives, and the JSON this website consumes). Every
          transformation is appended to a transformation ledger alongside its
          equation, its citation, and its input/output row counts, so any number
          on this page can be traced back to the archive row that produced it.
        </p>

        <h2 id="sample">6. Sample construction</h2>
        <p>
          The confirmed-planet sample ({compactInt(nPlanets)} planets across{" "}
          {compactInt(s.population.n_unique_host_systems)} host systems) is the
          archive&rsquo;s full <code>pscomppars</code> table, unfiltered by
          detection method or discovery year. We additionally ingest TESS
          Objects of Interest, Kepler Objects of Interest, K2 candidates, and
          Kepler Threshold Crossing Events as separate, explicitly labelled
          candidate populations — never merged into the confirmed count, and in
          the case of TCEs, the large majority of which are not planets at all,
          used only to characterise detection sensitivity.
        </p>

        <ArticleFigure
          src="/figures/discovery_timeline.png"
          width={1942}
          height={797}
          alt="Timeline of confirmed exoplanet discoveries by year and discovery method"
          caption={
            <>
              Confirmed-planet discoveries by year and method. The abrupt
              changes trace survey launches and observing strategies, not
              sudden changes in the Galaxy&rsquo;s planet population. This is why
              the full archive is retained while selection effects are kept
              visible.
            </>
          }
        />

        <SideNote eyebrow="Detection is a distance problem" side="left">
          The top-ranked candidates cluster within a few to a few tens of
          parsecs of the Sun — a temperate Earth-sized planet is currently
          detectable at all only around the nearest, quietest stars.
        </SideNote>

        <ArticleFigure
          src="/figures/distance_distribution.png"
          width={1315}
          height={791}
          alt="Histogram of distance for the analysed catalogue, with the top eight computed candidates marked by vertical lines"
          caption={
            <>
              Distance distribution of the analysed catalogue. Vertical lines
              mark the distances of the top eight computed candidates;
              sibling planets in the same system are merged into a single
              labelled line.
            </>
          }
        />

        <h2 id="crossmatch">7. Crossmatching</h2>
        <p>
          Planets carry multiple survey identifiers — a TRAPPIST-1 planet is also
          a K2, EPIC, TIC, TOI, and Gaia DR3 object. We resolve these through the
          archive&rsquo;s own alias-lookup service rather than string matching:
          &ldquo;Kepler-442 b&rdquo; and &ldquo;Kepler-44 b&rdquo; differ by one
          character and are different planets in different systems, so edit
          distance is never treated as evidence of identity. Every crossmatch
          records its method and confidence.
        </p>

        <ArticleFigure
          src="/figures/hr_diagram.png"
          width={1355}
          height={891}
          alt="Hertzsprung-Russell diagram of exoplanet host stars with conservative habitable-zone hosts highlighted and the model temperature range shaded"
          caption={
            <>
              Hertzsprung–Russell diagram of the host-star sample. Hosts of
              conservative-zone planets are highlighted; the shaded region
              marks the 2600–7200 K calibration range of the habitable-zone
              model. Stellar context is part of the inference, not background
              decoration.
            </>
          }
        />

        <h2 id="hz-model">8. Habitable-zone model</h2>
        <p>
          Habitable-zone boundaries follow Kopparapu et al. (2013), using the{" "}
          <em>erratum</em> coefficients (ApJ 770, 82) rather than the original
          Table 3, which the arXiv preprint still carries and which shifts the
          inner conservative boundary by over a percent in flux. We expose two
          zone definitions separately — conservative (runaway greenhouse to
          maximum greenhouse) and optimistic (recent Venus to early Mars) —
          because the disagreement between them is a genuine methodological
          uncertainty, not noise to be averaged away. Outside the fit&rsquo;s
          stated 2600–7200 K validity range we return an explicit &ldquo;model
          extrapolated&rdquo; flag rather than silently clamping: TRAPPIST-1, at
          2566 K, sits 34 K below the floor, and its habitable-zone status is
          reported both ways.
        </p>

        <SideNote eyebrow="Methodological citation" side="right">
          Kopparapu et al. (2013, ApJ 765, 131; 2013 erratum, ApJ 770, 82).
          Full bibliography on the{" "}
          <Link href="/references" className="link">
            References
          </Link>{" "}
          page.
        </SideNote>

        <ArticleFigure
          src="/figures/hz_diagram.png"
          width={1331}
          height={894}
          alt="Habitable-zone boundaries as a function of host effective temperature, with every confirmed planet placed by incident flux and temperature"
          caption={
            <>
              Habitable-zone boundaries after Kopparapu et al. (2013, erratum
              coefficients) as a function of host effective temperature.
              Shaded regions mark the conservative and optimistic zones;
              points are confirmed planets with radius &lt;2 R⊕, coloured by
              computed Earth-2.0 index. Solar System bodies are marked as
              reference points.
            </>
          }
        />

        <ArticleFigure
          src="/figures/flux_radius_hz.png"
          width={1256}
          height={891}
          alt="Incident stellar flux against planet radius with conservative habitable-zone candidates coloured by Earth-2.0 index"
          caption={
            <>
              Incident stellar flux against radius. Conservative-zone planets
              are coloured by computed Earth-2.0 index; the rest of the archive
              remains visible in grey. The shaded band is the conservative zone
              for a Sun-like host, a reference slice rather than a universal
              boundary for every stellar temperature.
            </>
          }
        />

        <h2 id="esi-model">9. Earth-similarity model</h2>
        <p>
          We compute the Schulze-Makuch et al. (2011) Earth Similarity Index from
          radius, bulk density, escape velocity, and equilibrium temperature.
          Because the paper&rsquo;s temperature term is defined against
          Earth&rsquo;s <em>surface</em> temperature (288 K) and exoplanet
          catalogues supply only <em>equilibrium</em> temperature (excluding
          greenhouse warming by construction), we reference against Earth&rsquo;s
          own equilibrium temperature (254 K) instead — and we state the
          consequence rather than hide it: Venus scores <strong>0.92</strong> on
          this metric, because its high albedo makes its equilibrium temperature
          cooler than Earth&rsquo;s. An Earth Similarity Index computed from data
          that actually exists for real exoplanets cannot distinguish an Earth
          from a Venus. This is a property of the observations, not a defect of
          this implementation, and Venus is carried through the whole pipeline as
          a control specifically so the degeneracy is visible in the results.
        </p>

        <ArticleFigure
          src="/figures/equilibrium_temperature.png"
          width={1315}
          height={864}
          alt="Distribution of calculated equilibrium temperatures with a Sun-like conservative habitable-zone reference band"
          caption={
            <>
              Equilibrium-temperature distribution using a uniform Earth-like
              Bond albedo of 0.306. The shaded reference range translates the
              Sun-like conservative habitable zone through the same assumption.
              It is not a surface-temperature estimate and includes no
              greenhouse model.
            </>
          }
        />

        <SideNote eyebrow="Methodological citation" side="left">
          Schulze-Makuch et al. (2011, Astrobiology 11, 1041). Venus scores{" "}
          <strong>0.92</strong> on this same metric — see{" "}
          <Link href="/limitations" className="link">
            Limitations
          </Link>
          .
        </SideNote>

        <ArticleFigure
          src="/figures/mass_radius.png"
          width={1256}
          height={854}
          alt="Mass-radius diagram for the analysed catalogue, coloured by mass provenance"
          caption={
            <>
              Mass–radius diagram for the analysed catalogue, coloured by
              mass provenance (measured, M sin i lower limit, or inferred
              from radius via a mass–radius relation). Diagonal lines mark
              constant bulk density; the horizontal line marks 1.6 R⊕, above
              which most planets are not predominantly rocky (Rogers 2015).
              Solar System bodies are shown as labelled reference points, not
              exoplanet observations.
            </>
          }
        />

        <h2 id="uncertainty">10. Uncertainty propagation</h2>
        <p>
          Every parameter with a published asymmetric uncertainty is sampled from
          a two-piece (split) normal distribution — {compactInt(
            s.monte_carlo.n_samples,
          )}{" "}
          draws per planet, seed {s.monte_carlo.seed} — and every derived
          quantity is recomputed per draw. Missing uncertainties are sampled as a
          delta function and counted, not invented: the resulting artificially
          narrow posterior is tracked as{" "}
          <code>mc_uncertainty_coverage</code> and penalised explicitly by the
          observational-confidence score, so a planet that looks precisely
          Earth-like only because nobody published error bars cannot outrank one
          that is genuinely well measured.
        </p>

        <ArticleFigure
          src="/figures/uncertainty.png"
          width={2015}
          height={834}
          alt="Candidate ranking comparison showing nominal values and Monte Carlo uncertainty intervals"
          caption={
            <>
              Ranking uncertainty after propagating the reported asymmetric
              measurement errors. Point estimates can appear neatly ordered;
              overlapping posterior intervals show where the data do not
              support a confident distinction between neighbouring candidates.
            </>
          }
        />

        <SideNote eyebrow="Computational scale" side="right">
          {compactInt(s.monte_carlo.n_samples)} draws ×{" "}
          {compactInt(mcPlanets)} planets ≈{" "}
          {compactInt(s.monte_carlo.n_samples * mcPlanets)}{" "}
          total samples, seed {s.monte_carlo.seed} for exact reproducibility.
        </SideNote>

        <ArticleFigure
          src="/figures/posterior_clouds.png"
          width={1344}
          height={1051}
          alt="Monte Carlo posterior clouds in radius-density space for the six highest-ranked candidates"
          caption={
            <>
              Monte Carlo posterior clouds ({compactInt(s.monte_carlo.n_samples)}
              {" "}draws per planet) in radius–density space for the six
              highest-ranked candidates, propagated from each planet&rsquo;s
              own published asymmetric uncertainties. Filled points mark
              posterior medians; Earth is shown as a reference point. A
              wider cloud is itself a result — it means the mass behind it
              was predicted from the radius, not measured.
            </>
          }
        />

        <h2 id="transit">11. Transit analysis</h2>
        <p>
          For planets with public MAST light curves, we detrend with a
          Savitzky–Golay filter (window forced to at least three times the
          transit duration), clip outliers <em>upward only</em> (a symmetric clip
          removes transits, which are downward excursions by definition), fold on
          the published ephemeris after converting it into the mission&rsquo;s
          own time system, and fit a trapezoid. Every fit is checked against the
          published depth and rejected as unvalidated on disagreement beyond a
          factor of 1.6. Validated on four bright benchmark planets (HD 189733 b,
          WASP-39 b, HD 209458 b, WASP-19 b) at ratios of 0.77–0.99 to published
          depth. None of the current top-ranked Earth-2.0 candidates produces a
          validated fit — see{" "}
          <Link href="/transit-lab" className="link">
            Transit Lab
          </Link>
          .
        </p>

        <ArticleFigure
          src="/figures/period_radius.png"
          width={1318}
          height={954}
          alt="Orbital period against planet radius for the confirmed catalogue, coloured by discovery method, with top Earth-2.0 candidates outlined"
          caption={
            <>
              Orbital period against planet radius for the full catalogue,
              coloured by discovery method. Open circles mark the top eight
              computed candidates and Earth is included only as a labelled
              reference. The dense short-period structure is the selection
              function of current surveys made visible.
            </>
          }
        />

        <h2 id="rv">12. Radial-velocity evidence</h2>
        <p>
          Public radial-velocity time series are retrieved from DACE together
          with the stellar activity indicators (log R&rsquo;HK, H-alpha, Ca II
          H&amp;K, CCF bisector span) measured from the same spectra. Every
          candidate period is checked against the periodograms of those
          indicators; a coincidence is flagged explicitly rather than silently
          accepted, because a rotating, spotted star produces an apparent
          velocity signal with no planet in it. A three-criterion reliability
          gate (minimum point count, amplitude significance, residual-to-
          amplitude ratio) blocks a fit from being reported as a measurement when
          the data cannot support it — a gate discovered to be necessary after an
          unconstrained fit on TRAPPIST-1 returned an apparent 10–41 Earth-mass
          planet where the true value is roughly one. See{" "}
          <Link href="/rv-lab" className="link">
            RV Lab
          </Link>
          .
        </p>

        <h2 id="spectroscopy">13. Atmospheric spectroscopy</h2>
        <p>
          {compactInt(Number(s.atmosphere["transmission_measurement_rows"]))}{" "}
          genuine transmission-spectroscopy measurements exist across{" "}
          {String(s.atmosphere["planets_with_transmission_spectra"])} planets, harmonised
          from two incompatible archive representations (transit depth as a
          percentage, and planet-to-star radius ratio) into a single ppm scale.
          These are strictly planetary-atmosphere measurements — never conflated
          with the separate stellar-spectra holdings, which constrain the host
          star and underpin radial-velocity work but say nothing directly about a
          planet&rsquo;s atmosphere. See{" "}
          <Link href="/spectral-lab" className="link">
            Spectral Lab
          </Link>
          .
        </p>

        <SideNote eyebrow="The instrument challenge" side="left">
          {topFacilities.slice(0, 2).map(([name, n], i) => (
            <span key={name}>
              {i > 0 && ", "}
              {shortFacilityName(name)}: {compactInt(n)}
            </span>
          ))}{" "}
          measurement rows. Two space telescopes supply most of the
          archive&rsquo;s atmospheric evidence.
        </SideNote>

        <ArticleFigure
          src="/figures/transmission_spectrum.png"
          width={1595}
          height={817}
          alt="Published transmission spectrum of WASP-39 b with expected molecular band positions annotated"
          caption={
            <>
              Published transmission spectrum of WASP-39 b, the best-observed
              planetary atmosphere in the archive at the time of this
              analysis. Dashed vertical lines mark expected molecular band
              positions, not detections — see{" "}
              <Link href="/spectral-lab" className="link">
                Spectral Lab
              </Link>
              .
            </>
          }
        />

        <h2 id="biosignature">14. Biosignature context</h2>
        <p>
          We compute no probability of life for any planet, and no metric in
          this project is designed to approximate one. There is no calibrated
          likelihood function for biology on exoplanets: one confirmed inhabited
          world, no confirmed uninhabited control with a directly comparable
          atmosphere, and an incomplete theory of abiotic false positives.
          Instead we document, per species, the documented abiotic production
          routes — water photolysis with hydrogen escape, CO₂ photolysis,
          serpentinisation — and the conditions (disequilibrium rather than a
          single gas, a characterised stellar UV environment, reported cloud and
          retrieval degeneracies, independent reproduction) that would need to
          hold before a biological interpretation could be taken seriously.
        </p>

        <h2 id="ranking">15. Candidate ranking</h2>
        <p>
          Four independent, interpretable scores — Earth similarity, conservative
          habitability, observational confidence, and characterisation potential
          — combine into a composite Earth-2.0 index by a{" "}
          <strong>weighted geometric mean</strong>, not an average. This choice
          is deliberate: under an arithmetic mean, an ultra-hot Jupiter with
          excellent measurements and strong observability would score
          respectably despite zero habitability, its strong components
          compensating for the disqualifying one. A geometric mean is
          non-compensatory. Weights are exposed and reader-adjustable on the{" "}
          <Link href="/ranking" className="link">
            Ranking
          </Link>{" "}
          page; the pipeline default weighting is 35% similarity, 40%
          habitability, 25% confidence, and 0% characterisation potential
          (excluded because it structurally penalises non-transiting planets
          such as Proxima Centauri b for a reason unrelated to habitability).
        </p>

        <ArticleFigure
          src="/figures/top_candidates.png"
          width={2194}
          height={1089}
          alt="Top computed Earth-2.0 candidates with component-score decomposition and Earth Similarity Index posterior intervals"
          caption={
            <>
              The leading computed candidates, with the composite ranking
              decomposed into its independently interpretable inputs and the
              Earth Similarity Index shown with propagated uncertainty. No bar
              is a probability of habitability or life.
            </>
          }
        />

        <h2 id="deep-dives">16. Deep-dive systems</h2>
        <p>
          The ten highest-ranked candidates are selected purely from the computed
          index, never hand-picked, and receive full deep-dive treatment: every
          parameter with its uncertainty and per-measurement provenance link,
          Monte Carlo posteriors, host-star and sibling-planet context, an
          attempted transit fit and an attempted radial-velocity analysis where
          public data exists, and an explicit statement of which analyses were
          <em>not</em> possible and why. Earth, Venus, Mars, Mercury and Jupiter
          run through the identical pipeline as labelled comparison controls.
        </p>

        <h2 id="results">17. Results</h2>
        <p>
          Of {compactInt(nPlanets)} confirmed planets, {compactInt(
            cov.n_with_measured_mass,
          )}{" "}
          ({pct(cov.n_with_measured_mass / nPlanets, 0)}) have a directly
          measured mass; {compactInt(cov.n_with_mass_inferred_from_radius)} (
          {pct(cov.n_with_mass_inferred_from_radius / nPlanets, 0)}) carry a mass
          predicted from the radius by a mass–radius relation and therefore add
          no independent information to density or escape velocity.{" "}
          {hz["n_in_conservative_hz_nominal"]} planets fall in the conservative
          habitable zone under the strict (non-extrapolated) model evaluation;{" "}
          {hz["n_in_optimistic_hz_nominal"]} under the optimistic definition.
          Intersecting habitable-zone membership with rocky plausibility (radius
          below 1.6 R⊕) narrows this to{" "}
          <strong>{hz["n_conservative_hz_and_below_1p6_re"]} planets</strong>, of
          which <strong>
            {hz["n_conservative_hz_and_below_1p6_re_with_measured_mass"]}
          </strong>{" "}
          has a measured mass. The computed top of the ranking — Proxima
          Centauri b, GJ 1061 d, GJ 1002 b, Wolf 1069 b, Teegarden&rsquo;s Star
          c, and GJ 1002 c — independently recovers nearby M-dwarf terrestrial
          systems the literature already treats among the leading temperate
          candidates, which we take as evidence the underlying physics is
          implemented correctly rather than as a novel discovery. TRAPPIST-1&rsquo;s
          planets, prominent in earlier runs of this pipeline, no longer lead
          the ranking: their host star&rsquo;s effective temperature (2566 K)
          sits below the habitable-zone model&rsquo;s calibrated floor, so the
          conservative-habitability score is discounted by the small fraction
          of the Monte Carlo posterior the model could actually evaluate,
          rather than reporting a confident-looking probability computed from
          only that minority of draws (see{" "}
          <Link href="/limitations" className="link">
            Limitations
          </Link>
          ).
        </p>

        <ArticleFigure
          src="/figures/ranking_distribution.png"
          width={1889}
          height={1159}
          alt="Distribution of Earth-2.0 component scores and composite ranking across the rankable confirmed-planet population"
          caption={
            <>
              Population-level score distributions. The composite is sparse at
              the high end because the geometric mean requires candidates to
              perform across all included dimensions; strength on one axis
              cannot erase a near-zero score on another.
            </>
          }
        />

        <ArticleFigure
          src="/figures/evidence_matrix.png"
          width={1551}
          height={1672}
          alt="Data-confidence matrix for the 22 highest-ranked candidates across mass provenance, uncertainty coverage, reference depth, habitable-zone validity, and transit, RV and spectroscopy data availability"
          caption={
            <>
              Data-confidence matrix for the 22 highest-ranked candidates.
              Each column is an independent evidential fact, not a
              decorative colour scale: mass provenance quality, fraction of
              propagated parameters with a published uncertainty, log-scaled
              independent reference depth, whether the host lies within the
              habitable-zone model&rsquo;s validity range, and whether
              transit, radial-velocity, and atmospheric spectroscopy data
              exist. A high composite index built on weak evidence is a
              different result from a high index built on strong evidence —
              this figure exists to make that distinction visible.
            </>
          }
        />

        <h2 id="biases">18. Observational biases</h2>
        <p>
          The discovery-method distribution in this catalogue is the shape of
          our instruments, not the true underlying planet population. Transit
          surveys favour short orbital periods and large planet-to-star radius
          ratios; radial-velocity surveys favour massive planets on close
          orbits around bright, quiet stars; direct imaging favours young, wide-
          separation giant planets. A temperate Earth-mass planet around a
          Sun-like star is disfavoured by every major detection method
          simultaneously — its transit probability is low, its RV amplitude is
          roughly 9 cm/s, and it sits far too close to its host for imaging. The
          preponderance of small-star candidates in this ranking is therefore
          partly a statement about M dwarfs being easier to search, not only a
          statement about where temperate rocky planets exist.
        </p>

        <SideNote eyebrow="The catalogue is a survey artefact" side="left">
          {Object.entries(s.population.discovery_methods as Record<string, number>)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([method, n]) => `${method}: ${compactInt(n)}`)
            .join(" · ")}
          . One method dominates because it is easiest, not because the
          underlying population is shaped that way.
        </SideNote>

        <h2 id="limitations">19. Limitations</h2>
        <p>
          The full accounting is in{" "}
          <Link href="/limitations" className="link">
            Limitations
          </Link>
          . The four load-bearing ones: the Earth Similarity Index cannot
          separate Earth from Venus given the data that exists; roughly half of
          catalogue masses were never measured; the habitable-zone model does not
          formally cover the TRAPPIST-1 host temperature; and an Earth twin&rsquo;s
          atmospheric transmission signal (about 1 ppm) is roughly an order of
          magnitude below demonstrated JWST precision, so finding an Earth
          analogue and characterising its atmosphere are separated by a
          generation of instruments.
        </p>

        <h2 id="future">20. Future observations</h2>
        <p>
          For transiting candidates, we compute the Kempton et al. (2018)
          Transmission and Emission Spectroscopy Metrics to indicate relative
          atmospheric-characterisation feasibility with current infrastructure,
          rather than promising any specific instrument can observe a specific
          target. For non-transiting candidates we report the expected
          radial-velocity semi-amplitude, which for the temperate small planets
          in this catalogue is frequently below 1 m/s — below the demonstrated
          floor of even the highest-precision current spectrographs for most
          targets, which is itself informative about what next-generation
          instruments would need to achieve.
        </p>

        <h2 id="conclusions">21. Conclusions</h2>
        <p>
          The search for Earth 2.0 is not currently constrained by the number of
          known exoplanets. It is constrained by how few of them are measured
          well enough to support the claim. A physically grounded, uncertainty-
          aware, and evidentially honest ranking surfaces a short, specific list
          of candidates worth prioritising for further observation, while making
          the boundary between what is known and what is merely plausible
          explicit at every step.
        </p>

        <h2 id="references">22. References</h2>
        <p>
          The full bibliography, with per-measurement links back to{" "}
          {compactInt(prov?.n_distinct_publications ?? 0)} distinct publications
          drawn from the archive&rsquo;s own reference metadata, is on the{" "}
          <Link href="/references" className="link">
            References
          </Link>{" "}
          page. Key methodological citations: Kopparapu et al. (2013, ApJ 765,
          131, with the 2013 erratum ApJ 770, 82); Schulze-Makuch et al. (2011,
          Astrobiology 11, 1041); Rogers (2015, ApJ 801, 41); Fulton et al.
          (2017, AJ 154, 109); Kempton et al. (2018, PASP 130, 114401).
        </p>
        </div>

        <aside className="research-evidence" aria-label="Analysis at a glance">
          <div className="research-evidence-card">
            <p className="eyebrow">Analysis at a glance</p>
            <dl>
              <div>
                <dt>Confirmed planets</dt>
                <dd>{compactInt(nPlanets)}</dd>
              </div>
              <div>
                <dt>Source records</dt>
                <dd>{compactInt(s.scale.total_source_records)}</dd>
              </div>
              <div>
                <dt>Archive datasets</dt>
                <dd>{s.scale.n_datasets_retrieved}</dd>
              </div>
              <div>
                <dt>MC draws / planet</dt>
                <dd>{compactInt(s.monte_carlo.n_samples)}</dd>
              </div>
            </dl>
          </div>

          <div className="research-evidence-card research-truth-card">
            <p className="eyebrow">Claim boundary</p>
            <p>
              This is a prioritisation study. It does not identify life,
              habitability, or a confirmed second Earth.
            </p>
          </div>

          <div className="research-evidence-card">
            <p className="eyebrow">Explore the evidence</p>
            <div className="research-rail-links">
              <Link href="/atlas">Candidate atlas</Link>
              <Link href="/transit-lab">Transit lab</Link>
              <Link href="/rv-lab">RV lab</Link>
              <Link href="/spectral-lab">Spectral lab</Link>
            </div>
          </div>
        </aside>
      </div>
    </article>
  );
}
