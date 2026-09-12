# Contributing

Contributions that improve provenance, scientific validity, reproducibility,
accessibility, or explanation are welcome.

1. Open an issue describing the scientific or software problem and the evidence
   needed to evaluate it.
2. Branch from `main`; keep generated products and their builders in the same
   change.
3. Preserve the evidence labels `OBSERVED`, `MODEL-INFERRED`, `SIMULATED`, and
   `SCENARIO-ASSUMPTION`. Never recast a model output as a measurement.
4. Add a source manifest for every new retrieval. Do not commit credentials or
   provider-controlled raw data.
5. Run `pytest -q`, `ruff check src tests scripts`, `mypy src/earth2`, release
   invariants, and the web checks relevant to your change.

Scientific changes should state their domain, priors, support limits, failure
modes, and how the proposal would change a released claim. Reports of apparent
errors are valued even when a correction is not yet known.
