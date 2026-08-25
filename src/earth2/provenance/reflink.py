"""Parse the NASA Exoplanet Archive's per-measurement reference links.

The archive attaches an HTML anchor to each composite parameter naming where
that specific value came from::

    <a refstr=STASSUN_ET_AL__2017
       href=https://ui.adsabs.harvard.edu/abs/2017AJ....153..136S/abstract
       target=ref>Stassun et al. 2017</a>

This is the raw material for the project's provenance panel: it means a reader
can be told, per number, which paper produced it.

Two kinds of link, which must not be conflated
----------------------------------------------
Some values are not from a publication at all::

    <a refstr=CALCULATED_VALUE href=/docs/pscp_calc.html target=_blank>Calculated Value</a>

These were computed by the archive from other columns (for example a radius
derived from a transit depth and a stellar radius, or a mass from a mass-radius
relation). Presenting such a value as "measured by Stassun et al." would be
false, so :func:`parse_reflink` flags them separately and the provenance table
records them as ``archive_calculated`` rather than as a citation.
"""

from __future__ import annotations

import html as _html
import re
from collections.abc import Sequence
from typing import Any

import pandas as pd

__all__ = [
    "ADS_BIBCODE_RE",
    "measurement_provenance_table",
    "parse_reflink",
    "reference_summary",
]

_REFSTR_RE = re.compile(r"refstr=([^\s>]+)", re.IGNORECASE)
_HREF_RE = re.compile(r"href=([^\s>]+)", re.IGNORECASE)
_LABEL_RE = re.compile(r">([^<]*)</a>", re.IGNORECASE)

#: ADS bibcodes are exactly 19 characters: YYYYJJJJJVVVVMPPPPA
ADS_BIBCODE_RE = re.compile(r"/abs/(?P<bibcode>[^/]{19})(?:/|$)")


def parse_reflink(html: str | None) -> dict[str, Any]:
    """Decompose one archive reference anchor.

    Returns a dict with ``ref_key``, ``label``, ``url``, ``bibcode`` and
    ``kind``, where ``kind`` is one of ``publication``, ``archive_calculated``
    or ``unknown``.
    """
    empty = {
        "ref_key": None, "label": None, "url": None,
        "bibcode": None, "kind": "unknown",
    }
    if html is None or not isinstance(html, str) or not html.strip():
        return empty
    if html.strip().lower() in ("<NA>".lower(), "nan", "none"):
        return empty

    m_key = _REFSTR_RE.search(html)
    m_href = _HREF_RE.search(html)
    m_label = _LABEL_RE.search(html)

    ref_key = m_key.group(1) if m_key else None
    url = m_href.group(1) if m_href else None
    # Labels arrive HTML-escaped: "Fulton &amp; Petigura 2018",
    # "Gajdo&scaron; et al. 2019". Unescape so author names render correctly
    # in the interface and in the bibliography rather than as entity soup.
    label = _html.unescape(m_label.group(1)).strip() if m_label else None

    bibcode = None
    if url:
        m_bib = ADS_BIBCODE_RE.search(url)
        if m_bib:
            bibcode = m_bib.group("bibcode")

    if ref_key and ref_key.upper() == "CALCULATED_VALUE":
        kind = "archive_calculated"
    elif bibcode or (url and "adsabs" in url.lower()) or ref_key:
        kind = "publication"
    else:
        kind = "unknown"

    # Relative archive URLs -> absolute.
    if url and url.startswith("/"):
        url = "https://exoplanetarchive.ipac.caltech.edu" + url

    return {
        "ref_key": ref_key, "label": label, "url": url,
        "bibcode": bibcode, "kind": kind,
    }


#: Human-readable names for the parameters carrying reference links.
PARAMETER_LABELS: dict[str, str] = {
    "pl_rade": "Planet radius",
    "pl_bmasse": "Planet mass",
    "pl_orbper": "Orbital period",
    "pl_orbsmax": "Semi-major axis",
    "pl_insol": "Incident flux",
    "pl_eqt": "Equilibrium temperature",
    "pl_dens": "Bulk density",
    "pl_orbeccen": "Orbital eccentricity",
    "st_teff": "Stellar effective temperature",
    "st_rad": "Stellar radius",
    "st_mass": "Stellar mass",
    "st_lum": "Stellar luminosity",
    "st_met": "Stellar metallicity",
    "st_age": "Stellar age",
    "sy_dist": "System distance",
}


def measurement_provenance_table(
    df: pd.DataFrame,
    name_col: str = "pl_name",
    parameters: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Long-format provenance: one row per (planet, parameter, source).

    Far smaller than carrying the raw HTML on every row, and directly consumable
    by the interface: given a planet and a parameter, look up which publication
    produced the number and link straight to it on ADS.
    """
    params = list(parameters) if parameters else [
        c[: -len("_reflink")] for c in df.columns if c.endswith("_reflink")
    ]

    rows: list[dict[str, Any]] = []
    for p in params:
        col = p + "_reflink"
        if col not in df.columns or name_col not in df.columns:
            continue
        value_col = p if p in df.columns else None
        sub = df[[name_col, col] + ([value_col] if value_col else [])].copy()
        for _, r in sub.iterrows():
            raw = r[col]
            if raw is None or (isinstance(raw, float)) or pd.isna(raw):
                continue
            info = parse_reflink(str(raw))
            if info["kind"] == "unknown" and not info["ref_key"]:
                continue
            rows.append({
                "pl_name": r[name_col],
                "parameter": p,
                "parameter_label": PARAMETER_LABELS.get(p, p),
                "value": (r[value_col] if value_col else None),
                "source_kind": info["kind"],
                "reference_key": info["ref_key"],
                "reference_label": info["label"],
                "reference_url": info["url"],
                "bibcode": info["bibcode"],
            })
    return pd.DataFrame(rows)


def reference_summary(prov: pd.DataFrame) -> dict[str, Any]:
    """Aggregate statistics over the provenance table.

    Includes the count of archive-calculated values, which is a genuine measure
    of how much of the catalogue is derived rather than observed.
    """
    if prov.empty:
        return {"n_links": 0}
    kinds = prov["source_kind"].value_counts().to_dict()
    pubs = prov[prov["source_kind"] == "publication"]
    return {
        "n_links": int(len(prov)),
        "by_kind": {str(k): int(v) for k, v in kinds.items()},
        "n_distinct_publications": int(pubs["reference_key"].nunique()),
        "n_with_ads_bibcode": int(pubs["bibcode"].notna().sum()),
        "n_planets_covered": int(prov["pl_name"].nunique()),
        "most_cited_sources": {
            str(k): int(v) for k, v in pubs["reference_label"].value_counts().head(15).items()
        },
        "archive_calculated_by_parameter": {
            str(k): int(v)
            for k, v in prov[prov["source_kind"] == "archive_calculated"]["parameter"]
            .value_counts().items()
        },
    }
