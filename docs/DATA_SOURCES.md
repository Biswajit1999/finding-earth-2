# Data sources

This document is the authoritative account of every archive this project reads
from, what it retrieves, and what it is allowed to do with what it retrieves.
It is generated in spirit from the same manifests the pipeline writes to
`data/manifests/`; the counts below are current as of the last analysis run
recorded in `results/analysis_summary.json`.

## NASA Exoplanet Archive

**Role:** analysis spine. **Access:** public TAP/ADQL, no authentication.
**Base:** `https://exoplanetarchive.ipac.caltech.edu/TAP/sync`

| Dataset id | Table | Role | Rows (last sync) |
|---|---|---|---:|
| `nasa_pscomppars` | `pscomppars` | Composite parameters, one row per confirmed planet | 6,354 |
| `nasa_ps` | `ps` | Per-publication parameter sets (reference counting) | 40,106 |
| `nasa_toi` | `toi` | TESS Objects of Interest (candidates) | 8,136 |
| `nasa_k2pandc` | `k2pandc` | K2 planets and candidates | 4,068 |
| `nasa_koi_dr25` | `q1_q17_dr25_koi` | Kepler Objects of Interest, DR25 | 8,054 |
| `nasa_tce_dr25` | `q1_q17_dr25_tce` | Kepler Threshold Crossing Events (detections, not planets) | 34,032 |
| `nasa_transitspec` | `transitspec` | Transmission spectroscopy (planetary atmospheres) | 5,948 |
| `nasa_emissionspec` | `emissionspec` | Emission spectroscopy (planetary atmospheres) | 2,361 |
| `nasa_spectra_index` | `spectra` | Index of archived spectrum files | 1,826 |
| `nasa_microlensing` | `ml` | Microlensing planets | 895 |
| `nasa_di_stars` | `di_stars_exep` | Direct-imaging target stars | 164 |
| `nasa_stellarhosts` | `stellarhosts` | Per-publication stellar parameters | 47,857 |

**Column list validation:** before every query, the requested column list is
checked against the live `TAP_SCHEMA.columns` for that table. A column the
archive has since retired is dropped and recorded in the manifest rather than
failing the whole retrieval.

**Two tables that are not interchangeable:** `pscomppars` gives the best
available published value per parameter, independently per column, and is
not a self-consistent single-paper solution. `ps` gives one row per actual
published parameter set and is what this project uses to count independent
references and to measure inter-publication disagreement in reported values.

**Acknowledgement required by the archive** (reproduced verbatim, included in
every page footer of the website):

> This research has made use of the NASA Exoplanet Archive, which is operated
> by the California Institute of Technology, under contract with the National
> Aeronautics and Space Administration under the Exoplanet Exploration
> Program.

**Dataset DOIs:** Planetary Systems, `10.26133/NEA12`; Planetary Systems
Composite Parameters, `10.26133/NEA13`; TESS Project Candidates,
`10.26134/ExoFOP5`; Kepler Objects of Interest, `10.26133/NEA4`; K2 Planets
and Candidates, `10.26133/NEA1`; Transmission Spectroscopy, `10.26133/NEA10`;
Emission Spectroscopy, `10.26133/NEA9`.

## Gaia Archive (ESA)

**Role:** independent astrometry crossmatch for confirmed-planet host stars.
**Access:** public TAP service, no authentication. **Base:**
`https://gea.esac.esa.int/tap-server/tap/sync`

This is an **exact-identifier crossmatch**, not a coordinate match: the NASA
Exoplanet Archive's `pscomppars` table already carries a `gaia_dr3_id` column
(a string like `"Gaia DR3 4919009555730599936"`) for 5,970 of 6,354 confirmed
planets (94%), spanning 4,408 of 4,764 unique host systems (92.5%). This
project extracts the numeric `source_id` from that string and queries
`gaiadr3.gaia_source` directly by `source_id` -- unambiguous by construction,
no tolerance radius or ambiguity flag needed. A host with no `gaia_dr3_id`
recorded by the NASA archive is simply absent from the crossmatch; no
coordinate-based fallback is attempted in this integration.

Added per host: parallax and parallax error (an independent distance check
against the archive's own adopted `sy_dist`, exposed as
`gaia_distance_disagreement_frac`; the median disagreement across all 4,408
matched hosts is 0.7%), proper motion, `ruwe` (Renormalised Unit Weight
Error -- values above ~1.4 are the standard flag for a poorly-fit or
unresolved-binary astrometric solution: 412 planets' hosts exceed this in the
current run), `non_single_star` (Gaia's own multiplicity flag), and native
Gaia G/BP/RP photometry. Gaia's own astrophysical parameters (e.g. GSP-Phot
stellar values) are deliberately **not** pulled in and blended with the
archive's adopted stellar parameters, to avoid re-introducing the
single-paper-per-row inconsistency the composite table's own caveat above
already describes.

Retrieved via `python -m earth2 sync-gaia`, which must run after `sync` (it
reads the `gaia_dr3_id` column `sync` already retrieved) and before
`analyse`. Implementation: `src/earth2/data_sources/gaia.py`.

**Acknowledgement required by the mission** (reproduced verbatim, included in
every page footer of the website):

> This work has made use of data from the European Space Agency (ESA)
> mission Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia Data
> Processing and Analysis Consortium (DPAC,
> https://www.cosmos.esa.int/web/gaia/dpac/consortium). Funding for the DPAC
> has been provided by national institutions, in particular the institutions
> participating in the Gaia Multilateral Agreement.

**Citation:** Gaia Collaboration, Vallenari, A., Brown, A. G. A., et al.
(2023), *Gaia Data Release 3. Summary of the content and survey properties*,
Astronomy & Astrophysics, 674, A1, doi:10.1051/0004-6361/202243940.

## MAST (Mikulski Archive for Space Telescopes), STScI

**Role:** public transit photometry for deep-dive systems and the transit
validation benchmark. **Access:** `astroquery`/`lightkurve` metadata-first
search, no authentication for public products.

Retrieval is search-then-download: `search_lightcurve()` returns available
products before anything is fetched, and a target with no public product is
reported as an explicit absence, never as an empty chart. Downloaded FITS
products are cached under `data/products/` (git-ignored, regenerable).

## DACE — Data & Analysis Center for Exoplanets, University of Geneva

**Role:** public radial-velocity time series with co-measured stellar activity
indicators. **Access:** the official `dace-query` Python package, public mode
(no `.dacerc` API key). Private DACE holdings are never accessed by this
project.

**Important distinction, stated explicitly throughout this project:** the
high-resolution stellar spectra DACE serves for radial-velocity work measure
the *star*. They are not planetary atmospheric transmission spectra, and this
project never presents them as such. Genuine planetary-atmosphere
transmission/emission spectra come exclusively from the NASA Exoplanet
Archive's `transitspec`/`emissionspec` tables above.

**Acknowledgement:** Buchschacher, N., Ségransan, D., Udry, S., Diaz, R.
(2015), *DACE: Data and Analysis Center for Exoplanets*, ASP Conference
Series, 495, 7.

## What was investigated but not integrated

**ESO Science Archive** was investigated during the research pass but is not
integrated: it was not required to reach a scientifically meaningful sample
size (164,209 provenance-tracked records is already well past the project's
stated 10,000-50,000 target), and its main value here would be supplementary
spectroscopic holdings for a handful of already-well-characterised deep-dive
targets rather than a population-wide addition. This is a scope decision, not
a technical blocker, and is recorded here rather than silently omitted.

Gaia DR3 bulk astrometric crossmatching, by contrast, **is** integrated (see
above) -- it moved from this list to a real integration once the exact
`gaia_dr3_id` crossmatch key already present in `pscomppars` was noticed and
used, rather than attempting a slower, more error-prone coordinate match.

## Raw payload policy

Raw archive payloads are never committed to this repository. `data/raw/` is
git-ignored. Every payload is re-retrievable via `python -m earth2 sync`,
because the manifest in `data/manifests/` records the literal ADQL/API query,
the resolved URL, the UTC retrieval timestamp, and a SHA-256 of the payload as
received. Re-syncing and comparing hashes is how this project detects archive
drift (a value changing between two dates) rather than treating a changed
answer as an error -- **but the archives themselves are living datasets, not
frozen files.** A query re-run today can return a response that differs from
what was originally hashed, if the archive has since revised, added or removed
records. The manifest can prove that drift occurred; it cannot restore the
original byte stream once the archive's own copy has changed. Reconstructing
today's exact historical response is not guaranteed -- only re-verifiable
against whatever the archive currently serves. Publication-grade,
frozen-in-time reproduction requires a separate immutable snapshot of the
release inputs (e.g. a DOI-backed data release), which this repository does
not yet publish.

## Software licence vs. data licence

The software in this repository is MIT-licensed (see `LICENSE`). That licence
covers the code only. The retrieved datasets remain governed by the terms of
their originating archives, listed above. This project does not claim
ownership of any astronomical dataset.
