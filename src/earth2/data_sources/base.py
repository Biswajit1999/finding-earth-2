"""Shared plumbing for every archive connector.

Responsibilities kept here so connectors stay thin:

* a retrying HTTP session with sane timeouts and an identifying User-Agent,
* an on-disk cache of raw payloads keyed by dataset id,
* automatic manifest creation on every successful retrieval.

Design rule: a connector returns ``(DataFrame, Manifest)``. It never returns a
DataFrame alone, because a table without provenance is exactly the thing this
project refuses to produce.
"""

from __future__ import annotations

import gzip
import io
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

from earth2 import __version__
from earth2.config import (
    CACHE_MAX_AGE_HOURS,
    HTTP_BACKOFF,
    HTTP_RETRIES,
    HTTP_TIMEOUT,
    RAW_DIR,
    USER_AGENT,
)
from earth2.provenance import Manifest, sha256_bytes, utc_now_iso


class ArchiveError(RuntimeError):
    """Raised when an archive cannot satisfy a request after retries."""


@dataclass
class FetchResult:
    """Raw payload plus the metadata needed to build a manifest."""

    content: bytes
    url: str
    from_cache: bool
    elapsed_s: float


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    return s


_SESSION = make_session()


def _cache_path(dataset_id: str) -> Path:
    return RAW_DIR / f"{dataset_id}.csv.gz"


def cache_age_hours(dataset_id: str) -> float | None:
    p = _cache_path(dataset_id)
    if not p.exists():
        return None
    return (time.time() - p.stat().st_mtime) / 3600.0


def read_cache(dataset_id: str) -> bytes | None:
    p = _cache_path(dataset_id)
    if not p.exists():
        return None
    with gzip.open(p, "rb") as fh:
        return fh.read()


def write_cache(dataset_id: str, payload: bytes) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    p = _cache_path(dataset_id)
    with gzip.open(p, "wb", compresslevel=6) as fh:
        fh.write(payload)
    return p


def http_get(
    url: str,
    params: dict | None = None,
    timeout: int = HTTP_TIMEOUT,
    retries: int = HTTP_RETRIES,
    backoff: float = HTTP_BACKOFF,
) -> FetchResult:
    """GET with exponential backoff.

    Retries on connection errors, timeouts, and 5xx/429. Does not retry other
    4xx -- a malformed ADQL query will fail identically every time and retrying
    only hides the error message.
    """
    last: Exception | None = None
    t0 = time.time()
    for attempt in range(retries):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return FetchResult(r.content, r.url, False, time.time() - t0)
            if r.status_code in (429, 500, 502, 503, 504):
                last = ArchiveError(f"HTTP {r.status_code} from {r.url}: {r.text[:300]}")
            else:
                raise ArchiveError(f"HTTP {r.status_code} from {r.url}: {r.text[:600]}")
        except (requests.Timeout, requests.ConnectionError) as exc:
            last = exc
        if attempt < retries - 1:
            time.sleep(backoff * (2**attempt))
    raise ArchiveError(f"GET failed after {retries} attempts: {url} :: {last}")


def fetch_csv(
    dataset_id: str,
    url: str,
    params: dict | None,
    *,
    archive: str,
    source_table: str,
    query: str,
    citation: str = "",
    doi: str = "",
    archive_url: str = "",
    notes: str = "",
    use_cache: bool = True,
    max_age_hours: float = CACHE_MAX_AGE_HOURS,
    low_memory: bool = False,
) -> tuple[pd.DataFrame, Manifest]:
    """Retrieve a CSV payload, parse it, cache it, and write its manifest.

    The manifest hashes the payload *as received*, before parsing, so the hash
    is a property of what the archive said rather than of how pandas felt about
    it that day.
    """
    payload: bytes | None = None
    from_cache = False
    resolved_url = url

    if use_cache:
        age = cache_age_hours(dataset_id)
        if age is not None and age <= max_age_hours:
            payload = read_cache(dataset_id)
            from_cache = payload is not None

    if payload is None:
        res = http_get(url, params=params)
        payload = res.content
        resolved_url = res.url
        write_cache(dataset_id, payload)

    try:
        df = pd.read_csv(io.BytesIO(payload), low_memory=low_memory)
    except Exception as exc:  # noqa: BLE001
        head = payload[:400].decode("utf-8", "replace")
        raise ArchiveError(f"{dataset_id}: could not parse CSV payload ({exc}). Head: {head!r}") from exc

    manifest = Manifest(
        dataset_id=dataset_id,
        archive=archive,
        source_table=source_table,
        query=query,
        request_url=resolved_url,
        retrieved_utc=utc_now_iso(),
        n_rows=int(len(df)),
        n_columns=int(df.shape[1]),
        sha256=sha256_bytes(payload),
        bytes_raw=len(payload),
        citation=citation,
        doi=doi,
        archive_url=archive_url,
        columns=[str(c) for c in df.columns],
        notes=(notes + (" [served from local cache]" if from_cache else "")).strip(),
        earth2_version=__version__,
        status="ok",
    )
    manifest.save()
    return df, manifest
