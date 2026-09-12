from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import build_publication_release as publication


def test_release_policy_excludes_archive_tables() -> None:
    forbidden = ("data/raw", "data/cache", "data/processed", "spectrum_measurements")
    assert publication.RELEASE_FILES
    assert not any(any(token in path for token in forbidden) for path in publication.RELEASE_FILES)


def test_generated_macros_are_sourced_and_complete() -> None:
    macros = publication.latex_macros()
    assert "\\newcommand{\\TotalSourceRecords}{164,209}" in macros
    assert "\\newcommand{\\OccurrenceMedian}{0.692}" in macros
    assert "\\newcommand{\\VenusESI}{0.874}" in macros
    assert "% Source commit:" in macros


def test_committed_release_manifest_verifies() -> None:
    root = Path(__file__).resolve().parents[1]
    release = root / "earth2-v2-data-release"
    inventory = json.loads((release / "release_inventory.json").read_text(encoding="utf-8"))
    assert inventory["doi"] == "pending"
    assert inventory["file_count_before_inventory"] >= 50
    for line in (release / "MANIFEST.sha256").read_text(encoding="ascii").splitlines():
        expected, rel = line.split("  ", 1)
        assert hashlib.sha256((release / rel).read_bytes()).hexdigest() == expected
