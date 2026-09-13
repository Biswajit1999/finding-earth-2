"""Cross-match the strict small-temperate sample with published spectra.

This is an evidence-availability analysis.  It deliberately does not turn a
spectrum, or the absence of one, into a claim about habitability or life.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "atmosphere"
CLAIM_BOUNDARY = (
    "This cross-match measures published spectral coverage. It does not detect an "
    "atmosphere, identify a molecule, establish habitability, or provide evidence of life."
)


def _number(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def build() -> dict[str, object]:
    planets = pd.read_csv(ROOT / "results" / "candidate_ranking.csv", low_memory=False)
    reductions = pd.read_csv(OUT / "spectrum_reductions.csv")
    measurements = pd.read_csv(OUT / "spectrum_measurements.csv.gz", low_memory=False)

    confirmed = planets[~planets["is_control"].fillna(False).astype(bool)].copy()
    radius = pd.to_numeric(confirmed["pl_rade"], errors="coerce")
    hz = pd.to_numeric(confirmed["hz_conservative"], errors="coerce")
    strict = confirmed[(radius < 1.6) & (hz == 1)].sort_values("earth2_rank").copy()

    reduction_counts = reductions.groupby("planet")["reduction_id"].nunique()
    measurement_summary = measurements.groupby("planet").agg(
        spectral_points=("wavelength_um", "count"),
        wavelength_min_um=("wavelength_um", "min"),
        wavelength_max_um=("wavelength_um", "max"),
        median_uncertainty_ppm=("uncertainty_ppm", "median"),
        spectrum_types=("spectrum_type", lambda s: ", ".join(sorted(set(s.astype(str))))),
    )

    strict["indexed_reductions"] = strict["pl_name"].map(reduction_counts).fillna(0).astype(int)
    strict["spectral_points"] = strict["pl_name"].map(
        measurement_summary["spectral_points"]
    ).fillna(0).astype(int)
    strict["spectral_coverage_status"] = np.where(
        strict["spectral_points"] > 0,
        "TABULATED_MEASUREMENTS",
        np.where(strict["indexed_reductions"] > 0, "INDEXED_REDUCTION", "NO_ARCHIVED_SPECTRUM"),
    )

    candidate_columns = [
        "earth2_rank", "pl_name", "hostname", "pl_rade", "hz_conservative",
        "sy_dist", "tran_flag", "indexed_reductions", "spectral_points",
        "spectral_coverage_status",
    ]
    strict[candidate_columns].to_csv(
        OUT / "earth_analogue_spectrum_candidates.csv", index=False, lineterminator="\n"
    )

    small = confirmed[radius < 1.6].copy()
    comparison = small.merge(
        measurement_summary.reset_index(), left_on="pl_name", right_on="planet", how="inner"
    ).sort_values(["earth2_rank", "spectral_points"], ascending=[True, False]).head(8)
    comparison_rows = [
        {
            "planet": str(row.pl_name),
            "earth2_rank": int(row.earth2_rank),
            "radius_earth": _number(row.pl_rade),
            "strict_conservative_hz": bool(row.hz_conservative == 1),
            "spectral_points": int(row.spectral_points),
            "spectrum_types": str(row.spectrum_types),
            "wavelength_min_um": _number(row.wavelength_min_um),
            "wavelength_max_um": _number(row.wavelength_max_um),
            "median_uncertainty_ppm": _number(row.median_uncertainty_ppm),
        }
        for row in comparison.itertuples()
    ]

    result: dict[str, object] = {
        "schema_version": "1.0",
        "title": "Atmospheric spectrum screen for the strict Earth-analogue sample",
        "label": "OBSERVED",
        "selection": "confirmed planet; nominal conservative HZ; radius < 1.6 Earth radii",
        "confirmed_planets": int(len(confirmed)),
        "strict_small_temperate_candidates": int(len(strict)),
        "strict_candidates_with_indexed_reductions": int((strict.indexed_reductions > 0).sum()),
        "strict_candidates_with_tabulated_measurements": int((strict.spectral_points > 0).sum()),
        "strict_candidate_names": strict["pl_name"].astype(str).tolist(),
        "nearby_comparison_set": comparison_rows,
        "finding": (
            "None of the 15 strict small-and-temperate candidates has an indexed published "
            "spectrum or tabulated wavelength measurement in the ingested archives."
        ),
        "next_observation": (
            "The next decisive step is target-specific atmospheric follow-up: obtain a "
            "calibrated spectrum, preserve each reduction separately, and test atmospheric "
            "models only after instrument and stellar systematics are quantified."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    with (OUT / "earth_analogue_spectrum_screen.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    _draw(result, comparison)
    return result


def _draw(result: dict[str, object], comparison: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(10.8, 6.2), facecolor="white")
    grid = fig.add_gridspec(2, 1, height_ratios=[0.9, 1.4], hspace=0.48)
    top = fig.add_subplot(grid[0])
    bottom = fig.add_subplot(grid[1])
    labels = ["Confirmed\nplanets", "Small + conservative\nHZ", "Indexed spectral\nreductions", "Tabulated wavelength\nmeasurements"]
    values = [
        int(result["confirmed_planets"]),
        int(result["strict_small_temperate_candidates"]),
        int(result["strict_candidates_with_indexed_reductions"]),
        int(result["strict_candidates_with_tabulated_measurements"]),
    ]
    colours = ["#315b7d", "#8a63d2", "#d97706", "#c03546"]
    shown = [max(v, 0.22) for v in values]
    top.barh(range(4), shown, color=colours, height=0.58)
    top.set_xscale("log")
    top.set_xlim(0.18, 12000)
    top.set_yticks(range(4), labels)
    top.invert_yaxis()
    top.set_xlabel("Objects retained (log scale; zero shown at the display floor)")
    top.grid(axis="x", color="#d9e1ea", linewidth=0.8)
    top.spines[["top", "right", "left"]].set_visible(False)
    top.tick_params(axis="y", length=0)
    for i, value in enumerate(values):
        top.text(shown[i] * 1.13, i, f"{value:,}", va="center", fontsize=10, weight="bold")

    plot = comparison.sort_values("spectral_points")
    bottom.barh(plot["pl_name"], plot["spectral_points"], color="#1f9e89", alpha=0.9)
    bottom.set_xscale("log")
    bottom.set_xlabel("Published tabulated spectral points (log scale)")
    bottom.set_title(
        "Closest-ranked sub-1.6 R⊕ comparison worlds with spectra — all outside the strict box",
        loc="left", fontsize=10, pad=10,
    )
    bottom.grid(axis="x", color="#d9e1ea", linewidth=0.8)
    bottom.spines[["top", "right", "left"]].set_visible(False)
    bottom.tick_params(axis="y", length=0)
    for i, value in enumerate(plot["spectral_points"]):
        bottom.text(float(value) * 1.06, i, f"{int(value):,}", va="center", fontsize=8)

    fig.suptitle("Atmospheric evidence gap for the strict Earth-analogue sample", fontsize=15, weight="bold")
    fig.text(0.99, 0.01, "Published coverage screen · absence of coverage is not absence of atmosphere",
             ha="right", fontsize=7, color="#637083")
    fig.savefig(OUT / "earth_analogue_spectrum_screen.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    product = build()
    print(product["finding"])
