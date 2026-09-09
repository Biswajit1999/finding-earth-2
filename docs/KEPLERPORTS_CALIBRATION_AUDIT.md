# KeplerPORTs per-target calibration audit

The pinned NASA/SETI reference file is retained in the local research scratch
area as `tmp/KeplerPORTs.py`; it is not imported into the package or redistributed
as project code. The adapter records its SHA-256 in the DR25 source manifests.
This audit is the boundary between the official artificial-signal counts and a
future survey-wide selection function.

The reference implementation constructs a target-specific pipeline detection
efficiency from the stellar radius, long- and short-timescale CDPP slopes, duty
cycle, and a period-dependent number of transits. It then interpolates the
window function and multiplies the two conditional terms. Its `mstar_from_stellarprops`
helper derives mass from radius and log(g), while `transit_duration` uses that
mass and an eccentricity argument. The reference's defaults and tabulated
coefficients are release-specific; they must not be replaced by a generic MES
logistic curve.

The implementation requires five auxiliary products that are not part of the
small INJ1 tables: the per-target DR25 one-sigma depth and window FITS files,
the MES-smearing/detection-efficiency HDF5 table, and the long/short slope
calibration tables. The archive documents these as the DR25 per-target
detection-contour products and warns that the full metric download is about
670 GB. This project therefore does not request that archive wholesale.

Before calibration can be used for an occurrence model, the following checks
are mandatory:

* pin and hash every coefficient table and the exact reference revision;
* verify FITS star IDs, period grids, units, finite values, monotonic window
  probabilities, and the expected target count;
* reproduce the reference Sun-like example and at least two edge cases;
* quantify the difference between the reference contour and the empirical INJ1
  recovery cells in the same target and signal domain;
* document how the 29,549 selected stars without an INJ1 trial enter the
  searched denominator; and
* keep transit geometry, observing-window probability, pipeline recovery,
  Robovetter classification, and candidate reliability as separate factors.

The current `results/population/dr25_summary.json` is therefore a measured
diagnostic of the INJ1 experiment, labelled `SIMULATED`. It is not a calibrated
per-target map, an inverse-detection-weight estimate, or an intrinsic occurrence
rate. A later occurrence result must state its population domain, target
denominator, interim prior, and treatment of reliability and astrophysical
false positives.

Primary references: NASA Exoplanet Archive completeness documentation,
KSCI-19101-002 (window/depth products), KSCI-19109-002 (flux-level injections),
KSCI-19110-001 (pixel-level injections), KSCI-19111-002 (per-target contours),
and KSCI-19114-002 (Robovetter reliability experiments). See
`docs/LITERATURE_V2.md` for stable URLs and the version audit.
