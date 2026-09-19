# Changelog

## 2.1.2 — 2026-09-19

- Separated scheduled candidate-data validation from frozen-release validation:
  live archive refreshes now run 293 non-frozen tests after rebuilding every
  scientific layer, while exact publication counts remain gated in normal CI.
- Stopped scheduled refreshes from replacing the hand-curated v2 README with
  the legacy report generator before opening a reviewable data pull request.

## 2.1.1 — 2026-09-19

- Fixed clean-checkout DR25 refreshes by rehydrating ignored raw inputs only
  after their source, byte length, SHA-256 digest and parsed row count match the
  committed manifest.
- Kept raw-only partial caches fail-closed and added regression coverage for
  catalogue hydration, support-product hydration and upstream drift rejection.

## 2.1.0 — 2026-09-19

- Added covariance-aware Gaussian information transfer and analytic break-even
  correlation calculations with unit and release-contract tests.
- Published an objective-conditioned planet-radius decision audit across 13
  eligible candidates; none of the indirect stellar-radius actions wins at
  `|rho| <= 0.90` despite 10 larger own-parameter scalar scores.
- Added deterministic PNG/SVG research outputs, clean-checkout rebuilding,
  public observatory evidence, documentation, and release-bundle integration.

## 2.0.0 — 2026-09-12

- Connected the observed Kepler DR25 catalogue to a validated, conditional
  selection-corrected occurrence posterior.
- Added evidence graph, reliability, selection, synthetic recovery, composition,
  continuous-HZ, XUV/escape, atmosphere, HWO, mission, information-gain,
  robustness, and Solar-System falsification products.
- Rebuilt the website as an interactive evidence observatory with freshness
  checks, accessible responsive layouts, and an author research journal.
- Added a generated v2 manuscript and deterministic, redistributable data bundle.

## 1.0.1 — 2026-08-24

- Published the reproducible catalogue, uncertainty propagation, candidate
  ranking, archive provenance, deep dives, figures, website, and v1 manuscript.
