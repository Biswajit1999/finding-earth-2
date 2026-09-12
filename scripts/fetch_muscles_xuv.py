"""Retrieve the three pinned MUSCLES SEDs used by the Phase 8 product."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads((ROOT / "data/manifests/muscles_xuv.json").read_text())
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if (
            path.exists()
            and path.stat().st_size == item["bytes"]
            and digest(path) == item["sha256"]
        ):
            print(f"verified {item['target']}: {path}", flush=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".part")
        with requests.get(item["url"], stream=True, timeout=60) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    handle.write(chunk)
        if temporary.stat().st_size != item["bytes"] or digest(temporary) != item["sha256"]:
            temporary.unlink(missing_ok=True)
            raise ValueError(f"integrity check failed for {item['target']}")
        temporary.replace(path)
        print(f"retrieved {item['target']}: {path}", flush=True)


if __name__ == "__main__":
    main()
