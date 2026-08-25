# Reproducibility

## Fresh clone to full pipeline

```bash
git clone https://github.com/Biswajit1999/finding-earth-2.git
cd finding-earth-2
python -m pip install -e ".[dev,products]"

# For the exact dependency versions the committed results/ and paper/ were
# regenerated against, install requirements-lock.txt first instead:
#   python -m pip install -r requirements-lock.txt
#   python -m pip install --no-deps -e ".[dev,products]"

make data           # python -m earth2 sync       -- retrieve archive tables
make sync-gaia       # python -m earth2 sync-gaia    -- cross-match hosts against Gaia DR3
make analyse         # python -m earth2 analyse     -- catalogue, Monte Carlo, ranking
make figures          # python -m earth2 figures      -- publication figures
make deepdive           # python -m earth2 deepdive -n 10 --transit --rv
make validate-transit  # python -m earth2 validate-transit
make export              # python -m earth2 export       -- browser-ready JSON
make report                # python -m earth2 report       -- regenerate README

cd web && npm install && npm run dev    # or: make web-build for a static export
```

Or the whole analysis pipeline in one step: `make all`.

## Determinism

| Source of non-determinism | How it is controlled |
|---|---|
| Monte Carlo sampling | Fixed seed `20260824` (`earth2.config.RANDOM_SEED`), `numpy.random.default_rng` |
| Archive query results | Every retrieval is a literal ADQL/API string recorded in `data/manifests/*.json`, with a SHA-256 of the payload as received |
| Software versions | `results/analysis_summary.json["software"]` records Python, numpy, pandas, scipy and astropy versions for the run that produced it |
| Ranking weights | Explicit defaults in `earth2.ranking.ScoreWeights`; any non-default run records its weights in the ledger |
| Random subsampling (3D universe export) | Seeded (`random_state=20260824`) when the point count is capped |

Given the same archive state and the same seed, `python -m earth2 analyse`
reproduces byte-identical `results/*.csv` and `*.parquet` output. Archive
values themselves are not static — a planet's published radius can change
when a new paper appears — which is why every manifest hashes the payload it
received: re-syncing and diffing hashes tells you *whether the archive's
answer changed*, a fact worth surfacing rather than an error to suppress.

## What "data last synchronised" means

`results/analysis_summary.json["generated_utc"]` and the sync-state file
record when the pipeline last successfully talked to the archives — not when
this repository was cloned or when the website was built. "Synchronised" means
kept current with continually maintained public catalogues, explicitly not
live telescope telemetry; the website states this distinction in its footer.

## Provenance chain

Every displayed number is traceable through five layers:

```
NASA Exoplanet Archive table
        |
per-measurement reference link (archive-attached, or "archive_calculated")
        |
data/manifests/*.json  (retrieval: query, URL, UTC, SHA-256)
        |
results/transformation_ledger.json  (equation, citation, parameters, row counts)
        |
results/candidate_ranking.csv + results/measurement_provenance.csv.gz
```

## Environment

- Python ≥3.9 (developed and tested on 3.9.19)
- Node.js ≥20, npm ≥10 for the web interface
- No paid API keys required. DACE is accessed in public mode; MAST and the
  NASA Exoplanet Archive require no authentication for the data this project
  uses.

## Regenerating a single stage

Every CLI stage is idempotent and reads only what the previous stage wrote, so
any stage can be re-run alone without repeating the ones before it — for
example, `python -m earth2 figures` after only changing a plot style does not
require re-syncing or re-analysing.
