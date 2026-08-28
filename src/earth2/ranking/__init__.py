"""Interpretable, reweightable candidate scoring. No black-box habitability model."""

from __future__ import annotations

from earth2.ranking.scores import (
    DEFAULT_WEIGHTS,
    FOLLOWUP_EPOCH_JD,
    MASS_CLASS_QUALITY,
    ScoreWeights,
    angular_separation_mas,
    emission_spectroscopy_metric,
    ephemeris_uncertainty_minutes,
    orbital_separation_au,
    rank_catalogue,
    reflected_light_contrast,
    rocky_plausibility,
    rv_semi_amplitude_ms,
    score_characterisation_potential,
    score_conservative_habitability,
    score_earth_similarity,
    score_observational_confidence,
    transmission_spectroscopy_metric,
)

__all__ = [
    "DEFAULT_WEIGHTS", "FOLLOWUP_EPOCH_JD", "MASS_CLASS_QUALITY", "ScoreWeights",
    "angular_separation_mas", "emission_spectroscopy_metric",
    "ephemeris_uncertainty_minutes", "orbital_separation_au",
    "rank_catalogue", "reflected_light_contrast", "rocky_plausibility",
    "rv_semi_amplitude_ms", "score_characterisation_potential",
    "score_conservative_habitability", "score_earth_similarity",
    "score_observational_confidence", "transmission_spectroscopy_metric",
]
