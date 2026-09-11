# Observed catalogue versus intrinsic population

Status: **Phase 5 interpretive release**. This product explains the already
released Kepler DR25 occurrence posterior. It does not introduce a new fitted
rate or change the Phase 4 likelihood.

## The evidence funnel

| Stage | Value | Evidence label |
|---|---:|---|
| Selected GK dwarfs searched | 114,105 | OBSERVED |
| KOIs in 50–500 days and 0.5–2 Earth radii | 89 | OBSERVED |
| Mean latent valid candidates | 53.97 | MODEL-INFERRED |
| Median shape-weighted exposure | 78.28 effective stars | MODEL-INFERRED |
| Intrinsic fixed-box occurrence | 0.692 planets per selected star | MODEL-INFERRED |

The last value has a 0.267–1.918 95% interval. The raw catalogue fraction and
the reliability-adjusted visible fraction are retained only to explain scale;
neither is used as an occurrence estimator. The posterior integrates the
target-specific selection function over the fitted period-radius population.

## Earth-pivot visibility

At 365.25 days and one Earth radius, interpolation of the released surface gives
a mean total selection probability of `1.9788e-5`, or about one selected signal
per 50,535 searched stars. The corresponding effective exposure is 2.258 stars
from the fixed 114,105-star search sample.

The separately displayed transit geometry, phase-window, pipeline and vetting
averages are diagnostics. The pipeline response already includes the observing
window, and averages of dependent terms must not be multiplied together.

## Website update contract

`scripts/build_observed_intrinsic_story.py` reads the occurrence posterior,
selection surface and candidate reliability product, then writes the research
JSON and figure. It copies the browser payload and PNG into `web/public` and
writes a SHA-256 manifest covering both research and web artifacts.

The static site always ships a verified bundled snapshot. When a reader opens
the occurrence chapter, the client requests the newest `occurrence.json` from
the repository's `main` branch with browser caching disabled. A newer snapshot
is accepted only when its schema, mixed evidence label and posterior source hash
are present. If the network request fails, the page keeps the bundled release.

## Claim boundary

This is a conditional fixed period-radius occurrence result for the selected
Kepler GK-dwarf sample. It is not a probability of habitability or biology, and
it is not a star-dependent habitable-zone eta-Earth estimate.

![Observed catalogue, selection surface and inferred population](../results/population/dr25_observed_vs_intrinsic.png)
