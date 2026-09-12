# Data licences, attribution, and redistribution boundaries

The MIT licence in [`LICENSE`](LICENSE) applies to this repository's software.
It does not relicense observations, catalogues, spectra, stellar models, or
literature supplied by third parties.

The pipeline retrieves public data from the NASA Exoplanet Archive, MAST,
Gaia/ESA, DACE, the NASA Exoplanet Science Institute HWO target catalogue, and
the MIST project. Each source remains governed by its provider's terms,
acknowledgement requests, and publication citations. Exact query text, retrieval
time, source URL, row count, and file hash are recorded under
[`data/manifests`](data/manifests); the full citation list and acknowledgement
text are in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## The v2 release boundary

`earth2-v2-data-release/` contains newly derived tables, posterior samples,
model outputs, query manifests, software configuration, and checksums. It
deliberately excludes cached and processed source tables, raw spectra, raw light
curves, raw radial velocities, the MIST grid/archive, and the HPIC catalogue.

Derived values may still encode or depend on third-party measurements. Reusers
must cite the original archives and publications listed in the manifests and
documentation. When a provider's terms and this repository differ, the
provider's terms control its source data.

## Software and project-authored products

Project-authored code is MIT licensed. Unless a file states otherwise, original
documentation, visual explanations, and derived research products are provided
for scholarly reuse with attribution to Biswajit Jana and citation of the v2
release. The Zenodo DOI is marked `pending` until the public deposit is minted;
no DOI has been invented.
