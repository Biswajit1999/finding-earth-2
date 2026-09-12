"""Reduction-preserving atmospheric spectrum evidence architecture."""

from __future__ import annotations

import hashlib
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd


def spectrum_reduction_id(
    *,
    planet: str,
    spectrum_type: str,
    bibcode: str | None,
    facility: str | None,
    instrument: str | None,
    archive_path: str | None,
) -> str:
    """Stable identity for one published spectrum reduction."""

    fields = [planet, spectrum_type, bibcode, facility, instrument, archive_path]
    normalized = "|".join("" if value is None else str(value).strip() for value in fields)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def compare_reduction_pair(
    first: pd.DataFrame,
    second: pd.DataFrame,
    *,
    minimum_tolerance_um: float = 0.02,
) -> dict[str, Any]:
    """Compare overlapping points without merging either reduction.

    Each point in the smaller reduction is paired with its nearest wavelength
    in the other when the separation is inside the larger of 0.02 micron and
    half the combined reported bandwidth.  The diagnostic is descriptive and
    never replaces the original rows.
    """

    if first.empty or second.empty:
        return {"matched_points": 0, "median_abs_delta_ppm": None, "max_abs_z": None}
    left, right = (first, second) if len(first) <= len(second) else (second, first)
    right_wavelength = right["wavelength_um"].to_numpy(dtype=float)
    deltas: list[float] = []
    z_scores: list[float] = []
    for _, point in left.iterrows():
        wavelength = float(point["wavelength_um"])
        distances = np.abs(right_wavelength - wavelength)
        if not np.isfinite(distances).any():
            continue
        position = int(np.nanargmin(distances))
        other = right.iloc[position]
        bandwidths = [point.get("bandwidth_um"), other.get("bandwidth_um")]
        finite_bandwidths = [
            abs(float(value)) for value in bandwidths if value is not None and np.isfinite(value)
        ]
        tolerance = max(minimum_tolerance_um, 0.5 * sum(finite_bandwidths))
        if distances[position] > tolerance:
            continue
        delta = float(point["measurement_ppm"] - other["measurement_ppm"])
        deltas.append(delta)
        errors = [point.get("uncertainty_ppm"), other.get("uncertainty_ppm")]
        if all(value is not None and np.isfinite(value) and value > 0 for value in errors):
            sigma = float(np.hypot(float(errors[0]), float(errors[1])))
            z_scores.append(delta / sigma)
    return {
        "matched_points": len(deltas),
        "median_abs_delta_ppm": float(np.median(np.abs(deltas))) if deltas else None,
        "max_abs_z": float(np.max(np.abs(z_scores))) if z_scores else None,
    }


def reduction_disagreement_catalogue(points: pd.DataFrame) -> list[dict[str, Any]]:
    """Return pairwise overlap diagnostics while preserving every reduction."""

    comparisons: list[dict[str, Any]] = []
    measured = points[
        points["measurement_role"].eq("measurement")
        & points["measurement_ppm"].notna()
        & points["wavelength_um"].notna()
    ]
    for (planet, spectrum_type), group in measured.groupby(["planet", "spectrum_type"]):
        reduction_ids = sorted(group["reduction_id"].unique())
        for first_id, second_id in combinations(reduction_ids, 2):
            diagnostic = compare_reduction_pair(
                group[group["reduction_id"].eq(first_id)],
                group[group["reduction_id"].eq(second_id)],
            )
            if diagnostic["matched_points"]:
                comparisons.append(
                    {
                        "label": "DERIVED",
                        "planet": str(planet),
                        "spectrum_type": str(spectrum_type),
                        "reduction_a": str(first_id),
                        "reduction_b": str(second_id),
                        **diagnostic,
                        "interpretation": (
                            "overlap diagnostic only; neither reduction is preferred or merged"
                        ),
                    }
                )
    return comparisons
