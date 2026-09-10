"""Expanded synthetic recovery for the hierarchical occurrence likelihood."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.special import expit

from earth2.population.occurrence import (
    OccurrenceDomain,
    build_powerlaw_grid,
    draw_imputed_posterior,
    log_gauss_legendre_quadrature,
    summarize_draws,
)


@dataclass(frozen=True)
class SyntheticScenario:
    name: str
    integrated_rate: float
    alpha: float = 0.0
    beta: float = 0.0
    density_family: str = "power_law"
    completeness_scale: float = 1.0
    candidate_reliability: float = 1.0
    radius_log_sigma: float = 0.0
    selection_log_sigma: float = 0.0
    fitted_exposure_scale: float = 1.0
    domain: OccurrenceDomain = OccurrenceDomain()
    expected_result: str = "recover"


def validation_scenarios() -> tuple[SyntheticScenario, ...]:
    earth_box = OccurrenceDomain(
        period_min_days=292.2,
        period_max_days=438.3,
        radius_min_earth=0.8,
        radius_max_earth=1.2,
    )
    return (
        SyntheticScenario("flat_population", 0.7),
        SyntheticScenario("power_law_population", 0.7, alpha=0.7, beta=-0.9),
        SyntheticScenario(
            "broken_radius_population",
            0.7,
            alpha=0.4,
            density_family="broken",
            expected_result="must_flag_model_misspecification",
        ),
        SyntheticScenario("earth_box_population", 0.04, domain=earth_box),
        SyntheticScenario("low_completeness", 0.7, completeness_scale=0.10),
        SyntheticScenario("finite_injection_uncertainty", 0.7, selection_log_sigma=0.12),
        SyntheticScenario("reliability_perturbation", 0.7, candidate_reliability=0.65),
        SyntheticScenario("stellar_radius_uncertainty", 0.7, radius_log_sigma=0.18),
        SyntheticScenario(
            "wrong_completeness_negative_control",
            0.7,
            fitted_exposure_scale=0.5,
            expected_result="must_fail_recovery",
        ),
    )


def _effective_stars(periods, radii, *, selected_stars: int = 114_105) -> np.ndarray:
    period = np.asarray(periods, float)
    radius = np.asarray(radii, float)
    geometry = 0.00465047 * (period / 365.25) ** (-2 / 3)
    pipeline = expit(-0.2 + 5 * np.log(radius))
    vetting = 0.85 - 0.08 * np.clip(np.log(period / 50) / np.log(10), 0, 1)
    return selected_stars * geometry * pipeline * vetting


def _truth_node_mass(scenario, quadrature, grid) -> np.ndarray:
    if scenario.density_family == "power_law":
        distance = (grid.alpha - scenario.alpha) ** 2 + (grid.beta - scenario.beta) ** 2
        return grid.node_mass[np.argmin(distance)]
    if scenario.density_family != "broken":
        raise ValueError("Unknown synthetic population family")
    u = np.log(quadrature.periods_days / scenario.domain.period_pivot_days)
    v = np.log(quadrature.radii_earth / scenario.domain.radius_pivot_earth)
    radius_term = np.where(v < 0, 1.5 * v, -1.5 * v)
    mass = np.exp(scenario.alpha * u + radius_term) * quadrature.weights
    return mass / mass.sum()


def _one_replicate(
    scenario: SyntheticScenario,
    *,
    seed: int,
    posterior_draws: int,
) -> dict[str, float | bool | int]:
    rng = np.random.default_rng(seed)
    quadrature = log_gauss_legendre_quadrature(scenario.domain, period_nodes=12, radius_nodes=10)
    grid = build_powerlaw_grid(
        quadrature,
        scenario.domain,
        alpha_values=np.linspace(-3, 3, 41),
        beta_values=np.linspace(-3, 3, 41),
    )
    exposure_truth = scenario.completeness_scale * _effective_stars(
        quadrature.periods_days, quadrature.radii_earth
    )
    truth_mass = _truth_node_mass(scenario, quadrature, grid)
    expected_planets = scenario.integrated_rate * float(truth_mass @ exposure_truth)
    expected_candidates = expected_planets / scenario.candidate_reliability
    candidate_count = int(rng.poisson(expected_candidates))
    detected_probability = truth_mass * exposure_truth
    detected_probability /= detected_probability.sum()
    node_index = rng.choice(len(detected_probability), size=candidate_count, p=detected_probability)
    period_centre = quadrature.periods_days[node_index]
    radius_centre = quadrature.radii_earth[node_index]
    periods = np.broadcast_to(period_centre, (posterior_draws, candidate_count)).copy()
    radii = np.broadcast_to(radius_centre, (posterior_draws, candidate_count)).copy()
    if scenario.radius_log_sigma:
        radii *= np.exp(rng.normal(0, scenario.radius_log_sigma, radii.shape))
    included = rng.random((posterior_draws, candidate_count)) < scenario.candidate_reliability
    included &= scenario.domain.mask(periods, radii)
    fitted_exposure = scenario.fitted_exposure_scale * exposure_truth
    if scenario.selection_log_sigma:
        u = np.log(quadrature.periods_days / scenario.domain.period_pivot_days)
        v = np.log(quadrature.radii_earth / scenario.domain.radius_pivot_earth)
        coefficient_draws = rng.normal(0, scenario.selection_log_sigma, (posterior_draws, 3))
        log_change = (
            coefficient_draws[:, :1]
            + coefficient_draws[:, 1:2] * u[None, :]
            + coefficient_draws[:, 2:3] * v[None, :]
        )
        fitted_exposure = fitted_exposure[None, :] * np.exp(log_change)
    posterior = draw_imputed_posterior(
        grid,
        fitted_exposure,
        periods,
        radii,
        included,
        seed=seed + 1,
    )
    interval = np.quantile(posterior["integrated_rate"], [0.025, 0.975])
    alpha_interval = np.quantile(posterior["alpha"], [0.025, 0.975])
    beta_interval = np.quantile(posterior["beta"], [0.025, 0.975])
    return {
        "candidate_count": candidate_count,
        "mean_imputed_planets": float(posterior["imputed_valid_candidate_count"].mean()),
        "rate_mean": float(posterior["integrated_rate"].mean()),
        "rate_median": float(np.median(posterior["integrated_rate"])),
        "rate_p025": float(interval[0]),
        "rate_p975": float(interval[1]),
        "rate_covered": bool(interval[0] <= scenario.integrated_rate <= interval[1]),
        "alpha_mean": float(posterior["alpha"].mean()),
        "alpha_covered": bool(alpha_interval[0] <= scenario.alpha <= alpha_interval[1]),
        "beta_mean": float(posterior["beta"].mean()),
        "beta_covered": bool(beta_interval[0] <= scenario.beta <= beta_interval[1]),
    }


def run_hierarchical_recovery(
    *,
    seed: int = 20260911,
    replicates: int = 60,
    posterior_draws: int = 256,
) -> dict:
    """Run required recovery, stress and deliberately wrong-completeness cases."""
    if replicates < 20 or posterior_draws < 128:
        raise ValueError("Hierarchical recovery requires >=20 replicates and >=128 draws")
    output = []
    seed_sequence = np.random.SeedSequence(seed)
    scenario_seeds = seed_sequence.spawn(len(validation_scenarios()))
    for scenario, scenario_seed in zip(validation_scenarios(), scenario_seeds):
        replicate_seeds = scenario_seed.generate_state(replicates)
        rows = [
            _one_replicate(
                scenario,
                seed=int(replicate_seed),
                posterior_draws=posterior_draws,
            )
            for replicate_seed in replicate_seeds
        ]
        rate_means = np.asarray([row["rate_mean"] for row in rows], float)
        rate_bias = float(rate_means.mean() - scenario.integrated_rate)
        relative_bias = rate_bias / scenario.integrated_rate
        coverage = float(np.mean([row["rate_covered"] for row in rows]))
        recovery_tolerance = (
            0.35 if scenario.name in {"earth_box_population", "low_completeness"} else 0.20
        )
        if scenario.expected_result == "recover":
            passed = abs(relative_bias) <= recovery_tolerance and 0.80 <= coverage <= 1.0
        elif scenario.expected_result == "must_flag_model_misspecification":
            passed = abs(relative_bias) >= 0.15 or coverage < 0.80
        else:
            passed = abs(relative_bias) >= 0.45
        threshold: dict[str, object]
        if scenario.expected_result == "recover":
            threshold = {
                "absolute_relative_bias_at_most": recovery_tolerance,
                "coverage_at_least": 0.80,
            }
        elif scenario.expected_result == "must_flag_model_misspecification":
            threshold = {"absolute_relative_bias_at_least_or_coverage_below": [0.15, 0.80]}
        else:
            threshold = {"absolute_relative_bias_at_least": 0.45}
        result = {
            "scenario": scenario.name,
            "label": "SIMULATED",
            "generating_density": scenario.density_family,
            "expected_result": scenario.expected_result,
            "truth": {
                "integrated_rate": scenario.integrated_rate,
                "alpha": scenario.alpha,
                "beta": scenario.beta,
            },
            "perturbations": {
                "completeness_scale": scenario.completeness_scale,
                "candidate_reliability": scenario.candidate_reliability,
                "radius_log_sigma": scenario.radius_log_sigma,
                "selection_log_sigma": scenario.selection_log_sigma,
                "fitted_exposure_scale": scenario.fitted_exposure_scale,
            },
            "replicates": replicates,
            "posterior_draws_per_replicate": posterior_draws,
            "mean_candidate_count": float(np.mean([row["candidate_count"] for row in rows])),
            "mean_imputed_planet_count": float(
                np.mean([row["mean_imputed_planets"] for row in rows])
            ),
            "rate": {
                "mean_posterior_mean": float(rate_means.mean()),
                "bias": rate_bias,
                "relative_bias": relative_bias,
                "rmse": float(np.sqrt(np.mean((rate_means - scenario.integrated_rate) ** 2))),
                "nominal_95_interval_coverage": coverage,
            },
            "threshold": threshold,
            "passed": bool(passed),
        }
        if scenario.density_family == "power_law":
            result["shape"] = {
                "mean_alpha": float(np.mean([row["alpha_mean"] for row in rows])),
                "mean_beta": float(np.mean([row["beta_mean"] for row in rows])),
                "alpha_95_interval_coverage": float(
                    np.mean([row["alpha_covered"] for row in rows])
                ),
                "beta_95_interval_coverage": float(np.mean([row["beta_covered"] for row in rows])),
            }
        output.append(result)
    passed = all(result["passed"] for result in output)
    return {
        "schema_version": "1.0",
        "label": "SIMULATED",
        "seed": seed,
        "method": (
            "Inhomogeneous Poisson point process in dlnP dlnR with a normalized "
            "separable power law, proper Gamma rate prior, Gaussian slope priors, "
            "and multiple imputation of selection, reliability and radius uncertainty"
        ),
        "scenarios": output,
        "release_gate": (
            "Every intended-recovery scenario must meet its bias and coverage threshold; "
            "the broken-family stress must expose model-family sensitivity, and the "
            "deliberately halved completeness surface must produce a large bias."
        ),
        "passed": bool(passed),
    }


def quick_validation(seed: int = 20260911) -> dict:
    """Small deterministic contract used by unit tests."""
    scenario = replace(validation_scenarios()[0], integrated_rate=0.7)
    rows = [_one_replicate(scenario, seed=seed + index, posterior_draws=128) for index in range(3)]
    return {
        "label": "SIMULATED",
        "finite": bool(
            all(
                np.isfinite(row["rate_mean"]) and row["rate_p025"] < row["rate_p975"]
                for row in rows
            )
        ),
        "rows": rows,
        "posterior_rate_summary": summarize_draws([float(row["rate_mean"]) for row in rows]),
    }
