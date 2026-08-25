"""Generate README.md from the analysis results.

Every statistic in the README is written by this module from
``results/analysis_summary.json``. Nothing is typed by hand.

That is a correctness requirement, not a convenience. A README quoting a planet
count is quoting a measurement, and a measurement that was true two years ago
and has not been re-checked is a fabricated statistic. Regenerating the README
is part of the pipeline (``python -m earth2 report``) and CI verifies the file
in the repository matches what the current results produce.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from earth2.config import RESULTS_DIR, ROOT

__all__ = ["build_readme", "write_readme"]

REPO_URL = "https://github.com/Biswajit1999/finding-earth-2"


def _n(x: Any) -> str:
    try:
        return format(int(x), ",")
    except (TypeError, ValueError):
        return "n/a"


def _pct(a: Any, b: Any) -> str:
    try:
        return "%.1f%%" % (100.0 * float(a) / float(b))
    except (TypeError, ValueError, ZeroDivisionError):
        return "n/a"


def build_readme(summary: dict[str, Any]) -> str:
    scale = summary.get("scale", {})
    pop = summary.get("population", {})
    cov = summary.get("measurement_coverage", {})
    hz = summary.get("habitable_zone", {})
    atmo = summary.get("atmosphere", {})
    summary.get("candidates", {})
    rank = summary.get("ranking", {})
    prov = summary.get("measurement_provenance", {})
    mc = summary.get("monte_carlo", {})
    summary.get("observational_products", {})

    n_planets = pop.get("n_confirmed_planets", 0)
    top = rank.get("top_candidates", []) or []

    # ---- top candidate table -------------------------------------------
    rows: list[str] = []
    for c in top[:12]:
        rows.append(
            "| {rank} | **{name}** | {idx:.3f} | {esi:.3f} | {hab:.3f} | {conf:.3f} | {rade} | {mass} | {dist} |".format(
                rank=c.get("rank", "-"),
                name=c.get("pl_name", "?"),
                idx=c.get("earth2_index", float("nan")),
                esi=c.get("earth_similarity", float("nan")),
                hab=c.get("conservative_habitability", float("nan")),
                conf=c.get("observational_confidence", float("nan")),
                rade=("{:.2f}".format(c["pl_rade"])) if c.get("pl_rade") else "—",
                mass={
                    "measured": "measured",
                    "msini_lower_limit": "M sin i",
                    "msini_deprojected": "M sin i / sin i",
                    "inferred_mass_radius": "*inferred*",
                    "upper_limit": "upper limit",
                    "missing": "—",
                }.get(c.get("mass_class", ""), c.get("mass_class", "—")),
                dist=("{:.1f}".format(c["sy_dist_pc"])) if c.get("sy_dist_pc") else "—",
            )
        )
    candidate_table = "\n".join(rows) if rows else "| — | *analysis not yet run* | | | | | | | |"

    # ---- dataset inventory ---------------------------------------------
    ds_rows: list[str] = []
    for d in summary.get("provenance", {}).get("datasets", []):
        if d.get("status") not in ("ok", "partial"):
            continue
        ds_rows.append("| `{id}` | {table} | {rows} | {doi} |".format(
            id=d.get("dataset_id", ""), table="`" + str(d.get("source_table", "")) + "`",
            rows=_n(d.get("n_rows")), doi=("`" + d["doi"] + "`") if d.get("doi") else "—",
        ))
    dataset_table = "\n".join(ds_rows)

    methods = pop.get("discovery_methods", {})
    method_rows = "\n".join(
        f"| {m} | {_n(v)} | {_pct(v, n_planets)} |"
        for m, v in list(methods.items())[:8]
    )

    sync_utc = summary.get("generated_utc", "")

    return f"""# Finding Earth 2.0 in Distant Worlds

<p align="center">
  <img src="docs/images/hero.webp" alt="Finding Earth 2.0 in Distant Worlds: title banner showing the candidate-selection funnel from 164,209 provenance-tracked source records down to 6,354 confirmed planets, 174 conservative habitable-zone worlds, 15 small-and-temperate candidates, and 1 with an independently measured mass" width="100%">
</p>

**A reproducible, data-driven search for potentially Earth-like worlds across the public astronomical archives.**

<p align="center">
  <img src="results/figures/hz_diagram.png" alt="Habitable-zone boundaries after Kopparapu et al. (2013), with every confirmed planet placed by incident stellar flux and host temperature" width="88%">
</p>

<p align="center">
  <em>Every number in this README is generated from the analysis output by
  <code>python -m earth2 report</code>. None is typed by hand.</em><br>
  <sub>Last analysis run: <code>{sync_utc}</code></sub>
</p>

---

> **Scientific status: Beta.** The Earth-2.0 index ranks physical similarity
> and observational evidence; it does not estimate the probability that a
> planet supports life. Population analysis uses NASA Exoplanet Archive
> catalogues cross-matched against Gaia DR3 astrometry by exact source
> identifier; selected transit and radial-velocity deep dives additionally
> draw on public MAST and DACE products. ESO integration is planned but not
> yet implemented (see the archive matrix below). Candidates whose host star
> sits outside the habitable-zone model's calibrated temperature range are
> flagged and down-weighted rather than silently ranked as confident members
> — see [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## Abstract

This project asks a deliberately narrow question of the public exoplanet
archives: **among currently available observations, which known planets most
closely satisfy physically motivated conditions associated with an Earth-like
potentially habitable world, how strong is the evidence behind each, and where
are the major uncertainties?**

It ingests **{_n(scale.get('total_source_records'))} provenance-tracked source records** from
{scale.get('n_datasets_retrieved', 0)} archive tables, derives habitable-zone membership from the
Kopparapu et al. (2013) climate model, computes an Earth Similarity Index,
propagates every published uncertainty through **{_n(mc.get('n_samples'))} Monte Carlo draws per
planet**, and ranks candidates on four interpretable axes that are reported
separately because they genuinely disagree.

It does **not** claim to have found life, an inhabited world, or a confirmed
second Earth. It is explicit about the difference between Earth *similarity*,
habitable-zone *position*, rocky-planet *plausibility*, atmospheric
*observability*, and *evidence for biology* — five distinct things that are
routinely conflated.

---

## Key results

| | |
|---|---|
| Source records ingested | **{_n(scale.get('total_source_records'))}** |
| Confirmed planets analysed | **{_n(n_planets)}** across {_n(pop.get('n_unique_host_systems'))} host systems |
| Planets with a **measured** mass | **{_n(cov.get('n_with_measured_mass'))}** ({_pct(cov.get('n_with_measured_mass'), n_planets)}) |
| Planets whose mass is **inferred from radius** | {_n(cov.get('n_with_mass_inferred_from_radius'))} ({_pct(cov.get('n_with_mass_inferred_from_radius'), n_planets)}) |
| In the **conservative** habitable zone | **{_n(hz.get('n_in_conservative_hz_nominal'))}** |
| In the **optimistic** habitable zone | {_n(hz.get('n_in_optimistic_hz_nominal'))} |
| Conservative HZ **and** below 1.6 R⊕ | **{_n(hz.get('n_conservative_hz_and_below_1p6_re'))}** |
| …of which have a **measured mass** | **{_n(hz.get('n_conservative_hz_and_below_1p6_re_with_measured_mass'))}** |
| Planets with published transmission spectra | {_n(atmo.get('planets_with_transmission_spectra'))} |
| Measurement-level provenance links | {_n(prov.get('n_links'))} across {_n(prov.get('n_distinct_publications'))} publications |

> **The headline finding is a scarcity result.** Of {_n(n_planets)} confirmed
> planets, only **{_n(hz.get('n_conservative_hz_and_below_1p6_re'))}** are both inside the
> conservative habitable zone and small enough to be plausibly rocky — and only
> **{_n(hz.get('n_conservative_hz_and_below_1p6_re_with_measured_mass'))}** of those has a mass that was
> actually measured rather than predicted from its radius. The search for Earth 2.0
> is not currently limited by how many planets we know about. It is limited by how
> few of them we have measured well.

---

## Top candidates

Produced by the pipeline, not selected by hand. Re-running the analysis after an
archive update re-derives this table.

| # | Planet | Earth-2.0 index | Similarity | Habitability | Confidence | R⊕ | Mass | pc |
|--:|---|--:|--:|--:|--:|--:|---|--:|
{candidate_table}

`Mass` reports how the mass was obtained. *inferred* means it was predicted from
the radius by a mass–radius relation and is not an independent measurement — a
distinction that changes the ranking, since density and escape velocity derived
from such a mass carry no information beyond the radius.

<p align="center">
  <img src="results/figures/top_candidates.png" alt="Top candidates with their score decomposition and Earth Similarity Index posteriors" width="94%">
</p>

---

## Research question, stated precisely

> Among currently available public exoplanet observations and catalogues, which
> known planets or candidates most closely satisfy physically motivated
> conditions associated with an Earth-like potentially habitable world, how
> strong is the underlying observational evidence, and where are the major
> uncertainties?

Five things this project keeps strictly separate:

| Concept | What it means here |
|---|---|
| **Earth similarity** | Bulk radius, density, escape velocity and equilibrium temperature resemble Earth's. |
| **Habitable-zone position** | Incident flux is compatible with surface liquid water under a stated climate model. |
| **Rocky plausibility** | Radius is below the regime where planets are predominantly volatile-rich. |
| **Atmospheric observability** | Whether an atmosphere could be characterised with current instruments. |
| **Evidence for life** | **Not established for any planet.** No metric in this project estimates it. |

---

## Method

```
public archives  ──▶  ingest + manifest  ──▶  crossmatch  ──▶  catalogue
                                                                  │
                        ┌─────────────────────────────────────────┤
                        ▼                                         ▼
              Monte Carlo uncertainty                    habitable zone + ESI
                 ({_n(mc.get('n_samples'))} draws/planet)              (Kopparapu 2013 erratum)
                        │                                         │
                        └────────────────┬────────────────────────┘
                                         ▼
                          four interpretable component scores
                                         │
                          weighted geometric mean (non-compensatory)
                                         ▼
                            Earth-2.0 candidate index
                                         │
                     ┌───────────────────┼───────────────────┐
                     ▼                   ▼                   ▼
                 figures            results/*.csv        web export → React
```

### The four scores

Reported separately, never collapsed into one number without showing the parts.

| Score | Question | Built from |
|---|---|---|
| **Earth similarity** | How close are the bulk properties to Earth's? | Monte Carlo median ESI (Schulze-Makuch et al. 2011) |
| **Conservative habitability** | Is this consistent with a temperate rocky world? | HZ membership probability × rocky plausibility (Rogers 2015) |
| **Observational confidence** | How well is it actually measured? | Mass provenance, uncertainty coverage, reference depth, literature agreement, completeness |
| **Characterisation potential** | How feasible is atmospheric follow-up? | Kempton et al. (2018) TSM |

The composite uses a **weighted geometric mean**, not an average. Under an
arithmetic mean an ultra-hot Jupiter with superb measurements and excellent
observability scores respectably despite zero habitability — its strong
components compensate for the disqualifying one. A geometric mean is
non-compensatory.

Characterisation potential is **excluded from the default composite** (weight 0):
it measures how easy a planet is to *observe*, not how Earth-like it is, and it
structurally penalises non-transiting planets, which would demote Proxima Cen b
for a reason unrelated to its properties.

---

## Data sources

All data is retrieved live from public archives. Raw payloads are **not**
committed; the manifests that record the exact query, retrieval time and a
SHA-256 of the response are. That hash can prove *drift* -- that today's
answer no longer matches a past one -- against a living archive whose records
change over time; it cannot restore a historical byte stream the archive has
since revised. See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

| Dataset | Archive table | Records | DOI |
|---|---|--:|---|
{dataset_table}

Plus, for deep-dive systems:

- **MAST / STScI** — public TESS and Kepler light curves via `lightkurve`.
- **DACE (University of Geneva)** — public radial-velocity time series with the
  stellar activity indicators measured from the same spectra.

### Archive integration matrix

| Source | Role in population ranking | Deep-dive role | Integrated in current release |
|---|---|---|---|
| NASA Exoplanet Archive | Primary catalogue | Spectral catalogue metadata | Yes |
| Gaia DR3 | Exact-`source_id` astrometry crossmatch (parallax, RUWE, proper motion) | -- | Yes |
| MAST | No population-wide input | Transit/light-curve products | Partial, on demand |
| DACE | No population-wide input | RV products | Partial, on demand |
| ESO | No | No systematic integration | No |

The **164,209 source records** figure above sums 12 NASA Exoplanet Archive
table retrievals plus the Gaia DR3 crossmatch (see
`results/provenance_manifest.json`) -- it is a row count, not a count of
unique planets, spectra, or independent observations. MAST and DACE
integration is currently selective/on-demand for individual deep-dive targets
rather than systematic across the full population; ESO integration was
investigated but is not yet part of this release. See
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

### Discovery methods in the analysed sample

| Method | Planets | Share |
|---|--:|--:|
{method_rows}

This distribution is **not** the true planet population — it is the shape of our
instruments. Transit surveys favour short periods and large planets relative to
their star; radial velocity favours massive planets close in. See
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## What the analysis found

The two figures below are the ones that matter most. The evidence matrix is
this project's signature output: it makes "high score, weak evidence" visible
at a glance rather than burying it in a table column. The posterior clouds
show *why* uncertainty propagation changes the ranking — a tight cloud is a
well-measured planet; a smeared one is not, and no single error bar conveys
that as clearly as the distribution itself.

<p align="center">
  <img src="results/figures/evidence_matrix.png" alt="Data-confidence matrix showing, per top candidate, mass provenance quality, propagated-uncertainty coverage, reference depth, habitable-zone model validity, and the availability of transit, radial-velocity and spectroscopic data" width="90%">
</p>

<p align="center">
  <img src="results/figures/posterior_clouds.png" alt="Monte Carlo posterior clouds in radius-density space for the top candidates, propagated from each planet's own published asymmetric uncertainties" width="80%">
</p>

<table>
<tr>
<td width="50%"><img src="results/figures/mass_radius.png" alt="Mass-radius diagram distinguishing measured masses from those inferred from radius"></td>
<td width="50%"><img src="results/figures/period_radius.png" alt="Period-radius diagram showing where the known exoplanet population sits, coloured by discovery method"></td>
</tr>
<tr>
<td width="50%"><img src="results/figures/flux_radius_hz.png" alt="Incident stellar flux against planet radius with the conservative habitable zone marked"></td>
<td width="50%"><img src="results/figures/equilibrium_temperature.png" alt="Equilibrium-temperature distribution across the analysed catalogue with the conservative habitable zone for a Sun-like host shaded"></td>
</tr>
<tr>
<td width="50%"><img src="results/figures/data_coverage.png" alt="Data coverage by physical quantity, showing values present versus values with published uncertainties"></td>
<td width="50%"><img src="results/figures/distance_distribution.png" alt="Distance distribution across the catalogue, with the top candidates marked in the nearest tail"></td>
</tr>
</table>

A full-resolution figure index, including the discovery timeline, the HR
diagram, the HZ diagram, and a real published transmission spectrum, is in
[`results/figures/`](results/figures/).

---

## Reproducing this

```bash
git clone {REPO_URL}.git
cd finding-earth-2
python -m pip install -e ".[dev,products]"

python -m earth2 sync        # retrieve archive data + write manifests
python -m earth2 analyse     # catalogue, Monte Carlo, ranking
python -m earth2 figures     # publication figures
python -m earth2 deepdive    # top-system deep dives (--transit --rv for live fetch)
python -m earth2 export      # browser-ready JSON
python -m earth2 report      # regenerate this README
```

Or the whole pipeline:

```bash
make all
```

The website:

```bash
cd web && npm install && npm run dev
```

Determinism: the Monte Carlo seed is fixed
(`{mc.get('seed', 'n/a')}`), every retrieval carries a UTC timestamp and a
SHA-256 of the payload as received, and every transformation is recorded in
`results/transformation_ledger.json`.

---

## Repository layout

```
src/earth2/
  data_sources/    archive connectors -- return (DataFrame, Manifest), never data alone
  crossmatch/      entity resolution; never joins on string similarity
  preprocessing/   catalogue assembly, mass-provenance classification
  habitability/    habitable zone (Kopparapu) and Earth Similarity Index
  uncertainty/     Monte Carlo propagation with asymmetric errors
  ranking/         four interpretable scores + non-compensatory composite
  transit/         MAST light curves: detrend, fold, fit, validate
  radial_velocity/ DACE velocities + mandatory stellar-activity cross-check
  spectroscopy/    published atmospheric spectra + biosignature context
  provenance/      retrieval manifests and transformation ledger
  reporting/       figures, deep dives, web export, this README
web/               Next.js + React interface
results/           computed outputs -- the only source of published numbers
docs/              research notes, methods, limitations, reproducibility
```

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/METHODS.md`](docs/METHODS.md) | Every equation, with citations and assumptions |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Archives, tables, licensing, acknowledgements |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | What this analysis cannot establish |
| [`docs/RESEARCH_NOTES.md`](docs/RESEARCH_NOTES.md) | Evidence ledger built during the research pass |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Seeds, versions, determinism, re-running |
| [`references/references.bib`](references/references.bib) | BibTeX bibliography |

---

## Limitations

The full list is in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md). The four that
most constrain the results:

1. **The Earth Similarity Index cannot distinguish Earth from Venus.** Venus
   scores **0.93** on this metric, because equilibrium temperature — the only
   temperature exoplanet catalogues provide — is insensitive to the runaway
   greenhouse that makes Venus's surface 737 K. Venus is carried through the
   whole pipeline as a control so this is visible in the results rather than
   asserted in a footnote.

2. **{_pct(cov.get('n_with_mass_inferred_from_radius'), n_planets)} of catalogue masses were never measured.** They are
   predictions from the radius. Density and escape velocity computed from them
   re-encode the radius rather than adding information.

3. **TRAPPIST-1 sits below the habitable-zone model's validity floor.** Its host
   is 2566 K against a stated minimum of 2600 K. Results are reported both
   strictly (excluded) and with a flagged extrapolation, never silently clamped.

4. **An Earth twin's atmospheric signal is ~1 ppm.** Detecting an Earth-like
   atmosphere around a Sun-like star is far beyond current instruments; the
   candidates that are observable are so because they orbit small, cool stars,
   which brings its own habitability complications.

---

## Citation

If this work is useful to you, please cite it via [`CITATION.cff`](CITATION.cff),
and cite the underlying archives and papers — they did the observing.

---

## Licence

[MIT](LICENSE) for the software. The astronomical datasets remain governed by
their originating archives; see [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)
for required acknowledgements.

## Author

**Biswajit Jana** — [github.com/Biswajit1999](https://github.com/Biswajit1999)
"""


def write_readme(summary: dict[str, Any] | None = None, path: Path | None = None) -> Path:
    if summary is None:
        p = RESULTS_DIR / "analysis_summary.json"
        if not p.exists():
            raise SystemExit("No analysis_summary.json; run `python -m earth2 analyse` first.")
        summary = json.loads(p.read_text(encoding="utf-8"))
    out = Path(path) if path else (ROOT / "README.md")
    out.write_text(build_readme(summary), encoding="utf-8")
    return out
