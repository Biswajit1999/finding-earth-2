"""Cross-check the generated result artefacts against each other before a release.

Unit tests validate individual functions against hand-picked inputs; this
script instead validates that the *committed output files* are mutually
consistent -- that the headline scale claim actually sums from the
provenance manifest, that the ranking has no impossible values, and that
Solar System controls never leak into the numbered ranking. None of this
duplicates ``tests/``: it runs against whatever is currently in ``results/``,
which is exactly the thing a reader downloads and a reviewer checks.

Usage::

    python -m earth2 analyse && python -m earth2 export   # regenerate first
    python scripts/check_release_invariants.py

Exits non-zero on the first failed invariant.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402

from earth2.config import RESULTS_DIR  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool) -> None:
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main() -> int:
    summary = json.loads((RESULTS_DIR / "analysis_summary.json").read_text())
    prov = json.loads((RESULTS_DIR / "provenance_manifest.json").read_text())
    ranking = pd.read_parquet(RESULTS_DIR / "candidate_ranking.parquet")

    retrieved = sum(int(r["n_rows"]) for r in prov.get("retrievals", []))
    check(
        "total_source_records matches the sum of provenance retrievals",
        retrieved == summary["scale"]["total_source_records"],
    )

    idx = pd.to_numeric(ranking["earth2_index"], errors="coerce").dropna()
    check("earth2_index is within [0, 1] for every scored row", idx.between(0.0, 1.0).all())

    is_control = ranking.get("is_control")
    if is_control is not None:
        is_control = is_control.fillna(False).astype(bool)
        exoplanets = ranking.loc[~is_control]
        check("pl_name is unique among non-control rows", exoplanets["pl_name"].is_unique)

        earth_rows = ranking.loc[is_control & (ranking["pl_name"] == "Earth")]
        check("exactly one Earth control row is present", len(earth_rows) == 1)

        ranked_controls = ranking.loc[is_control, "earth2_rank"].notna()
        check(
            "no Solar System control has a numbered rank",
            not ranked_controls.any() if "earth2_rank" in ranking.columns else True,
        )
    else:
        check("is_control column is present", False)

    if (
        "hz_teff_valid_fraction" in ranking.columns
        and "score_conservative_habitability" in ranking.columns
    ):
        low_valid = pd.to_numeric(ranking["hz_teff_valid_fraction"], errors="coerce") < 0.2
        high_habitability = (
            pd.to_numeric(ranking["score_conservative_habitability"], errors="coerce") > 0.7
        )
        check(
            "no candidate with <20% HZ-model-valid draws scores >0.7 conservative habitability",
            not (low_valid & high_habitability).any(),
        )

    population = RESULTS_DIR / "population"
    selection_validation = json.loads((population / "dr25_selection_validation.json").read_text())
    selection_surface = pd.read_csv(population / "dr25_selection_surface.csv")
    check("DR25 selection release gate passed", selection_validation["passed"] is True)
    check(
        "every DR25 selection cell uses the fixed 114,105-star denominator",
        selection_surface["target_stars"].eq(114105).all(),
    )
    selection_probabilities = selection_surface[
        [
            "mean_transit_geometry",
            "mean_phase_window",
            "mean_pipeline_including_window",
            "mean_vetting_given_recovered",
            "mean_pipeline_and_vetting",
            "mean_total_selection",
        ]
    ]
    check(
        "DR25 selection probabilities are finite and within [0, 1]",
        selection_probabilities.notna().all().all()
        and selection_probabilities.ge(0).all().all()
        and selection_probabilities.le(1).all().all(),
    )
    product_manifest = json.loads((population / "dr25_selection_products.json").read_text())
    product_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in product_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check("DR25 selection product hashes match the release manifest", product_hashes_match)

    hierarchical_validation = json.loads(
        (population / "validation/hierarchical_recovery.json").read_text()
    )
    check(
        "hierarchical occurrence synthetic release gate passed",
        hierarchical_validation["passed"] is True,
    )
    check(
        "hierarchical occurrence validation contains only simulated scenarios",
        hierarchical_validation["label"] == "SIMULATED"
        and all(row["label"] == "SIMULATED" for row in hierarchical_validation["scenarios"]),
    )
    required_scenarios = {
        "flat_population",
        "power_law_population",
        "broken_radius_population",
        "earth_box_population",
        "low_completeness",
        "finite_injection_uncertainty",
        "reliability_perturbation",
        "stellar_radius_uncertainty",
        "wrong_completeness_negative_control",
    }
    check(
        "hierarchical occurrence validation includes every required stress case",
        {row["scenario"] for row in hierarchical_validation["scenarios"]}
        == required_scenarios,
    )

    occurrence = json.loads((population / "dr25_occurrence_posterior.json").read_text())
    occurrence_samples = pd.read_csv(population / "dr25_occurrence_posterior_samples.csv")
    check(
        "DR25 occurrence result is explicitly model-inferred and uses 3,000 imputations",
        occurrence["label"] == "MODEL-INFERRED"
        and occurrence["likelihood"]["posterior_imputations"] == 3000,
    )
    check(
        "DR25 occurrence samples are finite, positive and consistently labelled",
        len(occurrence_samples) == 12000
        and occurrence_samples["label"].eq("MODEL-INFERRED").all()
        and occurrence_samples[
            ["integrated_rate", "alpha", "beta", "shape_weighted_effective_stars"]
        ]
        .notna()
        .all()
        .all()
        and occurrence_samples["integrated_rate"].gt(0).all()
        and occurrence_samples["shape_weighted_effective_stars"].gt(0).all(),
    )
    check(
        "DR25 occurrence slope posteriors do not pile up on numerical grid boundaries",
        all(
            value <= 0.01
            for posterior in occurrence["baseline_posteriors"].values()
            for value in posterior["slope_grid_boundary_fraction"].values()
        ),
    )
    check(
        "DR25 occurrence posterior-predictive tail diagnostics avoid extreme values",
        all(
            0.05 <= diagnostic[key] <= 0.95
            for diagnostic in occurrence["posterior_predictive_checks"].values()
            for key in (
                "count_upper_tail_probability",
                "period_mean_upper_tail_probability",
                "radius_mean_upper_tail_probability",
            )
        ),
    )
    check(
        "DR25 occurrence exposure quadrature is stable to released-surface resolution",
        occurrence["quadrature_and_surface_resolution_sensitivity"][
            "shape_weighted_exposure_relative_difference_over_slope_grid"
        ]["maximum_absolute"]
        <= 0.01,
    )
    check(
        "instrumental reliability correction lowers the full-box occurrence median",
        occurrence["sensitivity_by_estimand"]["full_fixed_box"][
            "without_instrumental_false_alarm_correction"
        ]["integrated_planets_per_star"]["p50"]
        > occurrence["baseline_posteriors"][
            "full_fixed_box__unsupported_lower"
        ]["integrated_planets_per_star"]["p50"],
    )
    occurrence_manifest = json.loads(
        (population / "dr25_occurrence_products.json").read_text()
    )
    occurrence_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in occurrence_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check("DR25 occurrence product hashes match the release manifest", occurrence_hashes_match)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} invariant(s) failed:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("All release invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
