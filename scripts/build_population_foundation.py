"""Build the pinned DR25 reliability and analysis-population foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from earth2.population.archive import fetch_product
from earth2.population.diagnostics import plot_reliability_grid
from earth2.population.kepler import StellarSelection
from earth2.population.reliability import (
    REPOSITORY_COMMIT,
    AnalysisPopulation,
    ReliabilityDomain,
    build_analysis_population,
    classify_observed_false_alarms,
    clean_false_alarm_experiments,
    fetch_support_product,
    reliability_grid,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def published_comparisons() -> dict:
    return {
        "schema_version": "1.0",
        "interpretation": (
            "A registry of estimands and domains, not a pooled meta-analysis. Finding Earth 2 "
            "has no real intrinsic occurrence result at this checkpoint."
        ),
        "studies": [
            {
                "study": "Hsu et al. 2019",
                "reference": "https://arxiv.org/abs/1902.01417",
                "survey": "Kepler DR25 with Gaia DR2 stellar radii",
                "stellar_population": "FGK stars",
                "estimand": "integrated planets per star f_R,P",
                "planet_radius_earth": [0.75, 1.5],
                "orbital_period_days": [237.0, 500.0],
                "reported_upper_limit_percentile_84_13": 0.27,
                "recommended_planning_range": [0.03, 0.40],
                "reported_differential_gamma_range": [0.06, 0.76],
                "comparison_status": "domain_matched_target; pending_project_intrinsic_inference",
            },
            {
                "study": "Bryson et al. 2020",
                "reference": "https://arxiv.org/abs/1906.03575",
                "survey": "Kepler DR25",
                "stellar_population": "GK dwarf stars",
                "estimand": "planets per star within 20 percent of Earth period and radius",
                "planet_radius_earth": [0.8, 1.2],
                "orbital_period_days": [292.2, 438.3],
                "reported_reliability_corrected": {
                    "median": 0.015,
                    "lower_error": 0.007,
                    "upper_error": 0.011,
                },
                "reported_without_reliability": {
                    "median": 0.034,
                    "lower_error": 0.012,
                    "upper_error": 0.018,
                },
                "comparison_status": "different_domain_and_stellar_contract",
            },
            {
                "study": "Bryson et al. 2021",
                "reference": "https://arxiv.org/abs/2010.14812",
                "survey": "Kepler DR25 with Gaia-based stellar properties",
                "stellar_population": "main-sequence dwarfs, 4800–6300 K",
                "estimand": "eta Earth in the star-dependent conservative habitable zone",
                "planet_radius_earth": [0.5, 1.5],
                "orbital_period_days": None,
                "reported_conservative_hz_bounds": [
                    {"median": 0.37, "lower_error_68": 0.21, "upper_error_68": 0.48},
                    {"median": 0.60, "lower_error_68": 0.36, "upper_error_68": 0.90},
                ],
                "bound_meaning": "Two completeness extrapolation assumptions",
                "comparison_status": "different_estimand; no direct numerical comparison",
            },
        ],
    }


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
        print(f"{kind:24s} {len(archive_frames[kind]):7d} validated rows", flush=True)

    support_frames, support_manifests = {}, {}
    for kind in (
        "droplist_inv",
        "droplist_scr1",
        "droplist_scr2",
        "droplist_scr3",
        "koifpp",
    ):
        support_frames[kind], support_manifests[kind] = fetch_support_product(root, kind)
        print(f"{kind:24s} {len(support_frames[kind]):7d} validated rows", flush=True)

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
    synthetic, synthetic_audit = clean_false_alarm_experiments(
        experiments, drop_lists, selected_kepids
    )
    observed, observed_audit = classify_observed_false_alarms(
        archive_frames["observed_tces"],
        selected_kepids,
        banned_tces=drop_lists["INV"]["TCE_ID"],
    )
    reliability_domain = ReliabilityDomain()
    period_edges = np.array([50, 100, 200, 300, 400, 500, 600], float)
    mes_edges = np.array([7, 8, 9, 10, 12, 15, 20, 30], float)
    grid = reliability_grid(
        synthetic,
        observed,
        period_edges,
        mes_edges,
        domain=reliability_domain,
    )
    grid_path = output / "dr25_reliability_grid.csv"
    grid.to_csv(grid_path, index=False, float_format="%.10g")
    plot_reliability_grid(grid, output / "dr25_reliability_diagnostics")

    koi_path = root / "data/processed/nasa_koi_dr25.parquet"
    if not koi_path.exists():
        raise FileNotFoundError("Run the main archive sync before building the population contract")
    koi = pd.read_parquet(koi_path)
    population_contract = AnalysisPopulation()
    population, population_audit = build_analysis_population(
        stars,
        koi,
        support_frames["koifpp"],
        archive_frames["observed_tces"],
        stellar_selection=selection,
        population=population_contract,
    )
    candidate_columns = [
        "kepid",
        "kepoi_name",
        "TCE_ID",
        "koi_disposition",
        "koi_pdisposition",
        "koi_period",
        "koi_period_err1",
        "koi_period_err2",
        "koi_prad",
        "koi_prad_err1",
        "koi_prad_err2",
        "koi_model_snr",
        "koi_score",
        "fpp_prob",
        "astrophysical_planet_probability",
        "astrophysical_planet_probability_label",
        "observed_tce_disposition",
        "observed_tce_mes",
        "published_comparison_box",
        "robovetter_score_is_candidate_reliability",
        "false_alarm_reliability",
        "total_candidate_reliability",
        "reliability_status",
    ]
    candidates_path = output / "dr25_analysis_population.csv"
    population.loc[population["eligible"], candidate_columns].to_csv(
        candidates_path, index=False, float_format="%.10g"
    )

    comparisons = published_comparisons()
    comparison_path = output / "published_occurrence_comparisons.json"
    comparison_path.write_text(
        json.dumps(comparisons, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    fpp_period_difference = (population["koi_period"] - population["fpp_koi_period"]).abs()
    mismatch_rows = population.loc[
        fpp_period_difference > 1,
        ["kepid", "kepoi_name", "koi_period", "fpp_koi_period", "fpp_prob"],
    ].to_dict("records")
    domain_synthetic = synthetic.loc[reliability_domain.mask(synthetic)]
    domain_observed = observed.loc[reliability_domain.mask(observed)]
    summary = {
        "schema_version": "1.0",
        "scope": "Kepler DR25 reliability inputs and fixed analysis-population contract",
        "release_status": "foundation_only_no_intrinsic_occurrence_result",
        "labels": {
            "false_alarm_experiments": "SIMULATED",
            "observed_tces": "OBSERVED",
            "false_alarm_reliability_equation": "MODEL-INFERRED",
            "astrophysical_false_positive_probability": "MODEL-INFERRED",
        },
        "stellar_selection": asdict(selection),
        "reliability_domain": asdict(reliability_domain),
        "analysis_population": population_audit,
        "false_alarm_experiment_cleaning": synthetic_audit,
        "observed_classification": observed_audit,
        "reliability_grid": {
            "pooling": "Unique delivered rows from INV, SCR1, SCR2 and SCR3; no duplicated trials",
            "published_code_difference": (
                "The pinned occurrence notebook repeats INV three times to balance one inverted "
                "experiment against three scrambled experiments. This descriptive grid does not "
                "turn those repeated rows into independent binomial trials."
            ),
            "equation": "R_FA = 1 - [F_FA/(1-F_FA)] * [(1-E_FA)/E_FA]",
            "domain_synthetic_trials": len(domain_synthetic),
            "domain_synthetic_rejected_as_fp": int(domain_synthetic["Disp"].eq("FP").sum()),
            "domain_observed_tces": len(domain_observed),
            "domain_observed_instrumental_false_alarms": int(
                domain_observed["observed_false_alarm"].sum()
            ),
            "cells": len(grid),
            "status_counts": {
                key: int(value) for key, value in grid["status"].value_counts().items()
            },
            "intervals": (
                "Jeffreys Beta(0.5,0.5) component posteriors; 20,000 deterministic draws per "
                "non-empty cell. Equation outputs are raw and never clipped to [0,1]."
            ),
            "candidate_assignment": "none_pending_validated_smooth_model",
        },
        "fpp_release_audit": {
            "rows": len(support_frames["koifpp"]),
            "missing_probabilities": int(support_frames["koifpp"]["fpp_prob"].isna().sum()),
            "period_mismatch_over_one_day": mismatch_rows,
        },
        "source_repository_commit": REPOSITORY_COMMIT,
        "source_hashes": {
            **{f"archive_{key}": value["sha256"] for key, value in archive_manifests.items()},
            **{f"support_{key}": value["sha256"] for key, value in support_manifests.items()},
        },
        "artifact_hashes": {
            "dr25_reliability_grid.csv": file_sha256(grid_path),
            "dr25_analysis_population.csv": file_sha256(candidates_path),
            "published_occurrence_comparisons.json": file_sha256(comparison_path),
        },
        "open_gates": [
            "Fit and validate a smooth false-alarm effectiveness and observed false-alarm model",
            "Propagate false-alarm and astrophysical-FPP uncertainty into candidate weights",
            "Complete per-target detection calibration across the full selected denominator",
            "Fit a measurement-error-aware hierarchical period-radius population likelihood",
            "Pass end-to-end real-data posterior predictive and literature-domain comparisons",
        ],
    }
    summary_path = output / "dr25_reliability_foundation.json"
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
