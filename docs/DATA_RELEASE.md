# Finding Earth 2.0 v2 data release

The publication bundle is built into `earth2-v2-data-release/` and a
deterministic `earth2-v2-data-release.zip`. It is ready for a Zenodo deposit;
the DOI remains **pending** until Zenodo mints it.

The bundle includes derived candidate and evidence tables, DR25 selection and
reliability products, occurrence posterior summaries and samples, composition,
climate, XUV, atmospheric-observability, HWO, mission, information-gain,
falsification, and sensitivity products. It also includes source-query
manifests, transformations, software versions, citation metadata, the source
commit, an inventory, and SHA-256 checksums.

It excludes `data/raw`, `data/cache`, `data/processed`, raw spectra, raw time
series, raw radial velocities, upstream MIST products, and the source HPIC table.
Those records remain with their providers. See [`DATA_LICENSES.md`](../DATA_LICENSES.md).

## Build and verify

```bash
python scripts/build_publication_release.py
python scripts/validate_manuscript.py
sha256sum -c earth2-v2-data-release/MANIFEST.sha256
```

Building twice from the same commit produces the same inventory, checksums,
paper macros, and ZIP bytes. `SOURCE_COMMIT` records the checkout used to make
the bundle, avoiding the impossible self-reference of embedding the release
commit's own hash inside itself.

## Zenodo deposit checklist

1. Create an upload and reserve its DOI.
2. Upload `earth2-v2-data-release.zip`.
3. Use title “Finding Earth 2.0 v2 data release”, version `2.0.0`, creator
   `Jana, Biswajit`, and release date `2026-09-13`.
4. Copy the abstract and keywords from `.zenodo.json`.
5. Add the GitHub repository as the related software identifier.
6. Publish, then replace `doi: pending` in the inventory and add the minted DOI
   to `CITATION.cff` in a DOI-only patch release.

No DOI is claimed before the external deposit exists.
