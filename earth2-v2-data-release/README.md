# Finding Earth 2.0 — v2 data release

This is the deterministic, machine-readable companion to the v2 manuscript.
It was built from source commit `096ccc48c57d0cfb12f0dc089c3e9dbac71976bc`.

The release contains derived catalogues, posterior summaries and samples,
selection/reliability surfaces, model-sensitivity tables, mission scenarios,
source query manifests, environment metadata, and exact software requirements.
It does **not** contain raw or processed third-party archive tables.

Evidence labels retain their strict meanings: `OBSERVED`, `MODEL-INFERRED`,
`SIMULATED`, and `SCENARIO-ASSUMPTION`. No score is a probability of life.

Verify every byte with `sha256sum -c MANIFEST.sha256` or an equivalent SHA-256
tool. See `release_inventory.json` for file roles and `DATA_LICENSES.md` for
source attribution and reuse boundaries.

Suggested Zenodo upload: `earth2-v2-data-release.zip`. Reserve or mint a DOI in
Zenodo, then replace the `doi: pending` field in the inventory and citation files
in a DOI-only patch release.
