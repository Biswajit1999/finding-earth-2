# `data/` — layout and commit policy

This directory is deliberately asymmetric: **descriptions of data are committed,
bulk data is not.**

| Path | Committed? | Contents |
|---|---|---|
| `manifests/` | **yes** | One JSON per retrieval: archive, exact query, URL, UTC timestamp, SHA-256 of the payload, row/column counts, citation, DOI. |
| `processed/` | **no** | Parquet mirrors of the retrieved archive tables. A cache: byte-reconstructible from `manifests/`. |
| `samples/` | **yes** | Tiny fixtures used by the test suite. Clearly synthetic where synthetic. |
| `../results/` | **yes** | The scientific outputs: rankings, coverage, summary JSON, provenance manifest. These are what the README and website quote. |
| `raw/` | **no** | Verbatim archive payloads. Large, owned by the archives, fully reconstructible. |
| `products/` | **no** | Bulk science products (light curves, spectra FITS, RV files) fetched on demand. |

## Why raw payloads are not in Git

1. They are large and would bloat clone time for no scientific gain.
2. They belong to the archives, not to this repository. See `docs/DATA_SOURCES.md`.
3. They are reconstructible: every manifest carries the literal query string and
   the endpoint, so `python -m earth2 sync` rebuilds them byte-for-byte in the
   normal case.

## Detecting archive drift

Archives are living datasets — a planet's radius can change when a new paper
lands. Each manifest stores the SHA-256 of the payload as retrieved. Re-running
`sync` and comparing hashes tells you *whether the archive's answer changed*,
which is a scientific fact worth knowing, not an error.

## What you will never find here

Fabricated rows, padded counts, duplicated records inflating a total, or
synthetic values written into a table that feeds the results. Synthetic data
exists only under `samples/` and only where the filename and the manifest say so.
