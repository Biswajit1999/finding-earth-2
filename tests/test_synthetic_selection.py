import numpy as np
import pytest

from earth2.population.synthetic_validation import (
    SyntheticSurvey,
    mean_selection,
    poisson_rate_posterior,
    proposal_mean_selection,
    run_validation,
    selection_factors,
)


def test_selection_factors_are_bounded_and_multiply_once():
    survey = SyntheticSurvey()
    factors = selection_factors([10, 100, 400], [1, 1, 1], survey)
    expected = factors["geometry"] * factors["window"] * factors["pipeline"] * factors["vetting"]
    np.testing.assert_allclose(factors["total"], expected)
    assert np.all(np.diff(factors["geometry"]) < 0)
    assert np.all((factors["total"] >= 0) & (factors["total"] <= 1))


def test_quadrature_selection_changes_with_injection_proposal():
    survey = SyntheticSurvey()
    assert 0 < mean_selection(survey) < 1
    flat = proposal_mean_selection(survey, 0, 0)
    skewed = proposal_mean_selection(survey, 1.2, -2)
    assert abs(skewed / flat - 1) > 0.1


def test_poisson_posterior_is_finite_at_zero_and_rejects_bad_exposure():
    posterior = poisson_rate_posterior(0, 100)
    assert posterior["lower"] > 0
    assert posterior["upper"] > posterior["mean"] > 0
    for detected, exposure in [(-1, 1), (1.5, 1), (1, 0), (1, np.inf)]:
        with pytest.raises(ValueError):
            poisson_rate_posterior(detected, exposure)


def test_seeded_end_to_end_recovery_and_coverage():
    first = run_validation(replicates=120, seed=8)
    second = run_validation(replicates=120, seed=8)
    assert first == second
    assert first["passed"]
    assert abs(first["selection_aware_relative_bias"]) < 0.03
    assert first["geometry_omitted_posterior_mean_average"] < 0.07
    assert 0.88 <= first["empirical_interval_coverage"] <= 1.0


def test_invalid_survey_and_too_few_replicates_fail_closed():
    with pytest.raises(ValueError):
        mean_selection(SyntheticSurvey(duty_cycle=1.1))
    with pytest.raises(ValueError, match="At least"):
        run_validation(replicates=49)
