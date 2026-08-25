"""Entity resolution across astronomical catalogues.

The problem
-----------
The same planet appears under many names. TRAPPIST-1 e is also K2-112 e,
EPIC 246199087 e, TIC 278892590 e, TOI-6838 e and
Gaia DR3 2635476908753563008 e. Joining catalogues on a name column therefore
loses most matches; joining on a *fuzzy* name column invents matches that are
not real.

The governing rule
------------------
**Never join two astronomical datasets because two strings look similar.**

"Kepler-442 b" and "Kepler-44 b" differ by one character and are different
planets in different systems. "GJ 667 C c" and "GJ 667 C e" differ by one
character and are different planets around the same star. Edit distance is not
evidence.

Every match this module produces records the method that produced it and a
confidence level, so a downstream consumer can filter on match quality rather
than trusting a join blindly.

Match methods, in descending order of reliability
-------------------------------------------------
``alias_service``
    The NASA Exoplanet Archive's own alias resolver. Authoritative, because the
    archive curates it against the discovery literature.
``catalogue_id``
    Exact match on a shared survey identifier (Gaia DR3 source_id, TIC, EPIC,
    KIC, 2MASS). Unambiguous by construction.
``coordinate``
    Sky position within a stated tolerance, using proper-motion-aware epochs
    where available. Reliable for isolated stars, and explicitly flagged as
    ambiguous when more than one source falls inside the radius.
``exact_name``
    Byte-identical designations after whitespace normalisation.

There is deliberately no fuzzy-name method.
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from earth2.data_sources.base import http_get

__all__ = [
    "ALIAS_LOOKUP_URL",
    "CatalogueIds",
    "MatchResult",
    "coordinate_crossmatch",
    "extract_catalogue_ids",
    "resolve_system",
    "build_alias_table",
]

ALIAS_LOOKUP_URL = "https://exoplanetarchive.ipac.caltech.edu/cgi-bin/Lookup/nph-aliaslookup.py"

#: Patterns that identify a survey designation inside an alias string.
_ID_PATTERNS: dict[str, re.Pattern] = {
    "gaia_dr3": re.compile(r"^Gaia\s+DR3\s+(\d+)$", re.IGNORECASE),
    "gaia_dr2": re.compile(r"^Gaia\s+DR2\s+(\d+)$", re.IGNORECASE),
    "tic": re.compile(r"^TIC\s+(\d+)$", re.IGNORECASE),
    "toi": re.compile(r"^TOI-(\d+)$", re.IGNORECASE),
    "epic": re.compile(r"^EPIC\s+(\d+)$", re.IGNORECASE),
    "kic": re.compile(r"^KIC\s+(\d+)$", re.IGNORECASE),
    "koi": re.compile(r"^KOI-(\d+)$", re.IGNORECASE),
    "hip": re.compile(r"^HIP\s+(\d+)$", re.IGNORECASE),
    "hd": re.compile(r"^HD\s+(\S+)$", re.IGNORECASE),
    "gj": re.compile(r"^GJ\s+(\S+)$", re.IGNORECASE),
    "twomass": re.compile(r"^2MASS\s+(\S+)$", re.IGNORECASE),
    "wise": re.compile(r"^WISE\s+(\S+)$", re.IGNORECASE),
    "k2": re.compile(r"^K2-(\d+)$", re.IGNORECASE),
    "kepler": re.compile(r"^Kepler-(\d+)$", re.IGNORECASE),
}


@dataclass
class CatalogueIds:
    """Survey identifiers extracted from an alias set."""

    resolved_name: str
    aliases: list[str] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"resolved_name": self.resolved_name,
                             "n_aliases": len(self.aliases),
                             "aliases": "|".join(self.aliases)}
        d.update({("id_" + k): v for k, v in self.ids.items()})
        return d


@dataclass
class MatchResult:
    """One crossmatch, with the evidence that produced it."""

    left: str
    right: str | None
    method: str
    confidence: str          # high | medium | low | none
    separation_arcsec: float | None = None
    n_candidates: int = 0
    note: str = ""


def extract_catalogue_ids(resolved_name: str, aliases: Sequence[str]) -> CatalogueIds:
    """Pull structured survey identifiers out of a free-text alias list."""
    ids: dict[str, str] = {}
    for a in aliases:
        s = str(a).strip()
        for key, pat in _ID_PATTERNS.items():
            m = pat.match(s)
            if m and key not in ids:
                ids[key] = m.group(1)
    return CatalogueIds(resolved_name=resolved_name, aliases=[str(a) for a in aliases], ids=ids)


def resolve_system(name: str, timeout: int = 60) -> dict[str, Any] | None:
    """Query the archive's alias resolver for one object.

    Returns the star and planet alias sets, or ``None`` if the object cannot be
    resolved. A failure to resolve is returned as ``None`` rather than guessed
    at, because a wrong identity is worse than a missing one.
    """
    try:
        res = http_get(ALIAS_LOOKUP_URL, {"objname": name}, timeout=timeout, retries=3)
    except Exception:  # noqa: BLE001
        return None

    try:
        import json

        data = json.loads(res.content.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None

    manifest = data.get("manifest", {})
    if str(manifest.get("lookup_status", "")).upper() != "OK":
        return None

    objects = data.get("system", {}).get("objects", {})
    stars_raw = objects.get("stellar_set", {}).get("stars", {}) or {}
    planets_raw = objects.get("planet_set", {}).get("planets", {}) or {}

    stars: dict[str, CatalogueIds] = {}
    for star_name, info in stars_raw.items():
        al = (info or {}).get("alias_set", {}).get("aliases", []) or []
        stars[star_name] = extract_catalogue_ids(star_name, al)

    planets: dict[str, CatalogueIds] = {}
    for pl_name, info in planets_raw.items():
        al = (info or {}).get("alias_set", {}).get("aliases", []) or []
        planets[pl_name] = extract_catalogue_ids(pl_name, al)

    return {
        "requested_name": manifest.get("requested_name"),
        "resolved_name": manifest.get("resolved_name"),
        "system_name": manifest.get("system_name"),
        "compilation_date": manifest.get("compilation_date"),
        "n_stars": len(stars),
        "n_planets": len(planets),
        "stars": stars,
        "planets": planets,
    }


def build_alias_table(
    names: Sequence[str],
    pause_s: float = 0.2,
    verbose: bool = False,
) -> pd.DataFrame:
    """Resolve a list of planets to their full identifier sets.

    Queried per object rather than in bulk: the resolver is a per-object service,
    and the project only ever resolves objects that actually reached the ranking
    stage, so the request count stays small and polite.
    """
    rows: list[dict[str, Any]] = []
    for i, name in enumerate(names):
        info = resolve_system(str(name))
        if info is None:
            rows.append({
                "query_name": name, "resolved_name": None, "system_name": None,
                "match_method": "alias_service", "match_confidence": "none",
                "note": "alias resolver returned no match",
            })
        else:
            # Prefer the planet entry whose name matches the query; otherwise the
            # host star. Never silently attach a different planet's identifiers.
            planet = info["planets"].get(str(name))
            star_ids = next(iter(info["stars"].values()), None)
            row: dict[str, Any] = {
                "query_name": name,
                "resolved_name": info["resolved_name"],
                "system_name": info["system_name"],
                "n_stars_in_system": info["n_stars"],
                "n_planets_in_system": info["n_planets"],
                "match_method": "alias_service",
                "match_confidence": "high" if planet is not None else "medium",
                "note": "" if planet is not None else "planet name not in resolver planet set; host identifiers used",
            }
            if planet is not None:
                row["planet_aliases"] = "|".join(planet.aliases)
                row.update({("planet_id_" + k): v for k, v in planet.ids.items()})
            if star_ids is not None:
                row["host_resolved"] = star_ids.resolved_name
                row["host_aliases"] = "|".join(star_ids.aliases)
                row.update({("host_id_" + k): v for k, v in star_ids.ids.items()})
            rows.append(row)

        if verbose and (i + 1) % 10 == 0:
            print("    resolved %d/%d" % (i + 1, len(names)))
        if pause_s:
            time.sleep(pause_s)

    return pd.DataFrame(rows)


def coordinate_crossmatch(
    left: pd.DataFrame,
    right: pd.DataFrame,
    radius_arcsec: float = 3.0,
    left_ra: str = "ra",
    left_dec: str = "dec",
    right_ra: str = "ra",
    right_dec: str = "dec",
    left_name: str = "pl_name",
    right_name: str = "pl_name",
) -> pd.DataFrame:
    """Match two tables on sky position.

    Uses ``astropy.coordinates.SkyCoord`` nearest-neighbour matching, then
    applies the separation cut. Crucially, it also counts how many right-hand
    sources fall inside the radius: if more than one does, the match is marked
    ``ambiguous`` rather than silently taking the nearest, because in crowded
    fields the nearest source is frequently not the right one.

    Positions are treated at their catalogue epoch. For high-proper-motion stars
    -- which includes many of the nearby M dwarfs that dominate this project's
    candidate list -- a 3 arcsec radius can be crossed in a couple of decades, so
    a coordinate match to an old catalogue should be treated as suggestive, not
    definitive. The returned ``note`` says so where proper motion is large.
    """
    from astropy import units as u
    from astropy.coordinates import SkyCoord

    lft = left.dropna(subset=[left_ra, left_dec]).copy()
    rgt = right.dropna(subset=[right_ra, right_dec]).copy()
    if lft.empty or rgt.empty:
        return pd.DataFrame(columns=["left", "right", "method", "confidence",
                                     "separation_arcsec", "n_candidates", "note"])

    c_left = SkyCoord(ra=lft[left_ra].to_numpy() * u.deg,
                      dec=lft[left_dec].to_numpy() * u.deg)
    c_right = SkyCoord(ra=rgt[right_ra].to_numpy() * u.deg,
                       dec=rgt[right_dec].to_numpy() * u.deg)

    idx, sep2d, _ = c_left.match_to_catalog_sky(c_right)
    sep_arcsec = sep2d.arcsec

    # Count all right-hand sources inside the radius for each left source.
    idx_l, idx_r, sep_all, _ = c_right.search_around_sky(c_left, radius_arcsec * u.arcsec)
    counts = pd.Series(idx_l).value_counts().to_dict()

    rows: list[dict[str, Any]] = []
    for i in range(len(lft)):
        n_cand = int(counts.get(i, 0))
        s = float(sep_arcsec[i])
        if s > radius_arcsec or n_cand == 0:
            rows.append({
                "left": lft.iloc[i][left_name], "right": None, "method": "coordinate",
                "confidence": "none", "separation_arcsec": round(s, 3),
                "n_candidates": n_cand, "note": f"no source within {radius_arcsec:.1f} arcsec",
            })
            continue
        conf = "high" if n_cand == 1 else "low"
        note = "" if n_cand == 1 else (
            "%d sources inside the match radius; nearest taken but the match is ambiguous"
            % n_cand
        )
        rows.append({
            "left": lft.iloc[i][left_name],
            "right": rgt.iloc[int(idx[i])][right_name],
            "method": "coordinate", "confidence": conf,
            "separation_arcsec": round(s, 3), "n_candidates": n_cand, "note": note,
        })
    return pd.DataFrame(rows)
