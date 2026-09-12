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

    observed_intrinsic = json.loads(
        (population / "dr25_observed_vs_intrinsic.json").read_text()
    )
    check(
        "observed-versus-intrinsic narrative keeps mixed evidence labels explicit",
        observed_intrinsic["label"] == "OBSERVED + MODEL-INFERRED"
        and {row["label"] for row in observed_intrinsic["funnel"]}
        == {"OBSERVED", "MODEL-INFERRED"},
    )
    check(
        "observed-versus-intrinsic web payload is byte-identical to the research product",
        (RESULTS_DIR.parent / "web/public/data/occurrence.json").read_bytes()
        == (population / "dr25_observed_vs_intrinsic.json").read_bytes(),
    )
    check(
        "Earth-pivot selection is finite, non-zero and below one percent",
        0
        < observed_intrinsic["earth_pivot_visibility"]["mean_total_selection"]
        < 0.01,
    )
    observed_manifest = json.loads(
        (population / "dr25_observed_intrinsic_products.json").read_text()
    )
    observed_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in observed_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check(
        "observed-versus-intrinsic product hashes match the release manifest",
        observed_hashes_match,
    )

    composition_dir = RESULTS_DIR / "composition"
    composition = json.loads(
        (composition_dir / "bulk_composition_ensemble.json").read_text()
    )
    composition_records = composition["records"]
    probabilities = [
        value
        for row in composition_records
        for key, value in row.items()
        if key.startswith("p_") and value is not None
    ]
    check(
        "composition ensemble is model-inferred and every probability is bounded",
        composition["label"] == "MODEL-INFERRED"
        and all(0 <= value <= 1 for value in probabilities),
    )
    check(
        "radius-predicted and minimum masses never enter two-dimensional composition models",
        all(
            row["p_rocky_zeng_fe_si_envelope"] is None
            and row["p_rocky_otegi_equal_prior"] is None
            for row in composition_records
            if not row["catalogue_mass_accepted_as_independent"]
        ),
    )
    earth_composition = next(row for row in composition_records if row["pl_name"] == "Earth")
    check(
        "Earth control is recovered inside the published Zeng terrestrial envelope",
        earth_composition["p_consistent_with_terrestrial_composition_zeng"] >= 0.99
        and earth_composition["p_requires_volatiles_zeng"] <= 0.01,
    )
    composition_manifest = json.loads(
        (composition_dir / "composition_products.json").read_text()
    )
    composition_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in composition_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check(
        "composition product hashes match the release manifest",
        composition_hashes_match,
    )

    climate_dir = RESULTS_DIR / "climate"
    mist_metadata = json.loads(
        (climate_dir / "mist_v1p2_main_sequence_grid.json").read_text()
    )
    mist_grid = pd.read_csv(climate_dir / "mist_v1p2_main_sequence_grid.csv")
    check(
        "compact MIST grid is explicitly model-inferred and hash-linked to its source",
        mist_metadata["label"] == "MODEL-INFERRED"
        and len(mist_metadata["source_sha256"]) == 64
        and hashlib.sha256(
            (climate_dir / "mist_v1p2_main_sequence_grid.csv").read_bytes()
        ).hexdigest()
        == mist_metadata["grid_sha256"],
    )
    check(
        "MIST grid contains finite, unique phase-0 interpolation cells",
        mist_grid[
            [
                "feh",
                "log10_age_years",
                "initial_mass_solar",
                "log10_luminosity_solar",
                "log10_teff_kelvin",
            ]
        ]
        .notna()
        .all()
        .all()
        and not mist_grid.duplicated(
            ["feh", "log10_age_years", "initial_mass_solar"]
        ).any()
        and mist_grid["label"].eq("MODEL-INFERRED").all(),
    )
    solar_track = mist_grid[
        mist_grid["feh"].eq(0)
        & mist_grid["initial_mass_solar"].eq(1)
        & mist_grid["log10_age_years"].between(9.0, 9.7)
    ].sort_values("log10_age_years")
    check(
        "solar-metallicity one-solar-mass MIST luminosity rises across the sampled main sequence",
        len(solar_track) >= 10
        and solar_track["log10_luminosity_solar"].iloc[-1]
        > solar_track["log10_luminosity_solar"].iloc[0],
    )
    mist_manifest = json.loads((climate_dir / "mist_grid_products.json").read_text())
    mist_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in mist_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check("compact MIST product hashes match the release manifest", mist_hashes_match)

    continuous = json.loads((climate_dir / "continuous_hz.json").read_text())
    continuous_records = continuous["records"]
    inferred_hz = [row for row in continuous_records if row["status"] == "inferred"]
    check(
        "continuous-HZ product preserves model label and full catalogue accounting",
        continuous["label"] == "MODEL-INFERRED"
        and continuous["population"]["confirmed_planets_evaluated"] == 6354
        and len(continuous_records) == 6354
        and len(inferred_hz) == continuous["population"]["inferred"],
    )
    continuous_probabilities = [
        model["p_current_hz"]
        for row in inferred_hz
        for model in row["climate_prescriptions"].values()
        if model["p_current_hz"] is not None
    ]
    continuous_fractions = [
        value
        for row in inferred_hz
        for model in row["climate_prescriptions"].values()
        for value in model["f_chz"].values()
        if value is not None
    ]
    check(
        "continuous-HZ probabilities and lifetime fractions are bounded",
        all(0 <= value <= 1 for value in continuous_probabilities)
        and all(0 <= value <= 1 for value in continuous_fractions),
    )
    check(
        "every inferred history passes support and luminosity-anchor contracts",
        all(
            row["supported_fraction"]
            >= continuous["sampling"]["minimum_supported_fraction"]
            and row["luminosity_anchor_max_abs_dex"] < 1e-10
            and set(row["climate_prescriptions"])
            == set(continuous["climate_prescriptions"])
            for row in inferred_hz
        ),
    )
    check(
        "climate agreement is the complement of boundary sensitivity",
        all(
            abs(row["model_agreement"] + row["boundary_sensitivity"] - 1) < 1e-12
            for row in inferred_hz
        ),
    )
    continuous_manifest = json.loads(
        (climate_dir / "continuous_hz_products.json").read_text()
    )
    continuous_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in continuous_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check(
        "continuous-HZ product hashes match the release manifest",
        continuous_hashes_match,
    )

    environment_dir = RESULTS_DIR / "environment"
    environment = json.loads(
        (environment_dir / "xuv_escape_scenarios.json").read_text()
    )
    environment_records = environment["records"]
    check(
        "XUV environment release contains the fixed high-value target set",
        environment["labels"] == ["DERIVED", "SCENARIO"]
        and len(environment_records) == 60
        and [row["earth2_rank"] for row in environment_records] == list(range(1, 61)),
    )
    muscles_records = [
        row for row in environment_records if row["muscles_current_environment"] is not None
    ]
    check(
        "MUSCLES matches retain stitched-evidence labels and archive source hashes",
        len(muscles_records) == 9
        and len({row["hostname"] for row in muscles_records}) == 3
        and all(
            row["muscles_current_environment"]["evidence_basis"]
            == "MAST_MUSCLES_STITCHED_OBSERVED_RECONSTRUCTED_MODEL_SED"
            and len(row["muscles_current_environment"]["source_sha256"]) == 64
            and row["muscles_current_environment"]["bands"]["xuv_5_912a"][
                "flux_at_planet_w_m2"
            ]
            > 0
            for row in muscles_records
        ),
    )
    escape_records = [
        row
        for row in environment_records
        if row["escape_status"] == "energy_limited_scenario_ensemble"
    ]
    check(
        "energy-limited escape ensembles span every declared assumption combination",
        len(escape_records) == environment["population"]["with_escape_ensemble"]
        and all(len(row["escape_scenarios"]) == 27 for row in escape_records)
        and all(
            scenario["label"] == "SCENARIO"
            and scenario["current_mass_loss_kg_s"] > 0
            and scenario["integrated_lost_earth_masses"] > 0
            and 0 < scenario["tide_factor"] <= 1
            for row in escape_records
            for scenario in row["escape_scenarios"]
        ),
    )
    check(
        "upper-limit masses never enter the atmospheric-escape calculation",
        all(
            not row["escape_scenarios"]
            for row in environment_records
            if row["planet_mass_basis"] == "upper_limit_not_used"
        ),
    )
    environment_manifest = json.loads(
        (environment_dir / "environment_products.json").read_text()
    )
    environment_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in environment_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check(
        "XUV and escape product hashes match the release manifest",
        environment_hashes_match,
    )

    atmosphere_dir = RESULTS_DIR / "atmosphere"
    atmosphere = json.loads(
        (atmosphere_dir / "atmosphere_evidence.json").read_text()
    )
    observability = pd.read_csv(atmosphere_dir / "observability_scenarios.csv")
    reductions = pd.read_csv(atmosphere_dir / "spectrum_reductions.csv")
    measurements = pd.read_csv(atmosphere_dir / "spectrum_measurements.csv.gz")
    check(
        "atmospheric evidence uses only the declared evidence classes",
        atmosphere["labels"] == ["OBSERVED", "DERIVED", "SCENARIO"]
        and observability["label"].eq("SCENARIO").all()
        and reductions["label"].eq("OBSERVED").all()
        and measurements["label"].eq("DERIVED").all(),
    )
    check(
        "atmospheric observability covers the fixed target set and four compositions",
        len(observability) == 60
        and [int(value) for value in observability["earth2_rank"]]
        == list(range(1, 61))
        and all(
            f"{name}__transmission_signal_ppm" in observability.columns
            for name in (
                "hydrogen_helium",
                "water_vapour",
                "earth_like_n2_o2",
                "carbon_dioxide",
            )
        ),
    )
    supported_observability = observability[
        observability["status"].eq("scenario_ensemble")
    ]
    check(
        "high molecular-weight atmospheres have the explicitly smaller clear-sky signal",
        len(supported_observability) == 54
        and (
            supported_observability["hydrogen_helium__transmission_signal_ppm"]
            > supported_observability["earth_like_n2_o2__transmission_signal_ppm"]
        ).all()
        and (
            supported_observability["hydrogen_to_earth_air_signal_ratio"]
            .sub(28.97 / 2.3)
            .abs()
            .lt(1e-8)
            .all()
        ),
    )
    check(
        "upper-limit planet masses never enter atmospheric signal scenarios",
        observability.loc[
            observability["planet_mass_basis"].eq("upper_limit_not_used"),
            "status",
        ]
        .eq("undetermined_missing_usable_mass_radius_temperature_or_star_radius")
        .all(),
    )
    spectrum_evidence = atmosphere["spectrum_evidence"]
    check(
        "spectrum archive rows preserve reductions and measurement provenance",
        len(reductions) == 1826
        and reductions["reduction_id"].is_unique
        and len(measurements) == 8309
        and measurements["reduction_id"].nunique() == 502
        and spectrum_evidence["comparison_count"] == 557
        and len(spectrum_evidence["reduction_comparisons"]) == 557
        and all(
            row["interpretation"]
            == "overlap diagnostic only; neither reduction is preferred or merged"
            for row in spectrum_evidence["reduction_comparisons"]
        ),
    )
    check(
        "missing program and DOI metadata remain explicit rather than fabricated",
        reductions["program_status"].eq("not_provided_by_archive_index").all()
        and measurements["program_status"].eq("not_provided_by_source_table").all()
        and spectrum_evidence["doi_metadata_status"]
        == "not_provided_by_current_archive_tables; bibcodes retained",
    )
    atmosphere_manifest = json.loads(
        (atmosphere_dir / "atmosphere_products.json").read_text()
    )
    atmosphere_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in atmosphere_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check(
        "atmospheric evidence product hashes match the release manifest",
        atmosphere_hashes_match,
    )

    hwo_dir = RESULTS_DIR / "hwo"
    hwo = json.loads((hwo_dir / "hwo_precursor_atlas.json").read_text())
    hwo_source = json.loads(
        (RESULTS_DIR.parent / "data/manifests/hwo_hpic.json").read_text()
    )
    hwo_atlas = pd.read_csv(
        hwo_dir / "hpic_v1p1_atlas.csv.gz",
        dtype={
            "star_name": "string",
            "tic_id": "string",
            "gaia_dr2_id": "string",
            "gaia_dr3_id": "string",
        },
        low_memory=False,
    )
    exoearth_forecast = pd.read_csv(hwo_dir / "exoearth_accessibility.csv.gz")
    known_planet_forecast = pd.read_csv(
        hwo_dir / "known_planet_accessibility.csv"
    )
    check(
        "HWO source manifest pins HPIC v1.1 and TSS25 independently",
        [dataset["dataset_id"] for dataset in hwo_source["datasets"]]
        == ["hpic_v1p1", "tss25_2025"]
        and all(
            dataset["rows"] == 12944
            and len(dataset["archive_sha256"]) == 64
            and len(dataset["table_sha256"]) == 64
            for dataset in hwo_source["datasets"]
        )
        and hashlib.sha256(
            (RESULTS_DIR.parent / "data/manifests/hwo_hpic.json").read_bytes()
        ).hexdigest()
        == hwo["source_manifest_sha256"],
    )
    check(
        "HPIC atlas preserves all unique stars, identifiers, and TSS25 tiers",
        len(hwo_atlas) == 12944
        and hwo_atlas["star_name"].is_unique
        and hwo_atlas["source_label"].eq("OBSERVED").all()
        and hwo_atlas["derived_geometry_label"].eq("DERIVED").all()
        and hwo_atlas["TSS_tier"].value_counts().sort_index().to_dict()
        == {1: 164, 2: 495, 3: 12285}
        and not hwo_atlas["gaia_dr3_id"].dropna().str.contains(r"[eE+]").any(),
    )
    hwo_eeid = hwo_atlas[
        hwo_atlas[["st_lum", "sy_dist", "eeid_au", "eeid_angular_mas"]]
        .notna()
        .all(axis=1)
    ]
    check(
        "EEID distances and angular scales reproduce their declared equations",
        len(hwo_eeid) == 12682
        and (
            hwo_eeid["eeid_au"].pow(2).sub(10 ** hwo_eeid["st_lum"]).abs()
            / (10 ** hwo_eeid["st_lum"])
        ).max()
        < 1e-8
        and (
            hwo_eeid["eeid_angular_mas"]
            .sub(1000 * hwo_eeid["eeid_au"] / hwo_eeid["sy_dist"])
            .abs()
            / hwo_eeid["eeid_angular_mas"]
        ).max()
        < 1e-8,
    )
    check(
        "exo-Earth accessibility remains a complete bounded forecast grid",
        len(exoearth_forecast) == 12944 * 3
        and exoearth_forecast["label"].eq("FORECAST").all()
        and exoearth_forecast["p_observable"].dropna().between(0, 1).all()
        and exoearth_forecast.loc[
            exoearth_forecast["status"].eq(
                "catalogue_conditioned_scenario_probability"
            ),
            "star_name",
        ].nunique()
        == 12682,
    )
    exoearth_wide = exoearth_forecast.pivot(
        index="star_name", columns="scenario", values="p_observable"
    ).dropna()
    check(
        "HWO analytic trade cases obey their inner-working-angle ordering",
        (
            exoearth_wide["analytic_8m_500nm_3lambda_d"]
            >= exoearth_wide["analytic_6m_500nm_3lambda_d"]
        ).all()
        and (
            exoearth_wide["analytic_6m_500nm_3lambda_d"]
            >= exoearth_wide["analytic_6m_750nm_3lambda_d"]
        ).all()
        and all(
            scenario["label"] == "SCENARIO"
            and scenario["interpretation"]
            == "generic analytic trade case; not a final HWO design"
            for scenario in hwo["instrument_scenarios"]
        ),
    )
    check(
        "known-planet imaging forecasts retain M sin i as a separate quantity",
        len(known_planet_forecast) == 744 * 3
        and known_planet_forecast["pl_name"].nunique() == 744
        and known_planet_forecast["hostname"].nunique() == 464
        and known_planet_forecast["p_observable"].dropna().between(0, 1).all()
        and known_planet_forecast.loc[
            known_planet_forecast["mass_class"].eq("msini_lower_limit"),
            "pl_name",
        ].nunique()
        == 406
        and (
            known_planet_forecast.loc[
                known_planet_forecast["mass_class"].eq("msini_lower_limit")
                & known_planet_forecast["true_mass_scenario_p50"].notna(),
                "true_mass_scenario_p50",
            ]
            >= known_planet_forecast.loc[
                known_planet_forecast["mass_class"].eq("msini_lower_limit")
                & known_planet_forecast["true_mass_scenario_p50"].notna(),
                "minimum_mass_earth",
            ]
        ).all(),
    )
    hwo_manifest = json.loads((hwo_dir / "hwo_products.json").read_text())
    hwo_hashes_match = all(
        path.exists()
        and path.stat().st_size == metadata["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == metadata["sha256"]
        for relative, metadata in hwo_manifest["files"].items()
        for path in [RESULTS_DIR.parent / relative]
    )
    check("HWO precursor product hashes match the release manifest", hwo_hashes_match)

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
