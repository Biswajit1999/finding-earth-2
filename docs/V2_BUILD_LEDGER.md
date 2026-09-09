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
