"""Deterministic synthetic tests of selection-aware occurrence normalisation.

This module creates no astronomical measurement. It verifies that the survey
likelihood recovers a known injected rate when its selection function is known.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit
from scipy.stats import gamma, poisson

from earth2.population.completeness import detection_probability


@dataclass(frozen=True)
class SyntheticSurvey:
    stars: int = 10_000
    occurrence_per_star: float = 0.7
    period_min_days: float = 10.0
    period_max_days: float = 400.0
    radius_min_earth: float = 0.7
    radius_max_earth: float = 2.0
    period_power: float = 0.3
    radius_power: float = -0.8
    dataspan_days: float = 1460.0
    duty_cycle: float = 0.9

    def validate(self) -> None:
        values = np.array(list(self.__dict__.values()), dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Synthetic survey parameters must be finite")
        if (
            self.stars <= 0
            or int(self.stars) != self.stars
            or self.occurrence_per_star <= 0
            or not 0 < self.period_min_days < self.period_max_days
            or not 0 < self.radius_min_earth < self.radius_max_earth
            or self.dataspan_days <= 0
            or not 0 < self.duty_cycle <= 1
        ):
            raise ValueError("Invalid synthetic survey domain")


def _sample_log_powerlaw(
    rng: np.random.Generator, size: int, lower: float, upper: float, power: float
) -> np.ndarray:
    """Sample dN/dln(x) proportional to x**power over finite bounds."""
    u = rng.random(size)
    if abs(power) < 1e-12:
        return np.exp(np.log(lower) + u * np.log(upper / lower))
    lo, hi = lower**power, upper**power
    return (lo + u * (hi - lo)) ** (1 / power)


def selection_factors(period_days, radius_earth, survey: SyntheticSurvey) -> dict[str, np.ndarray]:
    """Known scenario selection used only for synthetic falsification tests."""
    survey.validate()
    period, radius = np.broadcast_arrays(
        np.asarray(period_days, float), np.asarray(radius_earth, float)
    )
    if (
        not np.isfinite(period).all()
        or not np.isfinite(radius).all()
        or np.any(period <= 0)
        or np.any(radius <= 0)
    ):
        raise ValueError("Synthetic periods and radii must be finite and positive")
    # Circular Sun-like transit geometry; the cap only protects calls outside
    # this test's declared domain.
    geometry = np.clip(0.00465047 * (period / 365.256) ** (-2 / 3), 0, 1)
    expected_opportunities = survey.dataspan_days * survey.duty_cycle / period
    window = poisson.sf(2, expected_opportunities)
    mes = 10.0 * radius**2 * (period / 100.0) ** (-1 / 3)
    pipeline = expit((mes - 7.1) / 1.2)
    vetting = 0.98 * expit((mes - 6.0) / 1.5)
    total = detection_probability(geometry, pipeline, vetting, window=window)
    return {
        "geometry": geometry,
        "window": window,
        "pipeline": pipeline,
        "vetting": vetting,
        "total": total,
        "mes": mes,
    }


def _quadrature_nodes(lower: float, upper: float, power: float, order: int = 80):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    lo, hi = np.log(lower), np.log(upper)
    logx = (nodes + 1) * (hi - lo) / 2 + lo
    raw_weights = weights * (hi - lo) / 2 * np.exp(power * logx)
    return np.exp(logx), raw_weights / raw_weights.sum()


def mean_selection(survey: SyntheticSurvey, *, include_geometry: bool = True) -> float:
    """Integrate selection under the declared intrinsic shape by quadrature."""
    survey.validate()
    period, wp = _quadrature_nodes(
        survey.period_min_days, survey.period_max_days, survey.period_power
    )
    radius, wr = _quadrature_nodes(
        survey.radius_min_earth, survey.radius_max_earth, survey.radius_power
    )
    factors = selection_factors(period[None, :], radius[:, None], survey)
    probability = factors["total"]
    if not include_geometry:
        probability = probability / factors["geometry"]
    return float(np.sum(probability * wr[:, None] * wp[None, :]))


def simulate_detected_count(survey: SyntheticSurvey, rng: np.random.Generator) -> tuple[int, int]:
    survey.validate()
    planets = int(rng.poisson(survey.stars * survey.occurrence_per_star))
    period = _sample_log_powerlaw(
        rng, planets, survey.period_min_days, survey.period_max_days, survey.period_power
    )
    radius = _sample_log_powerlaw(
        rng, planets, survey.radius_min_earth, survey.radius_max_earth, survey.radius_power
    )
    probability = selection_factors(period, radius, survey)["total"]
    return planets, int(np.count_nonzero(rng.random(planets) < probability))


def poisson_rate_posterior(detected: int, exposure: float, credible_mass: float = 0.95) -> dict:
    """Jeffreys-prior posterior for a Poisson rate with known exposure."""
    if detected < 0 or int(detected) != detected or not np.isfinite(exposure) or exposure <= 0:
        raise ValueError("Detected count and exposure must be valid")
    if not 0 < credible_mass < 1:
        raise ValueError("credible_mass must be between zero and one")
    shape = detected + 0.5
    tail = (1 - credible_mass) / 2
    return {
        "mean": shape / exposure,
        "lower": gamma.ppf(tail, shape, scale=1 / exposure),
        "upper": gamma.ppf(1 - tail, shape, scale=1 / exposure),
        "shape": shape,
        "rate": exposure,
        "prior": "Jeffreys p(rate) proportional to rate^-1/2",
    }


def proposal_mean_selection(
    survey: SyntheticSurvey, period_power: float, radius_power: float
) -> float:
    proposal = SyntheticSurvey(
        **{**survey.__dict__, "period_power": period_power, "radius_power": radius_power}
    )
    return mean_selection(proposal)


def run_validation(
    survey: SyntheticSurvey = SyntheticSurvey(), *, replicates: int = 300, seed: int = 726381
) -> dict:
    """Run deterministic recovery and coverage tests against known truth."""
    if replicates < 50:
        raise ValueError("At least 50 replicates are required for a coverage diagnostic")
    rng = np.random.default_rng(seed)
    selection = mean_selection(survey)
    exposure = survey.stars * selection
    wrong_exposure = survey.stars * mean_selection(survey, include_geometry=False)
    estimates, wrong_geometry, raw, covered, detected_counts = [], [], [], [], []
    for _ in range(replicates):
        _, detected = simulate_detected_count(survey, rng)
        posterior = poisson_rate_posterior(detected, exposure)
        estimates.append(posterior["mean"])
        wrong_geometry.append(poisson_rate_posterior(detected, wrong_exposure)["mean"])
        raw.append(detected / survey.stars)
        covered.append(posterior["lower"] <= survey.occurrence_per_star <= posterior["upper"])
        detected_counts.append(detected)
    estimate_array = np.asarray(estimates)
    proposal_flat = proposal_mean_selection(survey, 0.0, 0.0)
    proposal_skewed = proposal_mean_selection(survey, 1.2, -2.0)
    return {
        "label": "SIMULATED",
        "seed": seed,
        "replicates": replicates,
        "truth_occurrence_per_star": survey.occurrence_per_star,
        "stars_per_replicate": survey.stars,
        "known_mean_selection": selection,
        "known_exposure_per_replicate": exposure,
        "mean_detected_count": float(np.mean(detected_counts)),
        "selection_aware_posterior_mean_average": float(estimate_array.mean()),
        "selection_aware_relative_bias": float(
            estimate_array.mean() / survey.occurrence_per_star - 1
        ),
        "selection_aware_rmse": float(
            np.sqrt(np.mean((estimate_array - survey.occurrence_per_star) ** 2))
        ),
        "nominal_interval_mass": 0.95,
        "empirical_interval_coverage": float(np.mean(covered)),
        "raw_detected_per_star_average": float(np.mean(raw)),
        "geometry_omitted_posterior_mean_average": float(np.mean(wrong_geometry)),
        "flat_log_proposal_mean_selection": proposal_flat,
        "skewed_proposal_mean_selection": proposal_skewed,
        "proposal_mean_relative_difference": proposal_skewed / proposal_flat - 1,
        "interpretation": "Controlled falsification test; no astronomical occurrence measurement",
        "passed": bool(
            abs(estimate_array.mean() / survey.occurrence_per_star - 1) < 0.03
            and 0.90 <= np.mean(covered) <= 0.99
            and np.mean(wrong_geometry) < survey.occurrence_per_star * 0.1
            and abs(proposal_skewed / proposal_flat - 1) > 0.1
        ),
    }
