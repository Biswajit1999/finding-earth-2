"""Conditional detection probabilities and finite injection statistics.

Calibration must use the same survey, processing release, target selection and
transit criterion. Reliability (candidate purity) is deliberately not an input
to a detection probability. See docs/LITERATURE_V2.md, S2--S4 and S9.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import beta


def probability_array(value, name: str = "probability") -> np.ndarray:
    a = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(a)) or np.any((a < 0) | (a > 1)):
        raise ValueError(f"{name} must contain finite probabilities in [0,1]")
    return a


@dataclass(frozen=True)
class SurveyContract:
    survey: str
    release: str
    target_sample: str
    transit_criterion: str
    calibration: str

    def __post_init__(self) -> None:
        if not all((self.survey, self.release, self.target_sample, self.calibration)):
            raise ValueError(
                "A selection function requires a survey, release, sample and calibration"
            )
        if self.transit_criterion not in {"centre_crossing", "any_overlap"}:
            raise ValueError("Explicit transit criterion required")

    def require_match(self, other: SurveyContract) -> None:
        if self != other:
            raise ValueError("Survey selection contracts do not match")


def detection_probability(
    geometry, pipeline, vetting, *, window=None, pipeline_includes_window: bool = False
) -> np.ndarray:
    """Combine conditional factors once. Recovery over all phases includes window.

    pipeline is P(recovered | transit, window) when a separate window is passed,
    or P(recovered | transit) when pipeline_includes_window=True.
    vetting is P(PC | recovered true injection). No reliability multiplier.
    """
    if pipeline_includes_window and window is not None:
        raise ValueError("Window would be counted twice")
    if not pipeline_includes_window and window is None:
        raise ValueError("A separate window probability is required")
    g, p, v = [probability_array(a) for a in (geometry, pipeline, vetting)]
    w = 1.0 if window is None else probability_array(window, "window")
    return g * p * v * w


def binomial_efficiency(
    successes,
    trials,
    *,
    credible_mass: float = 0.95,
    prior_alpha: float = 0.5,
    prior_beta: float = 0.5,
) -> dict:
    """Beta-binomial inference with an explicit Jeffreys prior by default.

    Empty cells return NaN, not a fabricated 50% detection efficiency. The
    serializer converts NaN to null. Intervals describe injection statistics
    conditional on exchangeable Bernoulli trials; heterogeneity is separate.
    """
    k, n = np.broadcast_arrays(np.asarray(successes, float), np.asarray(trials, float))
    if (
        not np.all(np.isfinite(k))
        or not np.all(np.isfinite(n))
        or np.any(k != np.floor(k))
        or np.any(n != np.floor(n))
        or np.any(k < 0)
        or np.any(n < k)
    ):
        raise ValueError("Binomial counts must be finite integers with 0 <= successes <= trials")
    if not 0 < credible_mass < 1:
        raise ValueError("credible_mass must be between zero and one")
    if not np.isfinite(prior_alpha + prior_beta) or min(prior_alpha, prior_beta) <= 0:
        raise ValueError("Beta prior parameters must be finite and positive")
    a, b = k + prior_alpha, n - k + prior_beta
    tail = (1 - credible_mass) / 2
    return {
        "trials": n.astype(int),
        "successes": k.astype(int),
        "supported": n > 0,
        "mean": np.where(n > 0, a / (a + b), np.nan),
        "lower": np.where(n > 0, beta.ppf(tail, a, b), np.nan),
        "upper": np.where(n > 0, beta.ppf(1 - tail, a, b), np.nan),
        "prior_alpha": prior_alpha,
        "prior_beta": prior_beta,
        "credible_mass": credible_mass,
    }
