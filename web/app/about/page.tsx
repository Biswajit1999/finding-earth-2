import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/PageHeader";
import { getSummary } from "@/lib/data";
import { slugify } from "@/lib/format";

const SITE_URL = "https://biswajit1999.github.io/finding-earth-2/";
const ABOUT_URL = `${SITE_URL}about/`;

export const metadata: Metadata = {
  title: "The Search",
  description:
    "Finding Earth 2.0 in Distant Worlds: explore the evidence behind the search for Earth-like exoplanets, habitable-zone candidates, measured masses, Monte Carlo uncertainty, transit and radial-velocity data, atmospheric spectra, and reproducible archive provenance.",
  alternates: { canonical: ABOUT_URL },
  openGraph: {
    type: "article",
    url: ABOUT_URL,
    title: "The Search — Finding Earth 2.0 in Distant Worlds",
    description:
      "From public astronomical archives to a small set of temperate, plausibly rocky worlds: the evidence, uncertainty and measurement limits behind Finding Earth 2.0.",
  },
};

const topicLinks = [
  ["scale", "We have thousands of planets"],
  ["first-cut", "164,209 records → the first cut"],
  ["mass", "The most important number might be one"],
  ["definitions", "Earth-like is not the same as habitable"],
  ["earth-at-100pc", "What Earth would look like from 100 parsecs"],
  ["life", "A candidate is not a discovery of life"],
  ["missing-mass", "The missing-mass problem"],
  ["provenance", "Every number has a history"],
  ["probability-cloud", "A planet is a probability cloud"],
  ["selection-effects", "The telescope shapes the catalogue"],
  ["survivors", "Meet the worlds that survived"],
  ["scores", "There is no single best planet"],
  ["next-observations", "What would convince us?"],
  ["evidence", "No aliens. No hype. Just the evidence."],
  ["closing-question", "Is there another Earth?"],
] as const;

const nf = new Intl.NumberFormat("en-GB");

export default function AboutPage() {
  const s = getSummary();
  const hz = s.habitable_zone as Record<string, number | string>;
  const sourceRecords = nf.format(s.scale.total_source_records);
  const confirmedPlanets = nf.format(s.population.n_confirmed_planets);
  const conservativeHz = nf.format(Number(hz.n_in_conservative_hz_nominal ?? 0));
  const smallTemperate = nf.format(
    Number(hz.n_conservative_hz_and_below_1p6_re ?? 0),
  );
  const independentlyMeasured = nf.format(
    Number(
      hz.n_conservative_hz_and_below_1p6_re_with_measured_mass ?? 0,
    ),
  );
  const mcDraws = nf.format(s.monte_carlo.n_samples);
  const topCandidates = s.ranking?.top_candidates?.slice(0, 5) ?? [];

  const aboutJsonLd = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: "The Search — Finding Earth 2.0 in Distant Worlds",
    url: ABOUT_URL,
    description:
      "A research narrative explaining how Finding Earth 2.0 searches public astronomical archives for potentially Earth-like exoplanets while keeping habitability, similarity, observability and evidence for biology separate.",
    isPartOf: {
      "@type": "WebSite",
      name: "Finding Earth 2.0 in Distant Worlds",
      url: SITE_URL,
    },
    author: {
      "@type": "Person",
      name: "Biswajit Jana",
      sameAs: "https://github.com/Biswajit1999",
    },
    about: [
      "exoplanets",
      "Earth-like planets",
      "habitable zones",
      "Earth Similarity Index",
      "NASA Exoplanet Archive",
      "Gaia DR3",
      "transit photometry",
      "radial velocity",
      "exoplanet spectroscopy",
      "Monte Carlo uncertainty propagation",
      "reproducible astrophysics",
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(aboutJsonLd).replace(/</g, "\\u003c"),
        }}
      />

      <PageHeader
        eyebrow="Finding Earth 2.0 in Distant Worlds"
        title="The Search"
        meta={`${sourceRecords} source records · ${confirmedPlanets} confirmed planets · ${smallTemperate} small + temperate first-cut candidates`}
      />

      <article className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
        <div className="prose-sci mx-auto">
          <p className="lead">
            Finding Earth 2.0 is a reproducible computational astrophysics
            project asking a deliberately difficult question: among the
            exoplanets we have actually measured, which worlds most closely
            satisfy physically motivated conditions associated with an
            Earth-like, potentially habitable planet — and how strong is the
            evidence behind each one?
          </p>
          <p>
            The project does not begin with a hand-picked list of famous
            planets. It begins with public astronomical archives, preserves
            provenance, propagates published uncertainty, and keeps Earth
            similarity, habitable-zone position, rocky plausibility,
            atmospheric observability and evidence for biology as separate
            questions. That distinction is central to the analysis.
          </p>

          <nav aria-label="The Search topics" className="my-10">
            <h2>Explore the questions behind the search</h2>
            <ol>
              {topicLinks.map(([id, label], i) => (
                <li key={id}>
                  <a href={`#${id}`} className="link">
                    {String(i + 1).padStart(2, "0")} — {label}
                  </a>
                </li>
              ))}
            </ol>
          </nav>

          <section id="scale">
            <h2>01 — We Have Thousands of Planets. Almost None Are Earth 2.0.</h2>
            <p>
              The age of exoplanet discovery has transformed astronomy.
              Thousands of confirmed worlds now orbit stars beyond the Solar
              System: hot Jupiters, sub-Neptunes, super-Earths, frozen giants,
              ultra-short-period planets and a much smaller population
              approaching Earth&apos;s scale.
            </p>
            <p>
              But discovering a planet and discovering another Earth are very
              different problems. Start with <strong>{confirmedPlanets} confirmed planets</strong>,
              then ask whether a world is small enough to plausibly be rocky,
              whether it receives temperate stellar irradiation, whether its
              radius and mass are actually measured, whether those measurements
              have useful uncertainties, and whether the host star lies inside
              the calibrated range of the adopted habitable-zone model.
            </p>
            <blockquote>
              <p>
                The remarkable thing is no longer how many planets we have
                discovered. It is how few survive a serious search for
                something remotely Earth-like.
              </p>
            </blockquote>
            <p>
              This project begins there — not with the assumption that another
              Earth exists in the catalogue, but with the question:
              <strong> what does the evidence actually allow us to say?</strong>
            </p>
          </section>

          <section id="first-cut">
            <h2>02 — {sourceRecords} Records. {smallTemperate} Worlds Survive the First Cut.</h2>
            <p>
              Finding Earth 2.0 begins with the archives. The current build
              brings together <strong>{sourceRecords} provenance-tracked source
              records</strong>, including catalogue measurements, stellar
              parameters, candidate records, spectroscopy metadata and
              supporting astronomical information.
            </p>
            <p>
              The search then narrows: <strong>{confirmedPlanets} confirmed
              planets</strong> → <strong>{conservativeHz} nominal conservative
              habitable-zone worlds</strong> → <strong>{smallTemperate} worlds
              that are both in the nominal conservative habitable zone and
              below the project&apos;s adopted 1.6 R⊕ first-cut radius threshold</strong>.
            </p>
            <p>
              Those {smallTemperate} are not declared &quot;Earth 2.0&quot;.
              They are simply the worlds for which the available measurements
              justify asking the next question: <strong>how much do we actually
              know about them?</strong>
            </p>
          </section>

          <section id="mass">
            <h2>03 — The Most Important Number Might Be {independentlyMeasured}.</h2>
            <p>
              Planetary radius tells us how large a world appears. An
              independent mass measurement adds a second physical constraint and
              helps us estimate bulk density, surface gravity and escape
              velocity without deriving everything from the radius itself.
            </p>
            <p>
              Among the {smallTemperate} small worlds surviving the nominal
              conservative-habitable-zone first cut, the current analysis finds
              <strong> {independentlyMeasured} with an independently measured
              mass</strong>. Other entries may rely on a radius-based inferred
              mass or an RV minimum mass, <em>M sin i</em>, which carries
              different information.
            </p>
            <blockquote>
              <p>
                Finding planets is no longer the whole problem. Measuring
                Earth-sized planets well enough is.
              </p>
            </blockquote>
          </section>

          <section id="definitions">
            <h2>04 — Earth-Like Is Not the Same as Habitable.</h2>
            <p>
              Finding Earth 2.0 deliberately separates five concepts that are
              often collapsed into a single headline.
            </p>
            <h3>Earth similarity</h3>
            <p>
              Do measurable bulk properties resemble Earth? Similarity is a
              comparison, not evidence of habitability.
            </p>
            <h3>Habitable-zone position</h3>
            <p>
              Does incident stellar flux fall within stated climate-model
              boundaries? Being inside a habitable zone does not prove liquid
              surface water exists.
            </p>
            <h3>Rocky plausibility</h3>
            <p>
              Is a predominantly rocky composition still plausible given the
              measured size and other constraints? Radius alone does not reveal
              geology or interior structure.
            </p>
            <h3>Atmospheric observability</h3>
            <p>
              Could present or future instruments realistically characterise
              the atmosphere? Observability is an instrumental question, not a
              habitability score.
            </p>
            <h3>Evidence for biology</h3>
            <p>
              No metric in this project estimates a probability of life, and no
              planet is presented as having established biological activity.
            </p>
            <p><strong>Five questions. Five different meanings. They should never be collapsed into one.</strong></p>
          </section>

          <section id="earth-at-100pc">
            <h2>05 — What Would Earth Look Like to Us From 100 Parsecs Away?</h2>
            <p>
              Put Earth around a distant star and move it outward: ten parsecs,
              thirty, one hundred. The familiar image disappears. Continents,
              cloud systems, oceans and cities are not what a distant observer
              would normally receive as direct evidence.
            </p>
            <p>
              What may remain are indirect observables: a periodic stellar
              dimming that constrains orbital period and radius, stellar
              irradiation and equilibrium-temperature estimates, perhaps a
              radial-velocity mass, and — in favourable cases — fragments of
              atmospheric information from spectroscopy.
            </p>
            <blockquote>
              <p>Finding another Earth may be easier than proving that it is another Earth.</p>
            </blockquote>
            <p>
              The gap between a beautiful planet rendering and what a telescope
              actually measures is one of the central ideas of this project.
            </p>
          </section>

          <section id="life">
            <h2>06 — A Candidate Is Not a Discovery of Life.</h2>
            <p>
              A world can be potentially rocky, temperate in its received
              stellar flux and close to Earth&apos;s size while the most
              important questions remain unanswered: atmosphere, pressure,
              climate, surface conditions, liquid water and biology.
            </p>
            <p>
              Finding Earth 2.0 therefore does not convert an Earth Similarity
              Index, a habitable-zone classification or a spectral feature into
              a made-up &quot;chance of life&quot;.
            </p>
            <p><strong>Interesting is not the same as inhabited.</strong></p>
          </section>

          <section id="missing-mass">
            <h2>07 — The Missing-Mass Problem</h2>
            <p>
              Two planets can have similar radii and radically different
              compositions. One may be dense and rocky; another may contain a
              substantial volatile inventory or retain a gaseous envelope.
            </p>
            <p>
              Radius asks <strong>how big?</strong> Mass begins to answer
              <strong> how much material?</strong> Together they constrain
              <strong> how dense?</strong> That is why independent mass
              measurements are disproportionately valuable for small,
              temperate candidates.
            </p>
            <p><strong>A radius tells us how big a world is. It doesn&apos;t always tell us what the world is.</strong></p>
          </section>

          <section id="provenance">
            <h2>08 — Every Number Has a History.</h2>
            <p>
              A catalogue value such as <strong>Radius: 1.07 R⊕</strong> can
              look like a single fact. Behind it may sit an observing programme,
              stellar-radius analysis, transit-depth measurement, published
              uncertainty, archive ingestion, unit validation, Monte Carlo
              propagation and a final ranking contribution.
            </p>
            <p>
              Finding Earth 2.0 treats that chain as part of the result. Derived
              values remain distinguishable from measured values, inferred
              masses remain distinguishable from independent measurements, and
              missing information remains missing instead of being quietly
              replaced by convenient numbers.
            </p>
            <p><strong>Don&apos;t trust the score. Trace it.</strong></p>
            <p>
              Explore the <Link href="/data" className="link">data and provenance</Link>{" "}
              or the <Link href="/methods" className="link">methods</Link> behind
              the calculations.
            </p>
          </section>

          <section id="probability-cloud">
            <h2>09 — What {mcDraws} Possible Versions of One Planet Look Like</h2>
            <p>
              A catalogue usually presents one central value, but measurements
              are not infinitely precise. Radius, mass, stellar temperature,
              luminosity, orbital parameters and incident flux may all carry
              uncertainty, and those uncertainties propagate into derived
              quantities and rankings.
            </p>
            <p>
              The current pipeline uses <strong>{mcDraws} Monte Carlo draws per
              planet</strong>. Each draw is a physically possible realisation
              under the reported measurement uncertainties and adopted model
              assumptions.
            </p>
            <p>
              A tightly constrained candidate forms a compact posterior cloud;
              a poorly measured candidate spreads across a much larger region.
              That width is itself scientific information.
            </p>
            <p><strong>A planet isn&apos;t one number. It&apos;s a probability cloud.</strong></p>
          </section>

          <section id="selection-effects">
            <h2>10 — The Telescope Shapes the Universe We Think We Know.</h2>
            <p>
              The observed exoplanet catalogue is not the intrinsic Galactic
              planet population. Transit surveys favour particular geometries
              and detectable dips over finite observing baselines; radial
              velocity is more sensitive to systems producing measurable
              stellar reflex motion; microlensing and direct imaging probe
              different parts of parameter space again.
            </p>
            <p>
              Geometry, sensitivity, mission duration, stellar properties,
              target selection and follow-up priorities all shape what enters
              the catalogue.
            </p>
            <p><strong>The exoplanet catalogue is not the Universe. It is the Universe filtered through our instruments.</strong></p>
          </section>

          <section id="survivors">
            <h2>11 — Meet the Worlds That Survived</h2>
            <p>
              The ranking is generated by the analysis rather than by a
              hand-curated favourites list. In the current build, the leading
              candidates include:
            </p>
            <ul>
              {topCandidates.map((c) => (
                <li key={c.pl_name}>
                  <Link
                    href={`/candidate/${slugify(c.pl_name)}`}
                    className="link"
                  >
                    <strong>{c.pl_name}</strong>
                  </Link>
                  {c.sy_dist_pc !== null
                    ? ` — ${c.sy_dist_pc.toFixed(1)} pc`
                    : ""}
                  {` · Earth-2.0 index ${c.earth2_index.toFixed(3)} · ${c.mass_class.replaceAll("_", " ")}`}
                </li>
              ))}
            </ul>
            <p>
              These worlds are not labelled confirmed Earth twins. A more
              defensible description is: <strong>worlds worth measuring
              better.</strong>
            </p>
            <p>
              See the complete <Link href="/ranking" className="link">ranking</Link>{" "}
              and <Link href="/atlas" className="link">candidate atlas</Link>.
            </p>
          </section>

          <section id="scores">
            <h2>12 — There Is No Single Definition of the “Best” Planet.</h2>
            <p>
              One candidate can have high Earth similarity and habitable-zone
              consistency but weak observational confidence. Another can be
              less Earth-like while being much more precisely measured and far
              easier to characterise.
            </p>
            <p>
              The project therefore exposes separate axes for
              <strong> Earth similarity</strong>,
              <strong> conservative habitability</strong>,
              <strong> observational confidence</strong> and
              <strong> characterisation potential</strong>.
            </p>
            <p><strong>The ranking is not designed to eliminate disagreement. It is designed to expose it.</strong></p>
          </section>

          <section id="next-observations">
            <h2>13 — What Would Convince Us?</h2>
            <p>
              A useful ranking should reveal what is missing. For one candidate,
              the most valuable next step may be an independent mass; for
              another, improved stellar parameters, repeat spectroscopy,
              stellar-activity monitoring, better orbital constraints or a
              genuinely informative atmospheric spectrum.
            </p>
            <p>
              The stronger question is often not &quot;which candidate ranks
              first?&quot; but <strong>which observation would reduce the most
              important uncertainty?</strong>
            </p>
            <p><strong>The ranking isn&apos;t the end of the search. It tells us what to measure next.</strong></p>
            <p>
              Explore the <Link href="/follow-up" className="link">follow-up analysis</Link>.
            </p>
          </section>

          <section id="evidence">
            <h2>14 — No Aliens. No Hype. Just the Evidence.</h2>
            <p>
              Potentially habitable exoplanets are easy to sensationalise. This
              project deliberately avoids invented biosphere probabilities,
              fake spectra, imaginary oceans presented as observations, and the
              automatic promotion of a habitable-zone location into a claim of
              habitability or life.
            </p>
            <p>
              Instead: <strong>measurements, uncertainties, published evidence,
              reproducible analysis and traceable provenance.</strong>
            </p>
            <p>
              Scientifically informed planet renders are interpretations, not
              direct images. Spectral bands are not automatically detections.
              Habitable-zone membership is not evidence of an inhabited world.
            </p>
            <p><strong>Wonder doesn&apos;t require exaggeration.</strong></p>
          </section>

          <section id="closing-question">
            <h2>15 — Is There Another Earth?</h2>
            <p>
              Thousands of planets are now known. Hundreds occupy regions that
              can be called temperate under stated models. A much smaller group
              begins to resemble some of the physical conditions associated
              with Earth, while major gaps remain in what we know about nearly
              all of them.
            </p>
            <p><strong>Is there another Earth?</strong></p>
            <p><strong>We don&apos;t know.</strong> That is the scientifically correct answer.</p>
            <p>
              But public archives are growing, measurements are becoming more
              precise and atmospheric characterisation is reaching worlds that
              were previously inaccessible. We may not yet know where Earth
              2.0 is, but we can now search the evidence at planetary scale.
            </p>
            <p>
              <Link href="/atlas" className="link">
                <strong>Explore the candidates →</strong>
              </Link>
            </p>
          </section>

          <hr />

          <section aria-labelledby="project-author">
            <h2 id="project-author">Project and author</h2>
            <p>
              <strong>Finding Earth 2.0 in Distant Worlds</strong> is an
              open-source research project by <strong>Biswajit Jana</strong>.
              The software is MIT-licensed; source astronomical datasets remain
              governed by their originating archives.
            </p>
            <p>
              <a
                href="https://github.com/Biswajit1999/finding-earth-2"
                className="link"
                target="_blank"
                rel="noreferrer"
              >
                Source repository
              </a>
              {" · "}
              <a
                href="https://github.com/Biswajit1999"
                className="link"
                target="_blank"
                rel="noreferrer"
              >
                Biswajit Jana on GitHub
              </a>
            </p>
            <p className="font-[family-name:var(--font-mono)] text-[12.5px]">
              earth2 v{s.earth2_version} · analysis generated{" "}
              {new Date(s.generated_utc)
                .toISOString()
                .slice(0, 16)
                .replace("T", " ")}{" "}
              UTC · Python {s.software?.python} · runtime {s.runtime_seconds}s
            </p>
          </section>
        </div>
      </article>
    </>
  );
}
