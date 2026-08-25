"""Interpretable, reweightable candidate scoring. No black-box habitability model."""

from __future__ import annotations

from earth2.ranking.scores import (
    DEFAULT_WEIGHTS,
    MASS_CLASS_QUALITY,
    ScoreWeights,
    emission_spectroscopy_metric,
    rank_catalogue,
    rocky_plausibility,
    rv_semi_amplitude_ms,
    score_characterisation_potential,
    score_conservative_habitability,
    score_earth_similarity,
    score_observational_confidence,
    transmission_spectroscopy_metric,
)

__all__ = [
    "DEFAULT_WEIGHTS", "MASS_CLASS_QUALITY", "ScoreWeights",
    "emission_spectroscopy_metric", "rank_catalogue", "rocky_plausibility",
    "rv_semi_amplitude_ms", "score_characterisation_potential",
    "score_conservative_habitability", "score_earth_similarity",
    "score_observational_confidence", "transmission_spectroscopy_metric",
]
