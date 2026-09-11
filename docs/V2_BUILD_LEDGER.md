# V2 build ledger

## Phase 0 — baseline audit, 2026-09-09

- Opened the existing clean checkout, inspected branches, remote and history,
  and fast-forwarded two existing remote changes to `82d5b12`.
- Inventoried every tracked path and SHA-256 in `v1_baseline_inventory.json`.
- Inspected scientific architecture, tests, stored outputs, figures, docs,
  manuscript, manifests, website routes, static-export configuration and CI.
- Ran all 186 Python tests: pass, coverage 49.45%. Ruff lint, mypy and six
  release invariants pass. Recorded 47-file pre-existing formatter debt.
- Website build passed (6,374 pages), type check passed, lint passed with one existing font warning. Sequential export check passed (21 templates / 6,373 HTML files). Twelve NASA raw payload hashes matched.
- No changes to scientific source or generated v1 analysis.
- Next: verify website build, preserve tag and push the baseline checkpoint.


## Phase 1 foundation — evidence and method audit, 2026-09-09

- Phase 0 checkpoint e1da67ac933f522562d9abaf8a85a817ce7349d1 and baseline tag pushed and remotely verified.
- Added typed, validated SQLite evidence graph; dependencies, provenance gaps,
  finite values, labels and cycle checks are explicit. No new dependency.
- Imported 89,073 non-null supported composite records; 58 input reference rows
  lack a usable value or supported mapping and are not quantity nodes. These
  are records, not independent observations. The scope excludes all-publication
  mass solutions and unrecorded uncertainties; documented rather than imputed.
- Added deterministic summary and four mass trace examples. V1 outputs unchanged.
- Added 12 evidence tests, including real adapter-contract behaviour on fixtures.
- Reviewed primary DR25 documents and likelihood/transit equations; wrote the
  literature decision register and explicitly listed unfinished method audits.
- Website unaffected; successful Phase 0 build remains applicable.
- Next: commit and verify this foundation before DR25 source retrieval.

## Phase 2 source-adapter checkpoint — 2026-09-09

- Evidence checkpoint 8a07cbfe822f767de7e0ac9c59adef2ed0c8ece6 pushed and remotely verified.
- Added transit geometry, explicit conditional detection factors and survey
  calibration contracts; reliability is separate from detection.
- Added strict official DR25 parsers, injection/Robovetter/stellar joins,
  injection-conditioned count grids with finite-sample intervals, and a bounded
  retrieval CLI with hash-verified caches and preserved retrieval timestamps.
- Added ten offline scientific and integrity tests; full suite: 208 passed.
- Website and v1 analysis products unaffected. Full source retrieval intentionally
  follows the tested, pushed adapter checkpoint.
- Phase 2 is not complete: per-target calibration, searched denominator and
  reliability must pass before any intrinsic population inference is released.

- Source adapter checkpoint 7287f65f1af530440bbdd40c062971830c223074 pushed
  and remotely verified. Stellar retrieval validated 200,038 original DR25 rows.
- First injection validation stopped on 586 undocumented-in-header code-2
  recoveries. Inspected the payload and primary ephemeris-match definition;
  now preserve and separately count code 2, requiring a matching official TCE.

## Phase 2 official data and diagnostics checkpoint — 2026-09-09

- Recovery audit checkpoint 57a5fbfdb7e8c83dcecfa780332acac2473996ce pushed and verified.
- Validated 200,038 stellar rows, 146,294 INJ1 injections and 45,377 INJ1
  recovered TCEs. Every injection joins a star; every positive recovery joins
  a target-consistent official vetting row. 38,668 pass vetting overall.
- Diagnostic cut selects 114,105 stars, 84,556 injections, 30,012 recoveries
  (359 code-2), and 26,219 vetted PCs. 29,549 selected archive stars lack an
  INJ1 trial; they must not be silently removed from an occurrence denominator.
- Generated count/interval CSV, source-linked JSON and inspected PNG/SVG plots.
  Eleven of 90 grid cells have no trials; these remain undefined, shown grey.
- All 209 tests pass; lint, mypy and original release invariants pass.
  Website inputs unchanged. Raw bytes remain ignored; three manifests retain
  their original retrieval dates and hash checks.
- Next: reproduce the pinned KeplerPORTs per-target model reference, validate
  domain restrictions and then build survey-wide selection. No eta-Earth claim.

## Phase 2 calibration boundary — 2026-09-09

- Added a KeplerPORTs audit documenting the target-specific inputs, release
  dependencies, 670 GB archive boundary, and checks required before any
  per-target selection function is used.
- The empirical INJ1 output remains explicitly SIMULATED. No inverse-detection
  weights or intrinsic occurrence estimate were added.

## Phase 2 pinned KeplerPORTs reference — 2026-09-09

- Pinned the official NASA KeplerPORTs repository at commit
  6770bc14516592f4e502a20d5c67e61d361c050f and hash-gated the six code,
  coefficient and KIC 3429335 example products required by the reference run.
- Added a wrapper that executes external upstream code only after integrity
  checks. Upstream files are not redistributed by this project.
- Found that upstream MES smearing draws 10,000 beta variates without a seed;
  pinned and recorded seed 21037. Two consecutive artifacts matched SHA-256
  4ccfa7ffbaa630ffa48b5213dc7b394b1b6bad11802217d291f76f53b3b98b74.
- Export is labelled MODEL-INFERRED and explicitly limited to a reference-code
  regression grid, not a survey population estimate.

## Frontend story and universe-console hotfix — 2026-09-10

- Reproduced the reported selected-system/discovery-history overlap using HD
  194490 b. The selected system now expands inside the search stack with a
  bounded scroll area; the history controls retain a separate bottom region.
- Added `/perspective`: Biswajit Jana's first-person learning log, evidence-label
  dictionary and author conclusion. Motion uses transform/opacity, remains
  content-complete without JavaScript and respects reduced-motion preference.
- Added an on-open data pulse that checks the newest processed `main` snapshot
  and falls back to the bundled verified artifact. Archive ingestion remains
  validation- and review-gated; the browser does not claim raw rows as results.
- TypeScript and the GitHub Pages production build pass. Export integrity checks
  22 route templates across 6,374 generated HTML files; ESLint has only the
  pre-existing Next.js custom-font warning. Visual QA checked the reported
  system and the complete perspective accessibility tree in the local
  production-equivalent interface.

## Phase 3 synthetic selection recovery — 2026-09-10

- Added a deterministic artificial survey with separately testable transit
  geometry, observing-window, pipeline-recovery and vetting terms.
- Across 300 replicates of 10,000 artificial stars, a selection-aware Poisson
  likelihood recovered the injected 0.7 planets-per-star rate at 0.704830 on
  average: +0.6901% bias, 0.074053 RMSE and 94.67% coverage for nominal 95%
  intervals.
- Negative controls show why the selection definition matters. The raw detected
  fraction is 0.00869767 per star, the geometry-omitted estimate is 0.0128705,
  and two alternative period-radius proposals change mean selection by 72.33%.
- Every output is labelled SIMULATED. No Kepler occurrence or habitability claim
  is made. Assumptions, omissions and the Phase 4 boundary are documented in
  `docs/SYNTHETIC_SELECTION_VALIDATION.md`.
- All 215 Python tests pass. Ruff lint/format checks pass for the new files and
  mypy passes across 53 source files. Two consecutive artifacts have identical
  SHA-256 `a61b68c726efda84b9ca306c9f635e20abe2f563ad5b5324cf9bb20178fc92db`.

## Phase 4 reliability-data and population-contract foundation — 2026-09-10

- Added strict adapters for all four official false-alarm experiments and the
  observed DR25 TCE table. Parsed/header row disagreements are pinned instead
  of rewritten; the twelve SCR2 zero-transit NTL rows remain visible.
- Pinned four known-signal drop lists and the 8,054-row FPP table to immutable
  `DR25-occurrence-public` commit
  `d200f54b6f0df49e0dae530e69983cdce5397bfb`, gated by SHA-256 and Git blob
  SHA-1. The FPP table's 178 missing probabilities and two large period
  mismatches are audited without imputation.
- Applied one explicit stellar and candidate contract: 114,105 selected stars,
  89 eligible candidates in 0.5–2.0 Earth radii and 50–500 days, and 11 in the
  0.75–1.5 Earth radii and 237–500 day Hsu comparison box. All 89 match an
  observed TCE and a finite FPP value.
- Added a 42-cell reliability diagnostic from 11,104 unique cleaned
  inverted/scrambled trials and 4,603 observed TCEs. Evidence labels are
  separate; raw equation posteriors are never clipped. Candidate reliability
  remains missing pending a validated smooth model.
- Added a machine-readable published-estimand registry so Hsu 2019, Bryson 2020
  and Bryson 2021 values cannot be compared outside their stated domains.
- Added a joint constrained smooth model with experiment intercepts. The
  parameterisation guarantees `0 < F_FA < E_FA < 1` and physical reliability
  without clipping. All four leave-one-experiment-out checks and the
  deterministic observed-TCE holdout improve Brier score and log loss over
  constant-rate baselines.
- All 60 generating-family recovery replicates converge; mean reliability RMSE
  is 0.04167 and the 95th-percentile RMSE is 0.07183. Regularization and
  experiment-weight sensitivity are exported separately from coefficient
  intervals.
- Candidate reliability is assigned to 87 of 89 eligible KOIs. Two above MES
  30 are withheld; all 11 published-box candidates are covered. Total
  reliability is explicitly conditional on the fixed delivered FPP value.

## Phase 4 survey-wide selection surface — 2026-09-10

- Built a target-specific signal model from circular transit duration, delivered
  DR25 duty cycle and dataspan, duration-scaled six-hour CDPP, original stellar
  parameters and an INJ1 calibration to official expected MES.
- Constrained both response models to be nondecreasing with MES and the pipeline
  response to be nondecreasing with observing-window probability. The pipeline
  term already includes its window, while conditional vetting and transit
  geometry remain separately inspectable. Reliability is never a detection
  multiplier.
- All five SHA-256 target folds pass. Held-out MES log-RMSE is 0.1526–0.1562;
  pipeline Brier score is 0.0820–0.0838 versus 0.1916–0.1988 for fold-matched
  constant baselines. Every conditional-vetting and combined-probability fold
  also improves both Brier score and log loss.
- Evaluated 357 period-radius cells after integrating five impact-parameter
  nodes for all 114,105 selected stars. This includes 29,549 selected targets
  with no INJ1 trial. Every probability is finite and bounded, total selection
  never exceeds geometry, effective-star exposure factorizes exactly and the
  result is nondecreasing with planet radius.
- The shared 25-cell comparison for pinned KeplerPORTs target KIC 3429335 has
  mean absolute pipeline difference 0.02261 and maximum difference 0.1818,
  within declared regression tolerances. Four alternative regularization fits
  change combined injection probabilities by at most 0.00251.
- Released model, validation, surface, reference-cell comparison, PNG/SVG and a
  SHA-256 product manifest. This completes the selection gate; no occurrence
  rate is claimed before the hierarchical likelihood and joint uncertainty
  propagation pass.

## Phase 4 hierarchical synthetic recovery — 2026-09-11

- Added a normalized separable power law per `d ln P d ln R` and the exact
  inhomogeneous-Poisson likelihood. The integrated rate has a fixed box meaning;
  the analytic power-law normalization is checked against log-space quadrature.
- Added multiple imputation for shared selection coefficients, correlated
  candidate reliability, asymmetric period/radius measurement errors and
  boundary migration. No fractional candidate count is substituted into a
  Poisson likelihood.
- Analytic selection derivatives match finite differences. The three sequential
  covariance blocks remain explicitly independent, and the pipeline window
  coefficient at its non-negative fit boundary is held fixed.
- All 60-replicate scenarios pass their declared gates: flat and power-law
  recovery, an Earth +/-20% box, low completeness, finite-injection uncertainty,
  reliability perturbation and stellar-radius uncertainty. The broken-law
  stress exposes 21.6% bias/50% coverage; a deliberately halved completeness
  surface exposes 99.3% bias/0% coverage.
- Every artifact remains labelled SIMULATED. The real Kepler rate remains
  withheld until the all-target quadrature and sensitivity suite complete.

## Phase 4 conditional fixed-box occurrence — 2026-09-11

- Evaluated 408 log-space quadrature nodes across three estimands for all
  114,105 selected targets and five impact-parameter nodes. The cache is gated
  by selection-model, stellar-source, quadrature-contract and derivative-code
  hashes.
- Propagated shared selection coefficients, correlated candidate reliability,
  external astrophysical FPP, asymmetric period/radius errors and boundary
  migration through 3,000 multiple imputations. Two candidates above MES 30
  are retained through explicit false-alarm-reliability endpoints.
- The broad 50–500 day, 0.5–2 Earth-radius rate is 0.692 planets per selected
  star with a 0.267–1.918 95% interval under the conservative endpoint. The
  alternative high-MES endpoint is 0.677 with a 0.260–1.911 interval.
- Broad-model projections give Gamma_Earth 0.246 per dlnP dlnR, 0.122 in the
  Hsu fixed box and 0.041 in the Earth +/-20% box. These are not star-dependent
  habitable-zone eta Earth values.
- The Hsu projection's 84th percentile is 0.227, within the published planning
  range and below its 0.27 benchmark. The Bryson-box interval overlaps the
  published result, while the median differs; no pooled or identity claim is
  made.
- Posterior-predictive checks pass, slope posteriors avoid numerical boundaries,
  and the all-target quadrature agrees with an independent released-surface
  integration to 0.64% across the slope grid. Radius uncertainty, reliability
  and the 3x3 piecewise population remain material sensitivities.

## Phase 5 observed versus intrinsic interpretation — 2026-09-11

- Added a deterministic narrative product joining the released candidate
  reliability, all-target selection surface and conditional occurrence
  posterior without recomputing or relabelling any science result.
- The evidence funnel keeps 114,105 searched stars and 89 catalogue candidates
  OBSERVED, while the 53.97 mean latent valid candidates, 78.28 median
  shape-weighted effective stars and 0.692 fixed-box rate remain MODEL-INFERRED.
- Evaluated the released selection surface at 365.25 days and one Earth radius.
  Mean total selection is 0.001979%, equivalent to about one selected signal per
  50,535 searched stars; component averages are diagnostics and are not
  multiplied as independent factors.
- Released JSON, PNG and deterministic SVG artifacts under a SHA-256 product
  manifest. The web JSON and figure are pipeline-copied release products, and
  the invariant checker verifies their hashes and byte identity.
- Added the story-first `/occurrence` chapter, homepage entry point, navigation,
  sitemap and author-perspective link. The client checks the newest committed
  GitHub `main` payload on each open, validates its schema and evidence label,
  and falls back to the bundled verified artifact when offline.
- The page states the scientific boundary in the main reading path: this is a
  fixed period-radius occurrence result, not habitability, biology or a
  star-dependent habitable-zone eta-Earth estimate.

## Phase 6 probabilistic composition — 2026-09-12

- Retained the v1 Rogers radius logistic as a named radius-only population
  baseline and added two-dimensional inference from independently measured mass
  and radius. Predicted mass, minimum mass and upper-limit classes are rejected
  by the composition evidence gate.
- Implemented the Zeng, Sasselov & Jacobsen two-layer iron-silicate envelope in
  its published 1–8 Earth-mass, CMF=0–0.4 domain. Outputs separate probability
  of requiring volatiles, consistency with the terrestrial family and draws too
  dense for that restricted family; no precise core fraction is inferred.
- Implemented an equal-prior Otegi rocky/volatile-rich relation comparison with
  a declared 0.20-dex model-scatter floor and 0.10/0.30-dex sensitivities. The
  Wolfgang relation remains a radius-to-mass prediction reference explicitly
  marked as non-dynamical.
- Propagated asymmetric errors through 4,000 deterministic draws per planet and
  added a correlation input contract. Current catalogue covariances are absent,
  so every affected record explicitly reports the zero-correlation assumption.
- Evaluated 3,852 planets in the 0.5–4 Earth-radius domain. There are 679
  independent measured masses, 352 Zeng-supported records and 609
  Otegi-supported records. Among three-model records, the median rocky-
  probability span is 0.251 and the 90th percentile is 0.485.
- The Earth control lies inside the restricted Zeng terrestrial envelope. Six
  focused tests and release invariants protect model equations, domains,
  covariance propagation, probability bounds, source-class separation and
  product hashes. Consecutive CSV/JSON/PNG/SVG builds are byte-identical.
