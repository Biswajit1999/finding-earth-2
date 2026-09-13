# Atmospheric spectrum screen for Earth 2.0 candidates

The project now cross-matches its strict small-and-temperate sample against the
ingested index of published atmospheric reductions and the tabulated wavelength
measurements. The selection is fixed before the cross-match: confirmed planet,
nominally inside the conservative Kopparapu habitable zone, and radius below
1.6 Earth radii.

## Result

The catalogue contains 6,354 confirmed planets and 15 that pass this strict
size-and-insolation screen. None of those 15 has an indexed atmospheric
reduction or a tabulated wavelength measurement in the currently ingested
archives. This is a useful negative coverage result: the ranking identifies
plausible targets, while the spectrum audit shows that atmospheric evidence is
still missing for the exact target class the project seeks.

The comparison panel includes the closest-ranked planets below 1.6 Earth radii
that do have spectral measurements. Every comparison object is outside the
strict selection, usually because its nominal irradiation is outside the
conservative habitable zone or the stellar-temperature model is out of range.
They demonstrate what the evidence format looks like; they are not substitute
Earth analogues.

## Outputs

- `results/atmosphere/earth_analogue_spectrum_screen.json` records the counts,
  comparison set, next observation and claim boundary.
- `results/atmosphere/earth_analogue_spectrum_candidates.csv` lists all 15
  strict candidates and their spectrum-coverage status.
- `results/atmosphere/earth_analogue_spectrum_screen.png` visualises the
  coverage funnel and comparison set.

## Claim boundary

This analysis measures published spectral coverage. A spectrum can constrain
atmospheric models only after reduction, calibration, instrument systematics
and stellar contamination are addressed. The cross-match does not detect an
atmosphere, identify a molecule, establish habitability, or provide evidence of
life. Its immediate scientific recommendation is to obtain calibrated,
target-specific spectra for the strict candidate set and preserve independent
reductions rather than averaging away disagreement.
