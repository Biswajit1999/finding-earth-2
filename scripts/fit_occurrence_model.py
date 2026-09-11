"""Fit validated fixed-box Kepler DR25 occurrence posteriors with uncertainty."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from earth2.population.archive import fetch_product
from earth2.population.hierarchical import (
    CandidateImputations,
    ReliabilityDraws,
    SelectionExposure,
    draw_candidate_imputations,
    draw_candidate_reliability,
    draw_selection_deltas,
    evaluate_selection_exposure,
    load_reliability_model,
    load_selection_model,
    perturb_selection_exposure,
    selection_parameter_contract,
)
from earth2.population.kepler import StellarSelection
from earth2.population.occurrence import (
    LogQuadrature,
    OccurrenceDomain,
    build_powerlaw_grid,
    draw_binned_posterior,
    draw_imputed_posterior,
    log_gauss_legendre_quadrature,
    powerlaw_integral,
    subdomain_fraction,
    summarize_draws,
)

SEED = 20260911
FULL_DOMAIN = OccurrenceDomain()
HSU_DOMAIN = OccurrenceDomain(
    period_min_days=237.0,
    period_max_days=500.0,
    radius_min_earth=0.75,
    radius_max_earth=1.5,
)
BRYSON_EARTH_DOMAIN = OccurrenceDomain(
    period_min_days=292.2,
    period_max_days=438.3,
    radius_min_earth=0.8,
    radius_max_earth=1.2,
)
ESTIMANDS = {
    "full_fixed_box": FULL_DOMAIN,
    "hsu_2019_fixed_box": HSU_DOMAIN,
    "bryson_2020_earth_20_percent_box": BRYSON_EARTH_DOMAIN,
}


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
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    normalized = b"\n".join(line.rstrip() for line in payload.split(b"\n"))
    if normalized != payload:
        path.write_bytes(normalized)


def exposure_cache_contract(
    root: Path,
    selection_model_path: Path,
    stellar_manifest: dict,
) -> dict:
    return {
        "selection_model_sha256": sha256(selection_model_path),
        "stellar_source_sha256": stellar_manifest["sha256"],
        "hierarchical_source_sha256": sha256(root / "src/earth2/population/hierarchical.py"),
        "estimands": {name: asdict(domain) for name, domain in ESTIMANDS.items()},
        "quadrature": {
            "full_fixed_box": {"period_nodes": 14, "radius_nodes": 12},
            "hsu_2019_fixed_box": {"period_nodes": 12, "radius_nodes": 10},
            "bryson_2020_earth_20_percent_box": {
                "period_nodes": 12,
                "radius_nodes": 10,
            },
        },
    }


def save_exposure_cache(
    path: Path,
    metadata_path: Path,
    exposures: dict[str, tuple[LogQuadrature, SelectionExposure]],
    contract: dict,
    selected_stars: int,
) -> None:
    rows = []
    for estimand, (quadrature, exposure) in exposures.items():
        for index in range(len(exposure.effective_stars)):
            row = {
                "estimand": estimand,
                "node_index": index,
                "period_days": quadrature.periods_days[index],
                "planet_radius_earth": quadrature.radii_earth[index],
                "log_quadrature_weight": quadrature.weights[index],
                "effective_stars": exposure.effective_stars[index],
                "label": "MODEL-INFERRED",
            }
            row.update(
                {
                    f"gradient::{name}": exposure.gradient[index, column]
                    for column, name in enumerate(exposure.coefficient_names)
                }
            )
            rows.append(row)
    write_csv(path, pd.DataFrame(rows))
    write_json(
        metadata_path,
        {
            "schema_version": "1.0",
            "label": "MODEL-INFERRED",
            "selected_stars": selected_stars,
            "contract": contract,
            "coefficient_blocks": {
                "mes": 11,
                "pipeline_including_window": 5,
                "vetting_given_recovered": 5,
                "cross_block_covariance": "not published; treated as zero",
            },
            "boundary_policy": (
                "The pipeline window coefficient fitted at its non-negative boundary "
                "is held fixed; other constrained draws must remain non-negative."
            ),
            "interpretation": (
                "Exact all-target effective-star exposure and analytic local coefficient "
                "derivatives at log-space quadrature nodes; not an occurrence rate."
            ),
            "csv_sha256": sha256(path),
        },
    )


def load_exposure_cache(
    path: Path,
    metadata_path: Path,
    model,
    contract: dict,
) -> dict[str, tuple[LogQuadrature, SelectionExposure]] | None:
    if not path.exists() or not metadata_path.exists():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("contract") != contract or metadata.get("csv_sha256") != sha256(path):
        return None
    frame = pd.read_csv(path)
    names, covariance, fixed = selection_parameter_contract(model)
    gradient_columns = [f"gradient::{name}" for name in names]
    if not set(gradient_columns).issubset(frame.columns):
        return None
    output = {}
    for estimand, domain in ESTIMANDS.items():
        configuration = contract["quadrature"][estimand]
        quadrature = log_gauss_legendre_quadrature(domain, **configuration)
        subset = frame.loc[frame["estimand"].eq(estimand)].sort_values("node_index")
        if (
            len(subset) != len(quadrature.weights)
            or not np.allclose(subset["period_days"], quadrature.periods_days)
            or not np.allclose(subset["planet_radius_earth"], quadrature.radii_earth)
            or not np.allclose(subset["log_quadrature_weight"], quadrature.weights)
        ):
            return None
        output[estimand] = (
            quadrature,
            SelectionExposure(
                effective_stars=subset["effective_stars"].to_numpy(float),
                gradient=subset[gradient_columns].to_numpy(float),
                coefficient_names=names,
                covariance=covariance,
                fixed_at_boundary=fixed,
            ),
        )
    return output


def get_exposures(
    root: Path,
    model,
    selected_stars: pd.DataFrame,
    contract: dict,
    *,
    rebuild: bool,
) -> dict[str, tuple[LogQuadrature, SelectionExposure]]:
    output = root / "results/population"
    cache_path = output / "dr25_occurrence_exposure.csv"
    metadata_path = output / "dr25_occurrence_exposure.json"
    cached = None if rebuild else load_exposure_cache(cache_path, metadata_path, model, contract)
    if cached is not None:
        print("Using validated all-target occurrence exposure cache", flush=True)
        return cached
    exposures: dict[str, tuple[LogQuadrature, SelectionExposure]] = {}
    for estimand, domain in ESTIMANDS.items():
        configuration = contract["quadrature"][estimand]
        quadrature = log_gauss_legendre_quadrature(domain, **configuration)
        print(
            f"Evaluating {estimand}: {len(quadrature.weights)} nodes x "
            f"{len(selected_stars):,} stars x {model.impact_quadrature_nodes} impacts",
            flush=True,
        )
        exposures[estimand] = (
            quadrature,
            evaluate_selection_exposure(model, selected_stars, quadrature, domain),
        )
    save_exposure_cache(
        cache_path,
        metadata_path,
        exposures,
        contract,
        len(selected_stars),
    )
    return exposures


def inference_run(
    domain: OccurrenceDomain,
    quadrature: LogQuadrature,
    exposure: SelectionExposure,
    candidates: pd.DataFrame,
    reliability: ReliabilityDraws,
    selection_deltas,
    *,
    unsupported_reliability: float,
    radius_error_scale: float = 1.0,
    slope_prior_sigma: float = 2.0,
    rate_prior_shape: float = 0.5,
    rate_prior_rate: float = 0.5,
    selection_uncertainty: bool = True,
    slope_grid_limit: float = 6.0,
    slope_grid_points: int = 81,
    seed: int,
) -> tuple[dict[str, np.ndarray], CandidateImputations]:
    grid = build_powerlaw_grid(
        quadrature,
        domain,
        alpha_values=np.linspace(-slope_grid_limit, slope_grid_limit, slope_grid_points),
        beta_values=np.linspace(-slope_grid_limit, slope_grid_limit, slope_grid_points),
        slope_prior_sigma=slope_prior_sigma,
    )
    imputation = draw_candidate_imputations(
        candidates,
        reliability,
        domain,
        unsupported_false_alarm_reliability=unsupported_reliability,
        radius_error_scale=radius_error_scale,
        seed=seed,
    )
    effective_stars = (
        perturb_selection_exposure(exposure, selection_deltas)
        if selection_uncertainty
        else exposure.effective_stars
    )
    posterior = draw_imputed_posterior(
        grid,
        effective_stars,
        imputation.periods_days,
        imputation.radii_earth,
        imputation.included,
        rate_prior_shape=rate_prior_shape,
        rate_prior_rate=rate_prior_rate,
        seed=seed + 1,
    )
    return posterior, imputation


def posterior_summary(posterior: dict[str, np.ndarray], *, slope_grid_limit: float = 6.0) -> dict:
    return {
        "integrated_planets_per_star": summarize_draws(posterior["integrated_rate"]),
        "period_slope_alpha": summarize_draws(posterior["alpha"]),
        "radius_slope_beta": summarize_draws(posterior["beta"]),
        "imputed_valid_candidate_count": summarize_draws(
            posterior["imputed_valid_candidate_count"]
        ),
        "shape_weighted_effective_stars": summarize_draws(
            posterior["shape_weighted_effective_stars"]
        ),
        "slope_grid_boundary_fraction": {
            "alpha": float(np.mean(np.abs(posterior["alpha"]) >= slope_grid_limit - 1e-10)),
            "beta": float(np.mean(np.abs(posterior["beta"]) >= slope_grid_limit - 1e-10)),
        },
    }


def full_domain_derived(posterior: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    rate = posterior["integrated_rate"]
    alpha = posterior["alpha"]
    beta = posterior["beta"]
    return {
        "gamma_earth_per_dlnp_dlnr": rate / powerlaw_integral(alpha, beta, FULL_DOMAIN),
        "full_model_projected_hsu_box_rate": rate
        * subdomain_fraction(alpha, beta, FULL_DOMAIN, HSU_DOMAIN),
        "full_model_projected_bryson_earth_box_rate": rate
        * subdomain_fraction(alpha, beta, FULL_DOMAIN, BRYSON_EARTH_DOMAIN),
    }


def quadrature_sensitivity(root: Path, direct_quadrature, direct_exposure, grid) -> dict:
    surface = pd.read_csv(root / "results/population/dr25_selection_surface.csv")
    periods = np.sort(surface["period_days"].unique())
    radii = np.sort(surface["planet_radius_earth"].unique())
    matrix = (
        surface.pivot(index="planet_radius_earth", columns="period_days", values="effective_stars")
        .loc[radii, periods]
        .to_numpy(float)
    )
    interpolator = RegularGridInterpolator(
        (np.log(radii), np.log(periods)),
        np.log(matrix),
        bounds_error=True,
    )

    def interpolate(quadrature) -> np.ndarray:
        points = np.column_stack([np.log(quadrature.radii_earth), np.log(quadrature.periods_days)])
        return np.exp(interpolator(points))

    interpolated_direct = interpolate(direct_quadrature)
    node_relative = (
        interpolated_direct - direct_exposure.effective_stars
    ) / direct_exposure.effective_stars
    fine_quadrature = log_gauss_legendre_quadrature(FULL_DOMAIN, period_nodes=20, radius_nodes=18)
    fine_grid = build_powerlaw_grid(
        fine_quadrature,
        FULL_DOMAIN,
        alpha_values=np.unique(grid.alpha),
        beta_values=np.unique(grid.beta),
    )
    direct_integrated = grid.node_mass @ direct_exposure.effective_stars
    fine_integrated = fine_grid.node_mass @ interpolate(fine_quadrature)
    relative = (fine_integrated - direct_integrated) / direct_integrated
    return {
        "comparison": (
            "direct 14x12 all-target quadrature versus log-linear interpolation of "
            "the released 21x17 all-target surface on a 20x18 quadrature"
        ),
        "direct_node_interpolation_relative_difference": {
            "median": float(np.median(node_relative)),
            "p95_absolute": float(np.quantile(np.abs(node_relative), 0.95)),
            "maximum_absolute": float(np.max(np.abs(node_relative))),
        },
        "shape_weighted_exposure_relative_difference_over_slope_grid": {
            "median": float(np.median(relative)),
            "p95_absolute": float(np.quantile(np.abs(relative), 0.95)),
            "maximum_absolute": float(np.max(np.abs(relative))),
        },
    }


def posterior_predictive_check(
    grid,
    quadrature: LogQuadrature,
    effective_star_draws: np.ndarray,
    posterior: dict[str, np.ndarray],
    imputation: CandidateImputations,
    *,
    seed: int,
) -> dict:
    """Replicate detected counts and log-coordinate means from posterior draws."""
    rng = np.random.default_rng(seed)
    draws = len(posterior["integrated_rate"])
    replicated_count = rng.poisson(
        posterior["integrated_rate"] * posterior["shape_weighted_effective_stars"]
    )
    observed_count = posterior["imputed_valid_candidate_count"]
    observed_u = np.full(draws, np.nan)
    observed_v = np.full(draws, np.nan)
    replicated_u = np.full(draws, np.nan)
    replicated_v = np.full(draws, np.nan)
    node_u = np.log(quadrature.periods_days / grid.domain.period_pivot_days)
    node_v = np.log(quadrature.radii_earth / grid.domain.radius_pivot_earth)
    for draw_index in range(draws):
        included = imputation.included[draw_index]
        if included.any():
            observed_u[draw_index] = np.mean(
                np.log(
                    imputation.periods_days[draw_index, included] / grid.domain.period_pivot_days
                )
            )
            observed_v[draw_index] = np.mean(
                np.log(
                    imputation.radii_earth[draw_index, included] / grid.domain.radius_pivot_earth
                )
            )
        if replicated_count[draw_index] > 0:
            node_probability = (
                grid.node_mass[posterior["grid_index"][draw_index]]
                * effective_star_draws[draw_index]
            )
            node_probability /= node_probability.sum()
            node = rng.choice(
                len(node_probability),
                size=replicated_count[draw_index],
                p=node_probability,
            )
            replicated_u[draw_index] = np.mean(node_u[node])
            replicated_v[draw_index] = np.mean(node_v[node])

    def finite_summary(values) -> dict:
        finite = np.asarray(values, float)
        finite = finite[np.isfinite(finite)]
        return {"finite_draws": len(finite), **summarize_draws(finite)}

    coordinate_mask = np.isfinite(observed_u) & np.isfinite(replicated_u)
    radius_mask = np.isfinite(observed_v) & np.isfinite(replicated_v)
    return {
        "replicated_detected_count": summarize_draws(replicated_count),
        "imputed_observed_valid_count": summarize_draws(observed_count),
        "count_upper_tail_probability": float(np.mean(replicated_count >= observed_count)),
        "replicated_mean_log_period_coordinate": finite_summary(replicated_u),
        "imputed_mean_log_period_coordinate": finite_summary(observed_u),
        "period_mean_upper_tail_probability": float(
            np.mean(replicated_u[coordinate_mask] >= observed_u[coordinate_mask])
        ),
        "replicated_mean_log_radius_coordinate": finite_summary(replicated_v),
        "imputed_mean_log_radius_coordinate": finite_summary(observed_v),
        "radius_mean_upper_tail_probability": float(
            np.mean(replicated_v[radius_mask] >= observed_v[radius_mask])
        ),
        "interpretation": (
            "Posterior-predictive tail probabilities near either zero or one flag "
            "count or first-moment tension; they are diagnostics, not calibrated p-values."
        ),
    }


def plot_posteriors(samples: pd.DataFrame, path: Path) -> None:
    plt.style.use("dark_background")
    plt.rcParams["svg.hashsalt"] = "finding-earth-2-dr25-occurrence"
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
    colors = {"lower": "#54d6e8", "upper": "#ffd166"}
    for scenario, color in colors.items():
        values = samples.loc[
            samples["estimand"].eq("full_fixed_box")
            & samples["unsupported_reliability_scenario"].eq(scenario),
            "integrated_rate",
        ]
        axes[0].hist(
            values, bins=45, density=True, histtype="step", lw=2, color=color, label=scenario
        )
    axes[0].set(
        xlabel="planets per selected star", ylabel="posterior density", title="Full fixed box"
    )
    axes[0].legend(title="2 high-MES KOIs")

    lower = samples.loc[
        samples["estimand"].eq("full_fixed_box")
        & samples["unsupported_reliability_scenario"].eq("lower")
    ]
    axes[1].hexbin(lower["alpha"], lower["beta"], gridsize=28, mincnt=1, cmap="viridis")
    axes[1].axvline(0, color="white", alpha=0.25, lw=1)
    axes[1].axhline(0, color="white", alpha=0.25, lw=1)
    axes[1].set(xlabel="period slope alpha", ylabel="radius slope beta", title="Population shape")

    box_data = [
        samples.loc[samples["estimand"].eq(name), "integrated_rate"].to_numpy(float)
        for name in ("hsu_2019_fixed_box", "bryson_2020_earth_20_percent_box")
    ]
    violin = axes[2].violinplot(box_data, showmedians=True, showextrema=False)
    for body, color in zip(violin["bodies"], ("#8be28b", "#e78cff")):
        body.set_facecolor(color)
        body.set_alpha(0.75)
    axes[2].set_xticks([1, 2], ["Hsu box", "Earth +/-20%"])
    axes[2].set(ylabel="planets per selected star", title="Direct fixed-box fits")
    figure.suptitle("Kepler DR25 occurrence posterior | MODEL-INFERRED", fontsize=14)
    figure.savefig(path.with_suffix(".png"), dpi=220, facecolor="#080b14")
    figure.savefig(path.with_suffix(".svg"), facecolor="#080b14", metadata={"Date": None})
    plt.close(figure)
    normalize_text_lf(path.with_suffix(".svg"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--draws", type=int, default=3000)
    parser.add_argument("--rebuild-exposure", action="store_true")
    args = parser.parse_args()
    if args.draws < 1000:
        raise ValueError("At least 1000 posterior imputations are required")
    root = args.root.resolve()
    output = root / "results/population"
    selection_path = output / "dr25_selection_model.json"
    reliability_path = output / "dr25_smooth_reliability_model.json"
    model = load_selection_model(selection_path)
    reliability_model = load_reliability_model(reliability_path)
    stars, stellar_manifest = fetch_product(root, "stars")
    stellar_selection = StellarSelection()
    selected_stars = stars.loc[stellar_selection.select(stars)].copy()
    if len(selected_stars) != 114_105:
        raise RuntimeError("DR25 selected-star denominator drifted from 114,105")
    contract = exposure_cache_contract(root, selection_path, stellar_manifest)
    exposures = get_exposures(
        root,
        model,
        selected_stars,
        contract,
        rebuild=args.rebuild_exposure,
    )

    candidates = pd.read_csv(output / "dr25_analysis_population.csv")
    if len(candidates) != 89:
        raise RuntimeError("DR25 occurrence candidate population drifted from 89")
    observed_tces, observed_tce_manifest = fetch_product(root, "observed_tces")
    candidates = candidates.merge(
        observed_tces[["TCE_ID", "period", "MES"]].rename(
            columns={"period": "observed_tce_period_days", "MES": "joined_observed_tce_mes"}
        ),
        on="TCE_ID",
        how="left",
        validate="one_to_one",
    )
    if candidates[
        ["observed_tce_period_days", "joined_observed_tce_mes"]
    ].isna().any().any() or not np.allclose(
        candidates["joined_observed_tce_mes"], candidates["observed_tce_mes"]
    ):
        raise RuntimeError("Candidate-to-observed-TCE join is incomplete or inconsistent")
    reliability_draws = draw_candidate_reliability(
        reliability_model, candidates, args.draws, seed=SEED + 10
    )
    if reliability_draws.supported.sum() != 87:
        raise RuntimeError("Smooth reliability support drifted from 87 candidates")
    selection_deltas = draw_selection_deltas(model, args.draws, seed=SEED + 20)
    samples = []
    summaries = {}
    baseline_objects: dict[str, tuple[dict[str, np.ndarray], CandidateImputations]] = {}
    for estimand_index, (estimand, domain) in enumerate(ESTIMANDS.items()):
        quadrature, exposure = exposures[estimand]
        scenarios = ("lower", "upper") if estimand == "full_fixed_box" else ("lower",)
        for scenario in scenarios:
            posterior, imputation = inference_run(
                domain,
                quadrature,
                exposure,
                candidates,
                reliability_draws,
                selection_deltas,
                unsupported_reliability=0.0 if scenario == "lower" else 1.0,
                seed=SEED + 100 + estimand_index * 20,
            )
            key = f"{estimand}__unsupported_{scenario}"
            baseline_objects[key] = (posterior, imputation)
            summaries[key] = posterior_summary(posterior)
            derived = full_domain_derived(posterior) if estimand == "full_fixed_box" else {}
            for draw_index in range(args.draws):
                row = {
                    "draw": draw_index,
                    "estimand": estimand,
                    "unsupported_reliability_scenario": scenario,
                    "integrated_rate": posterior["integrated_rate"][draw_index],
                    "alpha": posterior["alpha"][draw_index],
                    "beta": posterior["beta"][draw_index],
                    "imputed_valid_candidate_count": posterior["imputed_valid_candidate_count"][
                        draw_index
                    ],
                    "shape_weighted_effective_stars": posterior["shape_weighted_effective_stars"][
                        draw_index
                    ],
                    "label": "MODEL-INFERRED",
                }
                row.update({name: values[draw_index] for name, values in derived.items()})
                samples.append(row)
    sample_frame = pd.DataFrame(samples)

    full_quadrature, full_exposure = exposures["full_fixed_box"]
    baseline_lower, lower_imputation = baseline_objects["full_fixed_box__unsupported_lower"]
    sensitivity = {}
    sensitivity_specs: dict[str, dict[str, float | bool | int]] = {
        "selection_point_estimate": {"selection_uncertainty": False},
        "zero_radius_measurement_error": {"radius_error_scale": 0.0},
        "radius_errors_times_1_5": {"radius_error_scale": 1.5},
        "narrow_slope_prior_sigma_1": {"slope_prior_sigma": 1.0},
        "broad_slope_prior_sigma_3": {
            "slope_prior_sigma": 3.0,
            "slope_grid_limit": 9.0,
            "slope_grid_points": 91,
        },
        "gamma_rate_prior_1_1": {"rate_prior_shape": 1.0, "rate_prior_rate": 1.0},
    }
    for index, (name, overrides) in enumerate(sensitivity_specs.items()):
        posterior, _ = inference_run(
            FULL_DOMAIN,
            full_quadrature,
            full_exposure,
            candidates,
            reliability_draws,
            selection_deltas,
            unsupported_reliability=0,
            seed=SEED + 500 + index * 10,
            radius_error_scale=float(overrides.get("radius_error_scale", 1.0)),
            slope_prior_sigma=float(overrides.get("slope_prior_sigma", 2.0)),
            rate_prior_shape=float(overrides.get("rate_prior_shape", 0.5)),
            rate_prior_rate=float(overrides.get("rate_prior_rate", 0.5)),
            selection_uncertainty=bool(overrides.get("selection_uncertainty", True)),
            slope_grid_limit=float(overrides.get("slope_grid_limit", 6.0)),
            slope_grid_points=int(overrides.get("slope_grid_points", 81)),
        )
        sensitivity[name] = posterior_summary(
            posterior,
            slope_grid_limit=float(overrides.get("slope_grid_limit", 6.0)),
        )

    no_false_alarm_total = np.broadcast_to(
        (1 - candidates["fpp_prob"].to_numpy(float))[None, :],
        (args.draws, len(candidates)),
    ).copy()
    no_false_alarm_reliability = ReliabilityDraws(
        false_alarm=np.ones_like(no_false_alarm_total),
        total=no_false_alarm_total,
        supported=np.ones(len(candidates), bool),
    )
    no_reliability, _ = inference_run(
        FULL_DOMAIN,
        full_quadrature,
        full_exposure,
        candidates,
        no_false_alarm_reliability,
        selection_deltas,
        unsupported_reliability=1,
        seed=SEED + 600,
    )
    sensitivity["without_instrumental_false_alarm_correction"] = {
        **posterior_summary(no_reliability),
        "full_fit_derived_densities_and_projected_subdomains": {
            name: summarize_draws(values)
            for name, values in full_domain_derived(no_reliability).items()
        },
    }

    binned = draw_binned_posterior(
        full_quadrature,
        perturb_selection_exposure(full_exposure, selection_deltas),
        lower_imputation.periods_days,
        lower_imputation.radii_earth,
        lower_imputation.included,
        np.geomspace(FULL_DOMAIN.period_min_days, FULL_DOMAIN.period_max_days, 4),
        np.geomspace(FULL_DOMAIN.radius_min_earth, FULL_DOMAIN.radius_max_earth, 4),
        seed=SEED + 700,
    )
    sensitivity["piecewise_constant_3x3_population"] = {
        "integrated_planets_per_star": summarize_draws(binned["integrated_rate"]),
        "imputed_valid_candidate_count": summarize_draws(binned["imputed_valid_candidate_count"]),
    }

    direct_box_sensitivity = {}
    direct_specs: dict[str, dict[str, float | bool | int]] = {
        "selection_point_estimate": {"selection_uncertainty": False},
        "zero_radius_measurement_error": {"radius_error_scale": 0.0},
        "narrow_slope_prior_sigma_1": {"slope_prior_sigma": 1.0},
        "broad_slope_prior_sigma_3": {
            "slope_prior_sigma": 3.0,
            "slope_grid_limit": 9.0,
            "slope_grid_points": 91,
        },
        "gamma_rate_prior_1_1": {"rate_prior_shape": 1.0, "rate_prior_rate": 1.0},
    }
    for estimand in ("hsu_2019_fixed_box", "bryson_2020_earth_20_percent_box"):
        domain = ESTIMANDS[estimand]
        quadrature, exposure = exposures[estimand]
        estimand_sensitivity = {}
        for index, (name, overrides) in enumerate(direct_specs.items()):
            posterior, _ = inference_run(
                domain,
                quadrature,
                exposure,
                candidates,
                reliability_draws,
                selection_deltas,
                unsupported_reliability=0,
                seed=SEED + 800 + index * 10,
                radius_error_scale=float(overrides.get("radius_error_scale", 1.0)),
                slope_prior_sigma=float(overrides.get("slope_prior_sigma", 2.0)),
                rate_prior_shape=float(overrides.get("rate_prior_shape", 0.5)),
                rate_prior_rate=float(overrides.get("rate_prior_rate", 0.5)),
                selection_uncertainty=bool(overrides.get("selection_uncertainty", True)),
                slope_grid_limit=float(overrides.get("slope_grid_limit", 6.0)),
                slope_grid_points=int(overrides.get("slope_grid_points", 81)),
            )
            estimand_sensitivity[name] = posterior_summary(
                posterior,
                slope_grid_limit=float(overrides.get("slope_grid_limit", 6.0)),
            )
        posterior_without_reliability, _ = inference_run(
            domain,
            quadrature,
            exposure,
            candidates,
            no_false_alarm_reliability,
            selection_deltas,
            unsupported_reliability=1,
            seed=SEED + 900,
        )
        estimand_sensitivity["without_instrumental_false_alarm_correction"] = posterior_summary(
            posterior_without_reliability
        )
        baseline_imputation = baseline_objects[f"{estimand}__unsupported_lower"][1]
        binned_direct = draw_binned_posterior(
            quadrature,
            perturb_selection_exposure(exposure, selection_deltas),
            baseline_imputation.periods_days,
            baseline_imputation.radii_earth,
            baseline_imputation.included,
            np.geomspace(domain.period_min_days, domain.period_max_days, 3),
            np.geomspace(domain.radius_min_earth, domain.radius_max_earth, 3),
            seed=SEED + 910,
        )
        estimand_sensitivity["piecewise_constant_2x2_population"] = {
            "integrated_planets_per_star": summarize_draws(binned_direct["integrated_rate"]),
            "imputed_valid_candidate_count": summarize_draws(
                binned_direct["imputed_valid_candidate_count"]
            ),
        }
        direct_box_sensitivity[estimand] = estimand_sensitivity

    baseline_grid = build_powerlaw_grid(
        full_quadrature,
        FULL_DOMAIN,
        alpha_values=np.linspace(-6, 6, 81),
        beta_values=np.linspace(-6, 6, 81),
    )
    quadrature_check = quadrature_sensitivity(root, full_quadrature, full_exposure, baseline_grid)
    posterior_predictive = {}
    for index, estimand in enumerate(ESTIMANDS):
        domain = ESTIMANDS[estimand]
        quadrature, exposure = exposures[estimand]
        grid = build_powerlaw_grid(
            quadrature,
            domain,
            alpha_values=np.linspace(-6, 6, 81),
            beta_values=np.linspace(-6, 6, 81),
        )
        posterior, imputation = baseline_objects[f"{estimand}__unsupported_lower"]
        posterior_predictive[estimand] = posterior_predictive_check(
            grid,
            quadrature,
            perturb_selection_exposure(exposure, selection_deltas),
            posterior,
            imputation,
            seed=SEED + 1000 + index,
        )
    derived_summaries = {
        scenario: {
            name: summarize_draws(values) for name, values in full_domain_derived(posterior).items()
        }
        for scenario, posterior in {
            "unsupported_lower": baseline_objects["full_fixed_box__unsupported_lower"][0],
            "unsupported_upper": baseline_objects["full_fixed_box__unsupported_upper"][0],
        }.items()
    }
    unsupported = candidates.loc[
        ~reliability_draws.supported,
        ["kepoi_name", "observed_tce_mes", "fpp_prob", "koi_period", "koi_prad"],
    ].to_dict("records")

    result_path = output / "dr25_occurrence_posterior.json"
    samples_path = output / "dr25_occurrence_posterior_samples.csv"
    comparison_path = output / "dr25_occurrence_published_comparison.json"
    plot_base = output / "dr25_occurrence_posterior"
    write_csv(samples_path, sample_frame)
    plot_posteriors(sample_frame, plot_base)
    summary = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "release_status": "conditional_fixed_box_occurrence_not_habitability_or_life",
        "stellar_population": {
            "selected_stars": len(selected_stars),
            "selection": asdict(stellar_selection),
        },
        "candidate_population": {
            "eligible_koi_count": len(candidates),
            "smooth_reliability_supported": int(reliability_draws.supported.sum()),
            "unsupported_high_mes_candidates": unsupported,
            "unsupported_policy": (
                "Full-box posterior is bracketed by false-alarm reliability 0 and 1 "
                "for the two high-MES KOIs; external astrophysical FPP remains applied."
            ),
        },
        "likelihood": {
            "point_process": "inhomogeneous Poisson in d ln P d ln R",
            "population_density": (
                "F exp(alpha ln(P/365.25d) + beta ln(R/1Rearth)) / Z(alpha,beta)"
            ),
            "baseline_priors": {
                "F": "Gamma(shape=0.5, rate=0.5)",
                "alpha": "Normal(0, 2), evaluated on [-6,6]",
                "beta": "Normal(0, 2), evaluated on [-6,6]",
            },
            "posterior_imputations": args.draws,
            "interpretation": (
                "Two-stage posterior conditional on validated selection and reliability "
                "model families; shared coefficient draws retain candidate correlations."
            ),
        },
        "estimands": {
            name: {
                "domain": asdict(domain),
                "meaning": "planets per selected star integrated over this fixed box",
            }
            for name, domain in ESTIMANDS.items()
        },
        "baseline_posteriors": summaries,
        "full_fit_derived_densities_and_projected_subdomains": derived_summaries,
        "posterior_predictive_checks": posterior_predictive,
        "sensitivity_by_estimand": {
            "full_fixed_box": sensitivity,
            **direct_box_sensitivity,
        },
        "quadrature_and_surface_resolution_sensitivity": quadrature_check,
        "evidence_boundaries": [
            "No result is a probability of habitability or life.",
            "The fixed boxes are not a star-dependent habitable zone.",
            "Gamma_Earth is a differential density at the Earth pivot, not an integrated eta Earth.",
            "The 3x3 piecewise-constant result is a model-family sensitivity, not model averaging.",
        ],
        "source_hashes": {
            "selection_model": sha256(selection_path),
            "reliability_model": sha256(reliability_path),
            "analysis_population": sha256(output / "dr25_analysis_population.csv"),
            "observed_tce_source": observed_tce_manifest["sha256"],
            "occurrence_exposure": sha256(output / "dr25_occurrence_exposure.csv"),
            "hierarchical_validation": sha256(output / "validation/hierarchical_recovery.json"),
            "occurrence_source": sha256(root / "src/earth2/population/occurrence.py"),
            "hierarchical_source": sha256(root / "src/earth2/population/hierarchical.py"),
            "builder_source": sha256(Path(__file__)),
        },
    }
    write_json(result_path, summary)
    registry = json.loads(
        (output / "published_occurrence_comparisons.json").read_text(encoding="utf-8")
    )
    comparison = {
        "schema_version": "1.0",
        "label": "MODEL-INFERRED",
        "comparison_rule": (
            "Direct numerical comparison only for fixed boxes and compatible stellar "
            "contracts; no pooled estimate and no comparison to star-dependent HZ eta Earth."
        ),
        "project": {
            "full_model_projected_subdomains": derived_summaries["unsupported_lower"],
            "direct_box_diagnostics": {
                "hsu_2019_fixed_box": summaries["hsu_2019_fixed_box__unsupported_lower"][
                    "integrated_planets_per_star"
                ],
                "bryson_2020_earth_20_percent_box": summaries[
                    "bryson_2020_earth_20_percent_box__unsupported_lower"
                ]["integrated_planets_per_star"],
            },
            "interpretation": (
                "The full-model projections borrow shape information from the complete "
                "50-500 day, 0.5-2 Earth-radius domain. Direct box fits use only about "
                "four and one-and-a-half imputed valid candidates and are strongly prior "
                "and population-family sensitive; both views are retained."
            ),
        },
        "published_registry": registry,
    }
    write_json(comparison_path, comparison)
    artifacts = [
        result_path,
        samples_path,
        comparison_path,
        output / "dr25_occurrence_exposure.csv",
        output / "dr25_occurrence_exposure.json",
        plot_base.with_suffix(".png"),
        plot_base.with_suffix(".svg"),
    ]
    manifest = {
        "schema_version": "1.0",
        "product": "Kepler DR25 conditional fixed-box occurrence posterior",
        "files": {
            path.relative_to(root).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in artifacts
        },
    }
    write_json(output / "dr25_occurrence_products.json", manifest)
    print(
        "Occurrence inference complete. Review the fixed-box posterior and sensitivity "
        "products before treating this as a released astronomical result.",
        flush=True,
    )


if __name__ == "__main__":
    main()
