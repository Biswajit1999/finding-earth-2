# Finding Earth 2.0 project state

- Current phase: **100% complete for the declared v2.1, Beyond Earth 2.0 and
  LinkedIn media scope**. The public site, source repository and v2.1.2 GitHub
  Release are published; DOI minting remains an optional external archive action.
- Baseline commit: `82d5b127418e32d2cacc95c6ed12dc8dad140bac`.
- Existing capabilities: catalogue ingestion, exact Gaia DR3 crossmatch,
  measurement references, Kopparapu HZ, legacy ESI, Monte Carlo uncertainty,
  separate ranking axes, transit/RV deep dives, spectra, static research site.
- Stored dataset count: 13 retrievals / 164,209 rows; 6,354 confirmed planets
  across 4,764 hosts; five Solar-System controls are separate.
- Stored candidate counts: 174 nominal conservative HZ; 15 also below
  1.6 Earth radii; one classified as measured mass by v1, pending evidence audit.
- Tests: 292 passed; Ruff passes across source, tests, notebooks and scripts,
  and mypy passes across the source package. DR25
  contracts cover delivered row discrepancies, support-file integrity,
  target-isolated selection validation and the KeplerPORTs reference.
- Formatting: 47 pre-existing files differ from Ruff format; avoid a bulk rewrite.
- Website: production build (6,387 HTML files), lint and type check passed;
  static export integrity passed across 35 route templates. Browser QA reports
  zero console overlap and zero horizontal overflow at 1365x773 and 390x844.
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
- Last successful and remotely verified pre-Phase-11 commit:
  `0d140076f5882ad653a45a960e794c27c41a9424` (HWO precursor atlas and
  direct-imaging physics), authored as Biswajit Jana. Resolve this document's
  containing checkpoint with `git log -1 -- PROJECT_STATE.md`.
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
- Probabilistic bulk composition: 3,852 planets have radii inside the declared
  0.5–4 Earth-radius domain; 679 have an accepted independent measured mass.
  Rogers radius-only, Zeng iron-silicate and Otegi rocky/volatile views remain
  separate. Of these, 352 meet the Zeng support gate and 609 the Otegi gate.
  The median three-model rocky-probability span is 0.251 and its 90th percentile
  is 0.485. Mass-radius predictions, M sin i and upper limits never enter the
  two-dimensional composition inference.
- Phase 7 foundation: the official 221,507,784-byte MIST v1.2 basic-isochrone
  archive is pinned at SHA-256 `bb3f4274...0a92c8`, remains uncommitted raw
  input, and produces 22,266 committed phase-0 grid cells spanning 15
  metallicities, 0.5–1.5 solar masses and log-age 8.0–10.15 where main-sequence
  support exists. The catalogue contains 1,947 systems with age, mass,
  metallicity, luminosity, orbit and all corresponding uncertainty fields.
- Phase 7 inference: 815 of 6,354 confirmed planets pass the age-precision and
  complete-track gates. Each uses 256 deterministic posterior draws, an
  exactly present-luminosity-anchored MIST history, time-integrated `tau_HZ`
  and `f_CHZ`, and three separate Kopparapu boundary prescriptions. Unsupported
  systems remain `undetermined`; the result is not evidence of surface liquid
  water, habitability or life.
- Phase 8 environment: the 60 highest-ranked terrestrial-size candidates now
  carry separate bolometric and XUV diagnostics; 46 support bounded activity
  histories, 43 support 27-case energy-limited escape ensembles, and nine rows
  across Proxima Centauri, GJ 667 C and TRAPPIST-1 use exact-host pinned MAST
  MUSCLES SEDs. Stitched/reconstructed spectral evidence and all scenario
  assumptions remain explicit.
- Phase 9 atmosphere evidence: 54 of the leading 60 terrestrial-size targets
  support four clear, isothermal scale-height scenarios spanning H/He, water,
  Earth-like N2/O2 and CO2. The H/He signal is 12.596 times the Earth-like-air
  signal at fixed temperature and gravity. Separately, 1,826 archive spectrum
  reductions and 8,309 measurements retain stable reduction identities,
  references, instruments and source rows; 557 overlap diagnostics expose
  disagreement without pooling reductions or claiming a retrieval.
- Phase 10 HWO atlas: the hash-pinned HPIC v1.1 provides 12,944 stars and all
  129 published columns; TSS25 remains a separate exact-identity priority
  membership with 164 tier-1 and 495 tier-2 stars. EEID geometry is available
  for 12,682 stars and Kopparapu HZ geometry for 12,405. Three generic analytic
  coronagraph trade cases propagate 512 draws per supported star. Separately,
  744 known planets across 464 HPIC hosts are matched, 694 support imaging
  forecasts, and 406 M sin i planets retain their minimum mass while exposing
  an inclination-conditioned true-mass scenario.
- Phase 11 mission observatory: six independent profiles now state what JWST,
  HWO, ELT/ANDES, PLATO, Gaia and Roman measure, cannot establish, their
  wavelength/resolution concepts, current data and observation/forecast
  boundary. Fourteen evidence records retain dated official sources. Future
  release adapters refuse to label Gaia DR4 or pre-release ANDES, PLATO, HWO
  and Roman science data as observations. No combined mission ranking exists.
- Phase 12 information gain: the exact scalar linear-Gaussian expected-KL
  solution now evaluates 150 synthetic target-action combinations for the 25
  leading candidates. Eighty-three rows have adequate two-sided catalogue
  uncertainties across six named precision requirements. Cost remains separate.
  Ephemeris, XUV, atmosphere, albedo, transmission-spectrum and HWO-detection
  actions are withheld until defensible joint posteriors or instrument likelihoods
  exist; no generic instrument precision is fabricated.
- Phase 12.1 objective audit: a tested bivariate-Gaussian transfer calculation
  fixes the utility to planet-radius uncertainty and scans `|rho| = 0...1`.
  Thirteen candidates support both radius actions. Scalar stellar-radius EIG is
  larger for 10, but the indirect route wins for zero at `|rho| <= 0.90`.
  Kepler-296 f transfers 1.19 bits at the ceiling and needs `|rho| = 0.9952` to
  break even. Correlations remain SENSITIVITY coordinates, not measurements.
- Phase 13 falsification and robustness: Earth, Venus, Mars, Mercury and Jupiter
  remain unranked controls. Venus retains ESI 0.874 despite a hostile surface,
  falsifying any habitability reading of similarity; Mars shows that HZ membership
  is not climate. Twenty-five candidate rows expose HZ, composition, HWO and
  atmosphere model ranges plus rank spans across five legacy-weight menus.
- Phase 14 website: the Exoearth Evidence Observatory adds eleven requested
  routes for population, selection, climate, stellar environment, atmospheres,
  HWO, missions, information gain, model sensitivity, falsification and the
  evidence graph. The home page, research dictionary and author conclusion form
  one evidence-led story. A deterministic 1.1 MB browser payload hashes 18
  scientific inputs; a daily GitHub workflow rebuilds data while the browser
  checks the latest committed release on open. The Universe HUD now reserves
  separate control/history rows and passes automated overlap regression checks.
- Phase 15 publication package: the v2 manuscript has all 19 requested core
  sections and six technical appendices. Thirty-two headline values are
  generated from machine-readable products. The derived-only data release holds
  65 checksum-controlled files and produces a deterministic 3.54 MB Zenodo-ready
  ZIP; raw provider tables are excluded. Citation, software/data licensing,
  contribution, conduct, roadmap, changelog and scientific issue templates are
  present. Search metadata now exposes canonical, Dataset and ScholarlyArticle
  records. The DOI is explicitly pending rather than invented.
- Phase 16 final audit: all 26 machine-readable scientific gates pass. The final
  status answers all 24 requested release questions; the astronomer summary,
  full test/lint/type/build/export/browser evidence and exact release boundaries
  are recorded. GitHub Discussions, homepage metadata and eight research topics
  are enabled.
- Beyond Earth 2.0: the post-v2 frontier now includes inverse-square flux,
  angular-resolution and photon upper-bound calculations; special-relativistic
  Earth/traveller time; a communication timeline; a disciplined M51 candidate
  case study; a technosignature evidence matrix; scalable data architecture;
  and a prominently separated Biswajit Jana author perspective.
- LinkedIn package: 30.00-second 1350×1080 H.264/yuv420p MP4, inspected six-scene
  contact sheet, matching cover frame, reproducible Playwright capture script and
  ready-to-post caption with website, repository and Beyond links.
- Final author-story upgrade: `/perspective` now turns the future questions into
  a four-horizon animated mission trajectory with a reduced-motion path, responsive
  cards and explicit author/science boundaries. `docs/AUTHOR_VISION_AND_ROADMAP.md`
  records why the project exists, what it built, what it taught and the five-part
  future plan in a shareable report.
- Release engineering: the deterministic bundle now writes canonical LF bytes on
  every operating system, and NumPy array annotations are portable across the
  supported Python 3.10/3.12 CI matrix. The v2.1.2 tag and public GitHub Release
  identify the finished package.

## Execution contract

Preserve v1. Work in this repository with the authenticated author unchanged.
After each coherent milestone: tests, lint/format, affected website checks,
deterministic outputs, inspection, state/ledger update, commit, push, remote
verification. Checkpoint before bulk archive requests or expensive computation.
Never report a simulated recovery experiment as an astronomical measurement.

## Completed ordered phases

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
