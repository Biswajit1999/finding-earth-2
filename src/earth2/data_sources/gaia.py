"""Gaia DR3 bulk crossmatch.

Scope, honestly stated
----------------------
This is an **exact-identifier crossmatch**, the most reliable kind this
project's own `crossmatch` module ranks (see
:mod:`earth2.crossmatch.resolve`'s module docstring): the NASA Exoplanet
Archive's ``pscomppars`` table already carries a ``gaia_dr3_id`` column (a
string like ``"Gaia DR3 4919009555730599936"``) for 5,970 of 6,354 confirmed
planets (94%), spanning 4,408 of 4,764 unique host systems (92.5%). This
module extracts the numeric ``source_id`` from that string and queries
Gaia's own TAP service for each host star directly by ``source_id`` --
unambiguous by construction, with no sky-position matching, tolerance radius,
or ambiguity-flagging logic needed at all.

Systems whose host has no ``gaia_dr3_id`` recorded by the NASA archive are
**not** otherwise cross-matched here (no coordinate fallback is attempted in
this integration); they simply have no Gaia row. That is a real, stated
limitation of this specific integration, not a silent gap: a host is either
crossmatched by its own already-published Gaia identifier, or it is absent.

What this adds that the NASA archive alone does not
-----------------------------------------------------
* An **independent distance check**: ``sy_dist`` (the archive's adopted
  distance, itself very often already Gaia-parallax-derived by the original
  publication) against ``1000 / parallax_mas`` computed directly here from
  Gaia's own DR3 astrometric solution -- large disagreement is worth a
  reader's attention regardless of which side of it turns out to be right.
* ``ruwe`` (Renormalised Unit Weight Error): a value well above ~1.4 is the
  standard single-star-fit-quality flag for an unresolved binary or an
  otherwise poorly-fit astrometric solution -- relevant context for a
  candidate's confidence, since planet properties derived from a host
  assumed single can be wrong if the host is actually an unresolved pair.
* ``non_single_star``: Gaia's own flag that additional non-single-star
  solutions exist for this source.
* Gaia's native G/BP/RP photometry and proper motion, for readers who want
  them independent of the archive's own compiled photometry.

What this does not add
-----------------------
Gaia's own exoplanet-relevant astrophysical parameters (e.g. GSP-Phot
stellar parameters) are deliberately not pulled in and blended with the
archive's adopted stellar parameters: this project's ranking already takes
its stellar parameters from a single, documented source (``pscomppars``) and
mixing in a second independently-derived parameter set per star would
re-introduce exactly the "two papers, one row" inconsistency the archive's
own composite-table caveat already warns about (see
:mod:`earth2.data_sources.nasa_exoplanet_archive` module docstring).
"""

from __future__ import annotations

import io
import re
import time
from typing import Any

import pandas as pd

from earth2 import __version__
from earth2.config import CACHE_MAX_AGE_HOURS, HTTP_BACKOFF, HTTP_RETRIES, HTTP_TIMEOUT
from earth2.data_sources.base import (
    ArchiveError,
    cache_age_hours,
    make_session,
    read_cache,
    write_cache,
)
from earth2.provenance import Manifest, sha256_bytes, utc_now_iso

GAIA_TAP_SYNC = "https://gea.esac.esa.int/tap-server/tap/sync"
ARCHIVE_NAME = "Gaia Archive (ESA)"
ARCHIVE_URL = "https://gea.esac.esa.int/archive/"

#: The acknowledgement Gaia DR3 papers are required to include.
#: https://www.cosmos.esa.int/web/gaia-users/credits
CITATION = (
    "This work has made use of data from the European Space Agency (ESA) mission "
    "Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing "
    "and Analysis Consortium (DPAC, https://www.cosmos.esa.int/web/gaia/dpac/consortium). "
    "Funding for the DPAC has been provided by national institutions, in particular the "
    "institutions participating in the Gaia Multilateral Agreement."
)
#: Left blank rather than guessed: Gaia DR3 datasets are DOI-tracked at
#: https://www.cosmos.esa.int/web/gaia/dr3, but this project's own discipline
#: (see the blank `doi` entries in nasa_exoplanet_archive.dataset_specs) is to
#: state a DOI only when it has been directly confirmed against the source,
#: not to write one from memory that might be subtly wrong.
DOI = ""

GAIA_SOURCE_TABLE = "gaiadr3.gaia_source"

#: Columns pulled per source. Kept to what this module's docstring says it
#: adds -- not a blend of Gaia's own derived stellar-astrophysical parameters
#: into a catalogue that already has an adopted set from elsewhere.
GAIA_COLUMNS = [
    "source_id", "ra", "dec", "parallax", "parallax_error",
    "pmra", "pmra_error", "pmdec", "pmdec_error",
    "ruwe", "non_single_star",
    "phot_g_mean_mag", "phot_bp_mean_mag", "phot_rp_mean_mag", "bp_rp",
    "radial_velocity", "radial_velocity_error",
]

_GAIA_ID_RE = re.compile(r"Gaia\s+DR3\s+(\d+)", re.IGNORECASE)


def extract_source_id(gaia_dr3_id: Any) -> int | None:
    """Parse the numeric Gaia DR3 ``source_id`` out of the archive's string form.

    The NASA Exoplanet Archive stores this as ``"Gaia DR3 4919009555730599936"``,
    not as a bare integer. Returns ``None`` for anything that does not match --
    a missing or malformed identifier must not be silently coerced to some
    other source's id.
    """
    if gaia_dr3_id is None or (isinstance(gaia_dr3_id, float) and pd.isna(gaia_dr3_id)):
        return None
    m = _GAIA_ID_RE.search(str(gaia_dr3_id))
    return int(m.group(1)) if m else None


def hosts_with_gaia_ids(pscomppars: pd.DataFrame) -> pd.DataFrame:
    """One row per unique host system with a resolvable Gaia DR3 source_id.

    Multiple planets share a host and therefore share a ``gaia_dr3_id``; this
    collapses to the host level, since the crossmatch target is the star.
    """
    if "gaia_dr3_id" not in pscomppars.columns or "hostname" not in pscomppars.columns:
        return pd.DataFrame(columns=["hostname", "source_id"])

    # Gaia source_ids are up to 19 digits -- beyond float64's 2^53 exact-integer
    # range. ANY pandas Series holding a mix of None and Python ints -- even
    # transiently, e.g. from .map()/.apply() before a caller gets to filter it
    # -- is silently promoted to float64 (NaN needs a float slot), which
    # rounds a real id like 2635476908753563008 to ...136 the moment that
    # Series is created, well before an .astype("int64") downstream. The only
    # way to avoid it is to never construct that Series at all: extract and
    # filter in plain Python first, using .tolist()/zip() over the raw column
    # values rather than any pandas vectorised .map()/.apply() call.
    pairs = [
        (host, sid)
        for host, gid in zip(pscomppars["hostname"].tolist(), pscomppars["gaia_dr3_id"].tolist())
        if (sid := extract_source_id(gid)) is not None
    ]
    if not pairs:
        return pd.DataFrame(columns=["hostname", "source_id"])
    df = pd.DataFrame(pairs, columns=["hostname", "source_id"])
    df["source_id"] = df["source_id"].astype("int64")
    return df.drop_duplicates(subset=["hostname"]).reset_index(drop=True)


def _chunk(seq: list[int], size: int) -> list[list[int]]:
    return [seq[i:i + size] for i in range(0, len(seq), size)]


_SESSION = make_session()


def _post_adql(chunk_id: str, adql: str, use_cache: bool) -> tuple[pd.DataFrame, str, bool]:
    """POST one ADQL query to Gaia's TAP service, cached by ``chunk_id``.

    Gaia's TAP endpoint rejects a GET whose query string exceeds its URL-length
    limit well before a few hundred 19-digit source_ids fit in an ``IN (...)``
    clause (confirmed directly: HTTP 414 at 400 ids in the query string). POST
    puts the ADQL in the request body instead, which Gaia's own TAP service
    accepts at 2,000+ ids with no such limit -- this is why the Gaia connector
    cannot reuse :func:`earth2.data_sources.base.fetch_csv`, which is GET-only,
    though it reuses that module's cache primitives directly.
    """
    payload: bytes | None = None
    from_cache = False
    if use_cache:
        age = cache_age_hours(chunk_id)
        if age is not None and age <= CACHE_MAX_AGE_HOURS:
            payload = read_cache(chunk_id)
            from_cache = payload is not None

    if payload is None:
        last_exc: Exception | None = None
        for attempt in range(HTTP_RETRIES):
            try:
                r = _SESSION.post(
                    GAIA_TAP_SYNC,
                    data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql},
                    timeout=HTTP_TIMEOUT,
                )
                if r.status_code == 200:
                    payload = r.content
                    break
                if r.status_code in (429, 500, 502, 503, 504):
                    last_exc = ArchiveError(f"HTTP {r.status_code} from Gaia TAP: {r.text[:300]}")
                else:
                    raise ArchiveError(f"HTTP {r.status_code} from Gaia TAP: {r.text[:600]}")
            except Exception as exc:  # noqa: BLE001 -- retried below, re-raised after
                last_exc = exc
            if attempt < HTTP_RETRIES - 1:
                time.sleep(HTTP_BACKOFF * (2**attempt))
        if payload is None:
            raise ArchiveError(f"Gaia TAP POST failed after {HTTP_RETRIES} attempts: {last_exc}")
        write_cache(chunk_id, payload)

    df = pd.read_csv(io.BytesIO(payload))
    return df, sha256_bytes(payload), from_cache


def fetch_gaia_crossmatch(
    source_ids: list[int],
    dataset_id: str = "gaia_dr3_crossmatch",
    chunk_size: int = 1500,
    use_cache: bool = True,
) -> tuple[pd.DataFrame, Manifest]:
    """Query Gaia DR3 by exact ``source_id``, in batches.

    A ``WHERE source_id IN (...)`` ADQL query is exact-match and therefore
    cheap for Gaia's TAP service even at several thousand ids; ``chunk_size``
    exists only to keep any one POST body to a moderate size, not to work
    around a URL-length limit (POST has none here). Every chunk is cached and
    retried the same way every archive connector in this project is; the
    combined result is written under a single manifest so the crossmatch
    appears as one dataset in the provenance summary, with the number of
    chunks executed and each chunk's own payload hash recorded in its notes.

    Deliberately does **not** save a separate :class:`Manifest` file per
    chunk: ``ManifestStore.total_source_records()`` (the headline
    "N source records" figure quoted throughout this project) sums every
    manifest file's ``n_rows`` unconditionally, so a chunk manifest sitting
    alongside the aggregate manifest for the same rows would double-count
    every Gaia row in that figure. The per-chunk HTTP response is still
    cached on disk (via the same cache primitives every other connector
    uses) for fast re-runs; it just is not *also* recorded as its own
    provenance entry.
    """
    unique_ids = sorted({int(s) for s in source_ids})
    if not unique_ids:
        raise ValueError("fetch_gaia_crossmatch: no source_ids given")

    cols = ", ".join(GAIA_COLUMNS)
    frames: list[pd.DataFrame] = []
    chunk_digests: list[str] = []
    chunks = _chunk(unique_ids, chunk_size)
    any_from_cache = False

    for i, chunk in enumerate(chunks):
        id_list = ", ".join(str(s) for s in chunk)
        adql = f"select {cols} from {GAIA_SOURCE_TABLE} where source_id in ({id_list})"
        chunk_id = f"{dataset_id}_chunk{i:04d}"
        df, digest, from_cache = _post_adql(chunk_id, adql, use_cache)
        frames.append(df)
        chunk_digests.append(digest)
        any_from_cache = any_from_cache or from_cache

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=GAIA_COLUMNS)

    aggregate = Manifest(
        dataset_id=dataset_id,
        archive=ARCHIVE_NAME,
        source_table=GAIA_SOURCE_TABLE,
        query=(
            f"select {cols} from {GAIA_SOURCE_TABLE} where source_id in (...)"
            f" -- {len(chunks)} chunks of <= {chunk_size} ids each, {len(unique_ids)} ids total"
        ),
        request_url=GAIA_TAP_SYNC,
        retrieved_utc=utc_now_iso(),
        n_rows=int(len(combined)),
        n_columns=int(combined.shape[1]) if not combined.empty else len(GAIA_COLUMNS),
        sha256=sha256_bytes(
            "".join(chunk_digests).encode("ascii")
        ),  # combined fingerprint of every chunk's own payload hash
        citation=CITATION,
        doi=DOI,
        archive_url=ARCHIVE_URL,
        columns=list(combined.columns) if not combined.empty else GAIA_COLUMNS,
        notes=(
            f"Aggregate of {len(chunks)} chunked TAP queries against {len(unique_ids)} "
            "distinct source_ids (exact match, extracted from the NASA Exoplanet "
            "Archive's gaia_dr3_id column)."
            + (" Some chunks served from local cache." if any_from_cache else "")
        ),
        earth2_version=__version__,
        status="ok",
    )
    aggregate.save()
    return combined, aggregate


def crossmatch_summary(hosts: pd.DataFrame, gaia: pd.DataFrame) -> dict[str, Any]:
    """Headline crossmatch statistics for the analysis summary and README."""
    if gaia.empty:
        return {
            "n_hosts_with_gaia_dr3_id": int(len(hosts)),
            "n_hosts_crossmatched": 0,
            "n_ruwe_above_1p4": 0,
            "n_non_single_star_flagged": 0,
        }
    ruwe = pd.to_numeric(gaia.get("ruwe"), errors="coerce")
    nss = pd.to_numeric(gaia.get("non_single_star"), errors="coerce").fillna(0)
    return {
        "n_hosts_with_gaia_dr3_id": int(len(hosts)),
        "n_hosts_crossmatched": int(len(gaia)),
        "n_ruwe_above_1p4": int((ruwe > 1.4).sum()),
        "n_non_single_star_flagged": int((nss > 0).sum()),
    }
