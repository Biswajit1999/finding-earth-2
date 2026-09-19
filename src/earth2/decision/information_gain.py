"""Tractable expected-information-gain calculations.

All functions require an explicit prior and observation likelihood. They return
mutual information in nats and make no statement about observing cost or
instrument feasibility.
"""

from __future__ import annotations

import numpy as np


def _positive_finite(value: np.ndarray | float, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(array)) or np.any(array <= 0):
        raise ValueError(f"{name} must be finite and positive")
    return array


def gaussian_posterior_sigma(
    prior_sigma: np.ndarray | float,
    observation_sigma: np.ndarray | float,
) -> np.ndarray:
    """Posterior sigma for y = theta + Gaussian noise and a Gaussian prior."""

    prior = _positive_finite(prior_sigma, "prior_sigma")
    noise = _positive_finite(observation_sigma, "observation_sigma")
    return np.sqrt(1.0 / (1.0 / prior**2 + 1.0 / noise**2))


def gaussian_expected_information_gain(
    prior_sigma: np.ndarray | float,
    observation_sigma: np.ndarray | float,
) -> np.ndarray:
    """Exact expected KL divergence for a scalar linear-Gaussian observation.

    The result is in nats. It equals 0.5 log(1 + prior_variance/noise_variance)
    and is independent of the as-yet unobserved outcome in this conjugate case.
    """

    prior = _positive_finite(prior_sigma, "prior_sigma")
    noise = _positive_finite(observation_sigma, "observation_sigma")
    return 0.5 * np.log1p((prior / noise) ** 2)


def correlated_gaussian_target_information_gain(
    target_sigma: np.ndarray | float,
    measured_sigma: np.ndarray | float,
    correlation: np.ndarray | float,
    observation_sigma: np.ndarray | float,
) -> np.ndarray:
    """Information transferred to one Gaussian target by measuring another.

    ``target`` and ``measured`` have a bivariate Gaussian prior with Pearson
    correlation ``correlation``.  The observation is the measured parameter
    plus independent Gaussian noise.  The result is mutual information between
    the target parameter and that observation, in nats.

    This is deliberately a sensitivity calculation: a correlation must be
    supplied rather than inferred from marginal catalogue uncertainties.
    """

    _positive_finite(target_sigma, "target_sigma")
    measured = _positive_finite(measured_sigma, "measured_sigma")
    noise = _positive_finite(observation_sigma, "observation_sigma")
    rho = np.asarray(correlation, dtype=float)
    if np.any(~np.isfinite(rho)) or np.any(np.abs(rho) > 1):
        raise ValueError("correlation must be finite and lie in [-1, 1]")

    explained_fraction = rho**2 * measured**2 / (measured**2 + noise**2)
    return -0.5 * np.log1p(-explained_fraction)


def gaussian_transfer_break_even_correlation(
    target_information_nats: np.ndarray | float,
    measured_sigma: np.ndarray | float,
    observation_sigma: np.ndarray | float,
) -> np.ndarray:
    """Absolute correlation needed for an indirect measurement to hit a target EIG.

    Values above one mean the target cannot be reached under the declared
    Gaussian measurement model, even with perfect prior correlation.
    """

    target_information = np.asarray(target_information_nats, dtype=float)
    if np.any(~np.isfinite(target_information)) or np.any(target_information < 0):
        raise ValueError("target_information_nats must be finite and non-negative")
    measured = _positive_finite(measured_sigma, "measured_sigma")
    noise = _positive_finite(observation_sigma, "observation_sigma")
    required_explained_fraction = -np.expm1(-2 * target_information)
    return np.sqrt(required_explained_fraction * (measured**2 + noise**2) / measured**2)


def _binary_entropy(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(probability, 1e-15, 1 - 1e-15)
    return -(clipped * np.log(clipped) + (1 - clipped) * np.log(1 - clipped))


def bernoulli_test_information_gain(
    prior_probability: np.ndarray | float,
    *,
    sensitivity: np.ndarray | float,
    specificity: np.ndarray | float,
) -> np.ndarray:
    """Expected information about a binary state from an imperfect binary test."""

    prior = np.asarray(prior_probability, dtype=float)
    true_positive = np.asarray(sensitivity, dtype=float)
    true_negative = np.asarray(specificity, dtype=float)
    for value, name in [
        (prior, "prior_probability"),
        (true_positive, "sensitivity"),
        (true_negative, "specificity"),
    ]:
        if np.any(~np.isfinite(value)) or np.any((value < 0) | (value > 1)):
            raise ValueError(f"{name} must lie in [0, 1]")
    positive_probability = prior * true_positive + (1 - prior) * (1 - true_negative)
    conditional_entropy = prior * _binary_entropy(true_positive) + (1 - prior) * _binary_entropy(
        1 - true_negative
    )
    return _binary_entropy(positive_probability) - conditional_entropy
