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
