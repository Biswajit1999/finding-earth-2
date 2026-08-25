import type { Metadata } from "next";
import { PageHeader, Caveat } from "@/components/PageHeader";
import { SideNote } from "@/components/SideNote";
import { getSummary } from "@/lib/data";
import { compactInt, num, pct } from "@/lib/format";

export const metadata: Metadata = {
  title: "Limitations",
  description: "What this analysis can and cannot establish, stated plainly.",
};

export default function LimitationsPage() {
  const s = getSummary();
  const cov = s.measurement_coverage as Record<string, number>;
  const n = s.population.n_confirmed_planets;

  return (
    <>
      <PageHeader
        eyebrow="Read this before citing a number"
        title="What this analysis cannot establish"
        lede="A serious project states its limitations as prominently as its results. These are not disclaimers added after the fact — several were discovered while building the pipeline and changed how it works."
      />

      <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
        <div className="prose-sci mx-auto space-y-10">
          <section>
            <h2>The Earth Similarity Index cannot separate Earth from Venus</h2>
            <p>
              Venus scores <strong>0.92</strong> on the Earth Similarity Index
              computed by this pipeline. Its high Bond albedo makes its
              equilibrium temperature <em>cooler</em> than Earth&rsquo;s, and
              equilibrium temperature — not surface temperature — is the only
              temperature exoplanet catalogues provide. This is not a defect of
              this implementation; it is a property of the observations
              available for real exoplanets. No ESI computed from catalogue
              data can currently distinguish a temperate rocky world from a
              runaway-greenhouse one. Venus is carried through the entire
              pipeline as a labelled control specifically so this is visible
              in the results.
            </p>
            <SideNote eyebrow="Methodological citation" side="right">
              Schulze-Makuch et al. (2011, Astrobiology 11, 1041) defines the
              Earth Similarity Index this project computes.
            </SideNote>
          </section>

          <section>
            <h2>{pct(cov.n_with_mass_inferred_from_radius / n, 0)} of catalogue masses were never measured</h2>
            <p>
              They are predictions from the radius via a mass–radius relation.
              Density and escape velocity computed from such a mass re-encode
              the radius rather than adding independent information, which
              would make the ESI appear to combine four independent properties
              while actually being driven by one. This project classifies mass
              provenance explicitly and discounts inferred masses in the
              observational-confidence score.
            </p>
            <SideNote eyebrow="Mass provenance, in full" side="left">
              Measured: {compactInt(cov.n_with_measured_mass)}. M sin i:{" "}
              {compactInt(cov.n_with_msini_lower_limit)}. Inferred from radius:{" "}
              {compactInt(cov.n_with_mass_inferred_from_radius)}. Upper limit
              only: {compactInt(cov.n_with_mass_upper_limit_only)}.
            </SideNote>
          </section>

          <section>
            <h2>TRAPPIST-1 sits below the habitable-zone model&rsquo;s validity floor</h2>
            <p>
              The Kopparapu et al. (2013) fit is stated valid for 2600–7200 K
              host effective temperatures. TRAPPIST-1&rsquo;s host is 2566 K —
              34 K below the floor. A strict reading excludes the most-studied
              temperate terrestrial system known from every habitable-zone
              count. This project reports results both ways: strictly (with
              TRAPPIST-1 planets carrying &ldquo;undetermined&rdquo; HZ status)
              and with an explicitly flagged extrapolation. Neither reading is
              hidden.
            </p>
            <SideNote eyebrow="Methodological citation" side="right">
              Kopparapu et al. (2013, ApJ 765, 131; 2013 erratum, ApJ 770, 82)
              states the model&rsquo;s 2600–7200 K validity range explicitly.
            </SideNote>
          </section>

          <section>
            <h2>An Earth twin&rsquo;s atmospheric signal is about 1 ppm</h2>
            <p>
              For a real nitrogen-oxygen atmosphere (mean molecular weight ≈29)
              around a Sun-like star, the transmission-spectroscopy amplitude
              is roughly an order of magnitude smaller than for a
              hydrogen-dominated atmosphere of the same scale height, and well
              below demonstrated JWST precision. Finding an Earth analogue and
              characterising its atmosphere are separated by a generation of
              instruments; nothing in this project promises otherwise.
            </p>
            <SideNote eyebrow="The instrument gap" side="left">
              {compactInt(Number(s.atmosphere["transmission_measurement_rows"]))}
              {" "}genuine transmission measurements exist across{" "}
              {String(s.atmosphere["planets_with_transmission_spectra"])}{" "}
              planets — none of them Earth-sized in the habitable zone.
            </SideNote>
          </section>

          <Caveat tone="stop" title="Not established by this project, for any planet">
            Confirmed habitability. Evidence for life. A probability of
            biology. Detection of any biosignature gas. This project computes
            none of these, for any object in the catalogue, under any
            circumstance.
          </Caveat>

          <section>
            <h2>Discovery-method bias</h2>
            <p>
              The catalogue&rsquo;s method distribution reflects instrument
              sensitivity, not the true underlying planet population. Transit
              surveys favour short periods and large radius ratios;
              radial-velocity surveys favour massive, close-in planets around
              bright quiet stars; direct imaging favours young, wide-separation
              giants. A temperate Earth-mass planet around a Sun-like star is
              disfavoured by every major method at once.
            </p>
          </section>

          <section>
            <h2>Coverage gaps not integrated in this release</h2>
            <p>
              Gaia DR3 is now cross-matched by exact <code>source_id</code>{" "}
              for every host the archive links to one — {compactInt(s.gaia_crossmatch.n_hosts_matched)}{" "}
              systems — as an independent distance check, not a full
              astrometric re-reduction. The ESO Science Archive was
              investigated but is not built into this pipeline; see{" "}
              <a href="/data" className="link">
                Data sources
              </a>{" "}
              for the reasoning. Transit and RV analyses depend on public data
              existing at MAST and DACE respectively — most catalogue planets
              have neither, and this is reported as an explicit absence rather
              than omitted.
            </p>
            <SideNote eyebrow="Gaia cross-check, in full" side="right">
              {compactInt(s.gaia_crossmatch.n_hosts_matched)} hosts matched.
              Median distance disagreement:{" "}
              {num(s.gaia_crossmatch.median_distance_disagreement_pct, 2)}%.{" "}
              {compactInt(s.gaia_crossmatch.n_ruwe_above_1p4)} hosts flagged
              RUWE &gt; 1.4 (possible unresolved binary).
            </SideNote>
          </section>

          <section>
            <h2>Model and fit caveats</h2>
            <ul>
              <li>
                Transit-fit depths from this pipeline&rsquo;s own trapezoid
                model run 5–25% below published values (a known
                detrending systematic) and are never substituted for
                catalogue values.
              </li>
              <li>
                Radial-velocity semi-amplitude fits are gated by a
                three-criterion reliability check; a mass is withheld entirely
                when the fit fails it.
              </li>
              <li>
                Habitable-zone membership from Monte Carlo draws is
                conditional on the draw&rsquo;s temperature falling inside the
                model&rsquo;s validity range — the fraction of draws that do is
                reported alongside the probability.
              </li>
              <li>
                A high Earth Similarity Index alongside low observational
                confidence should never be read the same as a high index with
                high confidence; the two are reported as separate axes for
                exactly this reason.
              </li>
            </ul>
          </section>
        </div>
      </div>
    </>
  );
}
