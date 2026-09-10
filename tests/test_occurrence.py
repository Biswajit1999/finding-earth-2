"""Tests for the normalized log-period/log-radius Poisson likelihood."""

from __future__ import annotations

import numpy as np
import pytest

from earth2.population.occurrence import (
    OccurrenceDomain,
    build_powerlaw_grid,
    draw_imputed_posterior,
    infer_posterior_grid,
    log_gauss_legendre_quadrature,
    powerlaw_integral,
    subdomain_fraction,
)


def test_flat_powerlaw_integral_is_log_area_and_quadrature_normalizes():
    domain = OccurrenceDomain()
    expected = np.log(500 / 50) * np.log(2 / 0.5)
    assert powerlaw_integral(0, 0, domain) == pytest.approx(expected)
    quadrature = log_gauss_legendre_quadrature(domain, period_nodes=8, radius_nodes=7)
    grid = build_powerlaw_grid(
        quadrature,
        domain,
        alpha_values=[-2, 0, 2],
        beta_values=[-2, 0, 2],
    )
    assert np.allclose(grid.node_mass.sum(axis=1), 1)


def test_subdomain_fraction_is_bounded_and_flat_case_is_area_ratio():
    full = OccurrenceDomain()
    sub = OccurrenceDomain(
        period_min_days=237,
        period_max_days=500,
        radius_min_earth=0.75,
        radius_max_earth=1.5,
    )
    fraction = subdomain_fraction(0, 0, full, sub)
    expected = np.log(500 / 237) * np.log(1.5 / 0.75) / (np.log(500 / 50) * np.log(2 / 0.5))
    assert fraction == pytest.approx(expected)
    slopes = subdomain_fraction(np.array([-2, 0, 2]), 0.5, full, sub)
    assert np.all((slopes > 0) & (slopes < 1))


def test_grid_posterior_recovers_a_high_information_powerlaw_sample():
    rng = np.random.default_rng(42)
    domain = OccurrenceDomain()
    quadrature = log_gauss_legendre_quadrature(domain, period_nodes=16, radius_nodes=14)
    alpha_axis = np.linspace(-2, 2, 41)
    beta_axis = np.linspace(-2, 2, 41)
    grid = build_powerlaw_grid(
        quadrature,
        domain,
        alpha_values=alpha_axis,
        beta_values=beta_axis,
    )
    truth_index = np.flatnonzero(np.isclose(grid.alpha, 0.6) & np.isclose(grid.beta, -0.8))[0]
    probability = grid.node_mass[truth_index]
    node_index = rng.choice(len(probability), size=1200, p=probability)
    posterior = infer_posterior_grid(
        grid,
        np.full(len(probability), 1000.0),
        quadrature.periods_days[node_index],
        quadrature.radii_earth[node_index],
    )
    alpha_mean = float(posterior.probability @ posterior.alpha)
    beta_mean = float(posterior.probability @ posterior.beta)
    assert alpha_mean == pytest.approx(0.6, abs=0.15)
    assert beta_mean == pytest.approx(-0.8, abs=0.15)
    draws = posterior.draw(3000, seed=1)
    assert np.median(draws["integrated_rate"]) == pytest.approx(1.2, rel=0.08)


def test_occurrence_contract_rejects_outside_detections_and_bad_exposure():
    domain = OccurrenceDomain()
    quadrature = log_gauss_legendre_quadrature(domain, period_nodes=10, radius_nodes=10)
    grid = build_powerlaw_grid(
        quadrature,
        domain,
        alpha_values=[-1, 0, 1],
        beta_values=[-1, 0, 1],
    )
    with pytest.raises(ValueError, match="exposure"):
        infer_posterior_grid(grid, np.zeros(100), [100], [1])
    with pytest.raises(ValueError, match="inside"):
        infer_posterior_grid(grid, np.ones(100), [10], [1])
    with pytest.raises(ValueError, match="nested"):
        subdomain_fraction(
            0,
            0,
            domain,
            OccurrenceDomain(period_min_days=10, period_max_days=100),
        )


def test_vectorized_imputations_preserve_counts_and_broadcast_exposure():
    domain = OccurrenceDomain()
    quadrature = log_gauss_legendre_quadrature(domain, period_nodes=10, radius_nodes=10)
    grid = build_powerlaw_grid(
        quadrature,
        domain,
        alpha_values=np.linspace(-1, 1, 11),
        beta_values=np.linspace(-1, 1, 11),
    )
    period = np.array([[100.0, 300.0], [100.0, 300.0], [100.0, 300.0]])
    radius = np.ones_like(period)
    included = np.array([[True, True], [True, False], [False, False]])
    result = draw_imputed_posterior(
        grid,
        np.full(100, 100.0),
        period,
        radius,
        included,
        seed=4,
    )
    assert result["imputed_valid_candidate_count"].tolist() == [2, 1, 0]
    assert np.all(result["integrated_rate"] > 0)
    assert result["grid_index"].shape == (3,)
