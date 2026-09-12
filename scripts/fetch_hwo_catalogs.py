"""Fetch and verify the pinned HPIC v1.1 and TSS25 source archives."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data/manifests/hwo_hpic.json"
MEMBERS = {
    "hpic_v1p1": (
        "HPIC/full_HPIC.txt",
        "HPIC/README.txt",
        "HPIC/list_of_contaminants.txt",
        "HPIC/contaminants_README.txt",
    ),
    "tss25_2025": ("TSS25/TSS25_list.csv", "TSS25/README.txt"),
}


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def fetch(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)
    temporary.replace(destination)


def safe_extract(archive: Path, destination: Path, members: tuple[str, ...]) -> None:
    destination_resolved = destination.resolve()
    with tarfile.open(archive, "r:gz") as payload:
        by_name = {member.name: member for member in payload.getmembers()}
        missing = [name for name in members if name not in by_name]
        if missing:
            raise RuntimeError(f"archive is missing required members: {missing}")
        for name in members:
            member = by_name[name]
            target = (destination / name).resolve()
            if destination_resolved not in target.parents:
                raise RuntimeError(f"unsafe archive member: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = payload.extractfile(member)
            if source is None:
                raise RuntimeError(f"archive member is not a regular file: {name}")
            target.write_bytes(source.read())


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for dataset in manifest["datasets"]:
        archive = ROOT / dataset["archive_path"]
        if (
            not archive.exists()
            or archive.stat().st_size != dataset["archive_bytes"]
            or digest(archive) != dataset["archive_sha256"]
        ):
            print(f"Downloading {dataset['dataset_id']} from its pinned Zenodo record")
            fetch(dataset["source_url"], archive)
        if archive.stat().st_size != dataset["archive_bytes"]:
            raise RuntimeError(f"downloaded archive has wrong size: {archive}")
        if digest(archive) != dataset["archive_sha256"]:
            raise RuntimeError(f"downloaded archive has wrong SHA-256: {archive}")
        safe_extract(archive, ROOT / "data/raw/hwo", MEMBERS[dataset["dataset_id"]])
        table = ROOT / dataset["table_path"]
        if (
            table.stat().st_size != dataset["table_bytes"]
            or digest(table) != dataset["table_sha256"]
        ):
            raise RuntimeError(f"extracted table failed its pinned contract: {table}")
        print(f"Verified {dataset['dataset_id']}: {table}")


if __name__ == "__main__":
    main()
