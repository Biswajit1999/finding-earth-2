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
    summary = publication.load("results/analysis_summary.json")
    story = publication.load("results/population/dr25_observed_vs_intrinsic.json")
    falsification = publication.load("results/falsification/falsification_summary.json")
    assert f'\\newcommand{{\\TotalSourceRecords}}{{{summary["scale"]["total_source_records"]:,}}}' in macros
    median = story["intrinsic_posterior"]["full_fixed_box"]["p50"]
    assert f"\\newcommand{{\\OccurrenceMedian}}{{{median:.3f}}}" in macros
    assert f'\\newcommand{{\\VenusESI}}{{{falsification["venus_esi"]:.3f}}}' in macros
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
