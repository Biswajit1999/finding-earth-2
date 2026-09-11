"""Transparent inhomogeneous-Poisson occurrence inference in log period-radius space.

The intrinsic population is a normalized separable power law per
``d ln(period) d ln(radius)``.  The integrated rate therefore has an explicit
meaning, while the survey selection enters only through the Poisson exposure.
This module contains no Kepler-specific candidate or reliability policy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import gammaln, logsumexp


@dataclass(frozen=True)
class OccurrenceDomain:
    """Closed period-radius domain for one integrated occurrence estimand."""

    period_min_days: float = 50.0
    period_max_days: float = 500.0
    radius_min_earth: float = 0.5
    radius_max_earth: float = 2.0
    period_pivot_days: float = 365.25
    radius_pivot_earth: float = 1.0

    def validate(self) -> None:
        values = np.asarray(
            [
                self.period_min_days,
                self.period_max_days,
                self.radius_min_earth,
                self.radius_max_earth,
                self.period_pivot_days,
                self.radius_pivot_earth,
            ],
            float,
        )
        if (
            not np.isfinite(values).all()
            or np.any(values <= 0)
            or self.period_min_days >= self.period_max_days
            or self.radius_min_earth >= self.radius_max_earth
        ):
            raise ValueError("Occurrence domain must have finite positive ordered bounds")

    def mask(self, periods, radii) -> np.ndarray:
        self.validate()
        period, radius = np.broadcast_arrays(np.asarray(periods, float), np.asarray(radii, float))
        return (
            np.isfinite(period)
            & np.isfinite(radius)
            & (period >= self.period_min_days)
            & (period <= self.period_max_days)
            & (radius >= self.radius_min_earth)
            & (radius <= self.radius_max_earth)
        )


@dataclass(frozen=True)
class LogQuadrature:
    """Tensor-product quadrature nodes and weights in natural-log coordinates."""

    periods_days: np.ndarray
    radii_earth: np.ndarray
    weights: np.ndarray
    period_nodes: int
    radius_nodes: int

    def validate(self, domain: OccurrenceDomain) -> None:
        size = self.period_nodes * self.radius_nodes
        if (
            self.periods_days.shape != (size,)
            or self.radii_earth.shape != (size,)
            or self.weights.shape != (size,)
            or not np.isfinite(self.periods_days).all()
            or not np.isfinite(self.radii_earth).all()
            or not np.isfinite(self.weights).all()
            or np.any(self.weights <= 0)
            or not domain.mask(self.periods_days, self.radii_earth).all()
        ):
            raise ValueError("Log quadrature is malformed or outside its occurrence domain")


@dataclass(frozen=True)
class PowerLawGrid:
    """Cached slope grid and normalized population weights at quadrature nodes."""

    alpha: np.ndarray
    beta: np.ndarray
    node_mass: np.ndarray
    log_prior_shape: np.ndarray
    domain: OccurrenceDomain

    @property
    def size(self) -> int:
        return len(self.alpha)


@dataclass(frozen=True)
class PosteriorGrid:
    """Normalized posterior over slopes with conditional Gamma rate parameters."""

    alpha: np.ndarray
    beta: np.ndarray
    probability: np.ndarray
    exposure: np.ndarray
    rate_shape: float
    rate_prior_rate: float
    detected_count: int

    def draw(self, draws: int, *, seed: int = 20260911) -> dict[str, np.ndarray]:
        if draws <= 0:
            raise ValueError("Posterior draw count must be positive")
        rng = np.random.default_rng(seed)
        index = rng.choice(len(self.probability), size=draws, p=self.probability)
        rate = rng.gamma(
            self.rate_shape,
            1 / (self.rate_prior_rate + self.exposure[index]),
        )
        return {
            "integrated_rate": rate,
            "alpha": self.alpha[index],
            "beta": self.beta[index],
            "grid_index": index,
        }


def _log_coordinate_integral(
    slope: np.ndarray | float, lower: float, upper: float, pivot: float
) -> np.ndarray:
    """Integrate ``(x/pivot)**slope`` with respect to ``d ln x``."""
    slope_array = np.asarray(slope, float)
    if not np.isfinite(slope_array).all() or lower <= 0 or upper <= lower or pivot <= 0:
        raise ValueError("Power-law integral inputs are invalid")
    log_lower = np.log(lower / pivot)
    log_upper = np.log(upper / pivot)
    near_zero = np.abs(slope_array) < 1e-8
    safe_slope = np.where(near_zero, 1.0, slope_array)
    general = (
        np.exp(np.clip(safe_slope * log_upper, -700, 700))
        - np.exp(np.clip(safe_slope * log_lower, -700, 700))
    ) / safe_slope
    return np.where(near_zero, log_upper - log_lower, general)


def powerlaw_integral(
    alpha: np.ndarray | float,
    beta: np.ndarray | float,
    domain: OccurrenceDomain,
) -> np.ndarray:
    """Integral of the unnormalized population density over a domain."""
    domain.validate()
    alpha_array, beta_array = np.broadcast_arrays(np.asarray(alpha, float), np.asarray(beta, float))
    period = _log_coordinate_integral(
        alpha_array,
        domain.period_min_days,
        domain.period_max_days,
        domain.period_pivot_days,
    )
    radius = _log_coordinate_integral(
        beta_array,
        domain.radius_min_earth,
        domain.radius_max_earth,
        domain.radius_pivot_earth,
    )
    result = period * radius
    if not np.isfinite(result).all() or np.any(result <= 0):
        raise ValueError("Power-law normalization is non-finite or non-positive")
    return result


def subdomain_fraction(
    alpha,
    beta,
    full_domain: OccurrenceDomain,
    subdomain: OccurrenceDomain,
) -> np.ndarray:
    """Fraction of a normalized power law inside a nested period-radius box."""
    if (
        subdomain.period_min_days < full_domain.period_min_days
        or subdomain.period_max_days > full_domain.period_max_days
        or subdomain.radius_min_earth < full_domain.radius_min_earth
        or subdomain.radius_max_earth > full_domain.radius_max_earth
    ):
        raise ValueError("Occurrence subdomain must be nested inside the fitted domain")
    return powerlaw_integral(alpha, beta, subdomain) / powerlaw_integral(alpha, beta, full_domain)


def log_gauss_legendre_quadrature(
    domain: OccurrenceDomain,
    *,
    period_nodes: int = 14,
    radius_nodes: int = 12,
) -> LogQuadrature:
    """Construct a tensor-product Gauss-Legendre rule in log coordinates."""
    domain.validate()
    if period_nodes < 2 or radius_nodes < 2:
        raise ValueError("At least two quadrature nodes are required per axis")

    def axis(lower: float, upper: float, nodes: int) -> tuple[np.ndarray, np.ndarray]:
        coordinate, weight = np.polynomial.legendre.leggauss(nodes)
        log_lower, log_upper = np.log(lower), np.log(upper)
        mapped = (coordinate + 1) * (log_upper - log_lower) / 2 + log_lower
        return np.exp(mapped), weight * (log_upper - log_lower) / 2

    periods, period_weights = axis(domain.period_min_days, domain.period_max_days, period_nodes)
    radii, radius_weights = axis(domain.radius_min_earth, domain.radius_max_earth, radius_nodes)
    radius_grid, period_grid = np.meshgrid(radii, periods, indexing="ij")
    radius_weight_grid, period_weight_grid = np.meshgrid(
        radius_weights, period_weights, indexing="ij"
    )
    result = LogQuadrature(
        periods_days=period_grid.ravel(),
        radii_earth=radius_grid.ravel(),
        weights=(period_weight_grid * radius_weight_grid).ravel(),
        period_nodes=period_nodes,
        radius_nodes=radius_nodes,
    )
    result.validate(domain)
    return result


def build_powerlaw_grid(
    quadrature: LogQuadrature,
    domain: OccurrenceDomain,
    *,
    alpha_values=None,
    beta_values=None,
    slope_prior_sigma: float = 2.0,
) -> PowerLawGrid:
    """Cache normalized quadrature mass for a rectangular slope grid."""
    quadrature.validate(domain)
    if not np.isfinite(slope_prior_sigma) or slope_prior_sigma <= 0:
        raise ValueError("Slope prior scale must be finite and positive")
    if alpha_values is None:
        alpha_values = np.linspace(-4, 4, 81)
    if beta_values is None:
        beta_values = np.linspace(-4, 4, 81)
    alpha_axis = np.asarray(alpha_values, float)
    beta_axis = np.asarray(beta_values, float)
    if (
        alpha_axis.ndim != 1
        or beta_axis.ndim != 1
        or len(alpha_axis) < 3
        or len(beta_axis) < 3
        or not np.isfinite(alpha_axis).all()
        or not np.isfinite(beta_axis).all()
        or np.any(np.diff(alpha_axis) <= 0)
        or np.any(np.diff(beta_axis) <= 0)
    ):
        raise ValueError("Slope axes must be finite, increasing one-dimensional grids")
    alpha_grid, beta_grid = np.meshgrid(alpha_axis, beta_axis, indexing="ij")
    alpha = alpha_grid.ravel()
    beta = beta_grid.ravel()
    u = np.log(quadrature.periods_days / domain.period_pivot_days)
    v = np.log(quadrature.radii_earth / domain.radius_pivot_earth)
    normalization = powerlaw_integral(alpha, beta, domain)
    node_mass = np.exp(alpha[:, None] * u + beta[:, None] * v)
    node_mass *= quadrature.weights[None, :] / normalization[:, None]
    numerical_mass = node_mass.sum(axis=1)
    if not np.allclose(numerical_mass, 1, rtol=2e-10, atol=2e-12):
        raise ValueError("Log quadrature does not resolve the declared power-law slope grid")
    log_prior = -0.5 * ((alpha / slope_prior_sigma) ** 2 + (beta / slope_prior_sigma) ** 2)
    return PowerLawGrid(alpha, beta, node_mass, log_prior, domain)


def infer_posterior_grid(
    grid: PowerLawGrid,
    effective_stars,
    detected_periods,
    detected_radii,
    *,
    rate_prior_shape: float = 0.5,
    rate_prior_rate: float = 0.5,
) -> PosteriorGrid:
    """Evaluate the normalized slope posterior and conditional Gamma rate law."""
    exposure_nodes = np.asarray(effective_stars, float)
    if (
        exposure_nodes.shape != (grid.node_mass.shape[1],)
        or not np.isfinite(exposure_nodes).all()
        or np.any(exposure_nodes < 0)
        or not np.any(exposure_nodes > 0)
    ):
        raise ValueError("Effective-star exposure must be finite, non-negative and nonzero")
    period, radius = np.broadcast_arrays(
        np.asarray(detected_periods, float), np.asarray(detected_radii, float)
    )
    if period.ndim != 1 or not grid.domain.mask(period, radius).all():
        raise ValueError("Every included detection must be inside the fitted occurrence domain")
    if (
        not np.isfinite(rate_prior_shape)
        or not np.isfinite(rate_prior_rate)
        or rate_prior_shape <= 0
        or rate_prior_rate <= 0
    ):
        raise ValueError("Gamma rate prior parameters must be finite and positive")
    count = len(period)
    sum_u = float(np.log(period / grid.domain.period_pivot_days).sum())
    sum_v = float(np.log(radius / grid.domain.radius_pivot_earth).sum())
    normalization = powerlaw_integral(grid.alpha, grid.beta, grid.domain)
    exposure = grid.node_mass @ exposure_nodes
    posterior_shape = rate_prior_shape + count
    log_probability = (
        grid.log_prior_shape
        + grid.alpha * sum_u
        + grid.beta * sum_v
        - count * np.log(normalization)
        + gammaln(posterior_shape)
        - posterior_shape * np.log(rate_prior_rate + exposure)
    )
    log_probability -= logsumexp(log_probability)
    probability = np.exp(log_probability)
    return PosteriorGrid(
        alpha=grid.alpha,
        beta=grid.beta,
        probability=probability,
        exposure=exposure,
        rate_shape=posterior_shape,
        rate_prior_rate=rate_prior_rate,
        detected_count=count,
    )


def draw_imputed_posterior(
    grid: PowerLawGrid,
    effective_star_draws,
    candidate_period_draws,
    candidate_radius_draws,
    included_draws,
    *,
    rate_prior_shape: float = 0.5,
    rate_prior_rate: float = 0.5,
    seed: int = 57721,
    batch_size: int = 128,
) -> dict[str, np.ndarray]:
    """Draw one conditional posterior sample for each external-data imputation.

    Rows of ``included_draws`` select the latent valid candidates.  Selection,
    reliability and measurement draws therefore remain correlated within an
    imputation while this function evaluates the exact power-law grid posterior.
    A single exposure row is broadcast when selection uncertainty is disabled.
    """
    period = np.asarray(candidate_period_draws, float)
    radius = np.asarray(candidate_radius_draws, float)
    included = np.asarray(included_draws, bool)
    exposure = np.asarray(effective_star_draws, float)
    if (
        period.ndim != 2
        or radius.shape != period.shape
        or included.shape != period.shape
        or not np.isfinite(period).all()
        or not np.isfinite(radius).all()
        or np.any(period <= 0)
        or np.any(radius <= 0)
    ):
        raise ValueError("Candidate imputation arrays must be aligned, finite and positive")
    draws = period.shape[0]
    if exposure.ndim == 1:
        exposure = exposure[None, :]
    if (
        exposure.ndim != 2
        or exposure.shape[1] != grid.node_mass.shape[1]
        or exposure.shape[0] not in (1, draws)
        or not np.isfinite(exposure).all()
        or np.any(exposure < 0)
        or not np.all(np.any(exposure > 0, axis=1))
        or not np.isfinite(rate_prior_shape)
        or not np.isfinite(rate_prior_rate)
        or rate_prior_shape <= 0
        or rate_prior_rate <= 0
        or batch_size <= 0
    ):
        raise ValueError("Imputed exposure or Gamma prior contract is invalid")
    if np.any(included & ~grid.domain.mask(period, radius)):
        raise ValueError("An included imputed candidate lies outside the occurrence domain")
    count = included.sum(axis=1).astype(int)
    sum_u = np.where(included, np.log(period / grid.domain.period_pivot_days), 0).sum(axis=1)
    sum_v = np.where(included, np.log(radius / grid.domain.radius_pivot_earth), 0).sum(axis=1)
    normalization = powerlaw_integral(grid.alpha, grid.beta, grid.domain)
    rng = np.random.default_rng(seed)
    output_rate = np.empty(draws)
    output_alpha = np.empty(draws)
    output_beta = np.empty(draws)
    output_index = np.empty(draws, dtype=int)
    output_exposure = np.empty(draws)
    constant_exposure = exposure.shape[0] == 1
    shared_grid_exposure = grid.node_mass @ exposure[0] if constant_exposure else None
    for start in range(0, draws, batch_size):
        stop = min(start + batch_size, draws)
        if shared_grid_exposure is None:
            grid_exposure = exposure[start:stop] @ grid.node_mass.T
        else:
            grid_exposure = np.broadcast_to(shared_grid_exposure, (stop - start, grid.size))
        posterior_shape = rate_prior_shape + count[start:stop]
        log_probability = (
            grid.log_prior_shape[None, :]
            + sum_u[start:stop, None] * grid.alpha[None, :]
            + sum_v[start:stop, None] * grid.beta[None, :]
            - count[start:stop, None] * np.log(normalization)[None, :]
            + gammaln(posterior_shape)[:, None]
            - posterior_shape[:, None] * np.log(rate_prior_rate + grid_exposure)
        )
        log_probability -= logsumexp(log_probability, axis=1)[:, None]
        probability = np.exp(log_probability)
        cumulative = np.cumsum(probability, axis=1)
        index = (cumulative < rng.random(stop - start)[:, None]).sum(axis=1)
        index = np.minimum(index, grid.size - 1)
        row = np.arange(stop - start)
        selected_exposure = grid_exposure[row, index]
        output_rate[start:stop] = rng.gamma(
            posterior_shape, 1 / (rate_prior_rate + selected_exposure)
        )
        output_alpha[start:stop] = grid.alpha[index]
        output_beta[start:stop] = grid.beta[index]
        output_index[start:stop] = index
        output_exposure[start:stop] = selected_exposure
    return {
        "integrated_rate": output_rate,
        "alpha": output_alpha,
        "beta": output_beta,
        "grid_index": output_index,
        "shape_weighted_effective_stars": output_exposure,
        "imputed_valid_candidate_count": count,
    }


def draw_binned_posterior(
    quadrature: LogQuadrature,
    effective_star_draws,
    candidate_period_draws,
    candidate_radius_draws,
    included_draws,
    period_edges,
    radius_edges,
    *,
    total_rate_prior_shape: float = 0.5,
    rate_prior_rate: float = 0.5,
    seed: int = 141421,
) -> dict[str, np.ndarray]:
    """Fit an alternative piecewise-constant density on fixed log-space bins.

    Each bin has a proper Gamma prior with shape ``total_rate_prior_shape / n``.
    Because all bins share ``rate_prior_rate``, their prior sum matches the
    baseline total-rate Gamma prior before selection is applied.
    """
    period = np.asarray(candidate_period_draws, float)
    radius = np.asarray(candidate_radius_draws, float)
    included = np.asarray(included_draws, bool)
    exposure = np.asarray(effective_star_draws, float)
    period_bounds = np.asarray(period_edges, float)
    radius_bounds = np.asarray(radius_edges, float)
    if exposure.ndim == 1:
        exposure = exposure[None, :]
    if (
        period.ndim != 2
        or radius.shape != period.shape
        or included.shape != period.shape
        or exposure.ndim != 2
        or exposure.shape[1] != len(quadrature.weights)
        or exposure.shape[0] not in (1, len(period))
        or period_bounds.ndim != 1
        or radius_bounds.ndim != 1
        or len(period_bounds) < 2
        or len(radius_bounds) < 2
        or np.any(np.diff(period_bounds) <= 0)
        or np.any(np.diff(radius_bounds) <= 0)
        or not np.isfinite(exposure).all()
        or np.any(exposure < 0)
        or total_rate_prior_shape <= 0
        or rate_prior_rate <= 0
    ):
        raise ValueError("Binned occurrence inputs are malformed")
    domain = OccurrenceDomain(
        period_min_days=float(period_bounds[0]),
        period_max_days=float(period_bounds[-1]),
        radius_min_earth=float(radius_bounds[0]),
        radius_max_earth=float(radius_bounds[-1]),
    )
    quadrature.validate(domain)
    if np.any(included & ~domain.mask(period, radius)):
        raise ValueError("An included candidate lies outside the binned occurrence domain")
    draws = len(period)
    if exposure.shape[0] == 1:
        exposure = np.broadcast_to(exposure, (draws, exposure.shape[1]))
    period_bin = np.searchsorted(period_bounds, period, side="right") - 1
    radius_bin = np.searchsorted(radius_bounds, radius, side="right") - 1
    period_bin = np.minimum(period_bin, len(period_bounds) - 2)
    radius_bin = np.minimum(radius_bin, len(radius_bounds) - 2)
    node_period_bin = np.searchsorted(period_bounds, quadrature.periods_days, side="right") - 1
    node_radius_bin = np.searchsorted(radius_bounds, quadrature.radii_earth, side="right") - 1
    n_period = len(period_bounds) - 1
    n_radius = len(radius_bounds) - 1
    bins = n_period * n_radius
    bin_rate = np.empty((draws, bins))
    bin_count = np.empty((draws, bins), dtype=int)
    rng = np.random.default_rng(seed)
    prior_shape = total_rate_prior_shape / bins
    for radius_index in range(n_radius):
        for period_index in range(n_period):
            flat_index = radius_index * n_period + period_index
            candidate_mask = included & (period_bin == period_index) & (radius_bin == radius_index)
            count = candidate_mask.sum(axis=1)
            node_mask = (node_period_bin == period_index) & (node_radius_bin == radius_index)
            represented_log_area = quadrature.weights[node_mask].sum()
            if not np.isfinite(represented_log_area) or represented_log_area <= 0:
                raise ValueError("Every occurrence bin must contain quadrature support")
            bin_exposure = (
                exposure[:, node_mask] @ quadrature.weights[node_mask]
            ) / represented_log_area
            bin_count[:, flat_index] = count
            bin_rate[:, flat_index] = rng.gamma(
                prior_shape + count,
                1 / (rate_prior_rate + bin_exposure),
            )
    return {
        "integrated_rate": bin_rate.sum(axis=1),
        "bin_rate": bin_rate,
        "bin_count": bin_count,
        "imputed_valid_candidate_count": included.sum(axis=1),
        "period_edges": period_bounds,
        "radius_edges": radius_bounds,
    }


def summarize_draws(values) -> dict[str, float]:
    """Return finite posterior quantiles using one consistent schema."""
    array = np.asarray(values, float)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError("Posterior summary requires a non-empty finite vector")
    quantiles = np.quantile(array, [0.025, 0.16, 0.5, 0.84, 0.975])
    return {
        "p025": float(quantiles[0]),
        "p16": float(quantiles[1]),
        "p50": float(quantiles[2]),
        "p84": float(quantiles[3]),
        "p975": float(quantiles[4]),
        "mean": float(np.mean(array)),
    }
