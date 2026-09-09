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
