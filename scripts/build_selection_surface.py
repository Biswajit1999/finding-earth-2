"""Fit, validate and export the survey-wide Kepler DR25 selection surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from earth2.population.archive import fetch_product
from earth2.population.diagnostics import plot_selection_surface
from earth2.population.kepler import StellarSelection, join_injections
from earth2.population.selection_surface import (
    SelectionDomain,
    fit_selection_model,
    predict_injection_rows,
    target_averaged_surface,
    validate_injection_holdout,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        frame.to_csv(handle, index=False, float_format="%.12g", lineterminator="\n")


def normalize_text_lf(path: Path) -> None:
    """Keep text-artifact hashes identical after Git's cross-platform checkout."""
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    normalized = b"\n".join(line.rstrip() for line in payload.split(b"\n"))
    if normalized != payload:
        path.write_bytes(normalized)


def distribution_of_absolute_difference(values: np.ndarray) -> dict[str, float]:
    difference = np.abs(np.asarray(values, float))
    return {
        "mean": float(np.mean(difference)),
        "median": float(np.median(difference)),
        "p95": float(np.quantile(difference, 0.95)),
        "maximum": float(np.max(difference)),
    }


def compare_keplerports_reference(
    root: Path,
    model,
    selected_stars: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    reference = json.loads(
        (root / "results/population/keplerports_reference.json").read_text(encoding="utf-8")
    )
    periods = np.asarray(reference["period_days"], float)
    radii = np.asarray(reference["planet_radius_earth"], float)
    period_mask = (periods >= model.domain.period_min_days) & (
        periods <= model.domain.period_max_days
    )
    radius_mask = (radii >= model.domain.radius_min_earth) & (
        radii <= model.domain.radius_max_earth
    )
    periods = periods[period_mask]
    radii = radii[radius_mask]
    target = selected_stars.loc[selected_stars["kepid"].eq(3429335)]
    if len(target) != 1:
        raise RuntimeError("Pinned KeplerPORTs reference target is absent or duplicated")
    empirical = target_averaged_surface(model, target, periods, radii)
    reference_values = np.asarray(reference["pipeline_including_window"], float)[
        np.ix_(radius_mask, period_mask)
    ]
    reference_frame = pd.DataFrame(
        [
            {
                "period_days": period,
                "planet_radius_earth": radius,
                "keplerports_pipeline_including_window": reference_values[
                    radius_index, period_index
                ],
            }
            for radius_index, radius in enumerate(radii)
            for period_index, period in enumerate(periods)
        ]
    )
    comparison = empirical.merge(
        reference_frame,
        on=["period_days", "planet_radius_earth"],
        validate="one_to_one",
    )
    comparison = comparison[
        [
            "period_days",
            "planet_radius_earth",
            "keplerports_pipeline_including_window",
            "mean_pipeline_including_window",
        ]
    ].rename(
        columns={"mean_pipeline_including_window": "injection_calibrated_pipeline_including_window"}
    )
    comparison["difference"] = (
        comparison["injection_calibrated_pipeline_including_window"]
        - comparison["keplerports_pipeline_including_window"]
    )
    comparison["absolute_difference"] = comparison["difference"].abs()
    metrics = {
        "target_kic": 3429335,
        "upstream_commit": reference["upstream_commit"],
        "grid_cells_in_shared_domain": len(comparison),
        "mean_absolute_error": float(comparison["absolute_difference"].mean()),
        "root_mean_squared_error": float(
            np.sqrt(np.mean(comparison["difference"].to_numpy(float) ** 2))
        ),
        "maximum_absolute_error": float(comparison["absolute_difference"].max()),
        "thresholds": {
            "mean_absolute_error_at_most": 0.05,
            "maximum_absolute_error_at_most": 0.20,
        },
        "role": (
            "Independent implementation regression for one target; the held-out INJ1 "
            "experiment remains the primary validation"
        ),
    }
    metrics["passed"] = bool(
        metrics["mean_absolute_error"] <= metrics["thresholds"]["mean_absolute_error_at_most"]
        and metrics["maximum_absolute_error"]
        <= metrics["thresholds"]["maximum_absolute_error_at_most"]
    )
    return comparison, metrics


def surface_invariants(surface: pd.DataFrame, target_count: int) -> dict:
    probability_columns = [
        "mean_transit_geometry",
        "mean_phase_window",
        "mean_pipeline_including_window",
        "mean_vetting_given_recovered",
        "mean_pipeline_and_vetting",
        "mean_total_selection",
        "fraction_impact_target_evaluations_below_mes_training",
        "fraction_impact_target_evaluations_above_mes_training",
    ]
    probabilities = surface[probability_columns].to_numpy(float)
    bounded = bool(
        np.isfinite(probabilities).all()
        and np.all(probabilities >= 0)
        and np.all(probabilities <= 1)
    )
    factorized = bool(
        np.all(surface["mean_total_selection"] <= surface["mean_transit_geometry"])
        and np.allclose(
            surface["effective_stars"],
            target_count * surface["mean_total_selection"],
            rtol=2e-12,
            atol=1e-12,
        )
    )
    target_complete = bool(surface["target_stars"].eq(target_count).all())
    total = surface.pivot(
        index="planet_radius_earth", columns="period_days", values="mean_total_selection"
    ).sort_index()
    radius_differences = np.diff(total.to_numpy(float), axis=0)
    minimum_radius_step = float(radius_differences.min())
    radius_monotonic = bool(minimum_radius_step >= -1e-12)
    result = {
        "all_probabilities_finite_and_bounded": bounded,
        "total_selection_does_not_exceed_geometry_and_exposure_factorizes": factorized,
        "every_surface_cell_uses_all_selected_targets": target_complete,
        "total_selection_nondecreasing_with_planet_radius": radius_monotonic,
        "minimum_adjacent_radius_step": minimum_radius_step,
    }
    result["passed"] = all(
        result[key]
        for key in (
            "all_probabilities_finite_and_bounded",
            "total_selection_does_not_exceed_geometry_and_exposure_factorizes",
            "every_surface_cell_uses_all_selected_targets",
            "total_selection_nondecreasing_with_planet_radius",
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "results/population"
    output.mkdir(parents=True, exist_ok=True)

    frames, manifests = {}, {}
    for kind in ("stars", "injections", "vetting"):
        frames[kind], manifests[kind] = fetch_product(root, kind)
    stellar_selection = StellarSelection()
    selected_stars = frames["stars"].loc[stellar_selection.select(frames["stars"])].copy()
    selected_ids = set(selected_stars["kepid"].astype(int))
    joined = join_injections(frames["injections"], frames["vetting"], frames["stars"])
    selected_injections = joined.loc[joined["KIC_ID"].astype("Int64").isin(selected_ids)].copy()
    domain = SelectionDomain()
    domain_injections = selected_injections.loc[domain.mask(selected_injections)].copy()

    print("Running five target-level injection holdouts ...", flush=True)
    cross_validation = []
    for fold in range(5):
        print(f"  fold {fold + 1}/5", flush=True)
        cross_validation.append(
            validate_injection_holdout(
                selected_injections,
                domain=domain,
                folds=5,
                holdout=fold,
            )
        )
    cross_validation_passed = all(fold["passed"] for fold in cross_validation)
    if not cross_validation_passed:
        raise RuntimeError("At least one target-level injection holdout failed")

    print("Fitting the full constrained selection model ...", flush=True)
    model = fit_selection_model(selected_injections, domain=domain)
    baseline_prediction = predict_injection_rows(model, domain_injections)
    regularization_sensitivity = []
    for name, mes_penalty, detection_penalty in (
        ("weaker_mes_ridge", 1e-4, 0.1),
        ("stronger_mes_ridge", 1e-2, 0.1),
        ("weaker_detection_l2", 1e-3, 0.03),
        ("stronger_detection_l2", 1e-3, 1.0),
    ):
        print(f"  sensitivity: {name}", flush=True)
        alternative = fit_selection_model(
            selected_injections,
            domain=domain,
            mes_ridge_penalty=mes_penalty,
            detection_l2_penalty=detection_penalty,
        )
        alternative_prediction = predict_injection_rows(alternative, domain_injections)
        regularization_sensitivity.append(
            {
                "scenario": name,
                "mes_ridge_penalty": mes_penalty,
                "detection_l2_penalty": detection_penalty,
                "absolute_probability_difference": {
                    probability: distribution_of_absolute_difference(
                        alternative_prediction[probability] - baseline_prediction[probability]
                    )
                    for probability in (
                        "pipeline_including_window",
                        "vetting_given_recovered",
                        "pipeline_and_vetting",
                    )
                },
            }
        )

    print("Evaluating all selected stars on the period-radius surface ...", flush=True)
    periods = np.geomspace(domain.period_min_days, domain.period_max_days, 21)
    radii = np.geomspace(domain.radius_min_earth, domain.radius_max_earth, 17)
    surface = target_averaged_surface(model, selected_stars, periods, radii)
    invariants = surface_invariants(surface, len(selected_stars))
    if not invariants["passed"]:
        raise RuntimeError("Survey-wide selection surface failed a physical invariant")

    print("Comparing the pinned KeplerPORTs target ...", flush=True)
    reference_comparison, reference_metrics = compare_keplerports_reference(
        root, model, selected_stars
    )
    if not reference_metrics["passed"]:
        raise RuntimeError("Pinned KeplerPORTs comparison exceeded its regression tolerance")

    surface_path = output / "dr25_selection_surface.csv"
    comparison_path = output / "dr25_keplerports_selection_comparison.csv"
    model_path = output / "dr25_selection_model.json"
    validation_path = output / "dr25_selection_validation.json"
    plot_base = output / "dr25_selection_surface"
    write_csv(surface_path, surface)
    write_csv(comparison_path, reference_comparison)
    plot_selection_surface(surface, plot_base)
    normalize_text_lf(plot_base.with_suffix(".svg"))

    model_payload = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "scope": "Survey-wide Kepler DR25 selection over a fixed GK-dwarf target sample",
        "release_status": "validated_selection_surface_not_yet_an_occurrence_rate",
        "stellar_selection": asdict(stellar_selection),
        "stellar_denominator": {
            "archive_rows": len(frames["stars"]),
            "selected_unique_targets": len(selected_stars),
            "selected_targets_with_inj1_trial": int(
                selected_stars["kepid"].isin(selected_injections["KIC_ID"]).sum()
            ),
            "selected_targets_without_inj1_trial": int(
                (~selected_stars["kepid"].isin(selected_injections["KIC_ID"])).sum()
            ),
        },
        "calibration_sample": {
            "all_inj1_rows": len(joined),
            "selected_target_inj1_rows": len(selected_injections),
            "domain_inj1_rows": len(domain_injections),
            "domain_recoveries": int(domain_injections["pipeline_recovered"].sum()),
            "domain_vetted_planet_candidates": int(domain_injections["vetted_pc"].sum()),
            "domain_recovery_code_2": int(domain_injections["recovery_code_2"].sum()),
        },
        "model": model.to_dict(),
        "surface_grid": {
            "period_points": periods.tolist(),
            "radius_points": radii.tolist(),
            "cells": len(surface),
        },
        "source_manifests": {
            kind: {
                key: manifests[kind][key]
                for key in ("source_url", "retrieved_at_utc", "row_count", "sha256")
            }
            for kind in frames
        },
        "source_code_sha256": {
            "selection_surface": sha256(root / "src/earth2/population/selection_surface.py"),
            "builder": sha256(Path(__file__)),
        },
        "interpretation": (
            "Target-averaged detection exposure calibrated to official INJ1 artificial "
            "signals. It is not a planet count, occurrence rate, eta-Earth value or "
            "candidate-reliability estimate."
        ),
    }
    write_json(model_path, model_payload)

    validation = {
        "schema_version": "1.0",
        "target_level_cross_validation": {
            "method": (
                "Five mutually exclusive SHA-256(KIC_ID) folds; every injection around "
                "one target stays in one fold"
            ),
            "folds": cross_validation,
            "passed": cross_validation_passed,
        },
        "physical_invariants": invariants,
        "pinned_keplerports_comparison": reference_metrics,
        "regularization_sensitivity": regularization_sensitivity,
        "release_gate": (
            "Every target-level fold must pass MES calibration and beat constant-rate "
            "probability baselines; all surface invariants must hold; the independent "
            "KIC 3429335 reference comparison must remain within declared tolerances."
        ),
        "passed": bool(
            cross_validation_passed and invariants["passed"] and reference_metrics["passed"]
        ),
    }
    write_json(validation_path, validation)

    artifacts = [
        surface_path,
        comparison_path,
        model_path,
        validation_path,
        plot_base.with_suffix(".png"),
        plot_base.with_suffix(".svg"),
    ]
    product_manifest = {
        "schema_version": "1.0",
        "product": "Kepler DR25 survey-wide selection surface",
        "files": {
            path.relative_to(root).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in artifacts
        },
    }
    write_json(output / "dr25_selection_products.json", product_manifest)
    print(
        f"Selection release passed: {len(selected_stars):,} stars, "
        f"{len(domain_injections):,} domain injections, {len(surface):,} cells",
        flush=True,
    )


if __name__ == "__main__":
    main()
