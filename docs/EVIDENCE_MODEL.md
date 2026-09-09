# ExoEarth evidence model

The evidence index is additive. It preserves the v1 catalogue and its original
results, and supports explicit provenance queries without certifying every
archive parameter as independently measured.

## Scientific labels and unknown states

Quantities use OBSERVED, DERIVED, MODEL-INFERRED, SCENARIO, FORECAST or SIMULATED.
An unclassified quantity has a null label and a mandatory explanation; unknown
provenance is not silently promoted to OBSERVED. OBSERVED denotes an
archive-reported observational estimate in this first importer, not a raw photon
measurement, an independent physical constraint or a model-free value.
Scenarios, forecasts and simulations require explicit assumptions.

Stars and planets are separate entities. Measurements describe their entities
and link to a retrieval source and, where supplied, a publication reference.
Derived quantities link to input measurements and a model. External archive
calculations with unavailable inputs remain explicitly incomplete. They cannot
be presented as fully traceable local derivations.

```text
planet --orbits--> star
measurement --describes--> planet or star
measurement --retrieved_from--> source (query, UTC, payload hash)
measurement --published_in--> source (reference, URL, bibcode, DOI if known)
quantity --derived_from--> measurement or quantity
quantity --uses_model--> model (equation, version, assumptions)
```

The graph rejects duplicate identifiers with conflicting content, dangling links,
invalid relationship types, circular scientific derivations, non-finite numbers,
negative uncertainty magnitudes and unsupported evidence labels. SQL foreign
keys preserve referential integrity. The current versioned SQLite schema uses
indexed relations and JSON attributes; larger measurement tables can be
partitioned without treating archive rows as new physical entities.

## Required provenance contract

Measurement attributes include parameter, value, explicit unit, uncertainty
magnitudes, covariance, limit/estimate semantics, instrument, facility, program,
reduction, observation timestamp, retrieval time and publication identifiers.
Null fields mean unavailable. A missing-provenance list makes gaps inspectable.
A discovery facility must not be substituted for the instrument that measured a
particular radius or mass. A publication date is not an observation timestamp.

Local model records should include equation or method identifier, version,
validity domain and literature source. Local derived records must include
assumptions, software commit and uncertainty method. Different model results
and spectrum reductions must have distinct identifiers. Correlations may only
be attached when their source or joint-model derivation is documented.

## First implemented importer

Run, without archive access:

```bash
python -m earth2.evidence
python -m earth2.evidence --database data/products/evidence-v1.sqlite
```

An existing database is never overwritten. The input is the **committed**
`results/measurement_provenance.csv.gz`, `results/candidate_ranking.parquet`
and composite manifest. The importer supplies stable source-scoped identifiers,
star/planet relations, all supported composite parameter references and four
mass-evidence examples. It writes deterministic summaries to `results/evidence`.
No source is downloaded by this command. SQLite files remain local products.

```python
from earth2.evidence import EvidenceGraph
from earth2.evidence.catalogue import entity_id
from pathlib import Path

graph = EvidenceGraph.load(Path("data/products/evidence-v1.sqlite"))
for record in graph.measurements(entity_id("planet", "Proxima Cen b"), "pl_bmasse"):
    print(graph.trace(record.id))
```

The query answers which composite-selected reference backs a value. It does
**not yet** answer which *all* published mass solutions exist. Those require
the per-publication `ps` importer and publication-level validation. The
committed long-format table does not include uncertainties, observation IDs or
reductions, so this importer reports those as absent rather than borrowing them
from a potentially different snapshot. A later raw-table importer can enrich
the same contract with properly matched uncertainties.

Mass-radius predictions are MODEL-INFERRED. Minimum masses retain
`measurement_type=minimum_mass`; upper limits stay upper limits. V1's other
mass classes are left unclassified pending source verification, because the
baseline classifier has an unknown-to-measured fallback. Archive-derived
radii stay DERIVED. `st_lum` retains `dex(L_sun)`; it is not silently treated as
linear luminosity.

Repeated stellar measurements carried through several planets remain distinct
source records. `independent_measurement_count` is null: neither duplication nor
publication counts establish independence. Differently formatted references
are retained as source variants instead of fabricated bibliographic matches.

## Tests and remaining work

`tests/test_evidence.py` checks graph round trips, dependencies, cycles, labels,
null uncertainty and invalid numerical data. Generated examples exercise the
real committed inputs. Still required before the full evidence-graph release
gate: publication-solution ingestion, covariance/sample representation,
observation/spectrum-program entities, all local derived-result input chains,
and public graph navigation. This is an operational index and validated storage
contract, not a claim that missing provenance has been recovered.
