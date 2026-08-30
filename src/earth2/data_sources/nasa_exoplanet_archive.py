"""NASA Exoplanet Archive connector (TAP / ADQL).

The archive exposes a TAP service at::

    https://exoplanetarchive.ipac.caltech.edu/TAP/sync

Two tables carry the bulk of the science and they are *not* interchangeable:

``pscomppars``
    One row per confirmed planet (~6.3k). Columns are assembled from the best
    available published value for each parameter *independently*, so a single
    row can mix radius from one paper and stellar mass from another. Excellent
    completeness, but the row is not a self-consistent single-paper solution.

``ps``
    One row per *published parameter set* (~40k). A planet appears once per
    paper that measured it, with ``pl_refname`` naming the paper and
    ``default_flag`` marking the archive's preferred set. Self-consistent per
    row, and the only way to count how many independent references support a
    measurement.

This project uses ``pscomppars`` as the analysis spine (best completeness) and
``ps`` as the evidence layer (how many papers, how much do they disagree). The
distinction is surfaced to the reader rather than hidden.

Column conventions used throughout the archive
----------------------------------------------
``<col>err1``      upper (positive) uncertainty
``<col>err2``      lower uncertainty, stored as a negative number
``<col>lim``       limit flag: 0 measurement, 1 upper limit, -1 lower limit
``<col>_reflink``  HTML anchor naming the publication the value came from
"""

from __future__ import annotations

import pandas as pd

from earth2.data_sources.base import fetch_csv
from earth2.provenance import Manifest

TAP_SYNC = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
ARCHIVE_NAME = "NASA Exoplanet Archive"
ARCHIVE_URL = "https://exoplanetarchive.ipac.caltech.edu/"

#: The acknowledgement the archive asks users to include.
#: https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html
CITATION = (
    "This research has made use of the NASA Exoplanet Archive, which is operated by the "
    "California Institute of Technology, under contract with the National Aeronautics and "
    "Space Administration under the Exoplanet Exploration Program."
)

# DOIs the archive publishes for its holdings.
DOI_PS = "10.26133/NEA12"           # Planetary Systems
DOI_PSCOMPPARS = "10.26133/NEA13"   # Planetary Systems Composite Parameters
DOI_TOI = "10.26134/ExoFOP5"        # TESS Project Candidates / ExoFOP
DOI_KOI = "10.26133/NEA4"           # Kepler Objects of Interest (DR25 cumulative)
DOI_K2 = "10.26133/NEA1"            # K2 Planets and Candidates
DOI_TRANSITSPEC = "10.26133/NEA10"  # Transmission Spectroscopy
DOI_EMISSIONSPEC = "10.26133/NEA11"  # Emission Spectroscopy (retired table)

# --------------------------------------------------------------------------
# Column groups
# --------------------------------------------------------------------------
_IDENT = [
    "pl_name", "hostname", "pl_letter", "sy_snum", "sy_pnum", "cb_flag",
    "discoverymethod", "disc_year", "disc_facility",
]

_PLANET_MEASURED = [
    "pl_orbper", "pl_orbsmax", "pl_rade", "pl_bmasse", "pl_dens",
    "pl_orbeccen", "pl_insol", "pl_eqt", "pl_orbincl",
    "pl_trandep", "pl_trandur", "pl_ratdor", "pl_ratror", "pl_imppar",
    # Transit midpoint: required to fold a light curve on a PUBLISHED ephemeris.
    # Without it, the epoch must be fitted, which in a crowded multi-planet
    # system locks onto whichever blend is deepest rather than the target planet.
    "pl_tranmid",
]

_STAR_MEASURED = [
    "st_teff", "st_rad", "st_mass", "st_lum", "st_met", "st_age", "st_logg",
]

_SYSTEM_MEASURED = ["sy_dist", "sy_plx"]

#: Parameters we propagate uncertainty on. Each contributes value + err1 + err2 + lim.
UNCERTAIN_PARAMS = _PLANET_MEASURED + _STAR_MEASURED + _SYSTEM_MEASURED

_PHOTOMETRY = ["sy_vmag", "sy_kmag", "sy_jmag", "sy_hmag", "sy_gaiamag", "sy_tmag"]

_POSITION = ["ra", "dec"]

_FLAGS = [
    "tran_flag", "rv_flag", "ttv_flag", "ima_flag", "pul_flag",
    "micro_flag", "ast_flag", "obm_flag", "pl_controv_flag",
]

#: Observational-coverage counters. These are how the archive reports how much
#: evidence exists for a target, and they drive the data-confidence matrix.
_COVERAGE = [
    "pl_ntranspec", "pl_nespec", "pl_ndispec", "pl_nnotes",
    "st_nrvc", "st_nphot", "st_nspec",
]

#: Measurements whose per-value publication link we carry through to the UI.
REFLINK_PARAMS = [
    "pl_rade", "pl_bmasse", "pl_orbper", "pl_orbsmax", "pl_insol", "pl_eqt",
    "pl_dens", "pl_orbeccen", "st_teff", "st_rad", "st_mass", "st_lum",
    "st_met", "st_age", "sy_dist",
]


def _with_errors(cols: list[str]) -> list[str]:
    """Expand value columns into value + upper err + lower err + limit flag."""
    out: list[str] = []
    for c in cols:
        out += [c, c + "err1", c + "err2", c + "lim"]
    return out


def _dedupe(cols: list[str]) -> list[str]:
    seen: set = set()
    out: list[str] = []
    for c in cols:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def pscomppars_columns() -> list[str]:
    """Column list for the composite-parameters spine."""
    cols = (
        _IDENT
        + _with_errors(_PLANET_MEASURED)
        + _with_errors(_STAR_MEASURED)
        + [c for c in _with_errors(_SYSTEM_MEASURED) if not c.endswith("lim")]
        + ["st_spectype", "pl_bmassprov", "st_rotp", "st_vsin"]
        + _PHOTOMETRY
        + _POSITION
        + _FLAGS
        + _COVERAGE
        + ["tic_id", "hd_name", "hip_name", "gaia_dr3_id", "gaia_dr2_id"]
        + [p + "_reflink" for p in REFLINK_PARAMS]
        + ["rowupdate"]
    )
    return _dedupe(cols)


def ps_columns() -> list[str]:
    """Column list for the per-publication evidence layer."""
    cols = (
        _IDENT
        + ["default_flag", "soltype"]
        + _with_errors(_PLANET_MEASURED)
        + _with_errors(_STAR_MEASURED)
        + [c for c in _with_errors(_SYSTEM_MEASURED) if not c.endswith("lim")]
        + ["st_spectype", "pl_bmassprov"]
        + _POSITION
        + _FLAGS
        + ["pl_refname", "st_refname", "sy_refname", "disc_refname"]
        + ["pl_pubdate", "rowupdate", "releasedate"]
        + ["tic_id", "hd_name", "hip_name"]
    )
    return _dedupe(cols)


_SCHEMA_CACHE: dict[str, list[str]] = {}


def available_columns(table: str) -> list[str]:
    """Column names the archive currently exposes for ``table``.

    Queried from ``TAP_SCHEMA.columns`` rather than assumed. The archive adds and
    retires columns between data releases, and a hard-coded list that silently
    drifts is how a pipeline starts returning a 400 in six months' time.
    Cached per process.
    """
    key = table.lower()
    if key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[key]
    import io as _io

    from earth2.data_sources.base import http_get

    adql = "select column_name from TAP_SCHEMA.columns where table_name = '" + table + "'"
    res = http_get(TAP_SYNC, {"query": adql, "format": "csv"})
    cols = pd.read_csv(_io.BytesIO(res.content))["column_name"].astype(str).tolist()
    if not cols:
        # Some tables are registered under a different case in TAP_SCHEMA.
        adql = "select column_name from TAP_SCHEMA.columns where lower(table_name) = '" + key + "'"
        res = http_get(TAP_SYNC, {"query": adql, "format": "csv"})
        cols = pd.read_csv(_io.BytesIO(res.content))["column_name"].astype(str).tolist()
    _SCHEMA_CACHE[key] = cols
    return cols


def validate_columns(table: str, columns: list[str]) -> tuple[list[str], list[str]]:
    """Split a requested column list into (present, absent) against the live schema.

    Returns the kept columns in their original order plus the dropped ones, so
    the caller can record the drop in the manifest instead of failing opaquely.
    """
    have = {c.lower() for c in available_columns(table)}
    keep = [c for c in columns if c.lower() in have]
    drop = [c for c in columns if c.lower() not in have]
    return keep, drop


def build_adql(
    table: str,
    columns: list[str] | None = None,
    where: str = "",
    order_by: str = "",
) -> str:
    sel = ", ".join(columns) if columns else "*"
    q = "select " + sel + " from " + table
    if where:
        q += " where " + where
    if order_by:
        q += " order by " + order_by
    return q


def query(
    dataset_id: str,
    table: str,
    columns: list[str] | None = None,
    where: str = "",
    order_by: str = "",
    *,
    doi: str = "",
    notes: str = "",
    use_cache: bool = True,
    validate: bool = True,
) -> tuple[pd.DataFrame, Manifest]:
    """Run one ADQL query against the archive's TAP service.

    Returns the parsed table and its manifest. The literal ADQL string is stored
    in the manifest so the retrieval is reproducible verbatim.

    When ``validate`` is set and an explicit column list is given, the list is
    checked against the live TAP schema first. Columns the archive no longer
    exposes are dropped and recorded in the manifest notes rather than turning
    the whole retrieval into an ORA-00904.
    """
    if validate and columns:
        columns, dropped = validate_columns(table, columns)
        if dropped:
            notes = (notes + " [columns absent from live schema, dropped: "
                     + ", ".join(dropped) + "]").strip()
    adql = build_adql(table, columns, where, order_by)
    return fetch_csv(
        dataset_id,
        TAP_SYNC,
        {"query": adql, "format": "csv"},
        archive=ARCHIVE_NAME,
        source_table=table,
        query=adql,
        citation=CITATION,
        doi=doi,
        archive_url=ARCHIVE_URL,
        notes=notes,
        use_cache=use_cache,
    )


# --------------------------------------------------------------------------
# Dataset registry -- the definitive list of what this project ingests
# --------------------------------------------------------------------------
def dataset_specs() -> dict[str, dict]:
    """Every NASA Exoplanet Archive dataset the pipeline retrieves.

    Kept as data rather than as a pile of functions so ``sync`` can iterate over
    it, the docs can be generated from it, and adding a source is a one-entry
    change.
    """
    return {
        "nasa_pscomppars": {
            "table": "pscomppars",
            "columns": pscomppars_columns(),
            "doi": DOI_PSCOMPPARS,
            "role": "spine",
            "notes": (
                "Composite parameters: one row per confirmed planet, each column taken "
                "from the best available published value independently. Highest "
                "completeness; a row is NOT a self-consistent single-paper solution."
            ),
        },
        "nasa_ps": {
            "table": "ps",
            "columns": ps_columns(),
            "doi": DOI_PS,
            "role": "evidence",
            "notes": (
                "One row per published parameter set. Used to count independent "
                "references per planet and to measure inter-publication disagreement."
            ),
        },
        "nasa_toi": {
            "table": "toi",
            "columns": None,
            "doi": DOI_TOI,
            "role": "candidates",
            "notes": (
                "TESS Objects of Interest. Candidates, not confirmed planets; "
                "tfopwg_disp carries the TFOP working group disposition."
            ),
        },
        "nasa_k2pandc": {
            "table": "k2pandc",
            "columns": [
                "pl_name", "hostname", "epic_hostname", "epic_candname", "k2_name",
                "disposition", "discoverymethod", "disc_year", "disc_facility",
                "pl_orbper", "pl_orbpererr1", "pl_orbpererr2",
                "pl_rade", "pl_radeerr1", "pl_radeerr2",
                "pl_bmasse", "pl_bmasseerr1", "pl_bmasseerr2",
                "pl_orbsmax", "pl_insol", "pl_eqt", "pl_trandep", "pl_trandur",
                "st_teff", "st_rad", "st_mass", "st_logg", "st_met",
                "sy_dist", "ra", "dec", "sy_vmag", "sy_kmag", "sy_gaiamag",
                "tic_id", "default_flag", "soltype", "rowupdate",
            ],
            "doi": DOI_K2,
            "role": "candidates",
            "notes": "K2 planets and candidates.",
        },
        "nasa_koi_dr25": {
            "table": "q1_q17_dr25_koi",
            "columns": [
                "kepid", "kepoi_name", "kepler_name", "koi_disposition",
                "koi_pdisposition", "koi_score",
                "koi_period", "koi_period_err1", "koi_period_err2",
                "koi_prad", "koi_prad_err1", "koi_prad_err2",
                "koi_sma", "koi_teq", "koi_insol", "koi_insol_err1", "koi_insol_err2",
                "koi_depth", "koi_duration", "koi_ror", "koi_dor", "koi_impact",
                "koi_steff", "koi_srad", "koi_smass", "koi_slogg", "koi_smet",
                "koi_kepmag", "ra", "dec",
                "koi_fpflag_nt", "koi_fpflag_ss", "koi_fpflag_co", "koi_fpflag_ec",
                "koi_model_snr", "koi_num_transits", "koi_tce_plnt_num",
            ],
            "doi": DOI_KOI,
            "role": "candidates",
            "notes": (
                "Kepler Objects of Interest, Q1-Q17 DR25. Includes the four false-positive "
                "flags (not-transit-like, stellar eclipse, centroid offset, ephemeris match) "
                "which must be respected before treating a KOI as a planet candidate."
            ),
        },
        "nasa_tce_dr25": {
            "table": "q1_q17_dr25_tce",
            "columns": [
                "kepid", "tce_plnt_num", "tce_period", "tce_period_err",
                "tce_time0bk", "tce_duration", "tce_depth", "tce_depth_err",
                "tce_prad", "tce_prad_err", "tce_eqt", "tce_insol",
                "tce_ror", "tce_dor", "tce_impact", "tce_model_snr",
                "tce_num_transits", "tce_max_mult_ev",
                "tce_steff", "tce_srad", "tce_slogg", "tce_smet", "tce_smass",
                "ra", "dec",
            ],
            "doi": "",
            "role": "events",
            "notes": (
                "Kepler Threshold Crossing Events, DR25. These are detections, the large "
                "majority of which are NOT planets. Ingested to characterise detection "
                "sensitivity and selection effects, never counted as planets."
            ),
        },
        "nasa_transitspec": {
            "table": "transitspec",
            "columns": None,
            "doi": DOI_TRANSITSPEC,
            "role": "atmosphere",
            "notes": (
                "Transmission spectroscopy: per-bandpass transit depths for planets with "
                "published atmospheric observations. This is genuine PLANETARY ATMOSPHERE "
                "data -- distinct from the stellar spectra indexed in the `spectra` table."
            ),
        },
        "nasa_emissionspec": {
            "table": "emissionspec",
            "columns": None,
            "doi": DOI_EMISSIONSPEC,
            "role": "atmosphere",
            "notes": (
                "Emission spectroscopy: per-bandpass secondary-eclipse depths and "
                "brightness temperatures."
            ),
        },
        "nasa_spectra_index": {
            "table": "spectra",
            "columns": None,
            "doi": "",
            "role": "atmosphere_index",
            "notes": (
                "Index of archived spectrum files. spec_type distinguishes transmission / "
                "emission / stellar. Carries file paths, wavelength coverage and bibcodes."
            ),
        },
        "nasa_microlensing": {
            "table": "ml",
            "columns": [
                "pl_name", "hostname", "ml_name", "discoverymethod", "disc_year",
                "disc_facility", "pl_massj", "pl_massjerr1", "pl_massjerr2",
                "pl_orbsmax", "st_mass", "st_masserr1", "st_masserr2",
                "ra", "dec", "sy_dist",
            ],
            "doi": "",
            "role": "population",
            "notes": (
                "Microlensing planets. Included for population and selection-bias analysis: "
                "microlensing probes a very different region of parameter space to transits."
            ),
        },
        "nasa_di_stars": {
            "table": "di_stars_exep",
            "columns": None,
            "doi": "",
            "role": "population",
            "notes": "Direct-imaging target stars (NASA Exoplanet Exploration Program list).",
        },
        "nasa_stellarhosts": {
            "table": "stellarhosts",
            "columns": [
                "hostname", "sy_snum", "sy_pnum", "st_spectype",
                "st_teff", "st_tefferr1", "st_tefferr2",
                "st_rad", "st_raderr1", "st_raderr2",
                "st_mass", "st_masserr1", "st_masserr2",
                "st_lum", "st_lumerr1", "st_lumerr2",
                "st_met", "st_meterr1", "st_meterr2", "st_metratio",
                "st_age", "st_ageerr1", "st_ageerr2",
                "st_logg", "st_rotp", "st_vsin",
                "sy_dist", "sy_disterr1", "sy_disterr2", "sy_plx",
                "ra", "dec", "sy_vmag", "sy_kmag", "sy_gaiamag", "sy_tmag",
                "st_refname", "sy_refname",
            ],
            "doi": "",
            "role": "evidence",
            "notes": "Per-publication stellar host parameters; the stellar analogue of `ps`.",
        },
    }


def fetch_dataset(dataset_id: str, use_cache: bool = True) -> tuple[pd.DataFrame, Manifest]:
    specs = dataset_specs()
    if dataset_id not in specs:
        raise KeyError("Unknown NASA dataset id: " + dataset_id)
    s = specs[dataset_id]
    return query(
        dataset_id,
        s["table"],
        s["columns"],
        doi=s.get("doi", ""),
        notes=s.get("notes", ""),
        use_cache=use_cache,
    )


def fetch_aliases(names: list[str], use_cache: bool = True) -> tuple[pd.DataFrame, Manifest]:
    """Resolve archive aliases for a specific list of objects.

    ``object_aliases`` holds ~3.9M rows. We never pull it whole; we query only
    the objects that actually reached the ranking stage.
    """
    safe = [n.replace("'", "''") for n in names if isinstance(n, str) and n]
    if not safe:
        raise ValueError("fetch_aliases requires at least one object name")
    in_list = ", ".join("'" + n + "'" for n in safe)
    adql = "select * from object_aliases where resolved_name in (" + in_list + ")"
    return fetch_csv(
        "nasa_object_aliases_subset",
        TAP_SYNC,
        {"query": adql, "format": "csv"},
        archive=ARCHIVE_NAME,
        source_table="object_aliases",
        query=adql,
        citation=CITATION,
        archive_url=ARCHIVE_URL,
        notes="Alias resolution for " + str(len(safe)) + " objects that entered the ranking stage.",
        use_cache=use_cache,
    )
