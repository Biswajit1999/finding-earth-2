"""Named, deliberately limited models for bulk-composition evidence.

The functions in this module distinguish three questions:

* Rogers (2015) supplies a population-level radius-only baseline.
* Zeng, Sasselov & Jacobsen (2016) tests consistency with a two-layer
  iron/silicate family when an independent mass and radius are available.
* Otegi, Bouchy & Helled (2020) compares empirical rocky and volatile-rich
  population relations under an explicit equal-prior scenario.

These are model-conditional probabilities, not probabilities of habitability
and not precise interior inversions. A radius-predicted catalogue mass is never
accepted as independent composition evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CompositionConfig:
    """Sampling and model-support contract for one planet."""

    draws: int = 4000
    seed: int = 20260912
    min_supported_fraction: float = 0.5
    otegi_scatter_dex: float = 0.20

    def __post_init__(self) -> None:
        if self.draws < 100:
            raise ValueError("draws must be at least 100")
        if not 0 < self.min_supported_fraction <= 1:
            raise ValueError("min_supported_fraction must lie in (0, 1]")
        if self.otegi_scatter_dex <= 0:
            raise ValueError("otegi_scatter_dex must be positive")


def rogers_rocky_probability(radius_earth: np.ndarray | float) -> np.ndarray:
    """Return the retained v1 radius-only Rogers heuristic.

    Rogers (2015) found that most 1.6-Earth-radius planets in a short-period
    Kepler/RV sample are not dense enough for iron and silicate alone. The
    project's smooth 0.20-Earth-radius transition remains a diagnostic rather
    than a universal calibrated composition posterior.
    """

    radius = np.asarray(radius_earth, dtype=float)
    with np.errstate(over="ignore", invalid="ignore"):
        probability = 1 / (1 + np.exp((radius - 1.6) / 0.20))
    return np.where((radius > 0) & np.isfinite(radius), probability, np.nan)


def zeng_rocky_radius(
    mass_earth: np.ndarray | float,
    core_mass_fraction: float,
) -> np.ndarray:
    """Radius of the Zeng et al. (2016) two-layer rocky approximation.

    ``R/R_earth = (1.07 - 0.21 CMF) (M/M_earth) ** (1/3.7)`` is published for
    1--8 Earth masses and core-mass fractions from zero to 0.4. Values outside
    that domain are returned as NaN rather than extrapolated.
    """

    if not 0 <= core_mass_fraction <= 0.4:
        raise ValueError("core_mass_fraction must lie in [0, 0.4]")
    mass = np.asarray(mass_earth, dtype=float)
    valid = np.isfinite(mass) & (mass >= 1) & (mass <= 8)
    radius = (1.07 - 0.21 * core_mass_fraction) * mass ** (1 / 3.7)
    return np.where(valid, radius, np.nan)


def otegi_mass(
    radius_earth: np.ndarray | float,
    population: str,
) -> np.ndarray:
    """Otegi et al. (2020) empirical mass-radius relation.

    The rocky relation is ``M=0.9 R^3.45`` and the volatile-rich relation is
    ``M=1.74 R^1.58`` in Earth units. Population overlap is expected; these
    curves are competing empirical descriptions, not deterministic classes.
    """

    parameters = {
        "rocky": (0.90, 3.45),
        "volatile_rich": (1.74, 1.58),
    }
    if population not in parameters:
        raise ValueError("population must be 'rocky' or 'volatile_rich'")
    coefficient, exponent = parameters[population]
    radius = np.asarray(radius_earth, dtype=float)
    mass = coefficient * radius**exponent
    return np.where((radius > 0) & np.isfinite(radius), mass, np.nan)


def _split_normal_draws(
    centre: float,
    minus: float | None,
    plus: float | None,
    standard_normal: np.ndarray,
) -> np.ndarray:
    if not np.isfinite(centre) or centre <= 0:
        return np.full_like(standard_normal, np.nan, dtype=float)
    lower = abs(float(minus)) if minus is not None and np.isfinite(minus) else 0.0
    upper = abs(float(plus)) if plus is not None and np.isfinite(plus) else 0.0
    return centre + np.where(standard_normal < 0, standard_normal * lower, standard_normal * upper)


def _otegi_rocky_probability(
    mass: np.ndarray,
    radius: np.ndarray,
    scatter_dex: float,
) -> np.ndarray:
    """Equal-prior rocky/volatile probability with a declared model floor."""

    relation = {
        "rocky": (0.90, 0.06, 3.45, 0.12),
        "volatile_rich": (1.74, 0.38, 1.58, 0.10),
    }
    likelihoods = []
    log_radius = np.log(radius)
    for coefficient, coefficient_error, exponent, exponent_error in relation.values():
        predicted = np.log(coefficient) + exponent * log_radius
        sigma = np.sqrt(
            (coefficient_error / coefficient) ** 2
            + (exponent_error * log_radius) ** 2
            + (scatter_dex * np.log(10)) ** 2
        )
        residual = (np.log(mass) - predicted) / sigma
        likelihoods.append(np.exp(-0.5 * residual**2) / sigma)
    rocky, volatile = likelihoods
    return rocky / (rocky + volatile)


def infer_bulk_composition(
    *,
    radius_earth: float,
    radius_error_minus: float | None = None,
    radius_error_plus: float | None = None,
    mass_earth: float | None = None,
    mass_error_minus: float | None = None,
    mass_error_plus: float | None = None,
    independent_mass: bool = False,
    mass_radius_correlation: float | None = None,
    config: CompositionConfig | None = None,
) -> dict[str, float | int | str | bool | None]:
    """Infer model-conditional bulk-composition evidence for one planet.

    Correlated standard-normal variates propagate a supplied mass-radius
    correlation coefficient. When covariance is unavailable, zero correlation
    is an explicit assumption in the returned record.
    """

    cfg = config or CompositionConfig()
    if mass_radius_correlation is not None and not -1 <= mass_radius_correlation <= 1:
        raise ValueError("mass_radius_correlation must lie in [-1, 1]")
    rho = float(mass_radius_correlation or 0.0)
    rng = np.random.default_rng(cfg.seed)
    z_mass = rng.normal(size=cfg.draws)
    z_radius_independent = rng.normal(size=cfg.draws)
    z_radius = rho * z_mass + np.sqrt(1 - rho**2) * z_radius_independent
    radius = _split_normal_draws(
        radius_earth,
        radius_error_minus,
        radius_error_plus,
        z_radius,
    )
    positive_radius = np.isfinite(radius) & (radius > 0)
    radius = np.where(positive_radius, radius, np.nan)
    rogers_draws = rogers_rocky_probability(radius)
    p_rogers = float(np.nanmean(rogers_draws)) if np.isfinite(rogers_draws).any() else np.nan

    wolfgang_location = float(2.7 * radius_earth**1.3) if radius_earth > 0 else np.nan
    result: dict[str, float | int | str | bool | None] = {
        "label": "MODEL-INFERRED",
        "independent_mass_used": bool(independent_mass),
        "covariance_status": (
            "reported_correlation_propagated"
            if mass_radius_correlation is not None
            else "unavailable_assumed_zero"
        ),
        "mass_radius_correlation": mass_radius_correlation,
        "p_rocky_rogers_radius_only": p_rogers,
        "wolfgang_mass_location_earth": wolfgang_location,
        "wolfgang_intrinsic_scatter_earth": 1.9,
        "wolfgang_prediction_is_dynamical_mass": False,
        "zeng_supported_draw_fraction": 0.0,
        "p_rocky_zeng_fe_si_envelope": None,
        "p_requires_volatiles_zeng": None,
        "p_consistent_with_terrestrial_composition_zeng": None,
        "p_too_dense_for_zeng_cmf_0_to_0p4": None,
        "otegi_supported_draw_fraction": 0.0,
        "p_rocky_otegi_equal_prior": None,
        "p_rocky_otegi_scatter_0p10dex": None,
        "p_rocky_otegi_scatter_0p30dex": None,
        "p_rocky_model_min": p_rogers,
        "p_rocky_model_max": p_rogers,
        "p_rocky_model_range": None,
        "n_rocky_models_supported": 1,
    }
    if not independent_mass or mass_earth is None or not np.isfinite(mass_earth):
        result["composition_evidence_scope"] = "radius_only_baseline"
        return result

    mass = _split_normal_draws(
        mass_earth,
        mass_error_minus,
        mass_error_plus,
        z_mass,
    )
    mass = np.where(np.isfinite(mass) & (mass > 0), mass, np.nan)

    zeng_upper = zeng_rocky_radius(mass, 0.0)
    zeng_lower = zeng_rocky_radius(mass, 0.4)
    zeng_support = np.isfinite(radius) & np.isfinite(zeng_upper) & np.isfinite(zeng_lower)
    zeng_fraction = float(np.mean(zeng_support))
    result["zeng_supported_draw_fraction"] = zeng_fraction
    rocky_values: list[float] = [p_rogers]
    if zeng_fraction >= cfg.min_supported_fraction:
        supported_radius = radius[zeng_support]
        supported_upper = zeng_upper[zeng_support]
        supported_lower = zeng_lower[zeng_support]
        p_requires = float(np.mean(supported_radius > supported_upper))
        p_terrestrial = float(
            np.mean((supported_radius >= supported_lower) & (supported_radius <= supported_upper))
        )
        p_dense = float(np.mean(supported_radius < supported_lower))
        p_rocky_zeng = float(np.mean(supported_radius <= supported_upper))
        result.update(
            {
                "p_rocky_zeng_fe_si_envelope": p_rocky_zeng,
                "p_requires_volatiles_zeng": p_requires,
                "p_consistent_with_terrestrial_composition_zeng": p_terrestrial,
                "p_too_dense_for_zeng_cmf_0_to_0p4": p_dense,
            }
        )
        rocky_values.append(p_rocky_zeng)

    otegi_support = (
        np.isfinite(mass)
        & np.isfinite(radius)
        & (mass <= 25)
        & (radius >= 0.8)
        & (radius <= 4)
    )
    otegi_fraction = float(np.mean(otegi_support))
    result["otegi_supported_draw_fraction"] = otegi_fraction
    if otegi_fraction >= cfg.min_supported_fraction:
        probabilities = {
            "p_rocky_otegi_scatter_0p10dex": 0.10,
            "p_rocky_otegi_equal_prior": cfg.otegi_scatter_dex,
            "p_rocky_otegi_scatter_0p30dex": 0.30,
        }
        otegi_nominal = np.nan
        for key, scatter in probabilities.items():
            value = float(
                np.mean(
                    _otegi_rocky_probability(
                        mass[otegi_support],
                        radius[otegi_support],
                        scatter,
                    )
                )
            )
            result[key] = value
            if key == "p_rocky_otegi_equal_prior":
                otegi_nominal = value
        rocky_values.append(float(otegi_nominal))

    finite_rocky = np.asarray([value for value in rocky_values if np.isfinite(value)])
    result.update(
        {
            "composition_evidence_scope": "independent_mass_and_radius",
            "p_rocky_model_min": float(finite_rocky.min()),
            "p_rocky_model_max": float(finite_rocky.max()),
            "p_rocky_model_range": (
                float(finite_rocky.max() - finite_rocky.min())
                if len(finite_rocky) >= 2
                else None
            ),
            "n_rocky_models_supported": int(len(finite_rocky)),
        }
    )
    return result
