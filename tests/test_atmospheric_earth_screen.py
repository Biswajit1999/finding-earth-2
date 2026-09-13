"""Integrity tests for the generated Earth-analogue spectrum coverage screen."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_strict_spectrum_screen_matches_candidate_table() -> None:
    product = json.loads(
        (ROOT / "results/atmosphere/earth_analogue_spectrum_screen.json").read_text()
    )
    candidates = pd.read_csv(
        ROOT / "results/atmosphere/earth_analogue_spectrum_candidates.csv"
    )

    assert product["strict_small_temperate_candidates"] == len(candidates) == 15
    assert product["strict_candidates_with_indexed_reductions"] == 0
    assert product["strict_candidates_with_tabulated_measurements"] == 0
    assert candidates["indexed_reductions"].eq(0).all()
    assert candidates["spectral_points"].eq(0).all()
    assert candidates["spectral_coverage_status"].eq("NO_ARCHIVED_SPECTRUM").all()


def test_spectrum_screen_preserves_claim_boundary() -> None:
    product = json.loads(
        (ROOT / "results/atmosphere/earth_analogue_spectrum_screen.json").read_text()
    )
    boundary = product["claim_boundary"].lower()
    for unsupported_claim in ("detect an atmosphere", "identify a molecule", "habitability", "life"):
        assert unsupported_claim in boundary
    assert product["nearby_comparison_set"]
    assert all(not row["strict_conservative_hz"] for row in product["nearby_comparison_set"])
