"""Fit, validate and export the constrained DR25 false-alarm reliability model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from earth2.population.archive import fetch_product
from earth2.population.diagnostics import plot_smooth_reliability
from earth2.population.kepler import StellarSelection
from earth2.population.reliability import (
    AnalysisPopulation,
    ReliabilityDomain,
    build_analysis_population,
    classify_observed_false_alarms,
    clean_false_alarm_experiments,
    fetch_support_product,
)
from earth2.population.smooth_reliability import (
    DEFAULT_EXPERIMENT_WEIGHTS,
    candidate_reliability_posterior,
    fit_joint_reliability,
    predict_components,
    run_synthetic_recovery,
    validate_held_out_data,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "results/population"
    output.mkdir(parents=True, exist_ok=True)

    archive_frames, archive_manifests = {}, {}
    for kind in (
        "stars",
        "false_alarm_inv",
        "false_alarm_scr1",
        "false_alarm_scr2",
        "false_alarm_scr3",
        "observed_tces",
    ):
        archive_frames[kind], archive_manifests[kind] = fetch_product(root, kind)
    support_frames, support_manifests = {}, {}
    for kind in (
        "droplist_inv",
        "droplist_scr1",
        "droplist_scr2",
        "droplist_scr3",
        "koifpp",
    ):
        support_frames[kind], support_manifests[kind] = fetch_support_product(root, kind)

    selection = StellarSelection()
    stars = archive_frames["stars"]
    selected_kepids = stars.loc[selection.select(stars), "kepid"].astype(int)
    experiments = {
        "INV": archive_frames["false_alarm_inv"],
        "SCR1": archive_frames["false_alarm_scr1"],
        "SCR2": archive_frames["false_alarm_scr2"],
        "SCR3": archive_frames["false_alarm_scr3"],
    }
    drop_lists = {
        "INV": support_frames["droplist_inv"],
        "SCR1": support_frames["droplist_scr1"],
        "SCR2": support_frames["droplist_scr2"],
        "SCR3": support_frames["droplist_scr3"],
    }
    synthetic, _ = clean_false_alarm_experiments(experiments, drop_lists, selected_kepids)
    observed, _ = classify_observed_false_alarms(
        archive_frames["observed_tces"],
        selected_kepids,
        banned_tces=drop_lists["INV"]["TCE_ID"],
    )
    domain = ReliabilityDomain()
    print("Running held-out real-data checks ...", flush=True)
    held_out = validate_held_out_data(synthetic, observed, domain=domain)
    print("Running deterministic synthetic recovery ...", flush=True)
    synthetic_recovery = run_synthetic_recovery(domain=domain)
    validation = {
        "schema_version": "1.0",
        "real_data_holdouts": held_out,
        "synthetic_recovery": synthetic_recovery,
        "release_gate": (
            "Every experiment-transfer fold must improve Brier score and log loss over its "
            "training-fraction baseline; the deterministic generating-family recovery must "
            "pass all declared RMSE and convergence thresholds."
        ),
        "passed": bool(held_out["passed"] and synthetic_recovery["passed"]),
    }
    if not validation["passed"]:
        raise RuntimeError("Smooth reliability validation gate failed")
    validation_path = output / "smooth_reliability_validation.json"
    validation_path.write_text(
        json.dumps(validation, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    print("Fitting full constrained model and coefficient covariance ...", flush=True)
    fit = fit_joint_reliability(synthetic, observed, domain=domain)
    koi = pd.read_parquet(root / "data/processed/nasa_koi_dr25.parquet")
    population, population_audit = build_analysis_population(
        stars,
        koi,
        support_frames["koifpp"],
        archive_frames["observed_tces"],
        stellar_selection=selection,
        population=AnalysisPopulation(),
    )
    eligible = population.loc[population["eligible"]].copy()
    candidates = candidate_reliability_posterior(fit, eligible)

    sensitivity_frame = pd.DataFrame(
        {
            "period": candidates["observed_tce_period_days"],
            "MES": candidates["observed_tce_mes"],
            "Rp": candidates["koi_prad"],
        },
        index=candidates.index,
    )
    inside_sensitivity = domain.mask(sensitivity_frame)
    sensitivity_frame = sensitivity_frame.loc[inside_sensitivity]
    baseline_reliability = predict_components(fit, sensitivity_frame)["false_alarm_reliability"]
    regularization_sensitivity = []
    for penalty in (0.03, 0.3, 1.0):
        alternative_fit = fit_joint_reliability(
            synthetic,
            observed,
            domain=domain,
            l2_penalty=penalty,
            compute_covariance=False,
        )
        alternative = predict_components(alternative_fit, sensitivity_frame)[
            "false_alarm_reliability"
        ]
        difference = np.abs(alternative - baseline_reliability)
        regularization_sensitivity.append(
            {
                "l2_penalty": penalty,
                "median_absolute_candidate_difference": float(np.median(difference)),
                "maximum_absolute_candidate_difference": float(np.max(difference)),
            }
        )
    delivered_counts = synthetic.loc[domain.mask(synthetic), "experiment"].value_counts()
    delivered_weights = {
        experiment: float(delivered_counts[experiment] / delivered_counts.sum())
        for experiment in DEFAULT_EXPERIMENT_WEIGHTS
    }
    weighting_sensitivity = []
    for name, weights in (
        ("equal_experiments", dict.fromkeys(DEFAULT_EXPERIMENT_WEIGHTS, 0.25)),
        ("delivered_unique_rows", delivered_weights),
    ):
        alternative = predict_components(fit, sensitivity_frame, experiment_weights=weights)[
            "false_alarm_reliability"
        ]
        difference = np.abs(alternative - baseline_reliability)
        weighting_sensitivity.append(
            {
                "scheme": name,
                "weights": weights,
                "median_absolute_candidate_difference": float(np.median(difference)),
                "maximum_absolute_candidate_difference": float(np.max(difference)),
            }
        )
    candidate_columns = [
        "kepid",
        "kepoi_name",
        "TCE_ID",
        "koi_disposition",
        "koi_pdisposition",
        "koi_period",
        "koi_prad",
        "observed_tce_mes",
        "koi_score",
        "fpp_prob",
        "astrophysical_planet_probability",
        "false_alarm_reliability_p025",
        "false_alarm_reliability_p50",
        "false_alarm_reliability_p975",
        "total_candidate_reliability_p025",
        "total_candidate_reliability_p50",
        "total_candidate_reliability_p975",
        "published_comparison_box",
        "robovetter_score_is_candidate_reliability",
        "reliability_status",
        "false_alarm_reliability_label",
        "total_candidate_reliability_label",
    ]
    candidate_path = output / "dr25_candidate_reliability.csv"
    candidates[candidate_columns].to_csv(candidate_path, index=False, float_format="%.10g")
    plot_smooth_reliability(fit, candidates, output / "dr25_smooth_reliability")

    assigned = candidates["false_alarm_reliability_p50"].notna()
    model = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "scope": "Kepler DR25 instrumental false-alarm reliability",
        "release_status": "validated_for_candidates_inside_declared_period_radius_mes_domain",
        "fit": fit.to_dict(),
        "experiment_family_weights": DEFAULT_EXPERIMENT_WEIGHTS,
        "weighting_reason": (
            "One-half inverted family; one-half divided equally across three scrambled "
            "experiments. Rows are never duplicated as independent observations."
        ),
        "validation": {
            "passed": True,
            "artifact": validation_path.name,
            "sha256": sha256(validation_path),
        },
        "candidate_assignment": {
            "eligible_candidates": len(candidates),
            "assigned_inside_domain": int(assigned.sum()),
            "withheld_outside_domain_or_missing_fpp": int((~assigned).sum()),
            "published_comparison_box_candidates": int(
                candidates["published_comparison_box"].sum()
            ),
            "published_comparison_box_assigned": int(
                (candidates["published_comparison_box"] & assigned).sum()
            ),
            "interval": (
                "2.5/50/97.5 percentiles from 20,000 deterministic multivariate-normal "
                "coefficient draws using the penalized observed Hessian (Laplace approximation)"
            ),
            "astrophysical_fpp_treatment": (
                "Total reliability equals false-alarm reliability times (1-FPP). The external "
                "FPP value is fixed because its own model-parameter uncertainty is not delivered."
            ),
            "koi_score_used_as_reliability": False,
        },
        "sensitivity": {
            "candidate_rows_inside_domain": len(sensitivity_frame),
            "regularization": regularization_sensitivity,
            "experiment_weighting": weighting_sensitivity,
            "interpretation": (
                "Point-prediction sensitivity only; coefficient intervals retain the declared "
                "0.1 penalty and default experiment-family weighting."
            ),
        },
        "population_audit": population_audit,
        "source_hashes": {
            **{f"archive_{key}": value["sha256"] for key, value in archive_manifests.items()},
            **{f"support_{key}": value["sha256"] for key, value in support_manifests.items()},
        },
        "candidate_artifact": {
            "path": candidate_path.relative_to(root).as_posix(),
            "sha256": sha256(candidate_path),
        },
        "limitations": [
            "Quadratic log-period/MES surfaces can miss finer structure or target heterogeneity",
            "Experiment-family weighting is a declared design choice",
            "Laplace intervals do not include model-family uncertainty",
            "External astrophysical FPP model uncertainty is unavailable",
            "Two eligible high-MES candidates are outside the calibration domain and withheld",
            "No occurrence rate is computed by this model",
        ],
        "next_gate": (
            "Combine candidate reliability with the validated per-target detection surface in "
            "a measurement-error-aware hierarchical period-radius likelihood."
        ),
    }
    model_path = output / "dr25_smooth_reliability_model.json"
    model_path.write_text(json.dumps(model, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "validation_passed": True,
                "assigned_candidates": int(assigned.sum()),
                "withheld_candidates": int((~assigned).sum()),
                "model": model_path.relative_to(root).as_posix(),
                "candidate_sha256": sha256(candidate_path),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
