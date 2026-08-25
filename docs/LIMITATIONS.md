# Limitations

What this analysis can and cannot establish, stated as prominently as the
results. Several of these were discovered while building the pipeline and
changed how it works, rather than being written afterward as disclaimers.

## The Earth Similarity Index cannot separate Earth from Venus

Venus scores **0.92** on the Earth Similarity Index this pipeline computes.
Its high Bond albedo makes its equilibrium temperature cooler than Earth's,
and equilibrium temperature — not surface temperature — is the only
temperature exoplanet catalogues provide. This is a property of the available
observations, not a defect in this implementation: no ESI computed from real
exoplanet catalogue data can currently distinguish a temperate rocky world
from a runaway-greenhouse one. Venus is carried through the entire pipeline as
a labelled control specifically so this is visible in the results rather than
buried in a footnote. See `docs/METHODS.md` §2.

## Roughly half of catalogue masses were never measured

2,975 of 6,354 confirmed planets (47%) carry a mass predicted from the radius
by a mass–radius relation, not a dynamical measurement. Density and escape
velocity computed from such a mass re-encode the radius rather than adding
independent information — which would make the ESI appear to combine four
independent properties while actually being driven by one. This project
classifies mass provenance into an explicit, ordered evidence scale
(`measured` / `msini_deprojected` / `msini_lower_limit` / `upper_limit` /
`inferred_mass_radius` / `missing`) and discounts inferred masses directly in
the observational-confidence score.

## TRAPPIST-1 sits below the habitable-zone model's stated validity floor

The Kopparapu et al. (2013) fit is stated valid for 2600–7200 K. TRAPPIST-1's
host is 2566 K — 34 K below the floor. A strict reading excludes the
most-studied temperate terrestrial system known from every habitable-zone
count. This project reports results both ways: strictly (TRAPPIST-1 planets
carry `hz_conservative = NaN`, "undetermined") and with an explicitly flagged
extrapolation (`hz_conservative_clamped`, `hz_model_extrapolated = True`).
Neither reading is hidden, and Monte Carlo habitable-zone probabilities carry
a `hz_teff_valid_fraction` alongside them so a reader can see how much of the
posterior the model actually covers. That fraction is also multiplied
directly into `score_conservative_habitability` (`earth2.ranking.scores`),
so the composite ranking cannot read a conditional probability computed from
a small minority of valid draws as if it were a confident, unconditional one
-- an earlier version of the ranking exposed `hz_teff_valid_fraction` only as
metadata without this discount, which let TRAPPIST-1 e/f/g rank in the top
three despite roughly 90% of their Monte Carlo posterior falling outside the
model's domain. With the discount applied, TRAPPIST-1's planets no longer
lead the ranking (see the "Top candidates" table in `README.md`).

## An Earth twin's atmospheric signal is on the order of 1 ppm

For a real nitrogen–oxygen atmosphere (mean molecular weight ≈29 amu) around a
Sun-like star, the transmission-spectroscopy amplitude is roughly an order of
magnitude smaller than for a hydrogen-dominated atmosphere of the same scale
height, and well below demonstrated JWST precision (tens of ppm at best).
Finding an Earth analogue and characterising its atmosphere are separated by a
generation of instruments; nothing in this project implies otherwise.

## Not established by this project, for any planet, under any circumstance

- Confirmed habitability
- Evidence for life
- A probability of biology
- Detection of any biosignature gas

No metric in this project computes any of the above. There is no calibrated
likelihood function for biology on exoplanets — one confirmed inhabited world,
no confirmed uninhabited control with a directly comparable atmosphere, and an
incomplete theory of abiotic false positives for the candidate biosignature
gases. See `docs/RESEARCH_NOTES.md` for the abiotic-production literature this
project relies on instead of a life-probability score.

## Discovery-method bias

The catalogue's discovery-method distribution reflects instrument sensitivity,
not the true underlying exoplanet population. Transit surveys favour short
orbital periods and large planet-to-star radius ratios; radial-velocity
surveys favour massive, close-in planets around bright, quiet stars; direct
imaging favours young, wide-separation giant planets. A temperate Earth-mass
planet around a Sun-like star is disfavoured by every major detection method
simultaneously (transit probability low, RV amplitude ≈9 cm/s, angular
separation too small for imaging). The preponderance of small-star candidates
at the top of this ranking is partly a statement about M dwarfs being easier
to search, not solely a statement about where temperate rocky planets exist.

## Coverage gaps not integrated in this release

Gaia DR3 is cross-matched by exact `source_id` for every host the archive
itself links to one, as an independent distance check — not a full
astrometric re-reduction of the catalogue. The ESO Science Archive was
investigated but is not built into this pipeline (see `docs/DATA_SOURCES.md`
for the reasoning). Transit and radial-velocity deep-dive analyses depend on
public data existing at MAST and DACE respectively; most catalogue planets
have neither, and every deep-dive page reports that as an explicit
`"attempted": false` state rather than omitting the section.

## Model and fit caveats

- Transit-fit depths from this pipeline's own trapezoid model run 5–25% below
  published values (a known Savitzky–Golay detrending systematic, measured
  against four bright benchmark planets) and are never substituted for
  catalogue values.
- Radial-velocity semi-amplitude fits are gated by a three-criterion
  reliability check (point count, amplitude significance, residual-to-
  amplitude ratio); a mass is withheld entirely, not merely flagged, when a
  fit fails it. This gate exists because an earlier, ungated version of this
  fitter returned an apparent 10–41 Earth-mass "planet" for TRAPPIST-1's
  ~1-Earth-mass planets from 33 noisy radial-velocity points.
- Habitable-zone membership drawn from the Monte Carlo posterior is
  conditional on the draw's temperature falling inside the model's validity
  range; the fraction of draws that do (`hz_teff_valid_fraction`) is reported
  alongside the resulting probability so the conditioning is never invisible.
- A high Earth Similarity Index alongside low observational confidence must
  never be read the same as a high index with high confidence — the two are
  reported as separate axes for exactly this reason, and the composite index
  is non-compensatory between them.

## Scope decisions, stated as decisions

This project targets a genuinely large, genuinely provenance-tracked dataset
(164,209 source records across 12 NASA Exoplanet Archive tables plus a Gaia
DR3 exact-identifier crossmatch) rather than exhaustively integrating every
archive that could plausibly be relevant. Where a source was considered and
not integrated, that decision and its reasoning are recorded in
`docs/DATA_SOURCES.md` rather than left unexplained.
