"""Archive synchronisation.

"Real-time" in this project means *synchronised with continually maintained
public archives*. It does not mean live telescope telemetry, and the interface
says so.

Running ``python -m earth2 sync`` retrieves every registered dataset, writes a
manifest per dataset, and stores each raw payload under ``data/raw/`` (which is
git-ignored). Re-running with ``--force`` bypasses the cache and re-queries the
archives; comparing the new manifest hash to the committed one tells you whether
the archive's answer actually changed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from earth2.config import MANIFEST_DIR, PROCESSED_DIR, ensure_dirs
from earth2.data_sources import nasa_exoplanet_archive as nea
from earth2.data_sources.base import ArchiveError
from earth2.provenance import Manifest, ManifestStore, utc_now_iso

SYNC_STATE_PATH = MANIFEST_DIR / "_sync_state.json"


@dataclass
class SyncOutcome:
    dataset_id: str
    status: str          # ok | failed | skipped
    n_rows: int = 0
    elapsed_s: float = 0.0
    error: str = ""


def _store_parquet(dataset_id: str, df: pd.DataFrame) -> Path:
    """Persist a retrieved table as Parquet for fast downstream reads."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / (dataset_id + ".parquet")
    out = df.copy()
    # Parquet cannot hold mixed-type object columns; coerce the stragglers to
    # string rather than dropping them, since several are identifiers we need.
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].astype("string")
    out.to_parquet(path, index=False, compression="snappy")
    return path


def sync_nasa(
    only: list[str] | None = None,
    force: bool = False,
    verbose: bool = True,
) -> list[SyncOutcome]:
    """Retrieve every registered NASA Exoplanet Archive dataset.

    A failure on one dataset does not abort the run: the outcome is recorded and
    the remaining datasets still sync, so a single archive hiccup cannot leave
    the project with no data at all.
    """
    ensure_dirs()
    specs = nea.dataset_specs()
    ids = [i for i in specs if (not only or i in only)]
    outcomes: list[SyncOutcome] = []

    for dataset_id in ids:
        t0 = time.time()
        try:
            df, manifest = nea.fetch_dataset(dataset_id, use_cache=not force)
            _store_parquet(dataset_id, df)
            dt = time.time() - t0
            outcomes.append(SyncOutcome(dataset_id, "ok", len(df), dt))
            if verbose:
                print("  [ok]   %-22s %7d rows  %6.1fs  %6.1f MB"
                      % (dataset_id, len(df), dt, manifest.bytes_raw / 1e6))
        except (ArchiveError, Exception) as exc:  # noqa: BLE001
            dt = time.time() - t0
            msg = str(exc)[:400]
            outcomes.append(SyncOutcome(dataset_id, "failed", 0, dt, msg))
            # Record the failure as a manifest too, so a missing dataset is
            # visible in provenance rather than merely absent.
            Manifest(
                dataset_id=dataset_id,
                archive=nea.ARCHIVE_NAME,
                source_table=specs[dataset_id]["table"],
                query="",
                request_url=nea.TAP_SYNC,
                retrieved_utc=utc_now_iso(),
                n_rows=0,
                n_columns=0,
                sha256="",
                status="failed",
                notes="Retrieval failed: " + msg,
            ).save()
            if verbose:
                print("  [FAIL] %-22s %s" % (dataset_id, msg[:150]))

    return outcomes


def write_sync_state(outcomes: list[SyncOutcome]) -> Path:
    """Record when the last successful synchronisation happened.

    The website reads this to render "Data last synchronised: ... UTC" honestly,
    rather than showing the page build time and implying freshness it does not
    have.
    """
    ensure_dirs()
    store = ManifestStore()
    state = {
        "last_sync_utc": utc_now_iso(),
        "datasets_ok": sum(1 for o in outcomes if o.status == "ok"),
        "datasets_failed": sum(1 for o in outcomes if o.status == "failed"),
        "total_source_records": store.total_source_records(),
        "outcomes": [
            {
                "dataset_id": o.dataset_id,
                "status": o.status,
                "n_rows": o.n_rows,
                "elapsed_s": round(o.elapsed_s, 2),
                "error": o.error,
            }
            for o in outcomes
        ],
    }
    SYNC_STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return SYNC_STATE_PATH


def read_sync_state() -> dict:
    if not SYNC_STATE_PATH.exists():
        return {}
    return json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))


def run(only: list[str] | None = None, force: bool = False) -> list[SyncOutcome]:
    print("Synchronising with public astronomical archives")
    print("=" * 66)
    outcomes = sync_nasa(only=only, force=force)
    write_sync_state(outcomes)

    ok = [o for o in outcomes if o.status == "ok"]
    bad = [o for o in outcomes if o.status == "failed"]
    total = sum(o.n_rows for o in ok)
    print("-" * 66)
    print("  %d datasets ok, %d failed, %s source records retrieved"
          % (len(ok), len(bad), format(total, ",")))
    if bad:
        print("  failed: " + ", ".join(o.dataset_id for o in bad))
    return outcomes
