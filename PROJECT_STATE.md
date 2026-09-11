# Finding Earth 2.0 project state

- Current phase: **5 complete — observed-versus-intrinsic interpretation released; Phase 6 composition evidence ensemble next**; v2 is not complete.
- Baseline commit: `82d5b127418e32d2cacc95c6ed12dc8dad140bac`.
- Existing capabilities: catalogue ingestion, exact Gaia DR3 crossmatch,
  measurement references, Kopparapu HZ, legacy ESI, Monte Carlo uncertainty,
  separate ranking axes, transit/RV deep dives, spectra, static research site.
- Stored dataset count: 13 retrievals / 164,209 rows; 6,354 confirmed planets
  across 4,764 hosts; five Solar-System controls are separate.
- Stored candidate counts: 174 nominal conservative HZ; 15 also below
  1.6 Earth radii; one classified as measured mass by v1, pending evidence audit.
- Tests: 237 passed; Ruff passes across source, tests and scripts, and mypy
  passes across 59 source files plus the occurrence builder. DR25
  contracts cover delivered row discrepancies, support-file integrity,
  target-isolated selection validation and the KeplerPORTs reference.
- Formatting: 47 pre-existing files differ from Ruff format; avoid a bulk rewrite.
- Website: production build (6,375 HTML files), lint and type check passed;
  static export integrity passed across 23 route templates.
- Known limitations and scientific assumptions: see
  [baseline audit](docs/V2_BASELINE_AUDIT.md). A conditional fixed-box
  intrinsic-population result now exists; no calibrated habitability
  probability exists.
- Completed v2 milestones: Phase 0 audit/tag/remote checkpoint; additive evidence
  graph, 89,073 indexed records and deterministic examples; primary
  selection-method audit; official DR25 diagnostic integration; pinned
  KeplerPORTs reference; deterministic synthetic selection recovery. Broader
  literature and complete per-publication evidence enrichment remain open.
- DR25 source products: 200,038 original stellar rows; 146,294 injections; 45,377 recovered TCE vetting rows. All injections join a star. Diagnostic stellar subset: 114,105 stars / 84,556 injections / 30,012 recoveries / 26,219 vetted PCs. This is an artificial-signal experiment, not an occurrence estimate.
- Last successful and remotely verified commit:
  `08ba60cd34d7168edc89e9f819e28c69748f50ef` (conditional DR25
  occurrence posterior), authored as Biswajit Jana. Resolve this document's containing
  checkpoint with `git log -1 -- PROJECT_STATE.md`.
- KeplerPORTs reference: official NASA repository pinned at `6770bc14516592f4e502a20d5c67e61d361c050f`; six required files hash-gated. The documented KIC 3429335 grid reproduces byte-for-byte with explicit MES-smearing seed 21037. Upstream files remain external.
- Synthetic recovery: 300 replicates of 10,000 artificial stars recover a known
  0.7 planets-per-star rate with +0.69% relative bias and 94.67% coverage for
  nominal 95% intervals. The artifact is labelled SIMULATED and reproducible at
  SHA-256 `a61b68c726efda84b9ca306c9f635e20abe2f563ad5b5324cf9bb20178fc92db`.
- Reliability foundation: all observed/INV/SCR products, known-signal drop lists
  and astrophysical FPP inputs are hash-gated. The fixed contract selects
  114,105 stars and 89 candidates; 11 occupy the Hsu period-radius comparison
  box. The 42-cell diagnostic assigns no candidate reliability and makes no
  intrinsic claim.
- Smooth reliability: a joint physical parameterisation passes four experiment
  holdouts, a 931-row observed-TCE holdout and 60/60 synthetic recovery fits.
  It assigns 87 candidates; two above MES 30 remain withheld. Total reliability
  is conditional on fixed external FPP values.
- Survey-wide selection: 43,350 domain injections calibrate a constrained model
  evaluated over 357 period-radius cells for all 114,105 selected stars,
  including 29,549 without an INJ1 trial. All five target-level folds, physical
  invariants and the pinned KIC 3429335 reference check pass. The committed Git
  blobs match the product SHA-256 manifest.
- Hierarchical synthetic recovery: a normalized period-radius Poisson model and
  multiple-imputation uncertainty bridge pass flat, power-law, Earth-box,
  low-completeness, finite-injection, reliability and stellar-radius scenarios.
  A broken-radius-law stress and a deliberately halved completeness surface
  correctly expose misspecification. Every validation output is SIMULATED.
- Conditional fixed-box occurrence: the 50–500 day, 0.5–2 Earth-radius model
  gives 0.692 planets per selected star (95% interval 0.267–1.918) under the
  conservative high-MES reliability endpoint. Its Hsu-box projection is 0.122
  (84th percentile 0.227), while the Earth +/-20% projection is 0.041. These are
  MODEL-INFERRED population rates, not habitability or life probabilities.
- Observed-versus-intrinsic interpretation: a deterministic research product and
  three-panel figure connect 89 catalogue candidates to about 54 latent valid
  candidates, 78.3 shape-weighted effective stars and the broad 0.692 posterior.
  The Earth pivot exposes a mean total selection probability of 0.00198%, or
  roughly one selected signal per 50,535 searched stars. A new `/occurrence`
  chapter loads the bundled verified payload and checks GitHub `main` for a
  newer committed posterior on open.
- Exact next action: build the Phase 6 composition evidence ensemble without
  turning radius-only mass estimates into independent composition evidence.

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
