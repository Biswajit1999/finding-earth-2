"""Retrieval manifests.

A manifest is the complete, machine-readable answer to "where did this file come
from?": the archive, the exact query, the URL, the retrieval timestamp, the
payload hash, the row/column count, and the citation the archive asks for.

Manifests are committed to Git. Raw payloads are not. Between them, any user can
reconstruct the exact input the analysis ran on -- and detect if an archive has
since changed its answer, because the hash will not match.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from earth2.config import MANIFEST_DIR


def utc_now_iso() -> str:
    """Current UTC time, ISO-8601, second precision, explicit Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


@dataclass
class Manifest:
    """One retrieval event from one archive.

    Attributes
    ----------
    dataset_id
        Stable local identifier, e.g. ``nasa_pscomppars``. Used as the manifest
        filename and as the join key from processed tables back to provenance.
    archive
        Human-readable archive name, e.g. ``NASA Exoplanet Archive``.
    source_table
        The archive-side table or endpoint actually queried.
    query
        The exact ADQL/SQL or API parameters submitted. Reproducibility hinges
        on this being the literal string sent, not a paraphrase.
    request_url
        Fully-formed URL (without credentials) that produced the payload.
    retrieved_utc
        ISO-8601 UTC timestamp of successful retrieval.
    n_rows, n_columns
        Shape of the payload as parsed.
    sha256
        Hash of the raw payload bytes exactly as received.
    citation
        The acknowledgement/citation the archive requires for this dataset.
    doi
        Dataset DOI where the archive publishes one.
    notes
        Free text: substitutions, partial failures, known caveats.
    """

    dataset_id: str
    archive: str
    source_table: str
    query: str
    request_url: str
    retrieved_utc: str
    n_rows: int
    n_columns: int
    sha256: str
    bytes_raw: int = 0
    citation: str = ""
    doi: str = ""
    archive_url: str = ""
    columns: list[str] = field(default_factory=list)
    notes: str = ""
    earth2_version: str = ""
    status: str = "ok"  # ok | partial | failed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def path(self) -> Path:
        return MANIFEST_DIR / f"{self.dataset_id}.json"

    def save(self) -> Path:
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        p = self.path
        p.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return p

    @classmethod
    def load(cls, dataset_id: str) -> Manifest:
        p = MANIFEST_DIR / f"{dataset_id}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


class ManifestStore:
    """Read-side helper over the manifest directory."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory else MANIFEST_DIR

    def ids(self) -> list[str]:
        if not self.directory.exists():
            return []
        return sorted(p.stem for p in self.directory.glob("*.json"))

    def all(self) -> list[Manifest]:
        out: list[Manifest] = []
        known = set(Manifest.__dataclass_fields__)  # type: ignore[attr-defined]
        for i in self.ids():
            # Manifest.load(i) always reads from the module-level MANIFEST_DIR,
            # not self.directory -- reading the file directly here is what
            # makes a ManifestStore(directory=...) override actually work,
            # rather than silently falling back to the default directory
            # whenever it differs from the one passed in.
            try:
                p = self.directory / f"{i}.json"
                data = json.loads(p.read_text(encoding="utf-8"))
                out.append(Manifest(**{k: v for k, v in data.items() if k in known}))
            except Exception:  # noqa: BLE001 - a corrupt manifest must not kill reporting
                continue
        return out

    def total_source_records(self) -> int:
        """Total rows retrieved across every successful manifest.

        This is the number the README and the website quote as "source records".
        It is a sum of real retrieved rows -- never a target, never padded.
        """
        return sum(m.n_rows for m in self.all() if m.status in ("ok", "partial"))

    def summary_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "dataset_id": m.dataset_id,
                "archive": m.archive,
                "source_table": m.source_table,
                "n_rows": m.n_rows,
                "n_columns": m.n_columns,
                "retrieved_utc": m.retrieved_utc,
                "status": m.status,
                "sha256_short": m.sha256[:12],
                "doi": m.doi,
            }
            for m in self.all()
        ]
