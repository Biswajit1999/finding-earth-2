"""Tests for uncertainty propagation into the occurrence likelihood."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from earth2.population.hierarchical import (
    draw_candidate_imputations,
    draw_candidate_reliability,
    draw_selection_deltas,
    evaluate_selection_exposure,
    load_reliability_model,
    load_selection_model,
    perturb_selection_exposure,
)
from earth2.population.occurrence import OccurrenceDomain, log_gauss_legendre_quadrature

ROOT = Path(__file__).resolve().parents[1]


def star_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "kepid": [1, 2, 3],
            "mass": [1.0, 0.9, 1.1],
            "radius": [1.0, 0.85, 1.15],
            "logg": [4.44, 4.55, 4.35],
            "teff": [5772.0, 5300.0, 6100.0],
            "dataspan": [1470.0, 1400.0, 1450.0],
            "dutycycle": [0.92, 0.88, 0.95],
            "rrmscdpp06p0": [40.0, 70.0, 55.0],
            "cdppslplong": [-0.48, -0.5, -0.46],
            "cdppslpshrt": [-0.52, -0.49, -0.5],
        }
    )


def candidate_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observed_tce_period_days": [300.0, 300.0],
            "observed_tce_mes": [10.0, 31.0],
            "koi_period": [300.0, 300.0],
            "koi_period_err1": [0.01, 0.01],
            "koi_period_err2": [-0.01, -0.01],
            "koi_prad": [1.0, 1.0],
            "koi_prad_err1": [0.1, 0.1],
            "koi_prad_err2": [-0.1, -0.1],
            "fpp_prob": [0.25, 0.25],
        }
    )


def test_released_models_load_with_exact_parameter_schemas():
    selection = load_selection_model(ROOT / "results/population/dr25_selection_model.json")
    reliability = load_reliability_model(
        ROOT / "results/population/dr25_smooth_reliability_model.json"
    )
    assert selection.mes_calibration.coefficients.shape == (11,)
    assert selection.pipeline_including_window.coefficients.shape == (5,)
    assert reliability.theta.shape == (15,)
    assert reliability.covariance is not None
    assert reliability.covariance.shape == (15, 15)


def test_selection_gradient_matches_a_pipeline_intercept_finite_difference():
    model = load_selection_model(ROOT / "results/population/dr25_selection_model.json")
    domain = OccurrenceDomain()
    quadrature = log_gauss_legendre_quadrature(domain, period_nodes=3, radius_nodes=3)
    baseline = evaluate_selection_exposure(model, star_fixture(), quadrature, domain, chunk_size=2)
    epsilon = 1e-5
    shifted_pipeline = replace(
        model.pipeline_including_window,
        coefficients=model.pipeline_including_window.coefficients + np.array([epsilon, 0, 0, 0, 0]),
    )
    shifted = evaluate_selection_exposure(
        replace(model, pipeline_including_window=shifted_pipeline),
        star_fixture(),
        quadrature,
        domain,
        chunk_size=2,
    )
    numerical = (shifted.effective_stars - baseline.effective_stars) / epsilon
    analytic = baseline.gradient[:, 11]
    assert np.allclose(numerical, analytic, rtol=2e-4, atol=1e-9)
    assert baseline.fixed_at_boundary[14]


def test_selection_draws_respect_bounds_and_positive_exposure():
    model = load_selection_model(ROOT / "results/population/dr25_selection_model.json")
    domain = OccurrenceDomain()
    quadrature = log_gauss_legendre_quadrature(domain, period_nodes=3, radius_nodes=3)
    exposure = evaluate_selection_exposure(model, star_fixture(), quadrature, domain)
    deltas = draw_selection_deltas(model, 100, seed=9)
    pipeline_offset = 11
    vetting_offset = 16
    assert np.all(
        model.pipeline_including_window.coefficients[1] + deltas[:, pipeline_offset + 1] >= 0
    )
    assert np.all(deltas[:, pipeline_offset + 3] == 0)
    assert np.all(
        model.vetting_given_recovered.coefficients[1] + deltas[:, vetting_offset + 1] >= 0
    )
    perturbed = perturb_selection_exposure(exposure, deltas)
    assert perturbed.shape == (100, 9)
    assert np.all(np.isfinite(perturbed) & (perturbed > 0))


def test_reliability_draws_remain_correlated_and_withhold_outside_domain():
    fit = load_reliability_model(ROOT / "results/population/dr25_smooth_reliability_model.json")
    candidates = candidate_fixture()
    result = draw_candidate_reliability(fit, candidates, 1200, seed=10)
    assert result.supported.tolist() == [True, False]
    assert np.all((result.total[:, 0] > 0) & (result.total[:, 0] < 0.75))
    assert np.isnan(result.total[:, 1]).all()

    lower = draw_candidate_imputations(
        candidates,
        result,
        OccurrenceDomain(),
        unsupported_false_alarm_reliability=0,
        seed=11,
    )
    upper = draw_candidate_imputations(
        candidates,
        result,
        OccurrenceDomain(),
        unsupported_false_alarm_reliability=1,
        seed=11,
    )
    assert not lower.included[:, 1].any()
    assert upper.included[:, 1].mean() == pytest.approx(0.75, abs=0.04)
    assert np.all(lower.periods_days > 0)
    assert np.all(lower.radii_earth > 0)
