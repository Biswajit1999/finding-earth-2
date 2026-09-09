# V2 baseline audit

Audit date: 2026-09-09. Scientific author: Biswajit Jana.

## Repository checkpoint

The existing checkout is `finding-earth-2`, remote
`https://github.com/Biswajit1999/finding-earth-2.git`, branch `main`.
The initial clean local commit was `7dcdc609fcbe71ebd893d49cb8eb8d3c637c3112`.
Fetching revealed two existing remote commits; a fast-forward preserved both.
The audited v1 baseline is **82d5b127418e32d2cacc95c6ed12dc8dad140bac**.
No author configuration, scientific source, data output, or website was changed
before this audit. The existing `automated/data-refresh` branch was discovered
and left intact. No applicable AGENTS.md was present in the checkout or its
checked parent directories. The annotated tag `v1-baseline-before-v2` will
preserve this SHA, alongside the baseline checkpoint commit.

## Inventory and architecture

`v1_baseline_inventory.json` records every tracked file, its size and SHA-256,
plus source-payload verification and baseline counts. The repository contains
10,636 lines of Python source across 40 modules, 16 test modules, eight research
notebooks, the manuscript, bibliography, generated figures, and a Next.js static
website. The complete tracked-file inventory was inspected; implementation
inspection focused on ingestion, preprocessing, uncertainty, provenance,
ranking, reporting, tests, CLI, configuration, and workflow contracts.

The scientific path is `sync -> pipeline.run_analysis -> build_catalogue ->
propagate_catalogue -> rank_catalogue -> reporting`. It already separates
minimum masses, radius-inferred masses, upper limits and controls, attaches
per-parameter publication references, compares composite and coherent default
solutions, crossmatches Gaia DR3 identifiers, and produces independent follow-up
diagnostics. Classical HZ calculations use the Kopparapu 2013 erratum, with
explicit validity flags. The legacy ESI and 4,000-draw Monte Carlo remain intact.

`web/app` is a Next.js App Router static export with 6,354 candidate routes,
catalogue/atlas/ranking/compare pages, transit/RV/spectral labs, follow-up,
Galaxy and Universe views, references, methods and limitations. Scientific JSON
is read from `web/public/data`; builds do not query archives. There are 118
committed JSON products. There is no `.openai/hosting.json`; the deployment
target is the existing GitHub Pages site. Preserve this architecture.

CI has Python 3.10/3.12 tests, Ruff, mypy, release invariants, JSON contracts,
notebook execution and frontend checks. Deployment builds with
`BASE_PATH=/finding-earth-2`. A separate scheduled data-refresh workflow makes
archive-dependent updates through a pull request. No bulk data belongs in CI.

## Verified stored scientific result

The last stored analysis timestamp is `2026-08-28T20:00:42Z`, version 1.0.1.
These are stored v1 results, not a fresh archive census or intrinsic occurrence.

| Quantity | Stored value |
|---|---:|
| Source records, 13 retrievals | 164,209 |
| Confirmed planets | 6,354 |
| Host systems | 4,764 |
| Solar-System controls (excluded from planet count) | 5 |
| Nominal conservative HZ | 174 |
| Conservative HZ and radius below 1.6 Earth radii | 15 |
| Of those, classified as measured mass by v1 | 1 |
| Provenance links | 89,131 |
| Distinct source references counted as publications | 1,814 |
| Kepler KOI / TCE rows | 8,054 / 34,032 |
| Direct-imaging precursor stars | 164 |

The ranking table has 6,359 rows and 121 columns including controls. The evidence
matrix was inspected visually. Its mass-quality values are ranking diagnostics,
not calibrated measurement probabilities. The 164-star table is not the full
HWO Preliminary Input Catalog. The source-record sum includes related tables
and repeated entities; it is not a count of independent observations.

## Checks

| Command | Result |
|---|---|
| `python.exe -m pytest tests/ --cov=earth2 --cov-report=term --cov-fail-under=40` | 186 passed; 49.45% coverage; Python 3.9.19 |
| `python.exe -m ruff check src/ tests/ notebooks/` | Passed |
| `python.exe -m mypy src/earth2` | Passed, 40 source files |
| `python.exe scripts/check_release_invariants.py` | All six invariants passed |
| `python.exe -m ruff format --check src/ tests/` | Existing formatting debt: 47 files would change, 9 already formatted |
| `npm.cmd run lint` | Passed with one existing custom-font warning |
| `npm.cmd run typecheck` | Passed |
| `BASE_PATH=/finding-earth-2 npm.cmd run build` | Passed; 6,374 static pages |
| `BASE_PATH=/finding-earth-2 npm.cmd run check:export` | Passed; 21 templates / 6,373 HTML files |

On this Windows host use `git.exe` and `python.exe`: extensionless commands
resolve to unrelated System32 launchers. No global PATH or Git identity was
changed. No dependency migration was needed.

## Scientific and reproducibility limitations to carry forward

1. There is no surveyed-star denominator, DR25 injection-recovery integration,
   vetting model, or occurrence likelihood. A confirmed multi-survey catalogue
   cannot supply those by itself.
2. The v1 fallback in `classify_mass_provenance` treats an unrecognised mass
   provenance as measured. A v2 evidence import must retain an unknown state;
   publication-level mass semantics, including GJ 1061 d, need independent audit.
3. Archive-calculated radii exist. The 15-object cut is a cut on catalogue
   radii, not necessarily on independent measured radii. Mass and radius must
   be audited symmetrically before composition inference.
4. Legacy rocky logistic and weighted scores are heuristic diagnostics, not
   probabilities of habitability. Some public terminology needs revision.
5. Monte Carlo assumes independent inputs and fills unavailable uncertainties
   with delta distributions. It is uncertainty propagation, not a population
   posterior. HZ probabilities are conditional on model-valid draws.
6. The spectroscopy snapshot depends on retired aggregate tables alongside a
   spectrum-file index. Separate reductions need a modern data contract.
7. Manifests identify living archive responses but cannot restore vanished
   versions. Local raw caches are present, but raw payloads are not in Git.
   The manifest code/doc comments overstate reconstruction and re-date cache
   reads; preserve original retrieval metadata in new adapters.
8. The licence contains the MIT text plus a data-use appendix. Move that
   appendix to DATA_LICENSES.md in a later infrastructure milestone, preserving
   attribution. Do not assume third-party data use is covered by MIT.
9. Existing README and methods round Venus ESI differently; figures and all
   future numerical prose should use generated values.
10. A code-test pass does not establish scientific correctness, current archive
    validity, or publication readiness. Full v2 release gates remain open.

## Immediate extension points

Add `earth2.evidence` beside the existing provenance modules and a separate
`earth2.population` package, using the existing CLI and manifest conventions.
Start with official DR25 on-target injected-event recovery, surveyed targets,
strict identifiers, bounded selection probabilities and synthetic validation.
Keep reliability separate from detection efficiency; do not multiply purity
into a detection probability. Match every experiment to its own target sample
and catalogue version. Do not interpret real-data occurrence until recovery
and prior/completeness sensitivity checks pass.

All twelve cached NASA payloads match the recorded uncompressed SHA-256. Gaia is cached in chunks and was not verified against a single combined raw response. An export check accidentally started during the build encountered a transient missing path; the sequential check after build completion passed.
