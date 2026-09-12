# Atmospheric signal physics and evidence lab

Status: **Phase 9 release**. This chapter separates a target's approximate
observability from published atmospheric measurements and keeps every published
reduction distinct.

## Scale-height scenarios

For the 60 leading non-control planets at or below 2.5 Earth radii, the model
uses

\[
H=\frac{k_B T}{\mu m_H g},\qquad
\Delta\delta\simeq\frac{2N_HR_pH}{R_\star^2}.
\]

Every supported target is evaluated at `mu=2.3` (H/He), 18 (water vapour),
28.97 (Earth-like N2/O2) and 44 (CO2), with five scale heights and the
catalogue equilibrium temperature. These are clear, isothermal scenarios.
Clouds, hazes, refraction, vertical temperature structure and wavelength-
dependent opacity are not modeled. A mass upper limit is not substituted for a
measurement.

At fixed temperature and gravity the signal scales as `1/mu`: the H/He signal
is 12.6 times the Earth-like-air signal. The figure makes that assumption gap
visible rather than describing a terrestrial candidate with a hydrogen-rich
default.

## Reduction-preserving evidence

The evidence product contains all 1,826 NASA Exoplanet Archive spectrum-index
entries and all harmonized transmission and eclipse measurements. Every point
retains planet, wavelength, bandwidth, measurement, uncertainty, unit,
spectrum type, facility, instrument, paper label, ADS bibcode, reference URL,
source table, source row, limit status, archive spectrum path when matched, and
a stable reduction ID.

The current archive tables do not provide program IDs or paper DOIs. These
fields remain explicitly null with a `not_provided` status; the code does not
invent them. ADS bibcodes remain available for later DOI enrichment.

Published reductions are never pooled. When two reductions overlap in
wavelength, a separate diagnostic records the matched-point count, median
absolute depth difference and maximum standardized difference where both
uncertainties exist. This exposes disagreement while leaving both original
series intact. It is not an atmospheric retrieval and does not choose a
preferred reduction.

Expected molecular band locations elsewhere in the project remain annotation
only. No aligned feature becomes a molecular detection or biosignature claim.

## Reproduction

```powershell
python.exe scripts/build_atmosphere_evidence.py
python.exe -m pytest tests/test_spectrum_evidence.py tests/test_spectroscopy.py
python.exe scripts/check_release_invariants.py
```

The CSV/JSON, compressed point table, figure and product hashes are committed
under `results/atmosphere/`.
