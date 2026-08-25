# Research notes

A compact evidence ledger of findings from the research pass and from building
this pipeline against real data — kept because several of them changed the
implementation, and because "we checked and it mattered" is worth recording
alongside the code that resulted from it.

## Habitable-zone coefficients: the erratum trap

Kopparapu et al. (2013), ApJ 765, 131, was corrected by an erratum (ApJ 770,
82, June 2013) with updated Table 3 coefficients. The arXiv v1 preprint — the
copy most easily found by search, and the one ar5iv/Semantic Scholar mirrors
serve — carries **only the original, superseded table**. The version of
record on IOPscience contains both. Runaway-greenhouse S_eff for a Sun-like
star moves from 1.0512 (original) to 1.0385 (erratum), a ~1.2% shift that
moves the inner conservative habitable-zone edge and changes which planets
qualify. Verified by extracting both tables directly from the publisher PDF
(`fitz`/PyMuPDF text extraction) rather than trusting a secondary source.
**Action:** `COEFFS_ERRATUM_2013` is the default in
`earth2/habitability/hz.py`; `COEFFS_ORIGINAL_2013` is retained so the
correction's effect is measurable, not silently applied.

## Mass provenance: 47% of catalogue masses are not measurements

`pscomppars.pl_bmassprov` reveals that "mass" in the composite table means
four different things: a genuinely measured dynamical mass (35%), a
radial-velocity minimum mass M sin i (14%), a value predicted from the radius
via a mass–radius relation (47%), or an upper limit (3%). Using an M–R-relation
mass to compute density or escape velocity re-encodes the radius rather than
adding independent information — a fact invisible if `pl_bmasse` is treated as
a single homogeneous column, which most casual use of this archive does.
**Action:** `classify_mass_provenance()` resolves every planet into one of six
evidence classes, discounted explicitly in the observational-confidence score.

## The Earth Similarity Index cannot distinguish Earth from Venus

Running Venus through the ESI pipeline as a labelled control (rather than
only running it on exoplanets, where the comparison is invisible) surfaced
that Venus scores 0.92 — near-Earth-similar — because its high Bond albedo
gives it an equilibrium temperature *cooler* than Earth's, and equilibrium
temperature is the only temperature exoplanet catalogues can supply. The
Planetary Habitability Laboratory's oft-quoted Venus ESI (~0.44) uses surface
temperature, which does not exist as observational data for any exoplanet.
**Action:** documented as a structural limitation of the metric itself (not
of this implementation) in the module docstring, in `docs/LIMITATIONS.md`,
and on the website's home page, rather than only in a caveat a reader might
skip.

## ESI exponent bug: an extra square root at the tier-combining step

`esi_global()` forms `ESI_interior`/`ESI_surface` from two components that
each already carry exponent `w/2` (from `esi_component(..., n=2)`), then
combines the two tiers with one more `sqrt`. An earlier version took a
*second* `sqrt` when forming each tier -- `sqrt(esi_r * esi_d)` instead of
the plain product `esi_r * esi_d` -- compounding to `F_i^(w_i/8)` overall
instead of the published `F_i^(w_i/4)`. Both the buggy and correct formulae
give Earth = 1.0 exactly (every `F_i = 1`, and `1^anything = 1`), which is
why the one exact-value regression test in the original suite could not
catch it; the two other ESI tests were loose bounds (Venus > 0.9, Jupiter
< 0.6) that both formulae equally satisfy, since compressing values toward
1.0 moves Venus further above 0.9 and Jupiter's score is low enough under
either exponent to stay below 0.6. Caught by an external repository audit
that re-derived the exponent algebraically from the source; independently
confirmed here by evaluating both formulae on Venus's canonical parameters
(buggy: 0.960, corrected: 0.920) and cross-checking the corrected vectorised
implementation against a flat, independently coded evaluation of the
four-variable formula. **Action:** removed the extra `sqrt`; added
`test_esi_global_matches_independent_flat_formula_for_venus` and
`..._for_random_planets` (200 draws) to `tests/test_habitability_esi.py`, so
a reappearance of this exponent class of bug fails on an exact numerical
mismatch rather than a loose bound both the buggy and correct forms satisfy.
Every downstream artefact (`results/`, `paper/`, the website export) was
regenerated after the fix; see the version-1.0.1 commit for the full diff.

## TRAPPIST-1's host sits below the habitable-zone model's validity floor

TRAPPIST-1 (2566 K) is 34 K below Kopparapu's stated 2600 K floor — a fact
easy to miss because the model still *returns a number* when evaluated there;
it does not raise an error. Discovered while spot-checking why the
most-studied temperate terrestrial system in the literature was producing
`hz_conservative = NaN` in an early pipeline run. **Action:** the pipeline
carries two parallel evaluations (strict, NaN outside range; clamped, flagged
`hz_model_extrapolated`) rather than picking one silently.

**Follow-up:** this discovery initially fixed the *reporting* (the strict/
clamped split, `hz_teff_valid_fraction`) but not the *ranking* -- the
composite score kept using `hz_conservative_prob`, the Monte Carlo mean
conditional on the valid draws, without discounting for how few draws were
actually valid. That gap let TRAPPIST-1 e, f and g rank in the top three
despite the model being evaluable on only ~9% of their posterior, and was
caught by an external repository audit rather than by this project's own
tests: nothing in the test suite checked that a low `hz_teff_valid_fraction`
actually pulled the composite score down. Fixed by multiplying
`score_conservative_habitability` by `hz_teff_valid_fraction` directly
(`earth2.ranking.scores`); see `docs/LIMITATIONS.md`.

## Time-system mismatch in transit folding

TESS light curves are distributed in BTJD (BJD − 2457000); Kepler in BKJD
(BJD − 2454833). The archive's `pl_tranmid` is full BJD. Folding a TESS light
curve on an unconverted BJD epoch does not raise an error — the modulo
operation happily returns *a* phase, just the wrong one — producing a
plausible-looking but meaningless folded transit. Caught by validating the
fitted depth against the published depth on TRAPPIST-1 b and finding an
initially unexplained mismatch before tracing it to the epoch. **Action:**
`bjd_to_mission_time()` performs the conversion explicitly, and every transit
fit is checked against the published depth (rejected beyond a factor of 1.6)
before being reported as a measurement.

## An ungated RV amplitude fit fabricated a planet mass

Fitting a fixed-period circular orbit to 33 radial-velocity points of
TRAPPIST-1 (a faint, Tmag 14.9, M8 dwarf) returned K = 18–62 m/s and inferred
M sin i = 10–41 Earth masses for planets known to be roughly one Earth mass.
`curve_fit` will return *a* confident-looking amplitude from data that cannot
support one; nothing about the fit succeeding implies the fit means anything.
**Action:** a three-criterion reliability gate (≥20 points, amplitude
significance ≥3σ, residual scatter <5× the amplitude) must pass before a mass
is reported at all; TRAPPIST-1 f and g passed the significance criterion at
8σ and were caught only by the residual-scatter check, which is why all three
criteria are applied rather than the significance test alone.

## Blind period search finds the wrong period in crowded systems

A blind Box Least Squares search on TRAPPIST-1's 24-day TESS baseline (seven
transiting planets) returns 10.64 days — the period of none of them, almost
certainly a blend of several. **Action:** a published ephemeris always takes
precedence over a blind search result; the blind result is reported alongside
with an explicit agreement flag rather than silently substituted.

## Scale-height naivety overstates observability by ~12×

Computing an Earth twin's transmission signal with the default H/He mean
molecular weight (2.3 amu, appropriate for gas giants) gives ~12 ppm; with a
realistic N₂/O₂ secondary atmosphere (≈29 amu) it is ~1 ppm — an order of
magnitude smaller, and below demonstrated JWST precision. **Action:**
`atmospheric_scale_height_km()` requires the mean molecular weight as an
explicit parameter with no silent default used for terrestrial planets.

## Environment note: a pre-existing dependency conflict

`pyarrow` was installed with a broken DLL in the base environment
(`ImportError: DLL load failed`), unrelated to this project; repairing it
(reinstall to 21.0.0) surfaced a pre-existing, independent conflict — an
unrelated package `pyasassn==0.6.4` pins `pyarrow==4.0.1`. Recorded here
because it was discovered, not introduced, during this work; see the final
project report for the recommended resolution.
