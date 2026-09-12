"""Release checks for Solar-System controls and candidate robustness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_solar_system_controls_expose_venus_similarity_failure():
    controls = pd.read_csv(ROOT / "results/falsification/solar_system_controls.csv").set_index(
        "pl_name"
    )
    assert set(controls.index) == {"Earth", "Venus", "Mars", "Mercury", "Jupiter"}
    assert controls.loc["Earth", "esi_global"] == 1
    assert controls.loc["Earth", "hz_conservative_prob"] == 1
    assert controls.loc["Venus", "esi_global"] > 0.85
    assert controls.loc["Venus", "hz_conservative_prob"] == 0
    assert "cannot establish habitability" in controls.loc["Venus", "falsification_result"]


def test_candidate_sensitivity_is_bounded_to_declared_model_menu():
    output = ROOT / "results/falsification"
    robust = pd.read_csv(output / "candidate_model_sensitivity.csv")
    assert len(robust) == 25
    assert robust["pl_name"].is_unique
    assert robust["label"].eq("MODEL-SENSITIVITY").all()
    assert robust["legacy_rank_span"].ge(0).all()
    for column in [
        "hz_model_probability_range",
        "p_rocky_model_range",
        "hwo_accessibility_range",
    ]:
        assert robust[column].dropna().between(0, 1).all()

    summary = json.loads((output / "falsification_summary.json").read_text())
    assert summary["control_count"] == 5
    assert summary["candidate_count"] == 25
    assert len(summary["legacy_weight_scenarios"]) == 5
    assert "not all plausible models" in summary["claim_boundary"]
    manifest = json.loads((output / "falsification_products.json").read_text())
    for relative, metadata in manifest["files"].items():
        path = ROOT / relative
        assert path.stat().st_size == metadata["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
