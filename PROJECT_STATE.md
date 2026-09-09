# Finding Earth 2.0 project state

- Current phase: **1 — evidence index and selection-method literature checkpoint**; v2 is not complete.
- Baseline commit: `82d5b127418e32d2cacc95c6ed12dc8dad140bac`.
- Existing capabilities: catalogue ingestion, exact Gaia DR3 crossmatch,
  measurement references, Kopparapu HZ, legacy ESI, Monte Carlo uncertainty,
  separate ranking axes, transit/RV deep dives, spectra, static research site.
- Stored dataset count: 13 retrievals / 164,209 rows; 6,354 confirmed planets
  across 4,764 hosts; five Solar-System controls are separate.
- Stored candidate counts: 174 nominal conservative HZ; 15 also below
  1.6 Earth radii; one classified as measured mass by v1, pending evidence audit.
- Tests: 198 passed (baseline plus 12 evidence tests); Ruff lint, mypy and release invariants pass.
- Formatting: 47 pre-existing files differ from Ruff format; avoid a bulk rewrite.
- Website: production build (6,374 pages), lint and type check passed; static export integrity passed.
- Known limitations and scientific assumptions: see
  [baseline audit](docs/V2_BASELINE_AUDIT.md). No intrinsic-population result or
  calibrated habitability probability exists.
- Completed v2 milestones: Phase 0 audit/tag/remote checkpoint; additive evidence graph, 89,073 indexed records and deterministic examples; primary selection-method audit. Broader literature and complete per-publication evidence enrichment remain open.
- Last successful commit: `e1da67ac933f522562d9abaf8a85a817ce7349d1` (baseline checkpoint).
- Last verified remote: `e1da67ac933f522562d9abaf8a85a817ce7349d1`, `origin/main`, and the baseline tag verified 2026-09-09 by ls-remote.
- Exact next action: checkpoint this evidence/literature foundation, verify the push, then implement and fetch official DR25 INJ1 recovery and target-star products.

## Execution contract

Preserve v1. Work in this repository with the authenticated author unchanged.
After each coherent milestone: tests, lint/format, affected website checks,
deterministic outputs, inspection, state/ledger update, commit, push, remote
verification. Checkpoint before bulk archive requests or expensive computation.
Never report a simulated recovery experiment as an astronomical measurement.

## Remaining ordered phases

1. Literature and evidence architecture.
2. Kepler DR25 completeness integration.
3. Synthetic selection-function validation.
4. Population inference and published-study comparison.
5. Observed versus intrinsic interpretation.
6. Composition evidence ensemble.
7. Stellar evolution and climate-model sensitivity.
8. XUV environments and atmospheric-escape scenarios.
9. Modern atmospheric spectra and reduction provenance.
10. Full HWO preliminary catalogue and imaging posterior.
11. Mission-specific observatory.
12. Expected information gain.
13. Solar-System falsification and robustness.
14. Research website upgrade, preserving existing useful pages.
15. Generated manuscript and frozen data release.
16. Scientific release audit against all requested gates.

Only after the core passes its release gates: Beyond Earth 2.0 (data universe,
extragalactic feasibility, relativistic travel, communication delays,
technosignature evidence and a clearly separated author-perspective page).

Windows reproduction commands use `python.exe`, `git.exe` and `npm.cmd`.
Repository: `C:\Users\biswa\Documents\GitHub\finding-earth-2`.
