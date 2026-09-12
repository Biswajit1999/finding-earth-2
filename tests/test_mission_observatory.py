"""Contracts for the separate mission observatory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from earth2.missions.observatory import (
    EVIDENCE_LABELS,
    MISSION_PROFILES,
    RELEASE_ADAPTERS,
    FutureReleaseUnavailableError,
    validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]


def test_registry_has_six_ordered_complete_mission_views():
    validate_registry()
    assert [profile.mission_id for profile in MISSION_PROFILES] == [
        "jwst",
        "hwo",
        "andes",
        "plato",
        "gaia",
        "roman",
    ]
    for profile in MISSION_PROFILES:
        assert profile.measures
        assert profile.cannot_measure
        assert profile.wavelength
        assert profile.resolution
        assert profile.data_available
        assert profile.forecast_boundary


def test_registry_exposes_no_combined_score_contract():
    forbidden = {"score", "rank", "priority"}
    for profile in MISSION_PROFILES:
        assert forbidden.isdisjoint(profile.to_dict())


def test_future_release_adapters_refuse_observed_labels():
    adapters = {adapter.mission_id: adapter for adapter in RELEASE_ADAPTERS}
    assert adapters["gaia"].evidence_label("dr3") == "OBSERVED"
    assert adapters["jwst"].evidence_label("nea_atmosphere_2026-08-28") == "OBSERVED"
    for mission_id, release_id in [
        ("gaia", "dr4"),
        ("plato", "plato_science_release"),
        ("roman", "roman_science_release"),
        ("andes", "andes_science_release"),
        ("hwo", "hwo_science_release"),
    ]:
        with pytest.raises(FutureReleaseUnavailableError):
            adapters[mission_id].evidence_label(release_id)


def test_evidence_vocabulary_is_the_project_vocabulary():
    assert {
        "OBSERVED",
        "DERIVED",
        "MODEL-INFERRED",
        "SCENARIO",
        "FORECAST",
        "SIMULATED",
    } == EVIDENCE_LABELS


def test_built_products_are_separate_hash_gated_views():
    output = ROOT / "results/missions"
    index = json.loads((output / "mission_observatory.json").read_text())
    assert [item["mission_id"] for item in index["missions"]] == [
        "jwst",
        "hwo",
        "andes",
        "plato",
        "gaia",
        "roman",
    ]
    assert "aggregate" in index["separation_policy"]
    for item in index["missions"]:
        payload = json.loads((ROOT / item["evidence_file"]).read_text())
        assert payload["mission"]["mission_id"] == item["mission_id"]
        assert {row["label"] for row in payload["evidence_records"]} <= EVIDENCE_LABELS
        assert payload["mission"]["cannot_measure"]
        assert payload["mission"]["wavelength"]
        assert payload["mission"]["resolution"]

    manifest = json.loads((output / "mission_products.json").read_text())
    for relative, metadata in manifest["files"].items():
        path = ROOT / relative
        assert path.stat().st_size == metadata["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
