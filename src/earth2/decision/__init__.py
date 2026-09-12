"""Bayesian decision tools for action-specific observation planning."""

from earth2.decision.information_gain import (
    bernoulli_test_information_gain,
    gaussian_expected_information_gain,
    gaussian_posterior_sigma,
)

__all__ = [
    "bernoulli_test_information_gain",
    "gaussian_expected_information_gain",
    "gaussian_posterior_sigma",
]
