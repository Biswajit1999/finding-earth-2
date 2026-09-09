# Finding Earth 2.0 project state

- Current phase: **2 — official DR25 experiment integrated; per-target calibration next**; v2 is not complete.
- Baseline commit: `82d5b127418e32d2cacc95c6ed12dc8dad140bac`.
- Existing capabilities: catalogue ingestion, exact Gaia DR3 crossmatch,
  measurement references, Kopparapu HZ, legacy ESI, Monte Carlo uncertainty,
  separate ranking axes, transit/RV deep dives, spectra, static research site.
- Stored dataset count: 13 retrievals / 164,209 rows; 6,354 confirmed planets
  across 4,764 hosts; five Solar-System controls are separate.
- Stored candidate counts: 174 nominal conservative HZ; 15 also below
  1.6 Earth radii; one classified as measured mass by v1, pending evidence audit.
- Tests: 209 passed; Ruff lint, mypy (51 source files), and six v1 release invariants pass. Eleven DR25 contract tests cover the delivered recovery-code discrepancy.
- Formatting: 47 pre-existing files differ from Ruff format; avoid a bulk rewrite.
- Website: production build (6,374 pages), lint and type check passed; static export integrity passed.
- Known limitations and scientific assumptions: see
  [baseline audit](docs/V2_BASELINE_AUDIT.md). No intrinsic-population result or
  calibrated habitability probability exists.
- Completed v2 milestones: Phase 0 audit/tag/remote checkpoint; additive evidence graph, 89,073 indexed records and deterministic examples; primary selection-method audit. Broader literature and complete per-publication evidence enrichment remain open.
- DR25 source products: 200,038 original stellar rows; 146,294 injections; 45,377 recovered TCE vetting rows. All injections join a star. Diagnostic stellar subset: 114,105 stars / 84,556 injections / 30,012 recoveries / 26,219 vetted PCs. This is an artificial-signal experiment, not an occurrence estimate.
- Last successful and remotely verified commit before this checkpoint: `57a5fbfdb7e8c83dcecfa780332acac2473996ce` (recovery-code audit). Resolve this document's containing checkpoint with `git log -1 -- PROJECT_STATE.md`.
- Exact next action: preserve the validated input/diagnostic checkpoint, then reproduce the pinned NASA KeplerPORTs per-target reference calculation, audit its domains, and implement the population calibration. No real intrinsic inference yet.

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
