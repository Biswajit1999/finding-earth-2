"""Contracts for reduction-preserving atmospheric evidence."""

from __future__ import annotations

import pandas as pd

from earth2.spectroscopy.evidence import (
    reduction_disagreement_catalogue,
    spectrum_reduction_id,
)


def test_reduction_identity_changes_with_archive_path():
    common = {
        "planet": "Example b",
        "spectrum_type": "transmission",
        "bibcode": "2026ApJ...001A...1X",
        "facility": "Example Observatory",
        "instrument": "Example Spectrograph",
    }
    first = spectrum_reduction_id(**common, archive_path="reduction-a.tbl")
    second = spectrum_reduction_id(**common, archive_path="reduction-b.tbl")
    assert first != second


def test_conflicting_reductions_remain_separate_and_are_diagnosed():
    points = pd.DataFrame(
        [
            {
                "planet": "Example b",
                "spectrum_type": "transmission",
                "reduction_id": "a",
                "wavelength_um": 1.40,
                "bandwidth_um": 0.02,
                "measurement_ppm": 100.0,
                "uncertainty_ppm": 5.0,
                "measurement_role": "measurement",
            },
            {
                "planet": "Example b",
                "spectrum_type": "transmission",
                "reduction_id": "b",
                "wavelength_um": 1.40,
                "bandwidth_um": 0.02,
                "measurement_ppm": 150.0,
                "uncertainty_ppm": 5.0,
                "measurement_role": "measurement",
            },
        ]
    )
    comparisons = reduction_disagreement_catalogue(points)
    assert len(comparisons) == 1
    assert comparisons[0]["matched_points"] == 1
    assert comparisons[0]["max_abs_z"] > 7
    assert set(points["reduction_id"]) == {"a", "b"}
