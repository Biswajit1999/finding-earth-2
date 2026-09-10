"""Bounded retrieval and immutable provenance for the official DR25 experiment.

Cache reads verify raw bytes and retain the original retrieval timestamp. These
manifests live separately from the v1 catalogue manifest namespace.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from earth2.population.kepler import (
    STELLAR_COLUMNS,
    parse_ipac,
    parse_robovetter_ipac,
    parse_stars,
)

BASE = "https://exoplanetarchive.ipac.caltech.edu"
SPECS: dict[str, dict] = {
    "injections": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_inj1_plti.txt",
        "query": "Official DR25 INJ1 on-target planet injection table; all rows",
        "expected_rows": 146294,
        "extension": "txt",
        "experiment": "INJ1",
    },
    "vetting": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_inj1_tces.txt",
        "query": "Official DR25 INJ1 recovered-injection Robovetter table; all rows",
        "expected_rows": 45377,
        "extension": "txt",
        "experiment": "INJ1",
    },
    "stars": {
        "url": BASE
        + "/cgi-bin/nstedAPI/nph-nstedAPI?"
        + urlencode(
            {
                "table": "q1_q17_dr25_stellar",
                "format": "csv",
                "select": ",".join(STELLAR_COLUMNS),
            }
        ),
        "query": "SELECT " + ",".join(STELLAR_COLUMNS) + " FROM q1_q17_dr25_stellar",
        "expected_rows": None,
        "extension": "csv",
        "experiment": None,
    },
    "false_alarm_inv": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_inv_tces.txt",
        "query": "Official DR25 INV Robovetter false-alarm experiment; all rows",
        "expected_rows": 19531,
        "expected_declared_rows": 19536,
        "extension": "txt",
        "experiment": "INV",
    },
    "observed_tces": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_obs_tces.txt",
        "query": "Official DR25 observed Robovetter TCE results; all legitimate TCEs",
        "expected_rows": 32530,
        "expected_declared_rows": 32534,
        "extension": "txt",
        "experiment": "OBS",
    },
    "false_alarm_scr1": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_scr1_tces.txt",
        "query": "Official DR25 SCR1 Robovetter false-alarm experiment; all rows",
        "expected_rows": 24209,
        "expected_declared_rows": 24213,
        "extension": "txt",
        "experiment": "SCR1",
    },
    "false_alarm_scr2": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_scr2_tces.txt",
        "query": "Official DR25 SCR2 Robovetter false-alarm experiment; all rows",
        "expected_rows": 24217,
        "expected_declared_rows": 24222,
        "extension": "txt",
        "experiment": "SCR2",
    },
    "false_alarm_scr3": {
        "url": BASE + "/data/KeplerData/Simulated/kplr_dr25_scr3_tces.txt",
        "query": "Official DR25 SCR3 Robovetter false-alarm experiment; all rows",
        "expected_rows": 19811,
        "expected_declared_rows": 19811,
        "extension": "txt",
        "experiment": "SCR3",
    },
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_payload(payload: bytes, kind: str) -> pd.DataFrame:
    if kind == "stars":
        frame = parse_stars(payload)
    elif kind in {"injections", "vetting"}:
        frame = parse_ipac(payload, kind=kind)
    elif kind == "observed_tces" or kind.startswith("false_alarm_"):
        frame = parse_robovetter_ipac(payload, experiment=SPECS[kind]["experiment"])
    else:
        raise ValueError(f"Unsupported DR25 product: {kind}")
    expected = SPECS[kind]["expected_rows"]
    if not len(frame) or (expected is not None and len(frame) != expected):
        raise ValueError(f"Unexpected {kind} row count: {len(frame)}; expected {expected}")
    expected_declared = SPECS[kind].get("expected_declared_rows")
    if expected_declared is not None and frame.attrs.get("declared_nrows") != expected_declared:
        raise ValueError(
            f"Unexpected {kind} declared row count: "
            f"{frame.attrs.get('declared_nrows')}; expected {expected_declared}"
        )
    return frame


def fetch_product(
    root: Path, kind: str, *, session=None, max_bytes: int = 100_000_000
) -> tuple[pd.DataFrame, dict]:
    """Retrieve once, validate before saving; refuse incomplete/corrupt caches.

    A changed upstream release requires a new explicit cache namespace, rather
    than silently replacing a scientifically frozen input. No credentials used.
    """
    spec = SPECS[kind]
    raw = root / "data" / "raw" / "kepler_dr25" / f"{kind}.{spec['extension']}"
    manifest_path = root / "data" / "manifests" / "population" / f"dr25_{kind}.json"
    if raw.exists() or manifest_path.exists():
        if not (raw.exists() and manifest_path.exists()):
            raise ValueError(f"Incomplete cache for {kind}: both raw payload and manifest required")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = raw.read_bytes()
        if (
            manifest["source_url"] != spec["url"]
            or manifest["sha256"] != sha256(payload)
            or manifest["bytes"] != len(payload)
        ):
            raise ValueError(f"Cache integrity or source mismatch for {kind}")
        frame = validate_payload(payload, kind)
        if manifest["row_count"] != len(frame):
            raise ValueError("Cached manifest row count mismatch")
        return frame, manifest
    owned_session = session is None
    if owned_session:
        session = requests.Session()
        session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
            ),
        )
    try:
        with session.get(spec["url"], stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            if int(response.headers.get("Content-Length", 0)) > max_bytes:
                raise ValueError("Product exceeds configured download bound")
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Product exceeds configured download bound")
                chunks.append(chunk)
            payload = b"".join(chunks)
            final_url = response.url
    finally:
        if owned_session:
            session.close()
    frame = validate_payload(payload, kind)
    git = shutil.which("git.exe") or shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required to record software provenance")
    commit = subprocess.check_output([git, "rev-parse", "HEAD"], cwd=root, text=True).strip()
    manifest = {
        "schema_version": "1.0",
        "product": kind,
        "survey": "Kepler",
        "release": "DR25",
        "experiment": spec["experiment"],
        "source_url": spec["url"],
        "resolved_url": final_url,
        "query": spec["query"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(frame),
        **(
            {"declared_row_count": frame.attrs["declared_nrows"]}
            if "declared_nrows" in frame.attrs
            else {}
        ),
        "sha256": sha256(payload),
        "bytes": len(payload),
        "software_commit": commit,
        "adapter_sha256": sha256(Path(__file__).read_bytes()),
        "raw_path": raw.relative_to(root).as_posix(),
        "acknowledgement": "NASA Exoplanet Archive, operated by Caltech under contract with NASA; Kepler mission and DR25 pipeline/Robovetter teams.",
        "licence": "Not asserted; retain archive acknowledgement and consult source terms.",
        "documentation": BASE + "/docs/Kepler_completeness_reliability.html",
    }
    raw.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwrites. An interrupted pair is
    # intentionally rejected on the next run instead of silently being trusted.
    with raw.open("xb") as f:
        f.write(payload)
    with manifest_path.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, allow_nan=False)
        f.write("\n")
    return frame, manifest
